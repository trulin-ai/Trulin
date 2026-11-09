"""
Layer 5: Universal Candidate Claim & Verification Models.
Defines strongly-typed representations for candidate claims, extraction strategies,
verification plugin outcomes, and completeness ledger entries.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional

from pydantic import BaseModel, Field

from app.ingestion.parsers.evidence_model import ContentRole


class ExtractionStrategyType(str, Enum):
    """Extraction strategy assigned to candidate evidence units."""
    DETERMINISTIC_SCHEMA = "deterministic_schema"  # Zero-hallucination structured DB & BSON extractor
    LLM_SEMANTIC = "llm_semantic"                  # Semantic extractor for narrative prose & policies
    DOMAIN_RULES = "domain_rules"                  # Regex & pattern-based extractor for enterprise standards
    TABLE_AWARE = "table_aware"                    # Table grid extractor with cell, row, and column binding


class ClaimType(str, Enum):
    """Controlled enterprise vocabulary for claim classifications."""
    OBLIGATION = "OBLIGATION"
    PROHIBITION = "PROHIBITION"
    PERMISSION_OR_RIGHT = "PERMISSION_OR_RIGHT"
    POLICY_FACT = "POLICY_FACT"
    BENEFIT = "BENEFIT"
    SUMMARY_NON_CANONICAL = "SUMMARY_NON_CANONICAL"
    DOCUMENT_METADATA = "DOCUMENT_METADATA"
    INVARIANT = "INVARIANT"
    METRIC_RULE = "METRIC_RULE"
    DECISION = "DECISION"
    EXAMPLE = "EXAMPLE"
    REVISION_HISTORY = "REVISION_HISTORY"


class UnitOutcome(str, Enum):
    """The 6 explicit audit outcomes for every evidence unit passing through Layer 5."""
    PROCESSED_WITH_CLAIMS = "processed_with_claims"  # Successfully generated 1+ grounded atomic assertions
    PROCESSED_NO_CLAIMS   = "processed_no_claims"    # Examined thoroughly, verified purely descriptive without constraints
    SKIPPED_WITH_REASON   = "skipped_with_reason"    # Structural header, boilerplate, or out-of-scope element with reason
    NEEDS_REVIEW          = "needs_review"           # Ambiguous layout (e.g. merged cells or uncertain scope)
    FAILED_RETRYABLE      = "failed_retryable"       # Transient execution failure eligible for retry with alternate parser
    FAILED_TERMINAL       = "failed_terminal"        # Unrecoverable parsing error (e.g. corrupted binary encoding)


class TypedValue(BaseModel):
    """
    Strongly-typed representation of an extracted policy constraint, duration, percentage,
    or reference value. Preserves soft qualifiers and dimensional units without semantic loss.
    """
    value_type: str = Field(..., description="Semantic type: DURATION, PERCENTAGE, CURRENCY, CALENDAR_DEADLINE, BOOLEAN, TEXT_RULE, REFERENCE")
    scalar_min: Optional[float] = Field(default=None, description="Minimum numeric boundary or scalar value")
    scalar_max: Optional[float] = Field(default=None, description="Maximum numeric boundary (if range)")
    unit: Optional[str] = Field(default=None, description="Standardized measurement unit (e.g. days, hours, %, USD)")
    qualifier: Optional[str] = Field(default=None, description="Primary soft qualifier (e.g. up_to, typical, usually)")
    duration_type: Optional[str] = Field(default=None, description="Semantic classification: typical, maximum, minimum, target, provider_governed")
    time_basis: Optional[str] = Field(default=None, description="Reference baseline (e.g. delivery_date, purchase_date, holiday_window)")
    reference_id: Optional[str] = Field(default=None, description="Target section or identifier for REFERENCE values")
    raw_text: str = Field(..., description="Verbatim raw string from which this value was parsed")
    structured_rule: Optional[dict[str, Any]] = Field(default=None, description="Structured rule definition (e.g. calendar date rule)")


class TableGridBinding(BaseModel):
    """
    Cryptographic and spatial proof binding an extracted claim to a 2D table matrix.
    Prevents parallel-array cross-wiring between rows and values.
    """
    table_id: str = Field(..., description="Unique table identifier within the source document")
    row_key: str = Field(..., description="Key identifier for row (e.g. 'Grade E (E1, E2 & E3)')")
    column_header: str = Field(..., description="Column header (e.g. 'Probationers')")
    cell_value: str = Field(..., description="Verbatim raw cell value (e.g. '15 days')")
    normalized_value: Optional[Any] = Field(default=None, description="Normalized scalar value (e.g. 15)")
    normalized_unit: Optional[str] = Field(default=None, description="Measurement unit (e.g. 'days')")
    row_index: int = Field(default=0, description="0-indexed row position in grid")
    col_index: int = Field(default=0, description="0-indexed column position in grid")
    is_merged_cell: bool = Field(default=False, description="Flagged true if cell spans multiple rows/cols")
    qualifiers: List[str] = Field(default_factory=list, description="Extracted soft qualifiers (e.g. ['up_to', 'typical'])")
    typed_value: Optional[TypedValue] = Field(default=None, description="Structured typed representation of cell value")


class CandidateClaim(BaseModel):
    """
    An atomic claim candidate identified from an evidence unit.
    Preserves subject-predicate-object structure, exact quote locators, conditions, scope, and verification state.
    """
    candidate_id: str = Field(..., description="Deterministic unique identifier for this candidate")
    envelope_id: uuid.UUID = Field(..., description="Parent Layer 3 CanonicalSourceEnvelope identifier")
    unit_id: str = Field(..., description="Parent Layer 4 ParsedEvidenceUnit identifier")
    asset_id: str = Field(..., description="Native external asset identifier")
    content_role: ContentRole = Field(default=ContentRole.POLICY_RULE, description="Classified semantic role of parent content")
    
    # Stable Identity & Association (Anti-Cross-Wiring)
    run_id: Optional[uuid.UUID] = Field(default=None, description="Ingestion pipeline run identifier")
    source_unit_id: Optional[str] = Field(default=None, description="Layer 4 ParsedEvidenceUnit identifier")
    evidence_id: Optional[str] = Field(default=None, description="Cryptographic evidence locator identifier")
    table_binding: Optional[TableGridBinding] = Field(default=None, description="2D table grid binding coordinates")
    typed_value: Optional[TypedValue] = Field(default=None, description="Structured typed representation of claim value")
    
    # Semantic Representation
    claim_text: str = Field(..., description="Normalized claim statement")
    subject: str = Field(..., description="Entity or component governed by the claim")
    predicate: str = Field(..., description="Relationship or modal action (e.g. requires, enforces, is)")
    object: str = Field(..., description="Constraint, target value, or property")
    value: Optional[Any] = Field(default=None, description="Extracted numerical or quantitative scalar value (e.g. 60)")
    unit: Optional[str] = Field(default=None, description="Unit of measurement (e.g. days, hours, %)")
    time_basis: Optional[str] = Field(default=None, description="Reference baseline date (delivery_date, purchase_date, ship_date, holiday_window)")
    deadline: Optional[dict[str, Any]] = Field(default=None, description="Structured deadline specification if applicable")
    qualifier: Optional[str] = Field(default=None, description="Primary soft qualifier (typical, usually, may, recommended, at_discretion, where_possible)")
    qualifiers: List[str] = Field(default_factory=list, description="Soft qualifiers such as 'typical', 'recommended', 'up to', 'approximate'")
    modal_operator: Optional[str] = Field(default=None, description="Normative modal operator (must, shall, prohibited, required)")
    modality: str = Field(default="REQUIRED", description="Standardized normative modality: REQUIRED, PROHIBITED, PERMITTED, RECOMMENDED")
    conditions: List[Any] = Field(default_factory=list, description="Explicit contextual preconditions, triggers, or activation requirements")
    exceptions: List[str] = Field(default_factory=list, description="Explicit permitted exemptions or negative preconditions (e.g. Customer internal business use)")
    scope: dict[str, Any] = Field(default_factory=dict, description="Target population, grade, jurisdiction, or scope constraints")
    claim_type: str = Field(default="policy", description="Semantic category (policy, invariant, metric, decision)")
    
    # Provenance & Locators
    extraction_strategy: ExtractionStrategyType = Field(default=ExtractionStrategyType.DETERMINISTIC_SCHEMA)
    evidence_text_span: str = Field(..., description="Exact textual evidence quote from source")
    locator: dict[str, Any] = Field(default_factory=dict, description="Precision source coordinates")
    structured_values: dict[str, Any] = Field(default_factory=dict, description="Preserved native typed values or field paths")
    
    # Verification & Quality
    is_canonical: bool = Field(default=True, description="False if macro summary, example, revision history, or non-canonical context")
    cross_references: List[str] = Field(default_factory=list, description="External policies, instruments or documents referenced")
    status: str = Field(default="candidate", description="Validation status (candidate, verified, unverified, rejected)")
    confidence: float = Field(ge=0.0, le=1.0, default=1.0, description="Extraction and verification confidence score")
    is_ambiguous: bool = Field(default=False, description="Flagged true if cell bindings, scope, or conditions are ambiguous")
    ambiguity_reason: Optional[str] = Field(default=None, description="Recorded reason for ambiguity or escalation")
    verification_plugin: Optional[str] = Field(default=None, description="Name of plugin that verified this claim")
    verification_details: dict[str, Any] = Field(default_factory=dict, description="Cryptographic check and grounding proof")
    content_hash: str = Field(..., description="SHA-256 hash of the claim semantics and evidence")
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Phase 5 Extensions: Structured Provenance, Scope, Multi-Evidence, and Deduplication
    evidence_unit_ids: List[str] = Field(default_factory=list, description="IDs of all contributing source evidence units")
    evidence_relationship_type: Optional[str] = Field(default=None, description="Structural relation linking contributing evidence units")
    definition_references: List[str] = Field(default_factory=list, description="Referenced definition IDs or terms that qualify this claim")
    exception_references: List[str] = Field(default_factory=list, description="Referenced exception IDs or terms")
    temporal_scope: Optional[str] = Field(default=None, description="Temporal validity, window, or effective duration")
    geographic_scope: Optional[str] = Field(default=None, description="Geographic jurisdiction or applicable region")
    product_scope: Optional[str] = Field(default=None, description="Applicable product, service, tier, or SKU")
    entity_scope: Optional[str] = Field(default=None, description="Target entity, population, role, or audience")
    source_version: Optional[str] = Field(default=None, description="Source version of asset or envelope")
    is_current: bool = Field(default=True, description="Whether from current source version")
    raw_content: Optional[str] = Field(default=None, description="Raw content of primary evidence")
    normalized_content: Optional[str] = Field(default=None, description="Normalized readable content")
    extraction_status: str = Field(default="candidate", description="Extraction lifecycle status")
    extraction_warnings: List[str] = Field(default_factory=list, description="Extraction warnings or scope ambiguities")
    duplicate_of: Optional[str] = Field(default=None, description="Primary candidate ID if this is a duplicate occurrence")
    duplicate_occurrences: List[dict[str, Any]] = Field(default_factory=list, description="Separate evidence occurrences of the same claim")
    is_duplicate: bool = Field(default=False, description="Flagged true if this is a duplicate occurrence of an earlier candidate")

    @classmethod
    def create(
        cls,
        envelope_id: uuid.UUID,
        unit_id: str,
        asset_id: str,
        claim_text: str,
        subject: str,
        predicate: str,
        object_: str,
        evidence_text_span: str,
        value: Optional[Any] = None,
        unit: Optional[str] = None,
        time_basis: Optional[str] = None,
        qualifier: Optional[str] = None,
        qualifiers: Optional[List[str]] = None,
        modal_operator: Optional[str] = None,
        modality: str = "REQUIRED",
        conditions: Optional[List[Any]] = None,
        exceptions: Optional[List[str]] = None,
        scope: Optional[dict[str, Any]] = None,
        claim_type: str = "policy",
        is_canonical: Optional[bool] = None,
        cross_references: Optional[List[str]] = None,
        extraction_strategy: ExtractionStrategyType = ExtractionStrategyType.DETERMINISTIC_SCHEMA,
        locator: dict[str, Any] | None = None,
        structured_values: dict[str, Any] | None = None,
        is_ambiguous: bool = False,
        ambiguity_reason: Optional[str] = None,
        confidence: float = 1.0,
        run_id: Optional[uuid.UUID] = None,
        source_unit_id: Optional[str] = None,
        evidence_id: Optional[str] = None,
        table_binding: Optional[TableGridBinding] = None,
        typed_value: Optional[TypedValue] = None,
        deadline: Optional[dict[str, Any]] = None,
        content_role: ContentRole | str | None = None,
        evidence_unit_ids: Optional[List[str]] = None,
        evidence_relationship_type: Optional[str] = None,
        definition_references: Optional[List[str]] = None,
        exception_references: Optional[List[str]] = None,
        temporal_scope: Optional[str] = None,
        geographic_scope: Optional[str] = None,
        product_scope: Optional[str] = None,
        entity_scope: Optional[str] = None,
        source_version: Optional[str] = None,
        is_current: bool = True,
        raw_content: Optional[str] = None,
        normalized_content: Optional[str] = None,
        extraction_status: str = "candidate",
        extraction_warnings: Optional[List[str]] = None,
        duplicate_of: Optional[str] = None,
        duplicate_occurrences: Optional[List[dict[str, Any]]] = None,
        is_duplicate: bool = False,
    ) -> CandidateClaim:
        text_clean = claim_text.strip()
        hash_input = f"{asset_id}:{subject}:{predicate}:{object_}:{value}:{unit}:{evidence_text_span}:{source_version or ''}:{json.dumps(structured_values or {}, sort_keys=True, default=str)}"
        claim_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()
        cand_id = f"cand:{unit_id}:{claim_hash[:10]}"

        # Resolve ContentRole
        resolved_role = ContentRole.POLICY_RULE
        if content_role:
            try:
                resolved_role = ContentRole(content_role) if isinstance(content_role, str) else content_role
            except ValueError:
                resolved_role = ContentRole.POLICY_RULE

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

        # Resolve qualifier and time_basis
        resolved_qualifier = qualifier or (qualifiers[0] if qualifiers else None)
        resolved_time_basis = time_basis
        if not resolved_time_basis and typed_value and typed_value.time_basis:
            resolved_time_basis = typed_value.time_basis
        elif not resolved_time_basis and structured_values and structured_values.get("time_basis"):
            resolved_time_basis = structured_values.get("time_basis")

        # Resolve evidence_unit_ids
        resolved_evidence_unit_ids = list(evidence_unit_ids) if evidence_unit_ids else [source_unit_id or unit_id]

        # Resolve scopes
        resolved_scope = dict(scope or {})
        if temporal_scope:
            resolved_scope.setdefault("temporal", temporal_scope)
        else:
            temporal_scope = resolved_scope.get("temporal") or resolved_scope.get("temporal_scope")
        if geographic_scope:
            resolved_scope.setdefault("geographic", geographic_scope)
        else:
            geographic_scope = resolved_scope.get("geographic") or resolved_scope.get("geographic_scope")
        if product_scope:
            resolved_scope.setdefault("product", product_scope)
        else:
            product_scope = resolved_scope.get("product") or resolved_scope.get("product_scope")
        if entity_scope:
            resolved_scope.setdefault("entity", entity_scope)
        else:
            entity_scope = resolved_scope.get("entity") or resolved_scope.get("entity_scope")

        return cls(
            candidate_id=cand_id,
            envelope_id=envelope_id,
            unit_id=unit_id,
            asset_id=asset_id,
            content_role=resolved_role,
            run_id=run_id,
            source_unit_id=source_unit_id or unit_id,
            evidence_id=evidence_id or f"ev:{unit_id}",
            table_binding=table_binding,
            typed_value=typed_value,
            claim_text=text_clean,
            subject=subject.strip(),
            predicate=predicate.strip(),
            object=object_.strip(),
            value=value,
            unit=unit,
            time_basis=resolved_time_basis,
            deadline=deadline or (structured_values.get("deadline") if structured_values else None),
            qualifier=resolved_qualifier,
            qualifiers=qualifiers or ([resolved_qualifier] if resolved_qualifier else []),
            modal_operator=modal_operator,
            modality=modality,
            conditions=conditions or [],
            exceptions=exceptions or [],
            scope=resolved_scope,
            claim_type=claim_type,
            is_canonical=resolved_canonical,
            cross_references=cross_references or [],
            extraction_strategy=extraction_strategy,
            evidence_text_span=evidence_text_span.strip(),
            locator=locator or {},
            structured_values=structured_values or {},
            status="candidate",
            confidence=confidence,
            is_ambiguous=is_ambiguous,
            ambiguity_reason=ambiguity_reason,
            content_hash=claim_hash,
            extracted_at=datetime.now(timezone.utc),
            evidence_unit_ids=resolved_evidence_unit_ids,
            evidence_relationship_type=evidence_relationship_type,
            definition_references=definition_references or [],
            exception_references=exception_references or [],
            temporal_scope=temporal_scope,
            geographic_scope=geographic_scope,
            product_scope=product_scope,
            entity_scope=entity_scope,
            source_version=source_version,
            is_current=is_current,
            raw_content=raw_content,
            normalized_content=normalized_content or text_clean,
            extraction_status=extraction_status,
            extraction_warnings=extraction_warnings or [],
            duplicate_of=duplicate_of,
            duplicate_occurrences=duplicate_occurrences or [],
            is_duplicate=is_duplicate,
        )

    @classmethod
    def create_for_test(
        cls,
        claim_text: str,
        subject: str,
        predicate: str,
        object_: str,
        evidence_span: str,
        conditions: Optional[List[Any]] = None,
        exceptions: Optional[List[str]] = None,
        modality: str = "REQUIRED",
        claim_type: str = "policy",
    ) -> "CandidateClaim":
        """Convenience factory for unit tests."""
        return cls.create(
            envelope_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
            unit_id=f"unit_test_{uuid.uuid4().hex[:8]}",
            asset_id="asset_test",
            claim_text=claim_text,
            subject=subject,
            predicate=predicate,
            object_=object_,
            evidence_text_span=evidence_span,
            conditions=conditions or [],
            exceptions=exceptions or [],
            modality=modality,
            claim_type=claim_type,
            locator={"page": 1, "line": 1},
        )


class CompletenessLedgerRecord(BaseModel):
    """Audit entry recording the lifecycle of an individual evidence unit through Layer 5."""
    ledger_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    envelope_id: uuid.UUID
    unit_id: str
    asset_id: str
    block_type: str
    candidate_status: str     # discovered, extracted, verified, rejected, skipped
    outcome: UnitOutcome = Field(default=UnitOutcome.PROCESSED_WITH_CLAIMS)
    extractor_used: str
    verification_plugin: Optional[str] = None
    verification_passed: bool = False
    claims_count: int = 0
    failure_reason: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Layer5ExtractionResult(BaseModel):
    """Aggregated output of Layer 5 candidate extraction and verification."""
    envelope_id: uuid.UUID
    asset_id: str
    total_evidence_units_received: int
    candidates_discovered: int
    claims_extracted: int
    claims_verified: int
    claims_rejected: int
    completeness_score: float = Field(ge=0.0, le=1.0)
    candidates: List[CandidateClaim] = Field(default_factory=list)
    ledger_summary: dict[str, Any] = Field(default_factory=dict)
    extracted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict[str, Any]:
        return {
            "envelope_id": str(self.envelope_id),
            "asset_id": self.asset_id,
            "total_evidence_units_received": self.total_evidence_units_received,
            "candidates_discovered": self.candidates_discovered,
            "claims_extracted": self.claims_extracted,
            "claims_verified": self.claims_verified,
            "claims_rejected": self.claims_rejected,
            "completeness_score": self.completeness_score,
            "candidates": [c.model_dump() for c in self.candidates],
            "ledger_summary": self.ledger_summary,
            "extracted_at": self.extracted_at.isoformat(),
        }
