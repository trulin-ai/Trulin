import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ClaimDecayItem(BaseModel):
    claim_id: uuid.UUID
    claim_text: str
    document_title: str
    created_at: datetime
    age_days: int
    initial_trust: float
    current_decayed_trust: float
    freshness_score: float = Field(..., description="Time-based decay signal (controlled by System)")
    certification_status: str = Field(..., description="Legal/trust decision (controlled by validation + review workflow)")
    decay_pct: float
    drift_category: str  # "ACTIVE_FRESH", "AGING_WARNING", "STALE_TEMPORAL", "SEVERELY_DECAYED"
    recommended_action: str


class DriftAnalysisResponse(BaseModel):
    organization_id: uuid.UUID
    analyzed_at: datetime
    total_claims: int
    fresh_claims_count: int
    decayed_claims_count: int
    stale_documents_count: int
    average_age_days: int
    freshness_index_pct: float  # 0.0 - 100.0%
    decay_radar: Dict[str, int]  # e.g. {"<30d": 12, "30-90d": 8, "90-180d": 4, ">180d": 2}
    decayed_claims: List[ClaimDecayItem]


class AttestationPolicyConfig(BaseModel):
    source_authority: Optional[str] = "internal_standard"
    domain_pack: str = "regulatory_policy"
    review_horizon_days: int = 90
    mandatory_reattestation: bool = True
    grace_period_days: int = 15


class AttestationRecord(BaseModel):
    attestation_id: uuid.UUID
    claim_id: uuid.UUID
    attester_id: uuid.UUID
    attestation_decision: str  # "ATTESTED_VALID" or "RETIRED_SUPERSEDED"
    attestation_reason: str
    source_version: str
    evidence_version: str
    attested_at: datetime
    expires_at: datetime
    policy_config: Optional[AttestationPolicyConfig] = None


class ClaimRemediateRequest(BaseModel):
    claim_id: uuid.UUID
    action: str = Field(..., description="'RE_ATTEST' (re-certify freshness interval) or 'RETIRE' (deprecate)")
    attester_id: Optional[uuid.UUID] = Field(None, description="UUID of authorized data owner / reviewer")
    reason: Optional[str] = Field(None, description="Formal justification for policy re-attestation")
    notes: Optional[str] = None
    source_version: Optional[str] = Field(None, description="Document/clause version being attested")
    domain_pack: Optional[str] = Field(None, description="Domain pack determining review horizon (e.g. 'financial_controls', 'safety_compliance', 'regulatory_policy', 'general_faq')")
    review_horizon_days: Optional[int] = Field(None, description="Custom review horizon in days override")


class ClaimRemediateResponse(BaseModel):
    claim_id: uuid.UUID
    action_taken: str
    new_status: str
    freshness_score: float
    certification_status: str
    new_trust_score: float
    message: str
    timestamp: datetime
    attestation_record: Optional[AttestationRecord] = None
