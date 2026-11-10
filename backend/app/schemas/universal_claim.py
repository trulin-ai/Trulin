"""
Universal Claim Schema for Document-Agnostic Certification.

Separates derived graph fields from immutable evidence and enforces
strict verification that claim text is never fabricated from metadata.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
import uuid
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.schemas.evidence import ImmutableEvidenceSpan


class ClaimLifecycleState(str, Enum):
    CANDIDATE = "CANDIDATE"
    NORMALIZED = "NORMALIZED"
    GATE_EVALUATED = "GATE_EVALUATED"
    AUTOMATED_CERTIFIED = "AUTOMATED_CERTIFIED"
    QUALIFIED_CANONICAL = "QUALIFIED_CANONICAL"
    HUMAN_CERTIFIED = "HUMAN_CERTIFIED"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    QUARANTINED = "QUARANTINED"
    REJECTED = "REJECTED"
    DUPLICATE = "DUPLICATE"
    NON_RULE = "NON_RULE"


class ClaimType(str, Enum):
    RULE = "RULE"
    DEFINITION = "DEFINITION"
    REFERENCE = "REFERENCE"
    DESCRIPTION = "DESCRIPTION"
    RESPONSIBILITY = "RESPONSIBILITY"
    SECTION_MARKER = "SECTION_MARKER"


class ModalityType(str, Enum):
    MUST = "MUST"
    MAY = "MAY"
    MUST_NOT = "MUST_NOT"
    ENTITLED_TO = "ENTITLED_TO"
    CONDITIONAL = "CONDITIONAL"


class SubjectEntity(BaseModel):
    raw_text: str = Field(..., min_length=1)
    canonical_entity: str = Field(..., min_length=1)
    entity_role: Optional[str] = None  # e.g. "ANY_PARTY", "BUYER", "VENDOR", "EMPLOYER", "DISCLOSER"
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class PredicateAction(BaseModel):
    raw_text: str = Field(..., min_length=1)
    normalized_action: str = Field(..., min_length=1, description="Taxonomy ID registered in PredicateRegistry")
    taxonomy_version: str = Field("v1.0.0")
    confidence: float = Field(1.0, ge=0.0, le=1.0)


class ObjectEntity(BaseModel):
    raw_text: Optional[str] = None
    canonical_entity: Optional[str] = None
    entity_role: Optional[str] = None


class ConditionClause(BaseModel):
    text: str = Field(..., min_length=1)
    condition_type: str = Field("TRIGGER")  # TRIGGER, EXCEPTION, TIMEFRAME, PRECONDITION
    time_window: Optional[str] = None


class UniversalClaim(BaseModel):
    """
    Universal claim schema with immutable evidence binding.
    """
    model_config = ConfigDict(extra="ignore")

    claim_id: str = Field(default_factory=lambda: f"clm_{uuid.uuid4().hex[:12]}")
    parent_claim_id: Optional[str] = None
    child_index: Optional[int] = None

    evidence: ImmutableEvidenceSpan
    claim_text: str = Field(..., min_length=5, description="Verbatim quote or verified hygiene normalization of verbatim quote")

    subject: SubjectEntity
    predicate: PredicateAction
    object: Optional[ObjectEntity] = None

    modality: ModalityType = ModalityType.MUST
    conditions: List[ConditionClause] = Field(default_factory=list)
    claim_type: ClaimType = ClaimType.RULE

    lifecycle_state: ClaimLifecycleState = ClaimLifecycleState.CANDIDATE
    certification_tier: str = "REVIEW_REQUIRED"
    is_canonical: bool = False
    agent_accessible: bool = False

    gates: Dict[str, bool] = Field(default_factory=dict)
    rejection_reasons: List[str] = Field(default_factory=list)
    trust_score: float = Field(0.95, ge=0.0, le=1.0)
    risk_level: str = "MEDIUM"  # LOW, MEDIUM, HIGH, CRITICAL

    duplicate_of: Optional[str] = None

    @model_validator(mode="after")
    def validate_evidence_first_invariant(self) -> "UniversalClaim":
        """
        Enforce Evidence-First Invariant:
        Forbidden: claim_text synthesized via metadata template interpolation:
        e.g. f"{subject.raw_text} {predicate.normalized_action} {object.raw_text}."
        """
        quote_lower = self.evidence.verbatim_quote.strip().lower()
        text_lower = self.claim_text.strip().lower()

        # Disallow raw snake_case predicate identifiers interpolated into claim_text
        if "_" in self.predicate.normalized_action and self.predicate.normalized_action in text_lower:
            raise ValueError(
                f"Synthetic text detected: Predicate slug '{self.predicate.normalized_action}' was injected into claim text '{self.claim_text}'"
            )

        # Disallow trivial template concatenation: "Subject Predicate Object."
        if self.object and self.object.raw_text:
            template_candidate = f"{self.subject.raw_text} {self.predicate.normalized_action} {self.object.raw_text}.".lower()
            if text_lower == template_candidate:
                raise ValueError("Forbidden: claim_text was synthesized from metadata template string.")

        return self
