import decimal
import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict, field_validator

from app.db.enums import ConflictStatus, ReviewDecision
from app.schemas.claim import ClaimResponse


class ConflictResolveRequest(BaseModel):
    reviewer_id: uuid.UUID
    decision: ReviewDecision
    chosen_claim_id: uuid.UUID | None = None
    reason: str | None = None


class ConflictResponse(BaseModel):
    id: uuid.UUID
    claim_a_id: uuid.UUID
    claim_b_id: uuid.UUID
    conflict_type: str
    severity: str
    confidence: decimal.Decimal
    resolution_status: ConflictStatus
    resolved_claim_id: uuid.UUID | None = None
    resolved_by: uuid.UUID | None = None
    resolved_at: datetime | None = None
    created_at: datetime
    claim_a: ClaimResponse | None = None
    claim_b: ClaimResponse | None = None
    # Master Plan Structured Conflict Contract Fields
    conflicting_fields: list[str] | None = None
    supporting_evidence: dict | None = None
    source_authority: dict | None = None
    applicable_scope: dict | None = None
    effective_dates: dict | None = None
    reviewer_decision: str | None = None
    resolution_rationale: str | None = None

    model_config = ConfigDict(from_attributes=True)


class ConflictClusterSide(BaseModel):
    representative_claim_id: uuid.UUID
    representative_text: str
    source_title: str
    section: str | None = None
    trust_score: float
    claim_count: int
    claim_ids: list[uuid.UUID]
    applicable_scope: dict | None = None
    effective_dates: dict | None = None
    authority_level: int | None = None
    certification_status: str | None = None


class ConflictIssueResponse(BaseModel):
    issue_id: str
    topic: str
    conflict_type: str
    severity: str
    confidence: float
    impact_score: float = 0.0
    blast_radius: str = "ROUTINE"
    cluster_a: ConflictClusterSide
    cluster_b: ConflictClusterSide
    conflict_ids: list[uuid.UUID]
    total_conflicts: int
    created_at: datetime
    conflicting_fields: list[str] | None = None
    has_exception: bool = False
    can_one_click_resolve: bool = True
    safety_lock_reason: str | None = None
    precedence_rule: str | None = None
    resolution_rationale: str | None = None
    blast_radius_breakdown: dict[str, Any] | None = None


class ResolveIssueRequest(BaseModel):
    reviewer_id: uuid.UUID
    decision: ReviewDecision
    chosen_side: str  # "A", "B", or "DISMISS"
    reason: str | None = None

    @field_validator("decision", mode="before")
    def normalize_decision(cls, v):
        if isinstance(v, str):
            return v.lower()
        return v

