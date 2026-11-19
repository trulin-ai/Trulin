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
"""

from enum import Enum
from typing import Any, List, Optional
from pydantic import BaseModel, Field

from app.schemas.context import SectionContextItem


class ConflictClassificationType(str, Enum):
    CONTEXT_DEPENDENT = "CONTEXT_DEPENDENT"
    DIRECT_CONTRADICTION = "DIRECT_CONTRADICTION"
    NEEDS_SOURCE_CLARIFICATION = "NEEDS_SOURCE_CLARIFICATION"


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
