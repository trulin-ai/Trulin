import uuid
from datetime import datetime
from pydantic import BaseModel, Field


class DecisionContextItem(BaseModel):
    claim: str = Field(..., description="The factual statement or policy rule")
    source: str = Field(..., description="Source name or file path, e.g. handbook.pdf, policy-service")
    updated_at: str | None = Field(default=None, description="ISO timestamp or date string, e.g. 2025-11-04")
    authority_level: int | None = Field(default=50, ge=0, le=100, description="Authority rating 0-100")
    scope: str | None = Field(default=None, description="Applicable region/entity/tier, e.g. US, Enterprise, Global")
    claim_id: str | None = Field(default=None, description="Explicit UUID of the supporting/conflicting Claim")
    claim_version: str | None = Field(default=None, description="DocumentVersion UUID or snapshot hash")
    role: str = Field(default="context", description="Relationship role: supporting | conflicting | context")


class DecisionActor(BaseModel):
    id: str = Field(..., description="Agent or user identifier, e.g. agent-42")
    role: str = Field(default="support", description="Actor role, e.g. support, admin, developer, finance")


class DecisionEvaluateRequest(BaseModel):
    decision: str = Field(..., description="The intended decision or action, e.g. Determine whether customer is eligible for refund")
    actor: DecisionActor = Field(..., description="The agent or user executing the decision")
    context: list[DecisionContextItem] = Field(default_factory=list, description="Candidate evidence / claims retrieved by the agent")
    organization_id: uuid.UUID | None = Field(default=None, description="Organization ID for multi-tenant context")
    required_scope: str | None = Field(default=None, description="Required target scope, e.g. Enterprise, US, EMEA")

    @property
    def decision_prompt(self) -> str:
        return self.decision


class DecisionEvaluateResponse(BaseModel):
    decision: str = Field(..., description="Policy decision: ALLOW, ALLOW_WITH_CONSTRAINT, CLARIFY, REVIEW, or BLOCK")
    validity: str = Field(..., description="Evidence validity: VALID, INSUFFICIENT, or EXPIRED")
    risk: str = Field(..., description="Risk assessment: LOW, MEDIUM, or HIGH")
    reasons: list[str] = Field(default_factory=list, description="Explainable reasons why the decision was allowed, constrained, or blocked")
    preferred_source: str | None = Field(default=None, description="The most authoritative source identified")
    audit_id: str = Field(..., description="Unique audit reference identifier")
    suggested_action: str | None = Field(default=None, description="Recommended next action or clarification prompt for the agent")
    audit_token: str | None = Field(default=None, description="Cryptographic SHA-256 audit signature")
    execution_ms: int | None = Field(default=10, description="Evaluation execution latency in milliseconds")

    @property
    def verdict(self) -> str:
        return self.decision

    @property
    def risk_level(self) -> str:
        return self.risk



class DecisionStreamItemResponse(BaseModel):
    id: uuid.UUID
    audit_id: str
    actor_id: str
    actor_role: str
    decision_prompt: str
    verdict: str
    risk_level: str
    reasons: list[str] = Field(default_factory=list)
    preferred_source: str | None = None
    suggested_action: str | None = None
    audit_token: str
    execution_ms: int = 10
    created_at: datetime | None = None

