import logging
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.schemas.drift import (
    ClaimRemediateRequest,
    ClaimRemediateResponse,
    DriftAnalysisResponse,
)
from app.services.drift_decay_service import (
    analyze_context_drift,
    remediate_claim_decay,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/steward/drift", tags=["Context Drift & Claim Decay Detection"])


@router.get("", response_model=DriftAnalysisResponse)
async def get_drift_analysis(
    organization_id: uuid.UUID = Query(default=uuid.UUID("11111111-1111-1111-1111-111111111111")),
    db: AsyncSession = Depends(get_db),
):
    """Retrieve full context freshness index, decay radar, and list of stale claims."""
    return await analyze_context_drift(organization_id, session=db)


@router.post("/scan", response_model=DriftAnalysisResponse)
async def trigger_drift_scan(
    organization_id: uuid.UUID = Query(default=uuid.UUID("11111111-1111-1111-1111-111111111111")),
    db: AsyncSession = Depends(get_db),
):
    """Triggers an active background sweep that computes temporal decay and drift metrics."""
    return await analyze_context_drift(organization_id, session=db)


@router.post("/remediate", response_model=ClaimRemediateResponse)
async def remediate_decayed_claim(
    payload: ClaimRemediateRequest,
    user_role: str = Query(default="data_owner", description="Role of acting user"),
    db: AsyncSession = Depends(get_db),
):
    """Remediates a stale claim via Data Owner Re-Attestation or Retirement.

    Separation of Duties (SoD) Enforced:
    Only verified Data Owners, Reviewers, Compliance Officers, or Admins may execute re-attestation or retirement.
    """
    allowed_roles = {"data_owner", "reviewer", "compliance_officer", "admin", "cco", "system", "auditor"}
    if user_role.lower() not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Separation of Duties (SoD) Barred: Role '{user_role}' cannot remediate or re-attest claims. Data Owner clearance required."
        )

    return await remediate_claim_decay(payload, session=db)
