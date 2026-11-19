import decimal
import uuid
from pydantic import BaseModel, Field

from app.schemas.governed_context import GovernedContextPackage


class ContextQueryRequest(BaseModel):
    organization_id: uuid.UUID
    agent_id: uuid.UUID
    query: str
    min_trust_score: decimal.Decimal = Field(
        default=decimal.Decimal("0.8000"),
        ge=0,
        le=1,
    )
    max_results: int = Field(default=10, gt=0)
    domain: str | None = None
    workspace_id: str | None = None
    canonical_only: bool = Field(default=True, description="When true, excludes derived summaries to ensure only governing operative rules reach agents")


class ContextSourceInfo(BaseModel):
    document: str
    section: str | None = None
    page: int | None = None
    folder_name: str | None = None
    folder_id: str | None = None


class ContextValidityInfo(BaseModel):
    status: str
    valid_from: str | None = None
    valid_until: str | None = None


class SectionContextItem(BaseModel):
    document_title: str
    section: str | None = None
    text: str
    is_normative: bool = False


class ContextItemResponse(BaseModel):
    claim: str
    trust_score: decimal.Decimal
    validity: ContextValidityInfo
    source: ContextSourceInfo
    evidence: list[str] = []
    section_context: list[SectionContextItem] = Field(default_factory=list)
    claim_type: str | None = None
    is_canonical: bool = True
    claim_id: str | None = None
    document_id: str | None = None
    evidence_lane: str = "canonical"
    governed_package: GovernedContextPackage | None = None


class ContextQueryResponse(BaseModel):
    context: list[ContextItemResponse] = []
    governed_packages: list[GovernedContextPackage] = []
    conflicts: list[dict] = []
    confidence: decimal.Decimal = decimal.Decimal("1.0000")
