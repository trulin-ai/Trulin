import uuid
from typing import Any, Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.steward_agent import StewardAgentService

router = APIRouter(prefix="/steward", tags=["steward"])


class StewardActionRequest(BaseModel):
    action_type: str
    target_id: uuid.UUID
    payload: Optional[Dict[str, Any]] = None
    reviewer_id: Optional[uuid.UUID] = None
    rationale: Optional[str] = None


@router.get("/audit")
async def run_context_audit(
    organization_id: uuid.UUID = Query(uuid.UUID("11111111-1111-1111-1111-111111111111"), description="Organization ID"),
    db: AsyncSession = Depends(get_db),
):
    """Executes proactive data steward heuristic scan across documents, claims, and active contradictions."""
    agent = StewardAgentService(db)
    return await agent.run_context_audit(organization_id)


@router.post("/actions/apply")
async def apply_steward_action(
    req: StewardActionRequest,
    organization_id: uuid.UUID = Query(uuid.UUID("11111111-1111-1111-1111-111111111111"), description="Organization ID"),
    user_name: str = Query(default="Compliance Auditor", description="Acting user name"),
    user_role: str = Query(default="reviewer", description="Role of acting user"),
    db: AsyncSession = Depends(get_db),
):
    """Executes a recommended steward curation action (conflict resolution, deprecation, evidence attachment).

    Separation of Duties (SoD) Enforced:
    Only authorized roles (reviewer, compliance_officer, admin, cco) may apply curation recommendations.
    """
    allowed_roles = {"reviewer", "compliance_officer", "admin", "cco", "system", "auditor"}
    if user_role.lower() not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Separation of Duties (SoD) Barred: Role '{user_role}' cannot apply curation recommendations. Auditor clearance required."
        )

    agent = StewardAgentService(db)
    payload = req.payload or {}
    if req.rationale and "rationale" not in payload:
        payload["rationale"] = req.rationale

    result = await agent.apply_steward_action(
        action_type=req.action_type,
        target_id=req.target_id,
        payload=payload,
        reviewer_id=req.reviewer_id,
        user_name=user_name,
        user_role=user_role,
        organization_id=organization_id,
    )
    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=result.get("error", "Action failed"))
    return result
