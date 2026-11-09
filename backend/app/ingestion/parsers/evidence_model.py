"""
Layer 4: Universal Evidence Data Model.
Standardizes parsed content across all specialized source-family parsers
(Document, Structured Data, Conversations, and Metadata) into strongly-typed,
source-traceable, and deterministic EvidenceUnits.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.db.enums import SourceFamily


class ContentRole(str, Enum):
    """Controlled semantic classification for document blocks and evidence units."""
    POLICY_RULE = "policy_rule"           # Operative normative rule, obligation, entitlement, threshold, matrix
    DEFINITION = "definition"             # Glossary term, lexical definition, "means", "refers to"
    EXCEPTION = "exception"               # Specific carve-out, exclusion, or qualifying condition
    PROCEDURE = "procedure"               # Step-by-step workflow, administrative process, submission instruction
    FAQ = "faq"                           # Frequently asked questions & answers (Q&A pair)
    FAQ_QUESTION = "faq_question"         # Frequently asked question prompt (non-canonical)
    FAQ_ANSWER = "faq_answer"             # Answer to FAQ question
    EXAMPLE = "example"                   # Illustrative worked scenario, hypothetical calculation
    REVISION_HISTORY = "revision_history" # Version changelog, approval metadata, revision table, sign-off block
    HEADING = "heading"                   # Document header, section title, structural outline divider
    CONTACT_INFO = "contact_info"         # Support desk, HR email, contact phone number, address
    INTRODUCTORY_CONTEXT = "introductory_context" # Descriptive preface, non-normative framing
    DOCUMENT_METADATA = "document_metadata" # Document title, author, scope metadata
    SUMMARY = "summary"                   # Executive summary, document synopsis
    FORM_SPECIFICATION = "form_specification" # Form field requirements
    REFERENCE_CITATION = "reference_citation" # Citation of external statutes, regulatory references, or documentation links
    COMMUNICATION = "communication"       # Chat message, email, comment stream, discussion note
    METADATA = "metadata"                 # System/configuration metadata, lineage, telemetry
    UNKNOWN = "unknown"                   # Unclassified, fallback, or ambiguous content role

    @classmethod
    def parse_role(cls, value: Any) -> ContentRole:
        """Resolves role safely without silently converting invalid strings into POLICY_RULE."""
        if value is None:
            return cls.UNKNOWN
        if isinstance(value, cls):
            return value
        val_str = str(value).lower().strip()
        try:
            return cls(val_str)
        except ValueError:
            return cls.UNKNOWN


class ExtractionStatus(str, Enum):
    """Explicit extraction lifecycle state for an atomic evidence unit or extraction quality report."""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    EMPTY = "empty"
    UNSUPPORTED = "unsupported"
    NEEDS_OCR = "needs_ocr"
    # Backward-compatible aliases
    EXTRACTED = "extracted"
    SKIPPED = "skipped"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, ExtractionStatus):
            if self.value in ("success", "extracted") and other.value in ("success", "extracted"):
                return True
            if self.value in ("unsupported", "skipped") and other.value in ("unsupported", "skipped"):
                return True
            return self.value == other.value
        if isinstance(other, str):
            other_lower = other.lower().strip()
            if self.value in ("success", "extracted") and other_lower in ("success", "extracted"):
                return True
            if self.value in ("unsupported", "skipped") and other_lower in ("unsupported", "skipped"):
                return True
            return self.value == other_lower
        return super().__eq__(other)

    def __hash__(self) -> int:
        norm = "success" if self.value in ("success", "extracted") else ("unsupported" if self.value in ("unsupported", "skipped") else self.value)
        return hash(norm)

    @classmethod
    def resolve(cls, value: Any) -> ExtractionStatus:
        """Resolves extraction status safely, normalizing aliases and unrecognized strings."""
        if isinstance(value, cls):
            return value
        if value is None:
            return cls.SUCCESS
        v_str = str(value).lower().strip()
        if v_str in ("success", "extracted"):
            return cls.SUCCESS
        if v_str in ("partial", "partially_extracted"):
            return cls.PARTIAL
        if v_str in ("failed", "failure", "error"):
            return cls.FAILED
        if v_str in ("empty", "no_content"):
            return cls.EMPTY
        if v_str in ("unsupported", "skipped", "ignored"):
            return cls.UNSUPPORTED
        if v_str in ("needs_ocr", "ocr_required"):
            return cls.NEEDS_OCR
        try:
            return cls(v_str)
        except ValueError:
            return cls.FAILED


class StructuralRelationType(str, Enum):
    """Controlled structural relationship types allowed during Layer 4 evidence extraction."""
    PARENT_CHILD = "parent_child"
    SECTION_CONTAINS = "section_contains"
    TABLE_HAS_ROW = "table_has_row"
    ROW_HAS_CELL = "row_has_cell"
    DEFINITION_APPLIES_TO = "definition_applies_to"
    RULE_QUALIFIED_BY = "rule_qualified_by"
    RULE_HAS_EXCEPTION = "rule_has_exception"
    CONTINUES_ON_PAGE = "continues_on_page"
    RECORD_HAS_FIELD = "record_has_field"


class EvidenceRelationship(BaseModel):
    """
    Structural relationship between evidence units.
    Validation relations ('supports', 'contradicts') are strictly forbidden at Layer 4.
    """
    relation_type: StructuralRelationType
    target_unit_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("relation_type", mode="before")
    @classmethod
    def validate_relation_type(cls, v: Any) -> Any:
        v_str = str(getattr(v, "value", v)).lower().strip()
        if "support" in v_str or "contradict" in v_str:
            raise ValueError(
                f"Validation relations ({v_str}) are forbidden in Layer 4 EvidenceUnit relationships. "
                "Validation relations belong to Layer 5 / Layer 6."
            )
        try:
            return StructuralRelationType(v_str)
        except ValueError:
            raise ValueError(
                f"Invalid structural relation type: {v}. Must be one of {[t.value for t in StructuralRelationType]}"
            )


class SourceLocator(BaseModel, Mapping):
    """
    Strongly-typed source locator preserving exact fine-grained coordinates across all source types.
    Emulates a dict (implements collections.abc.Mapping) for seamless backward compatibility.
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    # Document / text coordinates
    page: Optional[int] = Field(default=None, alias="page_number")
    line: Optional[int] = Field(default=None, alias="line_number")
    start_offset: Optional[int] = Field(default=None, alias="start_char")
    end_offset: Optional[int] = Field(default=None, alias="end_char")
    bounding_box: Optional[dict[str, Any]] = None
    section_path: list[str] = Field(default_factory=list, alias="heading_path")

    # Table coordinates
    table_id: Optional[str] = None
    row_index: Optional[int] = None
    column_index: Optional[int] = None
    cell_reference: Optional[str] = None

    # JSON / BSON / hierarchical data
    json_path: Optional[str] = None
    array_index: Optional[int] = None

    # Spreadsheet coordinates
    sheet_name: Optional[str] = None
    cell_coordinate: Optional[str] = None

    # Conversation / chat coordinates
    message_timestamp: Optional[str] = Field(default=None, alias="timestamp")
    thread_id: Optional[str] = None

    # Source control / repository coordinates
    commit_sha: Optional[str] = None
    file_path: Optional[str] = None
    line_range: Optional[str] = None

    # Database coordinates
    database_table: Optional[str] = Field(default=None, alias="table")
    primary_key: Optional[str] = Field(default=None, alias="record_id")
    field_path: Optional[str] = Field(default=None, alias="column")

    _ALIAS_TO_ATTR: dict[str, str] = {
        "page_number": "page",
        "line_number": "line",
        "line_start": "line",
        "line_end": "line",
        "start_char": "start_offset",
        "end_char": "end_offset",
        "heading_path": "section_path",
        "table": "database_table",
        "table_name": "database_table",
        "record_id": "primary_key",
        "column": "field_path",
        "column_name": "field_path",
        "timestamp": "message_timestamp",
    }
    _ATTR_TO_ALIAS: dict[str, str] = {
        "page": "page_number",
        "start_offset": "start_char",
        "end_offset": "end_char",
        "section_path": "heading_path",
        "database_table": "table",
        "primary_key": "record_id",
        "field_path": "column",
        "message_timestamp": "timestamp",
    }

    @property
    def page_number(self) -> Optional[int]:
        return self.page

    @page_number.setter
    def page_number(self, value: Optional[int]) -> None:
        self.page = value

    @property
    def start_char(self) -> Optional[int]:
        return self.start_offset

    @start_char.setter
    def start_char(self, value: Optional[int]) -> None:
        self.start_offset = value

    @property
    def end_char(self) -> Optional[int]:
        return self.end_offset

    @end_char.setter
    def end_char(self, value: Optional[int]) -> None:
        self.end_offset = value

    @property
    def heading_path(self) -> list[str]:
        return self.section_path

    @heading_path.setter
    def heading_path(self, value: list[str]) -> None:
        self.section_path = value

    def to_dict(self) -> dict[str, Any]:
        """Returns standard dict representation including extra fields and aliases for backward compatibility."""
        d = self.model_dump(exclude_none=True)
        if self.__pydantic_extra__:
            d.update(self.__pydantic_extra__)
        for attr, alias in self._ATTR_TO_ALIAS.items():
            if attr in d and alias not in d:
                d[alias] = d[attr]
        return d

    def __getitem__(self, key: str) -> Any:
        if self.__pydantic_extra__ and key in self.__pydantic_extra__:
            return self.__pydantic_extra__[key]
        if hasattr(self, key) and key in type(self).model_fields:
            val = getattr(self, key)
            if val is not None:
                return val
        if key in self._ALIAS_TO_ATTR:
            target = self._ALIAS_TO_ATTR[key]
            val = getattr(self, target, None)
            if val is not None:
                return val
        raise KeyError(key)

    def get(self, key: str, default: Any = None) -> Any:
        try:
            return self[key]
        except KeyError:
            return default

    def __setitem__(self, key: str, value: Any) -> None:
        target = self._ALIAS_TO_ATTR.get(key, key)
        if hasattr(self, target) and target in type(self).model_fields:
            setattr(self, target, value)
        else:
            if self.__pydantic_extra__ is None:
                self.__pydantic_extra__ = {}
            self.__pydantic_extra__[key] = value

    def __contains__(self, key: str) -> bool:
        try:
            self[key]
            return True
        except KeyError:
            return False

    def __iter__(self):
        return iter(self.to_dict())

    def __len__(self):
        return len(self.to_dict())


def compute_content_hash(
    raw_content: str,
    normalized_content: str,
    structured_data: dict[str, Any] | None = None,
) -> str:
    """
    Deterministic SHA-256 hash of content, independent of source occurrence or location.
    Identical content across different locations or assets will share this content_hash.
    """
    basis_text = (normalized_content or raw_content or "").strip()
    data_str = json.dumps(structured_data, sort_keys=True, default=str) if structured_data else ""
    raw = f"{basis_text}|{data_str}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def compute_evidence_id(
    asset_id: str,
    locator: SourceLocator | dict[str, Any] | None,
    block_type: str,
    sequence_index: int = 0,
) -> str:
    """
    Stable logical evidence identity.
    Remains deterministic where the source identity and locator coordinates are stable.
    """
    loc_dict = locator.to_dict() if isinstance(locator, SourceLocator) else (locator or {})
    loc_serialized = json.dumps(loc_dict, sort_keys=True, default=str)
    raw = f"{asset_id}:{block_type}:{loc_serialized}:{sequence_index}".encode("utf-8")
    return f"ev_{hashlib.sha256(raw).hexdigest()[:16]}"


def compute_evidence_instance_id(
    envelope_id: uuid.UUID | str | None,
    asset_id: str,
    evidence_id: str,
    sequence_index: int,
    locator: SourceLocator | dict[str, Any] | None = None,
    instance_salt: str | None = None,
) -> str:
    """
    Unique occurrence identity.
    Guarantees that the same text at two source locations produces distinct evidence_instance_id values.
    """
    env_str = str(envelope_id) if envelope_id else "env"
    loc_dict = locator.to_dict() if isinstance(locator, SourceLocator) else (locator or {})
    loc_serialized = json.dumps(loc_dict, sort_keys=True, default=str)
    raw = f"{env_str}:{asset_id}:{evidence_id}:{sequence_index}:{loc_serialized}"
    if instance_salt:
        raw += f":{instance_salt}"
    return f"inst_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:20]}"


class EvidenceUnit(BaseModel):
    """
    Atomic unit of parsed evidence shared by all Layer 4 parsers and Layer 5 extraction.
    Establishes complete source-traceability, fine-grained coordinates, content roles,
    and structural relationships without hallucination.
    """
    evidence_id: str = Field(..., description="Stable logical evidence identity")
    evidence_instance_id: str = Field(..., description="Unique occurrence identity")
    asset_id: str = Field(..., description="Source asset identity")
    source_id: Optional[str] = Field(default=None, description="Connector or source identity")
    source_version: Optional[str] = Field(default=None, description="Source version when available")
    source_type: Optional[str] = Field(default=None, description="Source type (PDF, DOCX, XLSX, CSV, JSON, database, Slack, GitHub, etc.)")
    block_type: str = Field(..., description="Semantic block type (clause, heading, table_row, record_field, chat_message, etc.)")
    content_role: ContentRole = Field(default=ContentRole.UNKNOWN, description="Classified semantic role of this content unit")
    raw_content: str = Field(default="", description="Original extracted content verbatim")
    normalized_content: str = Field(default="", description="Derived readable content")
    structured_data: dict[str, Any] = Field(default_factory=dict, description="Native structured representation")
    parent_id: Optional[str] = Field(default=None, description="Parent unit identifier")
    related_unit_ids: list[str] = Field(default_factory=list, description="Related unit identifiers")
    relationships: list[EvidenceRelationship] = Field(default_factory=list, description="Structural relationships")
    locator: SourceLocator = Field(default_factory=SourceLocator, description="Validated source location")
    content_hash: str = Field(..., description="Deterministic SHA-256 hash of content, independent of source occurrence")
    is_claim_candidate: bool = Field(default=True, description="True if eligible for claim candidate extraction")
    is_canonical: bool = Field(default=True, description="False if illustrative example, revision log, heading, or metadata")
    is_current: bool = Field(default=True, description="False if obsolete or superseded")
    is_context_only: bool = Field(default=False, description="True if this unit serves solely as contextual reference")
    extraction_status: ExtractionStatus = Field(default=ExtractionStatus.EXTRACTED, description="Extraction lifecycle status")
    extraction_confidence: float = Field(default=1.0, ge=0.0, le=1.0, description="Extraction confidence score")
    warnings: list[str] = Field(default_factory=list, description="Extraction warnings or anomalies")
    parser_version: str = Field(default="1.0.0", description="Parser version")
    normalization_version: str = Field(default="1.0.0", description="Normalization version")

    # Backward compatibility fields
    unit_id: str = Field(default="", description="Legacy identifier alias (mirrors evidence_instance_id)")
    content_text: str = Field(default="", description="Legacy textual representation alias (mirrors normalized_content)")
    envelope_id: Optional[uuid.UUID] = Field(default=None, description="Parent Layer 3 CanonicalSourceEnvelope identifier")
    hierarchical_context: list[str] = Field(default_factory=list, description="Breadcrumb ancestry")
    sequence_index: int = Field(default=0, description="Order of appearance in the original asset")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Parser-specific extraction metadata")

    @field_validator("content_role", mode="before")
    @classmethod
    def _validate_content_role(cls, v: Any) -> ContentRole:
        return ContentRole.parse_role(v)

    @field_validator("locator", mode="before")
    @classmethod
    def _validate_locator(cls, v: Any) -> SourceLocator:
        if isinstance(v, SourceLocator):
            return v
        if isinstance(v, dict):
            return SourceLocator(**v)
        return SourceLocator()

    @field_validator("extraction_status", mode="before")
    @classmethod
    def _validate_extraction_status(cls, v: Any) -> ExtractionStatus:
        if isinstance(v, ExtractionStatus):
            return v
        val_str = str(v).lower().strip() if v else "extracted"
        try:
            return ExtractionStatus(val_str)
        except ValueError:
            return ExtractionStatus.EXTRACTED

    @model_validator(mode="after")
    def _sync_compatibility_and_validation(self) -> EvidenceUnit:
        # Guarantee unit_id and evidence_instance_id synchronization
        if not self.unit_id:
            self.unit_id = self.evidence_instance_id
        # Guarantee normalized_content and content_text synchronization
        if not self.normalized_content and self.content_text:
            self.normalized_content = self.content_text
        if not self.content_text and self.normalized_content:
            self.content_text = self.normalized_content
        # Guarantee raw_content is non-empty if normalized is present
        if not self.raw_content:
            self.raw_content = self.normalized_content or self.content_text
        # Ensure envelope_id is set from source_id if applicable
        if not self.envelope_id and self.source_id:
            try:
                self.envelope_id = uuid.UUID(str(self.source_id))
            except ValueError:
                pass
        return self

    @classmethod
    def create(
        cls,
        envelope_id: uuid.UUID | str | None = None,
        asset_id: str = "",
        block_type: str = "paragraph",
        content_text: str = "",
        structured_data: dict[str, Any] | None = None,
        locator: SourceLocator | dict[str, Any] | None = None,
        hierarchical_context: list[str] | None = None,
        sequence_index: int = 0,
        metadata: dict[str, Any] | None = None,
        content_role: ContentRole | str | None = None,
        is_canonical: bool | None = None,
        raw_content: str | None = None,
        normalized_content: str | None = None,
        source_id: str | None = None,
        source_version: str | None = None,
        source_type: str | None = None,
        parent_id: str | None = None,
        related_unit_ids: list[str] | None = None,
        relationships: list[EvidenceRelationship] | None = None,
        is_claim_candidate: bool | None = None,
        is_current: bool = True,
        is_context_only: bool | None = None,
        extraction_status: ExtractionStatus | str = ExtractionStatus.EXTRACTED,
        extraction_confidence: float = 1.0,
        warnings: list[str] | None = None,
        parser_version: str = "1.0.0",
        normalization_version: str = "1.0.0",
    ) -> EvidenceUnit:
        raw_content_val = raw_content if raw_content is not None else (content_text if content_text is not None else "")
        normalized_content_val = normalized_content if normalized_content is not None else (content_text or "").strip()
        data = structured_data or {}

        # Resolve ContentRole: Unknown roles must remain UNKNOWN (never silently converted to POLICY_RULE)
        if content_role is not None:
            resolved_role = ContentRole.parse_role(content_role)
        elif block_type == "heading":
            resolved_role = ContentRole.HEADING
        else:
            resolved_role = ContentRole.UNKNOWN

        # Resolve canonicity
        if is_canonical is None:
            if resolved_role in (
                ContentRole.DEFINITION,
                ContentRole.EXAMPLE,
                ContentRole.REVISION_HISTORY,
                ContentRole.HEADING,
                ContentRole.CONTACT_INFO,
                ContentRole.FAQ,
                ContentRole.FAQ_QUESTION,
                ContentRole.INTRODUCTORY_CONTEXT,
                ContentRole.DOCUMENT_METADATA,
                ContentRole.FORM_SPECIFICATION,
            ):
                resolved_canonical = False
            else:
                resolved_canonical = True
        else:
            resolved_canonical = is_canonical

        # Resolve claim candidacy: Definitions, FAQs, examples and exceptions remain candidates
        if is_claim_candidate is None:
            if resolved_role in (
                ContentRole.HEADING,
                ContentRole.REVISION_HISTORY,
                ContentRole.CONTACT_INFO,
                ContentRole.DOCUMENT_METADATA,
                ContentRole.REFERENCE_CITATION,
            ):
                resolved_candidate = False
            else:
                resolved_candidate = True
        else:
            resolved_candidate = is_claim_candidate

        # Resolve context-only
        if is_context_only is None:
            if resolved_role in (
                ContentRole.HEADING,
                ContentRole.INTRODUCTORY_CONTEXT,
                ContentRole.DOCUMENT_METADATA,
                ContentRole.REVISION_HISTORY,
                ContentRole.CONTACT_INFO,
            ):
                resolved_context_only = True
            else:
                resolved_context_only = False
        else:
            resolved_context_only = is_context_only

        # Resolve locator
        if locator is None:
            typed_locator = SourceLocator()
        elif isinstance(locator, SourceLocator):
            typed_locator = locator
        elif isinstance(locator, dict):
            typed_locator = SourceLocator(**locator)
        else:
            typed_locator = SourceLocator()

        # Compute deterministic hashes and IDs
        content_h = compute_content_hash(
            raw_content=raw_content_val,
            normalized_content=normalized_content_val,
            structured_data=data,
        )
        ev_id = compute_evidence_id(
            asset_id=asset_id,
            locator=typed_locator,
            block_type=block_type,
            sequence_index=sequence_index,
        )
        ev_inst_id = compute_evidence_instance_id(
            envelope_id=envelope_id,
            asset_id=asset_id,
            evidence_id=ev_id,
            sequence_index=sequence_index,
            locator=typed_locator,
        )

        env_uuid = None
        if envelope_id is not None:
            try:
                env_uuid = envelope_id if isinstance(envelope_id, uuid.UUID) else uuid.UUID(str(envelope_id))
            except ValueError:
                pass

        resolved_source_id = source_id or (str(env_uuid) if env_uuid else (str(envelope_id) if envelope_id else None))

        return cls(
            evidence_id=ev_id,
            evidence_instance_id=ev_inst_id,
            unit_id=ev_inst_id,
            asset_id=asset_id,
            source_id=resolved_source_id,
            source_version=source_version,
            source_type=source_type,
            block_type=block_type,
            content_role=resolved_role,
            raw_content=raw_content_val,
            normalized_content=normalized_content_val,
            content_text=normalized_content_val,
            structured_data=data,
            parent_id=parent_id,
            related_unit_ids=related_unit_ids or [],
            relationships=relationships or [],
            locator=typed_locator,
            content_hash=content_h,
            is_claim_candidate=resolved_candidate,
            is_canonical=resolved_canonical,
            is_current=is_current,
            is_context_only=resolved_context_only,
            extraction_status=extraction_status if isinstance(extraction_status, ExtractionStatus) else ExtractionStatus.resolve(extraction_status),
            extraction_confidence=extraction_confidence,
            warnings=warnings or [],
            parser_version=parser_version,
            normalization_version=normalization_version,
            envelope_id=env_uuid,
            hierarchical_context=hierarchical_context or [],
            sequence_index=sequence_index,
            metadata=metadata or {},
        )


# Backward-compatibility alias: existing code importing ParsedEvidenceUnit gets EvidenceUnit directly
ParsedEvidenceUnit = EvidenceUnit


class ExtractionQualityReport(BaseModel):
    """
    Standardized observability report for Layer 4 extraction quality, completeness,
    validation diagnostics, and source fidelity across all parsers and source types.
    """
    model_config = ConfigDict(extra="ignore")

    status: ExtractionStatus = ExtractionStatus.SUCCESS
    completeness_score: Union[float, str] = Field(
        default="NOT_MEASURED",
        description="Coverage ratio (0.0 to 1.0) when a reliable denominator exists, or 'NOT_MEASURED'"
    )

    # Document & file metrics
    expected_pages: Optional[int] = None
    processed_pages: Optional[int] = None
    expected_blocks: Optional[int] = None
    processed_blocks: Optional[int] = None

    # Table metrics
    detected_tables: Optional[int] = None
    extracted_tables: Optional[int] = None
    expected_table_rows: Optional[int] = None
    extracted_table_rows: Optional[int] = None
    expected_table_cells: Optional[int] = None
    extracted_table_cells: Optional[int] = None

    # Structured data metrics
    expected_csv_rows: Optional[int] = None
    processed_csv_rows: Optional[int] = None
    expected_jsonl_records: Optional[int] = None
    processed_jsonl_records: Optional[int] = None
    expected_records: Optional[int] = None
    processed_records: Optional[int] = None
    expected_fields: Optional[int] = None
    processed_fields: Optional[int] = None

    # OCR metrics
    ocr_pages: Optional[int] = None
    ocr_confidence: Optional[float] = None

    # Evidence unit & locator validation counts
    total_units: int = 0
    valid_evidence_units: int = 0
    valid_source_locators: int = 0

    # Truncation and drop details
    is_truncated: bool = False
    truncation_reason: Optional[str] = None
    dropped_records_count: int = 0

    # Diagnostics
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    unsupported_elements: List[str] = Field(default_factory=list)
    unprocessed_elements: List[str] = Field(default_factory=list)

    # Parser provenance & schema versions
    parser_name: str = ""
    parser_version: str = "1.0.0"
    normalizer_version: str = "1.0.0"
    evidence_schema_version: str = "1.0.0"
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvidenceValidationResult(BaseModel):
    """Structured result of Layer 4 evidence validation rules."""
    model_config = ConfigDict(extra="ignore")

    is_valid: bool = True
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    duplicate_ids: List[str] = Field(default_factory=list)
    missing_locators: List[str] = Field(default_factory=list)
    broken_references: List[str] = Field(default_factory=list)
    unprovenanced_units: List[str] = Field(default_factory=list)
    invalid_status_units: List[str] = Field(default_factory=list)
    mismatched_tables: List[str] = Field(default_factory=list)
    missing_source_fields: List[str] = Field(default_factory=list)


class EvidenceExtractionValidator:
    """Validates structural invariants, source locators, relationships, and provenance for Layer 4 evidence."""

    @classmethod
    def validate(cls, units: List[EvidenceUnit]) -> EvidenceValidationResult:
        result = EvidenceValidationResult()
        seen_instance_ids: set[str] = set()
        all_unit_ids: set[str] = set()

        for u in units:
            inst_id = u.evidence_instance_id or u.unit_id
            if inst_id:
                all_unit_ids.add(inst_id)
            if u.evidence_id:
                all_unit_ids.add(u.evidence_id)

        for idx, u in enumerate(units):
            uid = u.evidence_instance_id or u.unit_id or f"unit_{idx}"

            # 1. Duplicate or missing evidence IDs
            if not u.evidence_id:
                result.errors.append(f"Unit at index {idx} has missing or empty evidence_id")
                result.is_valid = False
            if not u.evidence_instance_id:
                result.errors.append(f"Unit at index {idx} has missing or empty evidence_instance_id")
                result.is_valid = False
            elif u.evidence_instance_id in seen_instance_ids:
                result.duplicate_ids.append(u.evidence_instance_id)
                result.errors.append(f"Duplicate evidence_instance_id detected: '{u.evidence_instance_id}'")
                result.is_valid = False
            if u.evidence_instance_id:
                seen_instance_ids.add(u.evidence_instance_id)

            # 2. Invalid source locators
            loc = u.locator
            has_valid_locator = False
            if loc:
                loc_dict = loc.model_dump() if hasattr(loc, "model_dump") else (loc if isinstance(loc, dict) else {})
                coord_fields = [
                    "page", "line", "line_start", "line_end", "start_char", "end_char", "start_offset", "end_offset",
                    "table_id", "row_index", "column_index", "json_path", "sheet_name", "record_pk",
                    "primary_key", "record_id", "database_table", "table", "container", "database",
                    "field_path", "field_name", "channel", "thread_id", "message_id", "commit_sha",
                    "file_path", "paragraph_index", "property_key", "section_path"
                ]
                def _has_coord_value(v: Any) -> bool:
                    if v is None:
                        return False
                    if isinstance(v, (int, float)):
                        return True
                    if isinstance(v, str):
                        return bool(v.strip())
                    if isinstance(v, (list, dict)):
                        return bool(v)
                    return True

                has_valid_locator = any(_has_coord_value(loc_dict.get(k)) for k in coord_fields)
                for num_key in ("page", "line", "line_start", "line_end", "start_char", "end_char", "start_offset", "end_offset", "row_index", "column_index"):
                    val = loc_dict.get(num_key)
                    if isinstance(val, (int, float)) and val < 0:
                        result.errors.append(f"Unit '{uid}' has negative coordinate {num_key}={val}")
                        result.is_valid = False

            if not has_valid_locator:
                result.missing_locators.append(uid)
                result.errors.append(f"Unit '{uid}' has missing or empty source locator coordinates")
                result.is_valid = False

            # 3. Broken parent-child relationships
            if u.parent_id and u.parent_id not in all_unit_ids:
                result.broken_references.append(f"{uid}->parent:{u.parent_id}")
                result.errors.append(f"Unit '{uid}' has parent_id '{u.parent_id}' that does not exist in evidence units")
                result.is_valid = False

            for rel in getattr(u, "relationships", []):
                target = rel.target_unit_id
                if rel.relation_type == StructuralRelationType.PARENT_CHILD and target not in all_unit_ids:
                    result.broken_references.append(f"{uid}->child:{target}")
                    result.errors.append(f"Unit '{uid}' has parent_child relationship pointing to nonexistent target '{target}'")
                    result.is_valid = False

            # 4. Missing table headers & 5. Mismatched table row widths
            if u.block_type in ("table", "table_row"):
                sd = u.structured_data or {}
                headers = sd.get("table_headers") or sd.get("headers") or []
                if u.block_type == "table" and (not headers or all(not str(h).strip() for h in headers)):
                    result.mismatched_tables.append(uid)
                    result.warnings.append(f"Table unit '{uid}' is missing header definitions")

                if u.block_type == "table_row":
                    cols = sd.get("columns") or {}
                    if headers and len(cols) != len(headers):
                        result.mismatched_tables.append(uid)
                        result.warnings.append(
                            f"Table row unit '{uid}' cell count ({len(cols)}) does not match header count ({len(headers)})"
                        )

            # 6. Missing source fields
            if not u.asset_id:
                result.missing_source_fields.append(f"{uid}:asset_id")
                result.errors.append(f"Unit '{uid}' is missing required asset_id")
                result.is_valid = False

            # 7. Normalized content without raw provenance
            norm_content = (u.normalized_content or u.content_text or "").strip()
            raw_content = (u.raw_content or "").strip()
            if norm_content and not raw_content and not u.structured_data:
                result.unprovenanced_units.append(uid)
                result.warnings.append(f"Unit '{uid}' has normalized content without raw content provenance")

            # 8. Evidence units with invalid extraction status
            if not isinstance(u.extraction_status, ExtractionStatus):
                try:
                    ExtractionStatus(str(u.extraction_status).lower())
                except ValueError:
                    result.invalid_status_units.append(uid)
                    result.errors.append(f"Unit '{uid}' has invalid extraction_status '{u.extraction_status}'")
                    result.is_valid = False

            # 9. Nonexistent unit references
            for rel_id in (u.related_unit_ids or []):
                if rel_id not in all_unit_ids:
                    result.broken_references.append(f"{uid}->related:{rel_id}")
                    result.warnings.append(f"Unit '{uid}' references nonexistent related unit '{rel_id}'")

        if result.errors:
            result.is_valid = False
        return result


class ParsedEvidenceResult(BaseModel):
    """
    Standard evidence bundle produced by any Layer 4 specialized parser for an envelope.
    Tracks parsing completeness, extraction status, and quality metrics.
    """
    model_config = ConfigDict(extra="ignore")

    envelope_id: uuid.UUID
    asset_id: str
    source_family: SourceFamily
    parser_name: str
    units: List[EvidenceUnit] = Field(default_factory=list)
    completeness_score: Union[float, str, None] = Field(
        default="NOT_MEASURED",
        description="Ratio of asset content successfully parsed without error, or 'NOT_MEASURED' if no denominator exists",
    )
    quality_metrics: dict[str, Any] = Field(default_factory=dict, description="Parsing fidelity metrics (e.g. tables parsed, char count)")
    quality_report: Optional[ExtractionQualityReport] = None
    extraction_status: ExtractionStatus = ExtractionStatus.SUCCESS
    parsed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @model_validator(mode="after")
    def sync_report_and_status(self) -> ParsedEvidenceResult:
        if self.quality_report is not None:
            self.extraction_status = self.quality_report.status
            if self.quality_report.completeness_score is not None:
                self.completeness_score = self.quality_report.completeness_score
        else:
            val_res = EvidenceExtractionValidator.validate(self.units)
            status = self.extraction_status
            if len(self.units) == 0:
                status = ExtractionStatus.EMPTY if self.completeness_score in ("NOT_MEASURED", 0.0, None) else ExtractionStatus.FAILED
            elif not val_res.is_valid:
                status = ExtractionStatus.PARTIAL

            valid_locators = sum(1 for u in self.units if u.locator and any(u.locator.model_dump().values()))
            self.quality_report = ExtractionQualityReport(
                status=status,
                completeness_score=self.completeness_score if self.completeness_score is not None else "NOT_MEASURED",
                total_units=len(self.units),
                valid_evidence_units=len(self.units) - len(val_res.duplicate_ids),
                valid_source_locators=valid_locators,
                warnings=list(val_res.warnings),
                errors=list(val_res.errors),
                parser_name=self.parser_name,
            )
            self.extraction_status = status
        return self

    def to_dict(self) -> dict[str, Any]:
        return {
            "envelope_id": str(self.envelope_id),
            "asset_id": self.asset_id,
            "source_family": self.source_family.value if hasattr(self.source_family, "value") else str(self.source_family),
            "parser_name": self.parser_name,
            "total_units": len(self.units),
            "completeness_score": self.completeness_score,
            "extraction_status": self.extraction_status.value if hasattr(self.extraction_status, "value") else str(self.extraction_status),
            "quality_metrics": self.quality_metrics,
            "quality_report": self.quality_report.model_dump() if self.quality_report else None,
            "parsed_at": self.parsed_at.isoformat(),
            "units": [u.model_dump() for u in self.units],
        }
