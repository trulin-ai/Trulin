"""
Chat & Policy Answer Schemas for Context Trust Layer.

Defines the typed answer contract for the Policy Answer Assistant:
1. Structured verified claims with full provenance (subject, predicate, object, modality).
2. Clean separation of verified rules from non-normative section context.
3. Preserved conditions and exceptions extracted from operative evidence.
4. Tri-state conflict classification:
   - CONTEXT_DEPENDENT
   - DIRECT_CONTRADICTION
   - NEEDS_SOURCE_CLARIFICATION
5. Grounding scores, verification status, and scoped document telemetry.
6. Schema Version 2 additions:
   - Response planning metadata (question_type, display_depth, group_by).
   - Structured explanation blocks with statement-level claim mapping.
   - Explicit scope summaries, limitations, and unanswered parts.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.context import SectionContextItem


class ConflictClassificationType(str, Enum):
    CONTEXT_DEPENDENT = "CONTEXT_DEPENDENT"
    DIRECT_CONTRADICTION = "DIRECT_CONTRADICTION"
    NEEDS_SOURCE_CLARIFICATION = "NEEDS_SOURCE_CLARIFICATION"


class QuestionType(str, Enum):
    LOOKUP = "lookup"                     # Fact, deadline, threshold, single metric
    INTERPRETATION = "interpretation"     # Meaning, scope of restriction, application
    COMPARISON = "comparison"             # Comparison across rules, documents, or terms
    PROCEDURE = "procedure"               # Prerequisites, ordered or unordered steps
    ACTION_ASSESSMENT = "action_assessment" # Permission to execute an action (ALLOW/BLOCK)
    CONFLICT = "conflict"                 # Disputed pathways / contradictory sources
    OVERVIEW = "overview"                 # Broad policy review / thematic summary
    UNSUPPORTED = "unsupported"           # Abstention / no verified rule in scope


class DisplayDepth(str, Enum):
    BRIEF = "brief"         # 50–100 words
    STANDARD = "standard"   # 120–250 words
    DETAILED = "detailed"   # 300–600 words
    AUTO = "auto"


class ExplanationStatement(BaseModel):
    id: str                               # e.g., "stmt-1"
    text: str                             # The substantive statement
    claim_ids: List[str] = Field(default_factory=list)
    source_indices: List[int] = Field(default_factory=list)
    is_normative: bool = True             # True = operative rule; False = non-normative context
    modality: str = "MUST"                # MUST, MAY, PROHIBITED, OPTIONAL


class ExplanationBlock(BaseModel):
    id: str                               # e.g., "block-1"
    heading: Optional[str] = None         # "Pre-Approval Prerequisites", "Return Criteria"
    block_type: str = "paragraph"         # "paragraph", "checklist", "table", "key_value"
    statements: List[ExplanationStatement] = Field(default_factory=list)


class ResponsePlan(BaseModel):
    question_type: QuestionType = QuestionType.INTERPRETATION
    requested_depth: DisplayDepth = DisplayDepth.AUTO
    resolved_depth: DisplayDepth = DisplayDepth.STANDARD
    scope_status: str = "resolved"        # "resolved", "ambiguous", "unbounded_workspace"
    group_by: str = "topic"               # "topic", "step", "criterion", "entity", "pathway"
    required_sections: List[str] = Field(
        default_factory=lambda: ["summary", "explanation", "conditions", "evidence"]
    )
    unanswered_parts: List[str] = Field(default_factory=list)


class ScopeSummary(BaseModel):
    label: str                            # e.g., "Selected Procurement Policy · v2.4 (Active)"
    document_ids: List[str] = Field(default_factory=list)
    document_titles: List[str] = Field(default_factory=list)
    resolution_status: str = "resolved"   # "resolved", "ambiguous", "unbounded_workspace"
    governance_boundary: Optional[str] = None


class GroundedClaimItem(BaseModel):
    claim_id: str
    source_index: int
    subject: str
    predicate: str
    object: str
    modality: str = "MUST"
    verbatim_evidence: str
    document_title: str
    document_id: Optional[str] = None
    section: Optional[str] = None
    page: int = 1
    trust_score: float = 1.0
    certification_tier: str = "AUTOMATED_CERTIFIED"


class ConflictPathway(BaseModel):
    path_label: str  # e.g., "Path A: Subscription Cancellation"
    source_title: str
    section: Optional[str] = None
    rule_summary: str
    conditions: List[str] = Field(default_factory=list)
    verbatim_quote: str


class ConflictPathwayAnalysis(BaseModel):
    is_conflicted: bool = True
    conflict_type: str = ConflictClassificationType.CONTEXT_DEPENDENT.value
    severity: str = "HIGH"
    conflict_summary: str
    pathways: List[ConflictPathway] = Field(default_factory=list)
    affected_claim_ids: List[str] = Field(default_factory=list)
    recommended_action: str


class AnswerScope(BaseModel):
    document_ids: List[str] = Field(default_factory=list)
    workspace: str = "policy"
    temporal_validity: str = "current"


class PolicyAnswerContract(BaseModel):
    # Schema Versioning (Defaults to "2" while preserving all v1 fields)
    schema_version: str = "2"

    # Core V1 Fields (Fully Preserved for 100% Backward Compatibility)
    bottom_line_answer: str
    conditions: List[str] = Field(default_factory=list)
    exceptions: List[str] = Field(default_factory=list)
    verified_claims_used: List[GroundedClaimItem] = Field(default_factory=list)
    section_context: List[SectionContextItem] = Field(default_factory=list)
    conflict_analysis: Optional[ConflictPathwayAnalysis] = None
    grounding_score: float = 1.0
    verification_status: str = "VERIFIED"  # "VERIFIED", "PARTIALLY_GROUNDED", "DISPUTED", "NO_VERIFIED_RULE"
    recommended_human_action: Optional[str] = None
    answer_scope: AnswerScope = Field(default_factory=AnswerScope)

    # Adaptive V2 Extensions (Optional / Additive)
    response_plan: Optional[ResponsePlan] = None
    scope_summary: Optional[ScopeSummary] = None
    explanation_blocks: List[ExplanationBlock] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)
    unanswered_parts: List[str] = Field(default_factory=list)
    wording_metadata: Optional[Dict[str, Any]] = None
