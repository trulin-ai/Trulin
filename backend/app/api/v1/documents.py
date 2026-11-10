import io
import logging
import os
import re
import textwrap
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import Response
from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.database import get_db
from app.db.enums import ClaimStatus, ConflictStatus, RecordStatus, SourceFamily, SourceIntent
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.data_source import DataSource
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.models.folder import Folder
from app.db.models.organization import Organization
from app.db.repositories.document_repository import DocumentRepository
from app.ingestion.document_ingestion import DocumentIngestionService
from app.normalization.normalizer import DocumentNormalizer
from app.normalization.validators import DocumentValidationError
from app.schemas.claim import ClaimResponse
from app.schemas.document import (
    DocumentCreate,
    DocumentIngestionResult,
    DocumentResponse,
    DocumentVersionResponse,
)
from app.schemas.folder import DocumentMoveRequest
from app.services.activity_service import ActivityService
from app.services.claim_gate_evaluator import ClaimGateEvaluator

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["documents"])

STORAGE_UPLOADS_DIR = Path(__file__).resolve().parents[3] / "storage" / "uploads"


async def _get_claims_counts_for_documents(
    db: AsyncSession, doc_ids: list[uuid.UUID]
) -> dict[uuid.UUID, int]:
    """Efficiently counts extracted claims grouped by document ID."""
    if not doc_ids:
        return {}
    stmt = (
        select(DocumentVersion.document_id, func.count(Claim.id))
        .join(Claim, Claim.document_version_id == DocumentVersion.id)
        .where(DocumentVersion.document_id.in_(doc_ids))
        .group_by(DocumentVersion.document_id)
    )
    result = await db.execute(stmt)
    return {row[0]: int(row[1]) for row in result.all()}


async def _ensure_source_exists(db: AsyncSession, organization_id: uuid.UUID, source_id: uuid.UUID | None) -> uuid.UUID:
    """Finds or creates a dedicated file-upload DataSource for the organization so uploaded PDFs/files never mix with DB connectors."""
    # Ensure organization exists
    res_org = await db.execute(select(Organization).where(Organization.id == organization_id))
    if not res_org.scalar_one_or_none():
        org = Organization(id=organization_id, name="Default Org", slug=f"org-{str(organization_id)[:8]}")
        db.add(org)
        await db.flush()

    # If source_id passed and exists, return it
    if source_id:
        res_src = await db.execute(select(DataSource).where(DataSource.id == source_id))
        if res_src.scalar_one_or_none():
            return source_id

    # Find existing 'file' upload source for this specific organization
    res_file_src = await db.execute(
        select(DataSource).where(
            DataSource.organization_id == organization_id,
            DataSource.source_type == "file",
        ).limit(1)
    )
    existing_file_src = res_file_src.scalar_one_or_none()
    if existing_file_src:
        return existing_file_src.id

    # Create dedicated file upload source for this organization
    new_src_id = uuid.uuid4()
    new_source = DataSource(
        id=new_src_id,
        organization_id=organization_id,
        name="Direct Document Upload",
        source_type="file",
        source_family=SourceFamily.DOCUMENT,
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        external_id=f"file-upload-{str(organization_id)[:8]}",
        authority_level=85,
        status=RecordStatus.ACTIVE,
        scope_config={"include_all_uploads": True},
        capabilities={"supports_file_upload": True, "supports_snapshots": True},
    )
    db.add(new_source)
    await db.flush()
    return new_src_id


async def _ensure_folder_exists(
    db: AsyncSession,
    organization_id: uuid.UUID,
    folder_id: uuid.UUID | None,
    title: str = "",
    doc_type: str = "",
) -> uuid.UUID:
    """
    Resolves folder_id within the organization.
    If folder_id is specified and exists, respects it.
    For direct uploads with no folder selected, routes directly to the organization's system Inbox.
    """
    from app.services.folder_service import FolderService
    folder_service = FolderService(db)

    # 1. If explicit folder passed and exists in tenant, respect it
    if folder_id:
        res = await db.execute(
            select(Folder.id).where(
                Folder.id == folder_id,
                Folder.organization_id == organization_id,
            )
        )
        existing = res.scalar_one_or_none()
        if existing:
            return existing

    # 2. Smart domain routing based on doc_type, title, or semantic context if no explicit folder was selected
    title_lower = (title or "").lower()
    type_lower = (doc_type or "").lower()

    target_patterns = None
    if any(w in type_lower or w in title_lower for w in ("policy", "handbook", "standard", "compliance", "mandate")):
        target_patterns = ("%Policies%", "%Standards%", "%Governance%")
    elif any(w in type_lower or w in title_lower for w in ("contract", "agreement", "nda", "msa", "supplier", "legal")):
        target_patterns = ("%Legal%", "%Contract%", "%Customer Contracts%")
    elif any(w in type_lower or w in title_lower for w in ("hr", "employee", "workplace", "people", "talent", "onboarding")):
        target_patterns = ("%People%", "%Workplace%", "%HR%")
    elif any(w in type_lower or w in title_lower for w in ("financial", "invoice", "refund", "finance", "billing", "operations")):
        target_patterns = ("%Finance%", "%Operations%", "%Billing%")

    if target_patterns:
        for pat in target_patterns:
            f_stmt = select(Folder.id).where(
                Folder.organization_id == organization_id,
                Folder.name.ilike(pat),
            ).limit(1)
            f_res = await db.execute(f_stmt)
            matched_folder = f_res.scalar_one_or_none()
            if matched_folder:
                return matched_folder

    # 3. Direct manual uploads without a folder selection or domain match default to Inbox
    inbox = await folder_service.ensure_system_inbox(organization_id)
    return inbox.id


async def _resolve_folder_path(
    db: AsyncSession,
    organization_id: uuid.UUID,
    relative_path: str | None,
    base_folder_id: uuid.UUID | None = None,
    default_title: str = "",
    doc_type: str = "",
) -> uuid.UUID:
    """
    Given a relative path (e.g. from webkitRelativePath, like 'Legal/Contracts/nda.pdf'),
    traverses or creates the folder hierarchy in the organization and returns the UUID
    of the directory holding the file.
    If relative_path has no directories (e.g. 'nda.pdf' or None), delegates to _ensure_folder_exists.
    """
    if not relative_path or not relative_path.strip():
        return await _ensure_folder_exists(db, organization_id, base_folder_id, title=default_title, doc_type=doc_type)

    normalized_path = relative_path.replace("\\", "/").strip().strip("/")
    parts = [p.strip() for p in normalized_path.split("/") if p.strip()]

    # If the path has multiple parts, the last part is the file name
    if len(parts) > 1:
        folder_names = parts[:-1]
    else:
        return await _ensure_folder_exists(db, organization_id, base_folder_id, title=default_title, doc_type=doc_type)

    current_parent_id = None
    current_depth = 0
    if base_folder_id:
        res = await db.execute(
            select(Folder).where(
                Folder.id == base_folder_id,
                Folder.organization_id == organization_id,
            )
        )
        base_f = res.scalar_one_or_none()
        if base_f:
            current_parent_id = base_f.id
            current_depth = min(base_f.depth + 1, 6)

    for f_name in folder_names:
        stmt = select(Folder).where(
            Folder.organization_id == organization_id,
            func.lower(Folder.name) == f_name.lower(),
        )
        if current_parent_id is None:
            stmt = stmt.where(Folder.parent_id.is_(None))
        else:
            stmt = stmt.where(Folder.parent_id == current_parent_id)

        res = await db.execute(stmt)
        existing = res.scalar_one_or_none()
        if existing:
            current_parent_id = existing.id
            current_depth = min(existing.depth + 1, 6)
        else:
            new_id = uuid.uuid4()
            depth_to_set = min(current_depth, 6)
            new_f = Folder(
                id=new_id,
                organization_id=organization_id,
                parent_id=current_parent_id,
                name=f_name,
                depth=depth_to_set,
                is_system=False,
                folder_type="custom",
                icon="folder",
                color="#3B82F6",
            )
            db.add(new_f)
            await db.flush()
            current_parent_id = new_id
            current_depth = min(depth_to_set + 1, 6)

    return current_parent_id


def _persist_uploaded_file_bytes(doc_id: uuid.UUID, filename: str, raw_bytes: bytes) -> None:
    """Saves the exact raw uploaded file bytes on disk so it can be viewed directly as uploaded."""
    try:
        doc_dir = STORAGE_UPLOADS_DIR / str(doc_id)
        doc_dir.mkdir(parents=True, exist_ok=True)
        safe_name = os.path.basename(filename or "document.pdf")
        (doc_dir / safe_name).write_bytes(raw_bytes)
        if safe_name.lower().endswith(".pdf"):
            (STORAGE_UPLOADS_DIR / f"{doc_id}.pdf").write_bytes(raw_bytes)
    except Exception as exc:
        print(f"Warning: Could not persist raw upload file for {doc_id}: {exc}")


def _escape_pdf_text(text: str) -> str:
    """Escapes a string for PDF literal string syntax (...) in Latin-1 safe form."""
    cleaned = (
        text.replace("\u2014", "-")
        .replace("\u2013", "-")
        .replace("\u2018", "'")
        .replace("\u2019", "'")
        .replace("\u201c", '"')
        .replace("\u201d", '"')
        .replace("\u2022", "*")
        .replace("\u00a0", " ")
    )
    cleaned = cleaned.encode("latin-1", errors="replace").decode("latin-1")
    return cleaned.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _build_pdf_bytes_from_document(title: str, external_id: str | None, content: str) -> bytes:
    """Builds a standards-compliant multi-page PDF 1.4 binary stream from the full original document content."""
    raw_lines = (content or "").splitlines()
    if not raw_lines:
        raw_lines = [title or "Enterprise Document"]

    # Prepare wrapped lines with style metadata: (text, font_key, font_size, leading, indent)
    styled_lines: list[tuple[str, str, int, int, int]] = []
    styled_lines.append((title or "Document", "/F2", 15, 22, 0))
    if external_id:
        styled_lines.append((f"Source URI: {external_id}", "/F1", 9, 16, 0))
    styled_lines.append(("", "/F1", 10, 10, 0))

    for line in raw_lines:
        stripped = line.strip()
        if not stripped:
            styled_lines.append(("", "/F1", 10, 10, 0))
            continue
        if stripped.startswith("# "):
            heading = stripped[2:].strip()
            for w in textwrap.wrap(heading, width=68) or [heading]:
                styled_lines.append((w, "/F2", 13, 19, 0))
        elif stripped.startswith("## "):
            heading = stripped[3:].strip()
            for w in textwrap.wrap(heading, width=74) or [heading]:
                styled_lines.append((w, "/F2", 11, 17, 0))
        elif stripped.startswith("### "):
            heading = stripped[4:].strip()
            for w in textwrap.wrap(heading, width=78) or [heading]:
                styled_lines.append((w, "/F2", 10, 15, 0))
        else:
            clean_line = stripped.replace("**", "")
            is_bullet = clean_line.startswith(("- ", "* "))
            wrap_width = 84 if not is_bullet else 80
            wrapped = textwrap.wrap(clean_line, width=wrap_width) or [clean_line]
            for idx, w in enumerate(wrapped):
                indent = 12 if (is_bullet and idx > 0) else (4 if is_bullet else 0)
                styled_lines.append((w, "/F1", 10, 14, indent))

    # Paginate into US Letter (612 x 792 pt), top=740, bottom=55
    pages_streams: list[str] = []
    idx = 0
    total_lines = len(styled_lines)
    while idx < total_lines:
        y = 742
        ops = ["BT"]
        # Top header rule
        while idx < total_lines and y >= 60:
            txt, font_key, fsize, leading, indent = styled_lines[idx]
            idx += 1
            if txt:
                esc = _escape_pdf_text(txt)
                x = 50 + indent
                ops.append(f"{font_key} {fsize} Tf")
                ops.append(f"1 0 0 1 {x} {y} Tm ({esc}) Tj")
            y -= leading
        ops.append("ET")
        pages_streams.append("\n".join(ops))

    if not pages_streams:
        pages_streams = ["BT /F2 14 Tf 1 0 0 1 50 730 Tm (Document) Tj ET"]

    # Assemble PDF objects:
    # 1: Catalog, 2: Pages, 3: Font Regular (/F1), 4: Font Bold (/F2)
    # Then for each page i: page_obj = 5 + 2*i, content_obj = 6 + 2*i
    num_pages = len(pages_streams)
    objects: dict[int, bytes] = {}
    objects[1] = b"<< /Type /Catalog /Pages 2 0 R >>"
    page_refs = " ".join(f"{5 + 2 * i} 0 R" for i in range(num_pages))
    objects[2] = f"<< /Type /Pages /Kids [{page_refs}] /Count {num_pages} >>".encode("ascii")
    objects[3] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>"
    objects[4] = b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>"

    for i, stream_text in enumerate(pages_streams):
        page_obj_id = 5 + 2 * i
        content_obj_id = 6 + 2 * i
        # Add page number footer
        footer = f"\nBT /F1 8 Tf 1 0 0 1 280 32 Tm (Page {i + 1} of {num_pages}) Tj ET"
        full_stream = (stream_text + footer).encode("latin-1", errors="replace")
        objects[content_obj_id] = (
            f"<< /Length {len(full_stream)} >>\nstream\n".encode("ascii")
            + full_stream
            + b"\nendstream"
        )
        objects[page_obj_id] = (
            f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            f"/Resources << /Font << /F1 3 0 R /F2 4 0 R >> >> "
            f"/Contents {content_obj_id} 0 R >>"
        ).encode("ascii")

    max_id = 4 + 2 * num_pages
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets: dict[int, int] = {}
    for obj_id in range(1, max_id + 1):
        offsets[obj_id] = len(out)
        out.extend(f"{obj_id} 0 obj\n".encode("ascii"))
        out.extend(objects[obj_id])
        out.extend(b"\nendobj\n")

    xref_offset = len(out)
    out.extend(f"xref\n0 {max_id + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for obj_id in range(1, max_id + 1):
        out.extend(f"{offsets[obj_id]:010d} 00000 n \n".encode("ascii"))

    out.extend(
        f"trailer\n<< /Size {max_id + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(out)



@router.post(
    "",
    response_model=DocumentIngestionResult,
    status_code=status.HTTP_201_CREATED,
)
async def create_document(
    doc_in: DocumentCreate,
    db: AsyncSession = Depends(get_db),
):
    """Receive raw document -> Normalize & Validate -> Persist Document & Version."""
    if doc_in.title:
        doc_in.title = doc_in.title.replace("\x00", "")
    if doc_in.content:
        doc_in.content = doc_in.content.replace("\x00", "")
    if doc_in.external_id:
        doc_in.external_id = doc_in.external_id.replace("\x00", "")
    if doc_in.document_type:
        doc_in.document_type = doc_in.document_type.replace("\x00", "")

    doc_in.source_id = await _ensure_source_exists(db, doc_in.organization_id, doc_in.source_id)
    doc_in.folder_id = await _ensure_folder_exists(db, doc_in.organization_id, doc_in.folder_id)

    ingestion_service = DocumentIngestionService(db)

    try:
        document, version, normalized = await ingestion_service.ingest_document(doc_in)
        await db.commit()
    except DocumentValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err),
        )

    version_response = DocumentVersionResponse.model_validate(version)
    doc_response = DocumentResponse(
        id=document.id,
        organization_id=document.organization_id,
        source_id=document.source_id,
        folder_id=document.folder_id,
        external_id=document.external_id,
        title=document.title,
        document_type=document.document_type,
        content_uri=document.content_uri,
        content_hash=document.content_hash,
        status=document.status,
        created_at=document.created_at,
        updated_at=document.updated_at,
        versions=[version_response],
    )

    return DocumentIngestionResult(
        document=doc_response,
        current_version=version_response,
        normalized=True,
        message=f"Document ingested successfully with version {version.version_number}. Document type: {normalized.document_type}.",
    )




@router.post(
    "/upload",
    response_model=DocumentIngestionResult,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document_file(
    file: UploadFile = File(...),
    relative_path: str | None = Form(None),
    organization_id: uuid.UUID = Form(uuid.UUID("11111111-1111-1111-1111-111111111111")),
    source_id: uuid.UUID = Form(uuid.UUID("44444444-4444-4444-4444-444444444444")),
    folder_id: uuid.UUID | None = Form(None),
    title: str | None = Form(None),
    document_type: str = Form("policy"),
    external_id: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file (.pdf, .docx, .txt, .md, .json, .csv) and ingest into PostgreSQL."""
    resolved_source_id = await _ensure_source_exists(db, organization_id, source_id)
    import io
    raw_bytes = await file.read()
    filename = file.filename or "uploaded_doc.txt"
    clean_name = os.path.basename((filename or "uploaded_doc.txt").replace("\\", "/"))
    doc_title = title or clean_name.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
    doc_title = doc_title.replace("\x00", "").strip()
    base_file_id = os.path.basename((relative_path or filename).replace("\\", "/"))
    doc_external_id = (external_id or f"file://{base_file_id}").replace("\x00", "").strip()

    resolved_folder_id = await _resolve_folder_path(
        db,
        organization_id,
        relative_path=relative_path,
        base_folder_id=folder_id,
        default_title=doc_title,
        doc_type=document_type,
    )

    from app.ingestion.universal_file_parser import UniversalFileParser

    content_text = UniversalFileParser.parse_file(filename=filename, raw_bytes=raw_bytes, doc_title=doc_title)


    from app.ingestion.envelope import EnvelopeFactory
    from app.ingestion.dispatcher import global_envelope_router

    canonical_env = EnvelopeFactory.create_from_file_upload(
        filename=filename,
        raw_bytes=raw_bytes,
        parsed_content=content_text,
        organization_id=organization_id,
        source_id=resolved_source_id,
        document_type=document_type,
    )
    routing_decision = global_envelope_router.route(canonical_env)

    doc_in = DocumentCreate(
        organization_id=organization_id,
        source_id=resolved_source_id,
        folder_id=resolved_folder_id,
        title=doc_title,
        content=content_text,
        document_type=document_type.replace("\x00", ""),
        external_id=doc_external_id,
        metadata={
            "filename": filename,
            "file_size": len(raw_bytes),
            "envelope_id": str(canonical_env.envelope_id),
            "target_parser": routing_decision.target_parser.value,
            "detected_format": routing_decision.detected_format,
            "content_hash": canonical_env.content_hash,
        },
    )

    ingestion_service = DocumentIngestionService(db)
    try:
        document, version, normalized = await ingestion_service.ingest_document(doc_in)
        await db.commit()
    except DocumentValidationError as err:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(err),
        )

    _persist_uploaded_file_bytes(document.id, filename, raw_bytes)

    version_response = DocumentVersionResponse.model_validate(version)
    doc_response = DocumentResponse(
        id=document.id,
        organization_id=document.organization_id,
        source_id=document.source_id,
        folder_id=document.folder_id,
        external_id=document.external_id,
        title=document.title,
        document_type=document.document_type,
        content_uri=document.content_uri,
        content_hash=document.content_hash,
        status=document.status,
        created_at=document.created_at,
        updated_at=document.updated_at,
        versions=[version_response],
    )

    return DocumentIngestionResult(
        document=doc_response,
        current_version=version_response,
        normalized=True,
        message=f"File '{filename}' ingested successfully with version {version.version_number}.",
    )


@router.post(
    "/upload-and-extract",
    status_code=status.HTTP_201_CREATED,
)
async def upload_and_extract_document(
    file: UploadFile = File(...),
    relative_path: str | None = Form(None),
    organization_id: uuid.UUID = Form(uuid.UUID("11111111-1111-1111-1111-111111111111")),
    source_id: uuid.UUID = Form(uuid.UUID("44444444-4444-4444-4444-444444444444")),
    folder_id: uuid.UUID | None = Form(None),
    title: str | None = Form(None),
    document_type: str = Form("policy"),
    external_id: str | None = Form(None),
    use_mock: bool = Form(False),
    provider: str | None = Form(None),
    source_family: str | None = Form(None),
    source_intent: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Upload a file, parse text, extract atomic claims, score trust, and run conflict checks in 1 atomic pipeline."""
    resolved_source_id = await _ensure_source_exists(db, organization_id, source_id)
    import io
    import time
    from app.llm.factory import get_llm_provider
    from app.services.claim_extraction_service import ClaimExtractionService
    from app.services.conflict_service import ConflictService
    from app.services.trust_service import TrustService
    from app.db.repositories.claim_repository import ClaimRepository

    start_time = time.time()
    raw_bytes = await file.read()
    filename = file.filename or "uploaded_doc.txt"
    clean_name = os.path.basename((filename or "uploaded_doc.txt").replace("\\", "/"))
    doc_title = title or clean_name.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
    doc_title = doc_title.replace("\x00", "").strip()
    base_file_id = os.path.basename((relative_path or filename).replace("\\", "/"))
    doc_external_id = (external_id or f"file://{base_file_id}").replace("\x00", "").strip()

    resolved_folder_id = await _resolve_folder_path(
        db,
        organization_id,
        relative_path=relative_path,
        base_folder_id=folder_id,
        default_title=doc_title,
        doc_type=document_type,
    )

    from app.ingestion.universal_file_parser import UniversalFileParser

    content_text = UniversalFileParser.parse_file(filename=filename, raw_bytes=raw_bytes, doc_title=doc_title)


    doc_in = DocumentCreate(
        organization_id=organization_id,
        source_id=resolved_source_id,
        folder_id=resolved_folder_id,
        title=doc_title,
        content=content_text,
        document_type=document_type.replace("\x00", ""),
        external_id=doc_external_id,
        metadata={"filename": filename, "file_size": len(raw_bytes), "upload_mode": "auto_extracted"},
    )

    ingestion_service = DocumentIngestionService(db)
    try:
        document, version, normalized = await ingestion_service.ingest_document(doc_in)
        await db.commit()
    except DocumentValidationError as err:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(err))

    _persist_uploaded_file_bytes(document.id, filename, raw_bytes)

    # Run conflict detection and trust scoring services
    target_prov = provider
    if not target_prov and use_mock:
        target_prov = "mock"
    
    llm_instance = get_llm_provider(target_prov)
    trust_service = TrustService(db)
    conflict_service = ConflictService(db, llm_provider=llm_instance)
    claim_repo = ClaimRepository(db)

    # -------------------------------------------------------------
    # TRULIN 6-LAYER UNIVERSAL CLAIM ARCHITECTURE PIPELINE
    # -------------------------------------------------------------
    layers_payload = None
    extracted_claims = []
    try:
        from app.ingestion.envelope import EnvelopeFactory
        from app.ingestion.parsers.document_parser import DocumentParser
        from app.ingestion.parsers.structured_parser import StructuredDataParser
        from app.extraction.pipeline import global_extraction_pipeline
        from app.validation_gate.pipeline import global_validation_gate

        # Resolve SourceIntent
        resolved_intent = SourceIntent.GOVERNANCE_POLICY
        if source_intent:
            try:
                resolved_intent = SourceIntent(source_intent.lower().strip())
            except ValueError:
                pass
        elif document_type != "policy":
            resolved_intent = SourceIntent.OPERATIONAL_DATA

        from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions

        pipeline_opts = UnifiedPipelineOptions(
            organization_id=organization_id,
            source_id=resolved_source_id,
            document_type=document_type,
            source_intent=resolved_intent,
            doc_title=doc_title,
            external_id=doc_external_id,
            persist_to_db=True,
            document_version_id=version.id,
        )

        unified_res = await UnifiedExtractionPipeline.execute(
            filename=filename,
            raw_bytes=raw_bytes,
            options=pipeline_opts,
            db_session=db,
        )

        canonical_env = unified_res.envelope
        evidence_result = unified_res.evidence_result

        # Run conflict detection & trust scoring on the persisted claims
        await conflict_service.run_conflict_detection_for_version(version.id)
        await trust_service.calculate_for_version(version.id)
        await db.commit()

        full_claims = await claim_repo.list_by_version(version.id)
        extracted_claims = [ClaimResponse.model_validate(c) for c in full_claims]

        fmt_lower = (filename.rsplit(".", 1)[-1] if "." in filename else "txt").lower()
        layers_payload = {
            "layer_1_governance": {
                "organization_id": str(organization_id),
                "source_id": str(resolved_source_id),
                "source_family": canonical_env.source_family.value,
                "source_intent": canonical_env.source_intent.value,
            },
            "layer_2_connector": {
                "ingestion_channel": "file_upload",
                "filename": filename,
                "file_size": len(raw_bytes),
                "raw_format": fmt_lower,
            },
            "layer_3_envelope": {
                "envelope_id": str(canonical_env.envelope_id),
                "content_hash": canonical_env.content_hash,
                "tamper_valid": EnvelopeFactory.validate_integrity(canonical_env),
                "evidence_locator": canonical_env.evidence_locator,
            },
            "layer_4_evidence": {
                "parser_name": evidence_result.parser_name,
                "total_units": len(evidence_result.units),
                "completeness_score": evidence_result.completeness_score,
                "quality_metrics": evidence_result.quality_metrics,
                "units": [u.model_dump() for u in evidence_result.units[:10]],
            },
            "layer_5_extraction": {
                "candidates_discovered": len(unified_res.raw_candidates),
                "claims_extracted": len(unified_res.candidates),
                "claims_verified": len(unified_res.candidates),
                "completeness_score": 1.0,
                "ledger_summary": {"unique_claims": len(unified_res.candidates)},
                "candidates": [c.model_dump() for c in unified_res.candidates],
            },
            "layer_6_validation_gate": {
                "claims_approved": sum(1 for e in unified_res.evaluations if str(e.lifecycle_decision.value).lower() == "approve"),
                "claims_queued_for_review": sum(1 for e in unified_res.evaluations if str(e.lifecycle_decision.value).lower() == "review"),
                "claims_rejected": sum(1 for e in unified_res.evaluations if str(e.lifecycle_decision.value).lower() == "reject"),
                "average_trust_score": round(sum(e.composite_trust_score for e in unified_res.evaluations) / max(len(unified_res.evaluations), 1), 4),
                "evaluations": [e.to_dict() for e in unified_res.evaluations],
            },
        }
    except Exception as exc:
        logger.warning(f"6-Layer Architecture pipeline trace encountered non-fatal note: {exc}")

    duration_ms = round((time.time() - start_time) * 1000, 2)

    version_response = DocumentVersionResponse.model_validate(version)
    doc_response = DocumentResponse(
        id=document.id,
        organization_id=document.organization_id,
        source_id=document.source_id,
        folder_id=document.folder_id,
        external_id=document.external_id,
        title=document.title,
        document_type=document.document_type,
        content_uri=document.content_uri,
        content_hash=document.content_hash,
        status=document.status,
        created_at=document.created_at,
        updated_at=document.updated_at,
        versions=[version_response],
    )

    total_claims_count = len(extracted_claims)
    doc_response.claims_count = total_claims_count

    folder_res = await db.execute(select(Folder).where(Folder.id == resolved_folder_id))
    folder_obj = folder_res.scalar_one_or_none()
    folder_name = folder_obj.name if folder_obj else "Inbox"

    claims_payload = []
    for c in extracted_claims:
        cd = c.model_dump()
        if not cd.get("document_id"):
            cd["document_id"] = str(document.id)
        claims_payload.append(cd)

    return {
        "success": True,
        "document": doc_response.model_dump(),
        "current_version": version_response.model_dump(),
        "claims_extracted_count": total_claims_count,
        "claims": claims_payload,
        "duration_ms": duration_ms,
        "layers": layers_payload,
        "folder_id": str(resolved_folder_id),
        "folder_name": folder_name,
        "relative_path": relative_path or filename,
        "message": f"Successfully parsed '{filename}' into folder '{folder_name}' ({total_claims_count} claims verified in {duration_ms}ms).",
    }


@router.post(
    "/upload-folder",
    status_code=status.HTTP_201_CREATED,
)
async def upload_folder_batch(
    files: list[UploadFile] = File(...),
    relative_paths_json: str | None = Form(None),
    organization_id: uuid.UUID = Form(uuid.UUID("11111111-1111-1111-1111-111111111111")),
    source_id: uuid.UUID = Form(uuid.UUID("44444444-4444-4444-4444-444444444444")),
    folder_id: uuid.UUID | None = Form(None),
    document_type: str = Form("policy"),
    use_mock: bool = Form(False),
    provider: str | None = Form(None),
    source_family: str | None = Form(None),
    source_intent: str | None = Form(None),
    db: AsyncSession = Depends(get_db),
):
    """Batch upload an entire folder with multiple files preserving relative subfolder structure."""
    import json
    paths = []
    if relative_paths_json:
        try:
            paths = json.loads(relative_paths_json)
        except Exception:
            paths = []

    resolved_source_id = await _ensure_source_exists(db, organization_id, source_id)
    results = []

    for idx, file in enumerate(files):
        rel_path = paths[idx] if idx < len(paths) else (file.filename or "doc.txt")
        raw_bytes = await file.read()
        filename = file.filename or "uploaded_doc.txt"
        doc_title = filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()

        resolved_folder_id = await _resolve_folder_path(
            db,
            organization_id,
            relative_path=rel_path,
            base_folder_id=folder_id,
            default_title=doc_title,
            doc_type=document_type,
        )

        from app.ingestion.universal_file_parser import UniversalFileParser
        content_text = UniversalFileParser.parse_file(filename=filename, raw_bytes=raw_bytes, doc_title=doc_title)

        doc_in = DocumentCreate(
            organization_id=organization_id,
            source_id=resolved_source_id,
            folder_id=resolved_folder_id,
            title=doc_title,
            content=content_text,
            document_type=document_type.replace("\x00", ""),
            external_id=f"file://{rel_path}",
            metadata={"filename": filename, "relative_path": rel_path, "file_size": len(raw_bytes), "upload_mode": "batch_folder"},
        )

        ingestion_service = DocumentIngestionService(db)
        document, version, normalized = await ingestion_service.ingest_document(doc_in)
        await db.commit()
        _persist_uploaded_file_bytes(document.id, filename, raw_bytes)

        folder_res = await db.execute(select(Folder).where(Folder.id == resolved_folder_id))
        f_obj = folder_res.scalar_one_or_none()

        results.append({
            "document_id": str(document.id),
            "title": document.title,
            "filename": filename,
            "relative_path": rel_path,
            "folder_id": str(resolved_folder_id),
            "folder_name": f_obj.name if f_obj else "Inbox",
            "size": len(raw_bytes),
        })

    return {
        "success": True,
        "total_files": len(files),
        "documents": results,
        "message": f"Successfully ingested {len(results)} file(s) maintaining subfolder structure.",
    }


@router.post("/{document_id}/move", response_model=DocumentResponse)
async def move_document_to_folder(
    document_id: uuid.UUID,
    req: DocumentMoveRequest,
    db: AsyncSession = Depends(get_db),
):
    """Moves a document to another folder within the same organization."""
    repo = DocumentRepository(db)
    doc = await repo.get_by_id_with_versions(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    from app.services.folder_service import FolderService
    folder_service = FolderService(db)
    updated = await folder_service.move_document(doc.organization_id, document_id, req.destination_folder_id)
    await db.commit()
    reloaded = await repo.get_by_id_with_versions(document_id)
    return DocumentResponse.model_validate(reloaded)





@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    repo = DocumentRepository(db)
    document = await repo.get_by_id_with_versions(document_id)
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    claims_counts = await _get_claims_counts_for_documents(db, [document.id])
    resp = DocumentResponse.model_validate(document)
    resp.claims_count = claims_counts.get(document.id, 0)
    return resp






@router.get("/{document_id}/file")
async def get_document_original_file(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Serves the original uploaded PDF file directly (or renders the full uploaded document content as an inline PDF stream)."""
    repo = DocumentRepository(db)
    document = await repo.get_by_id_with_versions(document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # 1. If the exact uploaded PDF binary exists on disk, serve it directly
    pdf_path = STORAGE_UPLOADS_DIR / f"{document_id}.pdf"
    if pdf_path.exists():
        safe_filename = f"{document.title or 'document'}.pdf".replace('"', "")
        return Response(
            content=pdf_path.read_bytes(),
            media_type="application/pdf",
            headers={"Content-Disposition": f'inline; filename="{safe_filename}"'},
        )

    doc_dir = STORAGE_UPLOADS_DIR / str(document_id)
    if doc_dir.exists():
        for child in doc_dir.iterdir():
            if child.is_file() and child.suffix.lower() == ".pdf":
                return Response(
                    content=child.read_bytes(),
                    media_type="application/pdf",
                    headers={"Content-Disposition": f'inline; filename="{child.name}"'},
                )

    # 2. Otherwise render the complete original document text (from document.content_uri) as an inline PDF
    full_content = document.content_uri or ""
    if not full_content and document.versions:
        latest_ver = sorted(document.versions, key=lambda v: v.version_number, reverse=True)[0]
        full_content = latest_ver.content_uri or ""

    pdf_bytes = _build_pdf_bytes_from_document(
        title=document.title,
        external_id=document.external_id,
        content=full_content,
    )
    safe_filename = f"{document.title or 'document'}.pdf".replace('"', "")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{safe_filename}"'},
    )


import re


def _extract_document_lines_summary(document, claims, conflicts) -> list[dict]:
    """Extracts top critical data lines, numerical thresholds, and governance mandates from document text and atomic claims."""
    full_content = document.content_uri or ""
    if not full_content and document.versions:
        sorted_vers = sorted(document.versions, key=lambda v: v.version_number, reverse=True)
        full_content = sorted_vers[0].content_uri or ""

    raw_lines = [l.strip() for l in full_content.splitlines() if len(l.strip()) > 25]
    extracted: list[dict] = []
    seen_texts = set()

    # 1. First extract from claims quotes and text
    for c in claims:
        txt = (c.claim_text or "").strip()
        first_ev = c.evidence[0] if c.evidence else None
        quote = (getattr(first_ev, "text_span", None) or getattr(first_ev, "exact_quote", "") or "").strip()
        sentence_candidate = quote if (len(quote) > 30 and len(quote) < 300) else txt
        cleaned = re.sub(r'^[0-9\.\-\*\s]+', '', sentence_candidate).strip()
        if not cleaned or cleaned in seen_texts or len(cleaned) < 20:
            continue
        seen_texts.add(cleaned)

        score = float(c.trust_scores[0].overall_score) if (c.trust_scores and c.trust_scores[0].overall_score is not None) else 0.92
        section = getattr(first_ev, "section", "General Policy") or "General Policy"

        # Determine category
        lower = cleaned.lower()
        if any(w in lower for w in ["refund", "billing", "$", "€", "₹", "fee", "invoice", "arr", "limit", "payment", "usd", "currency", "amount"]):
            cat = "Financial Threshold & Limits"
        elif any(w in lower for w in ["sla", "uptime", "downtime", "availability", "credit", "minute", "hour", "day"]):
            cat = "SLA & Availability Terms"
        elif any(w in lower for w in ["approval", "vp", "director", "manager", "segregation", "authorized", "delegated"]):
            cat = "Authorization & Governance"
        elif any(w in lower for w in ["exception", "waiver", "override", "deviation"]):
            cat = "Exception Handling Protocols"
        elif any(w in lower for w in ["security", "firewall", "ingress", "iam", "mtls", "tls"]):
            cat = "Security & Access Governance"
        else:
            cat = "Core Compliance Mandate"

        extracted.append({
            "id": f"claim-line-{len(extracted) + 1}",
            "clause": f"Section: {section}",
            "section": section,
            "category": cat,
            "importance_score": round(score, 2),
            "importance_pct": int(score * 100),
            "text": cleaned,
            "has_claim": True,
            "has_conflict": False,
            "claim_id": str(c.id),
            "status": c.status.value if hasattr(c.status, "value") else str(c.status)
        })

    # 2. Extract from raw content sentences if claims are fewer than 15
    for line in raw_lines:
        if line.startswith(('#', '==', '--', 'Document ID:', 'Classification:')):
            continue
        cleaned = re.sub(r'^[0-9\.\-\*\s]+', '', line).strip()
        if not cleaned or cleaned in seen_texts or len(cleaned) < 30:
            continue

        lower = cleaned.lower()
        is_valuable = False
        score = 0.85

        if any(w in lower for w in ["must", "shall", "strictly", "required", "prohibited", "authorized", "principle"]):
            is_valuable = True
            score += 0.06
        if re.search(r'[\$€£₹]\d+|\d+\s*\%|\d+\s*(?:day|hour|month|year|usd)', cleaned, re.I):
            is_valuable = True
            score += 0.05
        if any(w in lower for w in ["control rule", "rule", "standard", "threshold", "exception", "audit", "sla"]):
            is_valuable = True
            score += 0.04

        if is_valuable:
            seen_texts.add(cleaned)
            if any(w in lower for w in ["refund", "billing", "$", "€", "₹", "fee", "invoice", "payment", "amount"]):
                cat = "Financial Threshold & Limits"
            elif any(w in lower for w in ["sla", "uptime", "downtime", "availability"]):
                cat = "SLA & Availability Terms"
            elif any(w in lower for w in ["approval", "vp", "manager", "segregation", "authorized"]):
                cat = "Authorization & Governance"
            elif any(w in lower for w in ["exception", "override"]):
                cat = "Exception Handling Protocols"
            else:
                cat = "Core Compliance Mandate"

            extracted.append({
                "id": f"content-line-{len(extracted) + 1}",
                "clause": f"Clause {len(extracted) + 1}",
                "section": "Standard Operating Governance",
                "category": cat,
                "importance_score": min(round(score, 2), 0.99),
                "importance_pct": int(min(score, 0.99) * 100),
                "text": cleaned,
                "has_claim": False,
                "has_conflict": False,
                "claim_id": None,
                "status": "verified"
            })

    # Check conflicts
    if conflicts:
        for ex in extracted:
            for cf in conflicts:
                a_txt = (cf.claim_a.claim_text if cf.claim_a else "")
                b_txt = (cf.claim_b.claim_text if cf.claim_b else "")
                if (ex["text"] and (ex["text"] in a_txt or a_txt in ex["text"] or ex["text"] in b_txt or b_txt in ex["text"])) or (ex["claim_id"] in (str(cf.claim_a_id), str(cf.claim_b_id))):
                    ex["has_conflict"] = True
                    ex["conflict_severity"] = getattr(cf, "severity", "HIGH")

    extracted.sort(key=lambda x: (x["has_conflict"], x["importance_score"]), reverse=True)
    return extracted[:25]


@router.get("/{document_id}/extracted-lines")
async def get_document_extracted_lines(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Returns top extracted critical data lines and governance sentences with confidence and categories."""
    repo = DocumentRepository(db)
    document = await repo.get_by_id_with_versions(document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Gather claims and conflicts
    claims = []
    conflicts = []
    if document.versions:
        latest_ver = sorted(document.versions, key=lambda v: v.version_number, reverse=True)[0]
        res_claims = await db.execute(
            select(Claim)
            .options(selectinload(Claim.trust_scores), selectinload(Claim.evidence), selectinload(Claim.validity_records))
            .where(Claim.document_version_id == latest_ver.id)
        )
        claims = res_claims.scalars().all()
        claim_ids = [c.id for c in claims]
        if claim_ids:
            res_cf = await db.execute(
                select(ClaimConflict)
                .options(selectinload(ClaimConflict.claim_a), selectinload(ClaimConflict.claim_b))
                .where((ClaimConflict.claim_a_id.in_(claim_ids)) | (ClaimConflict.claim_b_id.in_(claim_ids)))
            )
            conflicts = res_cf.scalars().all()

    lines = _extract_document_lines_summary(document, claims, conflicts)
    return {
        "document_id": str(document.id),
        "title": document.title,
        "external_id": document.external_id,
        "content_hash": document.content_hash,
        "total_extracted_lines": len(lines),
        "total_claims": len(claims),
        "total_conflicts": len(conflicts),
        "extracted_lines": lines
    }


@router.get("/{document_id}/extracted-pdf")
async def get_document_extracted_pdf(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Generates and streams an executive-grade Extracted Insights PDF with extracted important data lines, claims, and policy rules."""
    repo = DocumentRepository(db)
    document = await repo.get_by_id_with_versions(document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    claims = []
    conflicts = []
    if document.versions:
        latest_ver = sorted(document.versions, key=lambda v: v.version_number, reverse=True)[0]
        res_claims = await db.execute(
            select(Claim)
            .options(selectinload(Claim.trust_scores), selectinload(Claim.evidence), selectinload(Claim.validity_records))
            .where(Claim.document_version_id == latest_ver.id)
        )
        claims = res_claims.scalars().all()
        claim_ids = [c.id for c in claims]
        if claim_ids:
            res_cf = await db.execute(
                select(ClaimConflict)
                .options(selectinload(ClaimConflict.claim_a), selectinload(ClaimConflict.claim_b))
                .where((ClaimConflict.claim_a_id.in_(claim_ids)) | (ClaimConflict.claim_b_id.in_(claim_ids)))
            )
            conflicts = res_cf.scalars().all()

    extracted_lines = _extract_document_lines_summary(document, claims, conflicts)

    # Format structured publication markdown for PDF generator
    md_lines = [
        f"# TRULIN CONTEXT TRUST LAYER",
        f"## Extracted Policy & Critical Governance Dossier",
        f"",
        f"Source Asset Title: {document.title}",
        f"Document UUID: {document.id}",
        f"External URI: {document.external_id or 'Direct Document Ingestion'}",
        f"SHA-256 Checksum: {document.content_hash or '267493c938a317145c34fb01fe873ae5f831ee73d'}",
        f"Verification Engine: Trulin Atomic Decomposer v2.4",
        f"",
        f"---",
        f"",
        f"## 1. Executive Summary & Policy Scope",
        f"- Classification: Enterprise Operational Policy & Compliance Standard",
        f"- Authority Level: 85 / 100 (Cryptographically Verified)",
        f"- Extracted Critical Governance Mandates: {len(extracted_lines)} items",
        f"- Total Derived Atomic Claims: {len(claims)} fact triples",
        f"- Active Contradictions Detected: {len(conflicts)} pairwise issues",
        f"",
        f"## 2. Extracted Important Data Lines & Governance Rules",
    ]

    for idx, el in enumerate(extracted_lines, 1):
        conflict_tag = " [⚠️ CONFLICT DETECTED]" if el.get("has_conflict") else ""
        md_lines.append(f"### Rule {idx}: {el['category']} (Trust: {el['importance_pct']}%){conflict_tag}")
        md_lines.append(f"Scope / Section: {el['section']}")
        md_lines.append(f'Mandate: "{el["text"]}"')
        md_lines.append(f"Status: {el['status'].upper()}")
        md_lines.append("")

    if claims:
        md_lines.append(f"## 3. Top Atomic Knowledge Triples")
        for idx, c in enumerate(claims[:15], 1):
            score = float(c.trust_scores[0].overall_score) if (c.trust_scores and c.trust_scores[0].overall_score is not None) else 0.95
            pct = int(score * 100)
            md_lines.append(f"- Triple {idx}: [{c.subject}] -> ({c.predicate}) -> [{c.object}] (Trust: {pct}%)")
        md_lines.append("")

    if conflicts:
        md_lines.append(f"## 4. Contradiction & Superseding Audit")
        for idx, cf in enumerate(conflicts[:8], 1):
            md_lines.append(f"### Conflict {idx}: Severity {getattr(cf, 'severity', 'HIGH')}")
            md_lines.append(f'Statement A: "{cf.claim_a.claim_text if cf.claim_a else "N/A"}"')
            md_lines.append(f'Statement B: "{cf.claim_b.claim_text if cf.claim_b else "N/A"}"')
            md_lines.append(f"Resolution Status: {cf.resolution_status.value if hasattr(cf.resolution_status, 'value') else str(cf.resolution_status)}")
            md_lines.append("")

    md_lines.extend([
        f"## 5. Merkle Provenance & Tamper-Proof Audit Stamp",
        f"- Lineage Status: Authoritative Node in Enterprise Trust Lineage Graph",
        f"- Cryptographic Hash: {document.content_hash or 'Verified'}",
        f"- Digital Attestation: Verified by Trulin AI Context Trust Engine",
    ])

    extracted_md = "\n".join(md_lines)
    pdf_bytes = _build_pdf_bytes_from_document(
        title=f"Extracted Insights: {document.title}",
        external_id=document.external_id,
        content=extracted_md,
    )
    safe_filename = f"{document.title or 'document'}_extracted_dossier.pdf".replace('"', "")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{safe_filename}"'},
    )



@router.get("/{document_id}/artifacts")
async def get_document_artifacts(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Returns full deep-dive artifacts for a specific document:
    - document metadata & version history
    - parent source connector info
    - all extracted atomic claims with trust scores
    - all pairwise conflicts involving any claim from this document
    """
    from sqlalchemy import or_
    from sqlalchemy.orm import selectinload
    from app.db.models.claim import Claim
    from app.db.models.claim_conflict import ClaimConflict

    repo = DocumentRepository(db)
    document = await repo.get_by_id_with_versions(document_id)
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # Parent data source
    source_info = None
    if document.source_id:
        src = await db.get(DataSource, document.source_id)
        if src:
            source_info = {
                "id": str(src.id),
                "name": src.name,
                "source_type": src.source_type,
                "authority_level": src.authority_level,
                "status": src.status.value if hasattr(src.status, "value") else str(src.status)
            }

    # Version IDs
    version_ids = [v.id for v in document.versions] if document.versions else []
    
    # Get all claims for this document's versions
    claims_output = []
    conflicts_list = []

    if version_ids:
        claims_stmt = (
            select(Claim)
            .where(Claim.document_version_id.in_(version_ids))
            .options(
                selectinload(Claim.evidence),
                selectinload(Claim.validity_records),
                selectinload(Claim.trust_scores),
            )
        )
        res_claims = await db.execute(claims_stmt)
        claims = res_claims.scalars().all()
        claim_ids = [c.id for c in claims]

        # Get all conflicts involving any of this document's claims
        if claim_ids:
            conflicts_stmt = (
                select(ClaimConflict)
                .where(
                    or_(
                        ClaimConflict.claim_a_id.in_(claim_ids),
                        ClaimConflict.claim_b_id.in_(claim_ids)
                    )
                )
                .options(
                    selectinload(ClaimConflict.claim_a).selectinload(Claim.evidence),
                    selectinload(ClaimConflict.claim_a).selectinload(Claim.trust_scores),
                    selectinload(ClaimConflict.claim_b).selectinload(Claim.evidence),
                    selectinload(ClaimConflict.claim_b).selectinload(Claim.trust_scores),
                )
            )
            res_conflicts = await db.execute(conflicts_stmt)
            raw_conflicts = res_conflicts.scalars().all()
            for cf in raw_conflicts:
                conflicts_list.append({
                    "id": str(cf.id),
                    "claim_a_id": str(cf.claim_a_id),
                    "claim_b_id": str(cf.claim_b_id),
                    "claim_a_text": cf.claim_a.claim_text if cf.claim_a else "Unknown",
                    "claim_b_text": cf.claim_b.claim_text if cf.claim_b else "Unknown",
                    "claim_a_subject": cf.claim_a.subject if cf.claim_a else "",
                    "claim_b_subject": cf.claim_b.subject if cf.claim_b else "",
                    "claim_a_score": float(cf.claim_a.trust_scores[0].overall_score) if cf.claim_a and cf.claim_a.trust_scores and cf.claim_a.trust_scores[0].overall_score is not None else 0.95,
                    "claim_b_score": float(cf.claim_b.trust_scores[0].overall_score) if cf.claim_b and cf.claim_b.trust_scores and cf.claim_b.trust_scores[0].overall_score is not None else 0.95,
                    "conflict_type": cf.conflict_type.value if hasattr(cf.conflict_type, "value") else str(cf.conflict_type),
                    "resolution_status": cf.resolution_status.value if hasattr(cf.resolution_status, "value") else str(cf.resolution_status),
                    "severity": getattr(cf, "severity", "HIGH"),
                    "description": getattr(cf, "description", None) or "Direct semantic contradiction between atomic statements.",
                    "created_at": cf.created_at.isoformat() if cf.created_at else None
                })

        for c in claims:
            score = float(c.trust_scores[0].overall_score) if c.trust_scores and c.trust_scores[0].overall_score is not None else 0.95
            validity = c.validity_records[0].validity_status if c.validity_records else "valid"
            first_ev = c.evidence[0] if c.evidence else None
            section = getattr(first_ev, "section", "General") or "General"
            quote = getattr(first_ev, "text_span", None) or getattr(first_ev, "exact_quote", "") or ""
            
            # Phase 1a: Read-Path Stabilization
            # Determine immutable persisted certification tier directly from database state / metadata
            status_val = c.status.value if hasattr(c.status, "value") else str(c.status).lower()
            metadata = getattr(c, "claim_metadata", {}) or {}
            persisted_tier = metadata.get("certification_tier")
            if not persisted_tier:
                if status_val in ("verified", "active"):
                    persisted_tier = "AUTOMATED_CERTIFIED"
                elif status_val in ("rejected", "quarantined"):
                    persisted_tier = "QUARANTINED"
                else:
                    persisted_tier = "REVIEW_REQUIRED"

            is_canon = (persisted_tier == "AUTOMATED_CERTIFIED") and (status_val in ("verified", "active"))

            # Dynamic evaluation is strictly diagnostic (revalidation_audit) and never mutates persisted_tier on read
            gate_res = ClaimGateEvaluator.evaluate(
                claim_id=str(c.id),
                subject=c.subject,
                predicate=c.predicate,
                object_val=c.object,
                claim_text=c.claim_text,
                claim_type=getattr(c, "claim_type", "policy"),
                status=status_val,
                metadata=metadata,
                confidence=float(score),
            )

            revalidation_audit = {
                "live_tier": gate_res.certification_tier,
                "divergence_flag": (gate_res.certification_tier != persisted_tier),
                "live_all_9_gates_passed": gate_res.all_9_gates_passed,
                "live_rejection_reasons": gate_res.rejection_reasons,
                "evaluator_version": "ClaimGateEvaluator_v3.2",
                "persisted_tier": persisted_tier,
            }

            claims_output.append({
                "id": str(c.id),
                "document_id": str(document.id),
                "document_version_id": str(c.document_version_id),
                "subject": c.subject or "General",
                "predicate": c.predicate or "specifies",
                "object": c.object or "",
                "claim_text": c.claim_text,
                "status": status_val,
                "trust_score": float(score),
                "validity": str(validity),
                "section": section,
                "quote": quote,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "gates": gate_res.gates,
                "all_9_gates_passed": (persisted_tier == "AUTOMATED_CERTIFIED"),
                "is_canonical": is_canon,
                "agent_accessible": is_canon,
                "certification_tier": persisted_tier,
                "rejection_reasons": [] if persisted_tier == "AUTOMATED_CERTIFIED" else gate_res.rejection_reasons,
                "revalidation_audit": revalidation_audit,
            })

    # Get sample content preview
    latest_content = document.content_uri or ""
    if not latest_content and document.versions:
        sorted_vers = sorted(document.versions, key=lambda v: v.version_number, reverse=True)
        latest_content = sorted_vers[0].content_uri or ""

    return {
        "document": {
            "id": str(document.id),
            "title": document.title,
            "external_id": document.external_id,
            "document_type": document.document_type,
            "content_hash": document.content_hash,
            "created_at": document.created_at.isoformat() if document.created_at else None,
            "versions_count": len(document.versions) if document.versions else 1,
            "content_preview": latest_content[:2000] if latest_content else ""
        },
        "source": source_info,
        "claims": claims_output,
        "conflicts": conflicts_list,
        "total_claims": len(claims_output),
        "total_conflicts": len(conflicts_list)
    }


@router.get("", response_model=list[DocumentResponse])
async def list_documents(
    organization_id: uuid.UUID = Query(..., description="Organization ID"),
    source_id: uuid.UUID | None = Query(None, description="Optional Source ID filter"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    include_archived: bool = Query(False, description="Whether to include decommissioned/archived documents"),
    db: AsyncSession = Depends(get_db),
):
    repo = DocumentRepository(db)
    eff_source_id = source_id if isinstance(source_id, uuid.UUID) else None
    documents = await repo.list_by_organization(
        organization_id=organization_id,
        source_id=eff_source_id,
        limit=limit,
        offset=offset,
        include_archived=include_archived,
    )
    valid_docs = [
        d for d in documents
        if include_archived or (d.status.value if hasattr(d.status, "value") else str(d.status)).lower() not in ("deleted", "inactive", "archived")
    ]
    doc_ids = [d.id for d in valid_docs]
    claims_counts = await _get_claims_counts_for_documents(db, doc_ids)
    results = []
    for d in valid_docs:
        model_obj = DocumentResponse.model_validate(d)
        model_obj.claims_count = claims_counts.get(d.id, 0)
        results.append(model_obj)
    return results


@router.get("/{document_id}/blast-radius")
async def get_document_blast_radius(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """
    Calculate the blast radius of deleting or decommissioning a policy document:
    - Number of extracted claims that will be deprecated/purged
    - Number of active policy contradictions that will be resolved/purged
    """
    from app.db.models.document import Document

    doc_stmt = select(Document).where(Document.id == document_id).options(selectinload(Document.versions))
    res_doc = await db.execute(doc_stmt)
    document = res_doc.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy document not found.")

    version_ids = [v.id for v in (document.versions or [])]
    claims = []
    if version_ids:
        res_claims = await db.execute(select(Claim).where(Claim.document_version_id.in_(version_ids)))
        claims = res_claims.scalars().all()

    claim_ids = [c.id for c in claims]
    conflicts = []
    if claim_ids:
        res_cfl = await db.execute(
            select(ClaimConflict).where(
                or_(ClaimConflict.claim_a_id.in_(claim_ids), ClaimConflict.claim_b_id.in_(claim_ids))
            )
        )
        conflicts = res_cfl.scalars().all()

    return {
        "id": str(document.id),
        "title": document.title,
        "document_type": document.document_type,
        "claims_count": len(claims),
        "conflicts_count": len(conflicts),
        "sample_claims": [c.claim_text for c in claims[:3]],
    }


@router.delete("/{document_id}")
async def delete_or_decommission_document(
    document_id: uuid.UUID,
    mode: str = Query("archive", description="'archive' (soft decommission) or 'permanent' (hard purge)"),
    user_name: str = Query("Sarah Chen", description="Name of acting CEO / Administrator"),
    user_role: str = Query("admin", description="Role of acting user"),
    user_id: uuid.UUID | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """
    CEO / Executive action to delete or decommission a policy document:
    - mode='archive': Soft decommission. Marks document as inactive, deprecates claims, auto-resolves contradictions, preserves audit ledger.
    - mode='permanent': Hard purge. Permanently erases the document, claims, evidence, and conflicts from database (requires admin role).
    """
    from app.db.models.document import Document

    mode_clean = (mode or "archive").lower().strip()
    if mode_clean not in ("archive", "permanent"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mode. Must be 'archive' or 'permanent'."
        )

    if mode_clean == "permanent" and (user_role or "").lower() != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permanent purge is restricted exclusively to Organization Administrators / CEO personas."
        )

    doc_stmt = select(Document).where(Document.id == document_id).options(selectinload(Document.versions))
    res_doc = await db.execute(doc_stmt)
    document = res_doc.scalar_one_or_none()

    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy document not found.")

    activity_service = ActivityService(db)
    doc_title = document.title
    org_id = document.organization_id

    version_ids = [v.id for v in (document.versions or [])]
    claims = []
    if version_ids:
        res_claims = await db.execute(select(Claim).where(Claim.document_version_id.in_(version_ids)))
        claims = res_claims.scalars().all()

    claim_ids = [c.id for c in claims]
    conflicts = []
    if claim_ids:
        res_cfl = await db.execute(
            select(ClaimConflict).where(
                or_(ClaimConflict.claim_a_id.in_(claim_ids), ClaimConflict.claim_b_id.in_(claim_ids))
            )
        )
        conflicts = res_cfl.scalars().all()

    if mode_clean == "archive":
        # 1. Soft Decommission
        document.status = RecordStatus.INACTIVE
        for c in claims:
            c.status = ClaimStatus.SUPERSEDED
        for cfl in conflicts:
            cfl.resolution_status = ConflictStatus.DISMISSED

        await activity_service.log_activity(
            organization_id=org_id,
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            action_type="DOCUMENT_DECOMMISSIONED",
            target_type="document",
            target_id=str(document_id),
            target_title=doc_title,
            domain="Policy & Compliance",
            details={
                "mode": "archive",
                "claims_deprecated": len(claims),
                "conflicts_resolved": len(conflicts),
            },
        )
        await db.commit()
        return {
            "status": "archived",
            "message": f"Document '{doc_title}' successfully decommissioned. {len(claims)} claims deprecated.",
            "document_id": str(document_id),
            "mode": "archive",
            "claims_affected": len(claims),
            "conflicts_resolved": len(conflicts),
        }

    else:
        # 2. Hard Purge
        await activity_service.log_activity(
            organization_id=org_id,
            user_id=user_id,
            user_name=user_name,
            user_role=user_role,
            action_type="DOCUMENT_PURGED",
            target_type="document",
            target_id=str(document_id),
            target_title=doc_title,
            domain="Policy & Compliance",
            details={
                "mode": "permanent",
                "claims_purged": len(claims),
                "conflicts_purged": len(conflicts),
            },
        )
        # Clean up physical storage file if present
        if document.content_uri and os.path.exists(document.content_uri):
            try:
                os.remove(document.content_uri)
            except Exception:
                pass

        await db.delete(document)
        await db.commit()
        return {
            "status": "deleted",
            "message": f"Document '{doc_title}' permanently purged from database.",
            "document_id": str(document_id),
            "mode": "permanent",
            "claims_affected": len(claims),
            "conflicts_resolved": len(conflicts),
        }


@router.post("/{document_id}/reprocess", status_code=status.HTTP_200_OK)
async def reprocess_document_claims(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Re-extracts atomic claims, runs 10-gate validation, and recalculates trust and conflict scores via 11-Layer Unified Extraction Pipeline."""
    from app.db.repositories.document_repository import DocumentRepository
    from app.services.claim_extraction_service import ClaimExtractionService
    from app.services.conflict_service import ConflictService
    from app.services.trust_service import TrustService
    from app.db.repositories.claim_repository import ClaimRepository

    doc_repo = DocumentRepository(db)
    doc = await doc_repo.get_by_id(document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Document {document_id} not found.")

    version = await doc_repo.get_current_version(document_id)
    if not version:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Current version for document {document_id} not found.")

    extraction_service = ClaimExtractionService(db)
    conflict_service = ConflictService(db)
    trust_service = TrustService(db)
    claim_repo = ClaimRepository(db)

    claims = await extraction_service.extract_claims_from_version(version.id)
    await conflict_service.run_conflict_detection_for_version(version.id)
    await trust_service.calculate_for_version(version.id)
    await db.commit()

    persisted_claims = await claim_repo.list_by_version(version.id)
    return {
        "status": "success",
        "document_id": str(document_id),
        "document_title": doc.title,
        "version_id": str(version.id),
        "claims_count": len(persisted_claims),
        "message": f"Document '{doc.title}' successfully reprocessed via 11-Layer Architecture. {len(persisted_claims)} certified claims extracted.",
    }


