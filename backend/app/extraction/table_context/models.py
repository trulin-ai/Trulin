"""
TCUSE Data Models: Canonical Table, Context Provenance, Semantic Interpretation,
Two-Level Claim Representations, Validation & Completeness Audits.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TableType(str, Enum):
    """12 enterprise table classifications supported by TCUSE."""
    POLICY_RULE = "policy_rule"
    ELIGIBILITY = "eligibility"
    THRESHOLD = "threshold"
    COMPARISON = "comparison"
    SCHEDULE = "schedule"
    RESPONSIBILITY = "responsibility"
    EXCEPTION = "exception"
    STATISTICAL = "statistical"
    REFERENCE = "reference"
    CALCULATION = "calculation"
    REVISION_HISTORY = "revision_history"
    METADATA_NAVIGATIONAL = "metadata_navigational"


class CellDisposition(str, Enum):
    """10 explicit dispositions for cell-level completeness auditing."""
    ATOMIC_FACT = "atomic_fact"
    CONTEXT_ENRICHED_CLAIM = "context_enriched_claim"
    CONTEXTUAL_HEADER = "contextual_header"
    CONDITION = "condition"
    EXCEPTION = "exception"
    SUPPORTING_INFORMATION = "supporting_information"
    METADATA = "metadata"
    NON_SEMANTIC = "non_semantic"
    FLAGGED_FOR_REVIEW = "flagged_for_review"
    EXTRACTION_FAILURE = "extraction_failure"


class NormalizedCellValue(BaseModel):
    """Rich normalized value preserving original raw representation alongside typed semantics."""
    raw_value: str
    normalized_value: Optional[Any] = None
    data_type: str = "text"  # currency, percentage, duration, range, date, numeric, boolean, formula, text, empty
    currency_code: Optional[str] = None
    unit: Optional[str] = None
    range_min: Optional[float] = None
    range_max: Optional[float] = None
    min_inclusive: Optional[bool] = None
    max_inclusive: Optional[bool] = None
    comparison_operator: Optional[str] = None  # >=, <=, >, <, ==, ~
    is_approximate: bool = False
    is_negative: bool = False
    qualifiers: List[str] = Field(default_factory=list)
    formula: Optional[str] = None
    cached_value: Optional[Any] = None
    is_formula_unavailable: bool = False
    is_inherited: bool = False
    is_original_blank: bool = False
    footnote_markers: List[str] = Field(default_factory=list)


class HeaderNode(BaseModel):
    """Represents a column header and its parent/child hierarchy."""
    col_index: int
    raw_header: str
    clean_header: str
    parent_header: Optional[str] = None
    header_path: List[str] = Field(default_factory=list)
    embedded_unit: Optional[str] = None
    embedded_currency: Optional[str] = None
    inferred_conditions: List[str] = Field(default_factory=list)
    footnote_markers: List[str] = Field(default_factory=list)
    role: str = "rule"  # scope, rule, condition, metadata, formula


class HeaderHierarchy(BaseModel):
    """Resolved multi-level header structure for a canonical table."""
    columns: List[HeaderNode] = Field(default_factory=list)
    raw_header_rows: List[List[str]] = Field(default_factory=list)
    scope_columns: List[str] = Field(default_factory=list)
    rule_columns: List[str] = Field(default_factory=list)
    has_grouped_headers: bool = False
    cross_column_dependencies: List[Dict[str, Any]] = Field(default_factory=list)


class ContextProvenanceItem(BaseModel):
    """A collected contextual artifact associated with a table, with exact provenance."""
    context_type: str  # title, caption, description, section_heading, subsection_heading, preceding_paragraph, following_paragraph, footnote, referenced_note, document_title, row_header
    text: str
    unit_id: Optional[str] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    page_number: Optional[int] = None
    distance_units: int = 0
    marker: Optional[str] = None  # e.g., "*", "[1]", "Note 1"
    confidence: float = 1.0


class TableContextBundle(BaseModel):
    """All collected context signals around a reconstructed table."""
    table_id: str
    document_title: Optional[str] = None
    table_title: Optional[ContextProvenanceItem] = None
    table_caption: Optional[ContextProvenanceItem] = None
    table_description: Optional[ContextProvenanceItem] = None
    parent_section_heading: Optional[ContextProvenanceItem] = None
    subsection_heading: Optional[ContextProvenanceItem] = None
    preceding_paragraph: Optional[ContextProvenanceItem] = None
    following_paragraphs: List[ContextProvenanceItem] = Field(default_factory=list)
    footnotes: List[ContextProvenanceItem] = Field(default_factory=list)
    referenced_notes: List[ContextProvenanceItem] = Field(default_factory=list)
    all_items: List[ContextProvenanceItem] = Field(default_factory=list)
    has_inconsistency: bool = False
    inconsistency_reasons: List[str] = Field(default_factory=list)
    context_fingerprint: str = ""


class TableSemanticInterpretation(BaseModel):
    """Table-level semantic meaning produced before row-level claim generation."""
    table_id: str
    table_type: TableType = TableType.POLICY_RULE
    business_domain: Optional[str] = None
    business_topic: Optional[str] = None
    table_purpose: Optional[str] = None
    primary_entity: Optional[str] = None
    secondary_entities: List[str] = Field(default_factory=list)
    entity_attributes: List[str] = Field(default_factory=list)
    relationship_type: Optional[str] = None
    canonical_predicate_stem: Optional[str] = None
    value_interpretation: Optional[str] = None
    scope_conditions: List[str] = Field(default_factory=list)
    rule_conditions: List[str] = Field(default_factory=list)
    actors: List[str] = Field(default_factory=list)
    actions: List[str] = Field(default_factory=list)
    permissions: List[str] = Field(default_factory=list)
    restrictions: List[str] = Field(default_factory=list)
    units: List[str] = Field(default_factory=list)
    temporal_applicability: Optional[str] = None
    geographic_applicability: Optional[str] = None
    exceptions: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    footnote_qualifications: Dict[str, str] = Field(default_factory=dict)
    is_ambiguous: bool = False
    missing_context_reasons: List[str] = Field(default_factory=list)
    semantic_confidence: float = 0.85
    interpretation_method: str = "hybrid_deterministic_nlp"


class AtomicTableFact(BaseModel):
    """Level 1 representation: explicit raw table fact preserving original source structure."""
    fact_id: str
    subject: str
    predicate: str = "has_value"
    object: str
    source_type: str = "table"
    table_id: str
    row_id: str
    row_index: int
    column_id: str
    col_index: int
    raw_value: str
    normalized_value: Optional[Any] = None
    evidence_unit_id: str


class TableConfidenceBreakdown(BaseModel):
    """Five separate confidence scores required by Section 13."""
    table_extraction: float = 1.0
    table_reconstruction: float = 1.0
    context_interpretation: float = 0.85
    claim_generation: float = 0.90
    evidence_verification: float = 0.95


class CanonicalTableRow(BaseModel):
    """Canonical representation of one data row in a reconstructed table."""
    row_id: str
    row_index: int
    unit_id: str
    raw_text: str
    page_number: Optional[int] = None
    char_start: Optional[int] = None
    char_end: Optional[int] = None
    cells: Dict[str, str] = Field(default_factory=dict)
    normalized_cells: Dict[str, NormalizedCellValue] = Field(default_factory=dict)
    is_ambiguous: bool = False
    ambiguity_reason: Optional[str] = None
    locator: Dict[str, Any] = Field(default_factory=dict)


class CanonicalTable(BaseModel):
    """Unified canonical representation of a reconstructed table regardless of source format."""
    table_id: str
    asset_id: str
    page_numbers: List[int] = Field(default_factory=list)
    extraction_method: str = "DocumentParser"
    headers: List[str] = Field(default_factory=list)
    header_hierarchy: HeaderHierarchy = Field(default_factory=HeaderHierarchy)
    rows: List[CanonicalTableRow] = Field(default_factory=list)
    context_bundle: TableContextBundle
    interpretation: Optional[TableSemanticInterpretation] = None
    extraction_confidence: float = 1.0
    reconstruction_confidence: float = 1.0


class TableConsistencyReport(BaseModel):
    """Result of the independent TableSemanticConsistencyValidator."""
    table_id: str
    passed: bool = True
    checks: Dict[str, bool] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    confidence_breakdown: TableConfidenceBreakdown = Field(default_factory=TableConfidenceBreakdown)


class TableCompletenessReport(BaseModel):
    """Result of both Cell-Level and Relationship-Level completeness audits."""
    table_id: str
    total_cells: int = 0
    cell_dispositions: Dict[str, str] = Field(default_factory=dict)  # cell_id -> CellDisposition
    cell_completeness_passed: bool = True
    missing_cells: List[str] = Field(default_factory=list)
    relationship_checks: Dict[str, bool] = Field(default_factory=dict)
    relationship_completeness_passed: bool = True

