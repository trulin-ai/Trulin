import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_permission
from app.core.permissions import Permission
from app.db.database import get_db
from app.db.models.user import User
from app.db.repositories.conflict_repository import ConflictRepository
from app.schemas.conflict import (
    ConflictIssueResponse,
    ConflictResolveRequest,
    ConflictResponse,
    ResolveIssueRequest,
)
from app.services.activity_service import ActivityService
from app.services.conflict_service import ConflictService

router = APIRouter(prefix="/conflicts", tags=["conflicts"])


@router.get("/pending", response_model=list[ConflictResponse])
async def list_pending_conflicts(
    organization_id: uuid.UUID | None = Query(None, description="Optional organization ID filter"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    repo = ConflictRepository(db)
    conflicts = await repo.list_pending_review(
        organization_id=organization_id,
        limit=limit,
        offset=offset,
    )
    return [ConflictResponse.model_validate(c) for c in conflicts]


@router.get("/issues", response_model=list[ConflictIssueResponse])
async def list_conflict_issues(
    organization_id: uuid.UUID | None = Query(None, description="Optional organization ID filter"),
    limit: int = Query(100, ge=1, le=200),
    db: AsyncSession = Depends(get_db),
):
    """List pending conflicts grouped into semantic Governance Issues."""
    service = ConflictService(db)
    issues = await service.get_clustered_conflict_issues(
        organization_id=organization_id,
        limit=limit,
    )
    return [ConflictIssueResponse.model_validate(issue) for issue in issues]


@router.post("/issues/{issue_id}/resolve")
async def resolve_conflict_issue(
    issue_id: str,
    req: ResolveIssueRequest,
    user_name: str = Query(default="Diana Vance", description="Name of acting user"),
    user_role: str = Query(default="reviewer", description="Role of acting user"),
    organization_id: uuid.UUID | None = Query(None, description="Optional organization ID filter"),
    _authorized_user: Optional[User] = Depends(require_permission(Permission.CONFLICTS_RESOLVE)),
    db: AsyncSession = Depends(get_db),
):
    """Resolve an entire clustered Governance Issue in a single atomic action."""
    service = ConflictService(db)
    activity_service = ActivityService(db)
    result = await service.resolve_conflict_issue(
        issue_id=issue_id,
        reviewer_id=req.reviewer_id,
        decision=req.decision,
        chosen_side=req.chosen_side,
        reason=req.reason,
        organization_id=organization_id,
    )
    org_id = organization_id or uuid.UUID("11111111-1111-1111-1111-111111111111")
    resolved_by_id = result.get("reviewer_id") or req.reviewer_id
    await activity_service.log_activity(
        organization_id=org_id,
        user_id=resolved_by_id,
        user_name=user_name,
        user_role=user_role,
        action_type="CONFLICT_RESOLVED",
        target_type="conflict_issue",
        target_id=issue_id,
        target_title=f"Governance Issue {issue_id[:20]} ({result.get('resolved_conflicts_count', 0)} conflicts)",
        domain="Finance & Billing",
        details={
            "decision": req.decision.value if hasattr(req.decision, "value") else str(req.decision),
            "chosen_side": req.chosen_side,
            "resolved_conflicts_count": result.get("resolved_conflicts_count", 0),
            "reason": req.reason,
        },
    )
    await db.commit()
    return result


@router.post("/re-evaluate")
async def re_evaluate_conflicts(
    organization_id: uuid.UUID | None = Query(None, description="Optional organization ID filter"),
    user_role: str = Query(default="reviewer", description="Role of acting user"),
    _authorized_user: Optional[User] = Depends(require_permission(Permission.CONFLICTS_RESOLVE)),
    db: AsyncSession = Depends(get_db),
):
    """Re-evaluate all pending conflicts against the current context-aware contradiction rules and purge false positives."""
    service = ConflictService(db)
    result = await service.re_evaluate_all_pending(organization_id=organization_id)
    return {
        "status": "success",
        "purged_false_positives": result["purged"],
        "retained_conflicts": result["retained"],
        "message": f"Purged {result['purged']} false-positive conflicts. Retained {result['retained']} genuine conflicts.",
    }


@router.post("/auto-resolve")
async def auto_resolve_conflicts_endpoint(
    organization_id: uuid.UUID | None = Query(None, description="Optional organization ID filter"),
    user_name: str = Query(default="Autonomous Precedence Engine", description="Name of acting agent"),
    user_role: str = Query(default="system", description="Role of acting agent"),
    shadow_mode: bool = Query(default=False, description="Run in recommendation-only mode without database mutations"),
    db: AsyncSession = Depends(get_db),
):
    """Autonomous enterprise conflict resolution: sweep pending conflicts, apply deterministic precedence rules, and resolve deterministic/low-blast-radius conflicts without human bottleneck."""
    service = ConflictService(db)
    activity_service = ActivityService(db)
    result = await service.auto_resolve_conflicts(
        organization_id=organization_id,
        shadow_mode=shadow_mode,
    )
    
    org_id = organization_id or uuid.UUID("11111111-1111-1111-1111-111111111111")
    if not shadow_mode and result.get("auto_resolved_count", 0) > 0:
        acting_user_id = await service._ensure_valid_reviewer(organization_id=org_id)
        await activity_service.log_activity(
            organization_id=org_id,
            user_id=acting_user_id,
            user_name=user_name,
            user_role=user_role,
            action_type="AUTO_CONFLICTS_RESOLVED",
            target_type="conflict_batch",
            target_id=str(uuid.uuid4()),
            target_title=f"Autonomous Precedence Resolution ({result['auto_resolved_count']} conflicts)",
            domain="Enterprise Governance",
            details={
                "auto_resolved_count": result["auto_resolved_count"],
                "total_evaluated": result["total_evaluated"],
                "rules_breakdown": result.get("rules_breakdown", {}),
            },
        )
        await db.commit()
    elif shadow_mode:
        result["shadow_mode"] = True
        result["mode"] = "RECOMMENDATION_ONLY"
        
    return result


@router.post("/{conflict_id}/resolve", response_model=ConflictResponse)
async def resolve_conflict(
    conflict_id: uuid.UUID,
    req: ConflictResolveRequest,
    user_name: str = Query(default="Diana Vance", description="Name of acting user"),
    user_role: str = Query(default="reviewer", description="Role of acting user"),
    db: AsyncSession = Depends(get_db),
):
    service = ConflictService(db)
    activity_service = ActivityService(db)
    conflict = await service.resolve_conflict(
        conflict_id=conflict_id,
        reviewer_id=req.reviewer_id,
        decision=req.decision,
        chosen_claim_id=req.chosen_claim_id,
        reason=req.reason,
    )
    # Log resolution activity
    if conflict:
        # Determine organization_id from claim_a if available
        org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
        if conflict.claim_a and conflict.claim_a.organization_id:
            org_id = conflict.claim_a.organization_id
        await activity_service.log_activity(
            organization_id=org_id,
            user_id=conflict.resolved_by or req.reviewer_id,
            user_name=user_name,
            user_role=user_role,
            action_type="CONFLICT_RESOLVED",
            target_type="conflict",
            target_id=str(conflict.id),
            target_title=f"Conflict {str(conflict.id)[:8]} ({conflict.conflict_type})",
            domain="Finance & Billing",
            details={
                "decision": req.decision.value if hasattr(req.decision, "value") else str(req.decision),
                "chosen_claim_id": str(req.chosen_claim_id) if req.chosen_claim_id else None,
                "reason": req.reason,
            },
        )
    await db.commit()
    return ConflictResponse.model_validate(conflict)



