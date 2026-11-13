import asyncio
import hashlib
import logging
import uuid
from typing import Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.enums import ClaimStatus
from app.db.models.claim import Claim
from app.db.models.claim_evidence import ClaimEvidence
import decimal
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.claim_validity import ClaimValidity
from app.db.models.document_version import DocumentVersion
from app.db.repositories.claim_repository import ClaimRepository
from app.db.repositories.document_repository import DocumentRepository
from app.ingestion.grounding_verifier import GroundingVerifier
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider
from app.normalization.normalizer import DocumentNormalizer

logger = logging.getLogger(__name__)


class ClaimExtractionService:
    """Hybrid Local-First Claim Extraction & Python Grounding Verification Service.
    
    1. Pre-filters empty/noisy sections deterministically.
    2. Uses Ollama/configured LLM with structured schema outputs.
    3. Runs Python GroundingVerifier: validates exact evidence in source document,
       computes SHA-256 hashes, exact character offsets, and verifies numerical integrity.
    4. Enforces canonical deduplication and persists verified claims into PostgreSQL.
    """

    def __init__(
        self,
        session: AsyncSession,
        llm_provider: BaseLLMProvider | None = None,
    ):
        self.session = session
        self.doc_repo = DocumentRepository(session)
        self.claim_repo = ClaimRepository(session)
        self.normalizer = DocumentNormalizer()
        self.llm = llm_provider or get_llm_provider()
        self.semaphore = asyncio.Semaphore(getattr(settings, "extraction_max_concurrency", 2))

    @staticmethod
    def calculate_evidence_hash(text_span: str) -> str:
        return hashlib.sha256(text_span.encode("utf-8")).hexdigest()

    async def extract_claims_from_version(
        self,
        document_version_id: uuid.UUID,
    ) -> Sequence[Claim]:
        # 1. Fetch document version and parent document
        version = await self.session.get(DocumentVersion, document_version_id)
        if not version:
            raise ValueError(f"Document version {document_version_id} not found.")

        doc = await self.doc_repo.get_by_id(version.document_id)
        if not doc:
            raise ValueError(f"Parent document for version {document_version_id} not found.")

        raw_text = version.content_uri or ""

        # -------------------------------------------------------------
        # TRULIN 11-LAYER UNIVERSAL CLAIM ARCHITECTURE PIPELINE
        # -------------------------------------------------------------
        try:
            from app.db.enums import SourceFamily, SourceIntent
            from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions

            is_thread = (
                doc.document_type in ("communication", "slack_message")
                or (doc.metadata and isinstance(doc.metadata, dict) and doc.metadata.get("thread_ts"))
            )
            resolved_family = SourceFamily.CONVERSATION if is_thread else SourceFamily.DOCUMENT
            doc_type_clean = str(doc.document_type or "policy").lower().strip()
            is_governance = any(k in doc_type_clean for k in ("policy", "standard", "handbook", "guideline", "manual", "compliance", "terms", "sop", "governance"))
            resolved_intent = (
                SourceIntent.GOVERNANCE_POLICY
                if is_governance
                else SourceIntent.OPERATIONAL_DATA
            )
            doc_filename = (
                (doc.metadata.get("filename") if (doc.metadata and isinstance(doc.metadata, dict)) else None)
                or f"{doc.title}.md"
            )

            pipeline_opts = UnifiedPipelineOptions(
                organization_id=doc.organization_id,
                source_id=doc.source_id,
                document_type=doc.document_type or "document",
                source_intent=resolved_intent,
                source_family=resolved_family,
                doc_title=doc.title,
                external_id=doc.external_id,
                persist_to_db=True,
                document_version_id=version.id,
                parsed_content=raw_text,
            )

            await UnifiedExtractionPipeline.execute(
                filename=doc_filename,
                raw_bytes=raw_text.encode("utf-8"),
                options=pipeline_opts,
                db_session=self.session,
                parsed_content=raw_text,
            )
            await self.session.flush()

            persisted_claims = await self.claim_repo.list_by_version(version.id)
            if persisted_claims:
                logger.info(
                    "UnifiedExtractionPipeline (11-Layer) extracted and verified %d claims for version %s",
                    len(persisted_claims),
                    document_version_id,
                )
                return persisted_claims
        except Exception as exc:
            logger.warning(
                "UnifiedExtractionPipeline encountered note for version %s (%s). Falling back to section extractor.",
                document_version_id,
                exc,
            )

        normalized = self.normalizer.normalize(
            document_id=doc.id,
            document_version_id=version.id,
            title=doc.title,
            raw_text=raw_text,
        )

        # 2. Extract sections with pre-filtering and concurrency throttle
        async def _extract_section(section):
            scrubbed_content = self.normalizer.scrub_noise(section.content)
            if not scrubbed_content.strip():
                scrubbed_content = section.content

            # Deterministic Pre-filter: skip obvious non-assertive noise sections
            if not GroundingVerifier.needs_claim_extraction(scrubbed_content):
                logger.debug("Skipping non-assertive section '%s' via deterministic pre-filter", section.title)
                from app.llm.schemas import ClaimExtractionResult
                return section, ClaimExtractionResult(claims=[], extraction_model=self.llm.model if hasattr(self.llm, "model") else "prefilter")

            sec_display = section.title or "General"
            qualified_sec_title = f"{doc.title} > {sec_display}" if sec_display != "General" else doc.title

            async with self.semaphore:
                result = await self.llm.extract_claims(
                    document_title=doc.title,
                    section_title=qualified_sec_title,
                    section_content=scrubbed_content,
                )
                return section, result

        section_results = await asyncio.gather(
            *[_extract_section(s) for s in normalized.sections],
            return_exceptions=False,
        )

        extracted_claim_records: list[Claim] = []
        claim_cache: dict[str, Claim] = {}
        require_evidence_match = getattr(settings, "extraction_require_evidence_match", True)
        require_numeric_grounding = getattr(settings, "extraction_require_numeric_grounding", True)

        # 3. Python Grounding Verification, Deduplication & Database Persistence
        for section, result in section_results:
            for item in result.claims:
                # 3a. Deterministic Grounding & Evidence Offset Verification in Python
                verification = GroundingVerifier.verify_and_ground_claim(
                    claim=item,
                    source_text=raw_text,
                    section_start_offset=section.start_char_offset,
                    require_numeric_grounding=require_numeric_grounding,
                )

                if not verification.is_valid:
                    if require_evidence_match:
                        logger.warning(
                            "Dropping ungrounded candidate claim '%s': %s",
                            item.claim_text[:60],
                            verification.rejection_reason,
                        )
                        continue

                # 3b. Multi-factor Canonical Matching Keys
                norm_text_key = " ".join(item.claim_text.strip().lower().split())
                sub_clean = (item.subject or "").strip().lower()
                pred_clean = (item.predicate or "").strip().lower()
                obj_clean = (item.object or "").strip().lower()
                spo_key = f"{sub_clean}::{pred_clean}::{obj_clean}" if (sub_clean and pred_clean) else None

                num_key = None
                if item.numeric_value is not None and sub_clean and pred_clean:
                    num_key = f"{sub_clean}::{pred_clean}::{item.numeric_value}::{item.numeric_unit or ''}"

                # 3c. Check canonical deduplication cache
                claim = (
                    claim_cache.get(norm_text_key)
                    or (claim_cache.get(spo_key) if spo_key else None)
                    or (claim_cache.get(num_key) if num_key else None)
                )

                if not claim:
                    claim = Claim(
                        organization_id=doc.organization_id,
                        document_version_id=version.id,
                        claim_text=item.claim_text,
                        subject=item.subject[:255] if item.subject else None,
                        predicate=item.predicate[:255] if item.predicate else None,
                        object=item.object,
                        claim_type=item.claim_type[:50] if item.claim_type else "policy",
                        extraction_method=result.extraction_method,
                        extraction_model=result.extraction_model,
                        status=ClaimStatus.ACTIVE,
                    )
                    self.session.add(claim)
                    await self.session.flush()
                    await self.session.refresh(claim)

                    # Register canonical cache keys
                    claim_cache[norm_text_key] = claim
                    if spo_key:
                        claim_cache[spo_key] = claim
                    if num_key:
                        claim_cache[num_key] = claim

                    extracted_claim_records.append(claim)

                    validity = ClaimValidity(
                        claim_id=claim.id,
                        valid_from=item.valid_from,
                        valid_until=item.valid_until,
                        version=str(version.version_number),
                        is_current=version.is_current,
                        validity_status="active" if version.is_current else "outdated",
                    )
                    self.session.add(validity)

                    # Initial Claim Trust Score calculation
                    base_conf = decimal.Decimal(str(round(verification.verified_confidence, 4)))
                    ts = ClaimTrustScore(
                        claim_id=claim.id,
                        source_score=decimal.Decimal("0.9500"),
                        freshness_score=decimal.Decimal("1.0000"),
                        evidence_score=base_conf,
                        consistency_score=decimal.Decimal("0.9500"),
                        authority_score=decimal.Decimal("0.9500"),
                        human_score=decimal.Decimal("0.0000"),
                        overall_score=base_conf,
                    )
                    self.session.add(ts)

                # 3d. Always attach verified Direct Quote Evidence
                evidence_text = verification.verified_evidence_text or item.evidence_text_span or item.claim_text
                evidence = ClaimEvidence(
                    claim_id=claim.id,
                    document_id=doc.id,
                    evidence_type="direct_quote",
                    section=section.title,
                    text_span=evidence_text,
                    start_offset=verification.start_offset,
                    end_offset=verification.end_offset,
                    evidence_hash=verification.evidence_hash or self.calculate_evidence_hash(evidence_text),
                    page_number=section.page_number or 1,
                )
                self.session.add(evidence)

        await self.session.flush()
        logger.info(
            "ClaimExtractionService finished: %d grounded claims saved for version %s",
            len(extracted_claim_records),
            document_version_id,
        )
        return extracted_claim_records
