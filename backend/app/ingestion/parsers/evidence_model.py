"""
Layer 4: Universal Evidence Data Model.
Standardizes parsed content across all specialized source-family parsers
(Document, Structured Data, Conversations, and Metadata) into strongly-typed evidence units.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.db.enums import SourceFamily


class ContentRole(str, Enum):
    """Controlled semantic classification for document blocks and evidence units."""
    POLICY_RULE = "policy_rule"           # Operative normative rule, obligation, entitlement, threshold, matrix
    DEFINITION = "definition"             # Glossary term, lexical definition, "means", "refers to"
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
    FORM_SPECIFICATION = "form_specification" # Form field requirements
    REFERENCE_CITATION = "reference_citation" # Citation of external statutes, regulatory references, or documentation links (non-normative)
    NON_RULE_CONTEXT = "non_rule_context"     # Descriptive prose, background scope, capability, or promotional framing


class ParsedEvidenceUnit(BaseModel):
    """
    Atomic unit of parsed evidence (e.g., a policy clause, a database row, a chat message).
    Preserves exact source locators and native structured data for zero-hallucination grounding.
    """
    unit_id: str = Field(..., description="Deterministic unique identifier for this evidence unit")
    envelope_id: uuid.UUID = Field(..., description="Parent Layer 3 CanonicalSourceEnvelope identifier")
    asset_id: str = Field(..., description="Native external asset identifier")
    block_type: str = Field(..., description="Semantic block type (clause, heading, table_row, record_field, chat_message, metric_rule)")
    content_role: ContentRole = Field(default=ContentRole.POLICY_RULE, description="Classified semantic role of this content unit")
    is_canonical: bool = Field(default=True, description="False if illustrative example, revision log, heading, or contact metadata")
    content_text: str = Field(..., description="Normalized textual representation suitable for candidate claim extraction")
    structured_data: dict[str, Any] = Field(default_factory=dict, description="Pristine native typed values, column schemas, or JSON paths")
    locator: dict[str, Any] = Field(default_factory=dict, description="Fine-grained source-specific locator coordinates")
    hierarchical_context: list[str] = Field(default_factory=list, description="Breadcrumb ancestry (e.g. ['Section 2', 'Clause 2.1'])")
    content_hash: str = Field(..., description="Deterministic SHA-256 hash of this atomic unit")
    sequence_index: int = Field(default=0, description="Order of appearance in the original asset")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Parser-specific extraction metadata")

    # Phase 1: Layer 4 Evidence Contract Extensions
    structure_type: Optional[str] = Field(default=None, description="Layout structure: table_row, prose_clause, list_item, heading")
    table_id: Optional[str] = Field(default=None, description="Table identifier within document")
    row_id: Optional[str] = Field(default=None, description="Row identifier within table")
    column_headers: list[str] = Field(default_factory=list, description="Column headers for tabular units")
    cells: dict[str, str] = Field(default_factory=dict, description="Pristine cell map {col_header: cell_value}")
    parent_context: Optional[str] = Field(default=None, description="Enclosing lead-in paragraph, section intro, or parent rule context")
    section_path: list[str] = Field(default_factory=list, description="Section ancestry path e.g. ['8', 'Refund Methods and Payment Types']")
    char_start: Optional[int] = Field(default=None, description="Physical start offset in document text")
    char_end: Optional[int] = Field(default=None, description="Physical end offset in document text")
    resolved_references: list[dict[str, Any]] = Field(default_factory=list, description="Explicit semantic references e.g. timeline references, cross-references")

    @classmethod
    def create(
        cls,
        envelope_id: uuid.UUID,
        asset_id: str,
        block_type: str,
        content_text: str,
        structured_data: dict[str, Any] | None = None,
        locator: dict[str, Any] | None = None,
        hierarchical_context: list[str] | None = None,
        sequence_index: int = 0,
        metadata: dict[str, Any] | None = None,
        content_role: ContentRole | str | None = None,
        is_canonical: bool | None = None,
        structure_type: str | None = None,
        table_id: str | None = None,
        row_id: str | None = None,
        column_headers: list[str] | None = None,
        cells: dict[str, str] | None = None,
        parent_context: str | None = None,
        section_path: list[str] | None = None,
        char_start: int | None = None,
        char_end: int | None = None,
        resolved_references: list[dict[str, Any]] | None = None,
    ) -> ParsedEvidenceUnit:
        text_clean = (content_text or "").strip()
        data = structured_data or {}
        loc = locator or {}
        hier = hierarchical_context or []

        # Resolve ContentRole
        resolved_role = ContentRole.POLICY_RULE
        if content_role:
            try:
                resolved_role = ContentRole(content_role) if isinstance(content_role, str) else content_role
            except ValueError:
                resolved_role = ContentRole.POLICY_RULE
        elif block_type == "heading":
            resolved_role = ContentRole.HEADING

        # Resolve canonicity: definitions, examples, history, headings, FAQs, intro context are non-canonical
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

        # Derive Phase 1 structured contract fields
        res_char_start = char_start if char_start is not None else (loc.get("start_char") or loc.get("char_start"))
        res_char_end = char_end if char_end is not None else (loc.get("end_char") or loc.get("char_end"))
        res_section_path = section_path if section_path is not None else list(hier)
        res_structure = structure_type or ("table_row" if block_type == "table_row" else ("heading" if block_type == "heading" else ("list_item" if block_type == "clause" else "prose_clause")))
        res_table_id = table_id or data.get("table_id") or loc.get("table_id")
        res_row_id = row_id or data.get("row_id") or (f"{res_table_id}_row_{data.get('row_index')}" if res_table_id and data.get("row_index") is not None else None)
        res_col_headers = column_headers if column_headers is not None else (data.get("table_headers") or data.get("column_headers") or (loc.get("table_grid", {}).get("col_headers") if isinstance(loc.get("table_grid"), dict) else []))
        res_cells = cells if cells is not None else (data.get("columns") or data.get("cells") or {})
        res_refs = resolved_references if resolved_references is not None else (data.get("resolved_references") or [])

        # Calculate unit hash
        hash_input = f"{asset_id}:{block_type}:{resolved_role.value}:{text_clean}:{json.dumps(data, sort_keys=True, default=str)}"
        unit_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
        unit_id = f"{envelope_id}:{sequence_index}:{unit_hash[:12]}"

        return cls(
            unit_id=unit_id,
            envelope_id=envelope_id,
            asset_id=asset_id,
            block_type=block_type,
            content_role=resolved_role,
            is_canonical=resolved_canonical,
            content_text=text_clean,
            structured_data=data,
            locator=loc,
            hierarchical_context=hier,
            content_hash=unit_hash,
            sequence_index=sequence_index,
            metadata=metadata or {},
            structure_type=res_structure,
            table_id=res_table_id,
            row_id=res_row_id,
            column_headers=res_col_headers or [],
            cells=res_cells or {},
            parent_context=parent_context,
            section_path=res_section_path,
            char_start=res_char_start,
            char_end=res_char_end,
            resolved_references=res_refs,
        )


class ParsedEvidenceResult(BaseModel):
    """
    Standard evidence bundle produced by any Layer 4 specialized parser for an envelope.
    Tracks parsing completeness and quality metrics.
    """
    envelope_id: uuid.UUID
    asset_id: str
    source_family: SourceFamily
    parser_name: str
    units: List[ParsedEvidenceUnit] = Field(default_factory=list)
    completeness_score: float = Field(ge=0.0, le=1.0, default=1.0, description="Ratio of asset content successfully parsed without error")
    completeness_ledger: List[dict[str, Any]] = Field(default_factory=list, description="Audit ledger accounting for every unit, operative status, and valid skip reasons")
    quality_metrics: dict[str, Any] = Field(default_factory=dict, description="Parsing fidelity metrics (e.g. tables parsed, char count)")
    parsed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "envelope_id": str(self.envelope_id),
            "asset_id": self.asset_id,
            "source_family": self.source_family.value if hasattr(self.source_family, "value") else str(self.source_family),
            "parser_name": self.parser_name,
            "total_units": len(self.units),
            "completeness_score": self.completeness_score,
            "completeness_ledger": self.completeness_ledger,
            "quality_metrics": self.quality_metrics,
            "parsed_at": self.parsed_at.isoformat(),
            "units": [u.model_dump() for u in self.units],
        }
