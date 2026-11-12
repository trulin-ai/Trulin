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
from typing import Any, Dict, List, Optional

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


class FieldEvidenceBinding(BaseModel):
    """Exact character-level evidence binding for a structured claim field."""
    field: str = Field(..., description="Target field: subject, action, object, condition, limit, exception, scope")
    evidence_span: str = Field(..., description="Exact textual span from source that proves this field")
    char_start: Optional[int] = Field(default=None, description="Start character offset in source document")
    char_end: Optional[int] = Field(default=None, description="End character offset in source document")
    cell_key: Optional[str] = Field(default=None, description="Column header or key if proved by table cell")


class TypedEntity(BaseModel):
    """Entity representation with category classification."""
    text: str = Field(..., description="Canonical entity label")
    type: str = Field(default="actor", description="Entity category: actor, product_category, payment_instrument, financial_disbursement, service, document_version")


class TypedAction(BaseModel):
    """Two-level action and normative role specification."""
    predicate: str = Field(..., description="Predicate slug e.g. receives_store_credit_bonus, has_posting_duration")
    universal_role: Optional[str] = Field(default="specifies", description="Base role: requires, permits, prohibits, entitles, specifies, limits, excludes, describes, references, classifies_as")
    typed_subtype: Optional[str] = Field(default=None, description="Specific subtype: return_window, posting_duration, cancellation_window, price_adjustment_window, reporting_window, trial_refund_window, store_credit_incentive")
    semantic_role: Optional[str] = Field(default=None, description="Granular role: receives, provides, requests, approves, issues, cancels")
    modality: str = Field(default="REQUIRED", description="Standardized normative modality: REQUIRED, PROHIBITED, PERMITTED, RECOMMENDED, MUST, MAY, CANNOT, WILL")
    polarity: str = Field(default="positive", description="Semantic polarity: positive or negative")


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
    is_inherited: bool = Field(default=False, description="True if value was inherited from a merged parent cell")
    is_original_blank: bool = Field(default=False, description="True if original source cell was blank prior to merge inheritance")
    formula: Optional[str] = Field(default=None, description="Original spreadsheet formula if applicable")
    header_hierarchy: List[str] = Field(default_factory=list, description="Parent-to-child header path")
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
    limits: List[str] = Field(default_factory=list, description="Explicit quantitative caps or limits (e.g. maximum bonus $25, once per year)")
    scope: dict[str, Any] = Field(default_factory=dict, description="Target population, grade, jurisdiction, or scope constraints")
    claim_type: str = Field(default="policy", description="Semantic category (policy, invariant, metric, decision)")
    
    # Phase 2: Typed Evidence-Bound Representations
    typed_subject: Optional[TypedEntity] = Field(default=None, description="Typed entity representation of subject")
    typed_action: Optional[TypedAction] = Field(default=None, description="Two-level action role and modality")
    typed_object: Optional[TypedEntity] = Field(default=None, description="Typed entity representation of object")
    evidence_bindings: List[FieldEvidenceBinding] = Field(default_factory=list, description="Character-level evidence bindings for each structured field")
    normalization_history: List[Dict[str, Any]] = Field(default_factory=list, description="Phase 5: Non-destructive normalization audit trail and field diffs")
    
    # Provenance & Locators
    extraction_strategy: ExtractionStrategyType = Field(default=ExtractionStrategyType.DETERMINISTIC_SCHEMA)
    evidence_text_span: str = Field(..., description="Exact textual evidence quote from source")
    locator: dict[str, Any] = Field(default_factory=dict, description="Precision source coordinates")
    structured_values: dict[str, Any] = Field(default_factory=dict, description="Preserved native typed values or field paths")
    semantic_context: Optional[Dict[str, Any]] = Field(default=None, description="TCUSE table-level semantic interpretation context")
    atomic_fact: Optional[Dict[str, Any]] = Field(default=None, description="Level 1 explicit raw table fact")
    evidence_refs: List[str] = Field(default_factory=list, description="Complete set of cell and contextual evidence unit IDs")
    confidence_breakdown: Optional[Dict[str, float]] = Field(default=None, description="Independent extraction/reconstruction/interpretation/claim/evidence confidence scores")
    
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
        limits: Optional[List[str]] = None,
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
        typed_subject: Optional[TypedEntity] = None,
        typed_action: Optional[TypedAction] = None,
        typed_object: Optional[TypedEntity] = None,
        evidence_bindings: Optional[List[FieldEvidenceBinding]] = None,
    ) -> CandidateClaim:
        text_clean = claim_text.strip()
        hash_input = f"{asset_id}:{subject}:{predicate}:{object_}:{value}:{unit}:{evidence_text_span}:{json.dumps(structured_values or {}, sort_keys=True, default=str)}"
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
            limits=limits or [],
            scope=scope or {},
            claim_type=claim_type,
            is_canonical=resolved_canonical,
            cross_references=cross_references or [],
            extraction_strategy=extraction_strategy,
            evidence_text_span=evidence_text_span.strip(),
            locator=locator or {},
            structured_values=structured_values or {},
            typed_subject=typed_subject,
            typed_action=typed_action,
            typed_object=typed_object,
            evidence_bindings=evidence_bindings or [],
            status="candidate",
            confidence=confidence,
            is_ambiguous=is_ambiguous,
            ambiguity_reason=ambiguity_reason,
            content_hash=claim_hash,
            extracted_at=datetime.now(timezone.utc),
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
    table_context_summary: dict[str, Any] = Field(default_factory=dict)
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
            "table_context_summary": self.table_context_summary,
            "extracted_at": self.extracted_at.isoformat(),
        }
