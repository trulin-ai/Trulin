import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, require_authenticated_permission
from app.core.permissions import Permission
from app.db.database import get_db
from app.db.enums import ClaimStatus, ConflictStatus, RecordStatus, UserRole
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.data_source import DataSource
from app.db.models.folder import Folder
from app.db.models.user import User
from app.db.repositories.user_repository import UserRepository
from app.schemas.user import (
    ActivityLogCreate,
    ActivityLogResponse,
    UserCreate,
    UserResponse,
    UserUpdate,
)
from app.services.activity_service import ActivityService

router = APIRouter(prefix="/users", tags=["Users & Governance"])


def _resolve_authorized_org(current_user: User, requested_org_id: uuid.UUID | None) -> uuid.UUID:
    """Enforce tenant isolation by deriving org scope from the authenticated user."""
    if requested_org_id is not None and requested_org_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cross-organization user or governance access denied.",
        )
    return current_user.organization_id


def _role_str(role: Any) -> str:
    return role.value if hasattr(role, "value") else str(role)


@router.get("", response_model=list[UserResponse])
async def list_users(
    organization_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List team members for the authenticated user's organization (read-only, no cross-tenant side effects)."""
    org_id = _resolve_authorized_org(current_user, organization_id)
    user_repo = UserRepository(db)
    return await user_repo.list_by_organization(org_id)


@router.post("", response_model=UserResponse, status_code=201)
async def create_user(
    user_in: UserCreate,
    current_user: User = Depends(require_authenticated_permission(Permission.ORG_INVITE)),
    db: AsyncSession = Depends(get_db),
):
    """Create a team member within the authenticated user's organization."""
    org_id = _resolve_authorized_org(current_user, user_in.organization_id)
    user_repo = UserRepository(db)
    activity_service = ActivityService(db)

    existing = await user_repo.get_by_email(org_id, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail="User with this email already exists in organization.")

    user = await user_repo.create_user(
        organization_id=org_id,
        name=user_in.name,
        email=user_in.email.strip().lower(),
        role=user_in.role,
        title=user_in.title,
        department=user_in.department,
        avatar_url=user_in.avatar_url,
    )

    await activity_service.log_activity(
        organization_id=org_id,
        user_id=current_user.id,
        user_name=current_user.name,
        user_role=_role_str(current_user.role),
        action_type="MEMBER_INVITED",
        target_type="user",
        target_id=str(user.id),
        target_title=f"{user.name} ({_role_str(user.role)})",
        domain=user.department or "General",
        details={"email": user.email, "role": _role_str(user.role), "title": user.title},
    )
    await db.commit()
    return user


@router.patch("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: uuid.UUID,
    user_in: UserUpdate,
    current_user: User = Depends(require_authenticated_permission(Permission.ORG_MEMBERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Update user role, title, department, or lifecycle status with SoD & last-admin guards."""
    user_repo = UserRepository(db)
    activity_service = ActivityService(db)

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot modify a user in another organization.",
        )

    is_target_admin = _role_str(user.role).lower() == "admin" and user.status == RecordStatus.ACTIVE
    demoting_admin = user_in.role is not None and _role_str(user_in.role).lower() != "admin"
    deactivating_admin = user_in.status is not None and user_in.status != RecordStatus.ACTIVE
    if is_target_admin and (demoting_admin or deactivating_admin):
        admin_count_stmt = (
            select(func.count(User.id))
            .where(User.organization_id == user.organization_id)
            .where(User.role == UserRole.ADMIN)
            .where(User.status == RecordStatus.ACTIVE)
        )
        res = await db.execute(admin_count_stmt)
        if (res.scalar() or 0) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot demote or deactivate the sole active Administrator of the organization.",
            )

    if user_in.name is not None:
        user.name = user_in.name
    if user_in.role is not None and user_in.role != user.role:
        old_role = _role_str(user.role)
        user.role = user_in.role
        await activity_service.log_activity(
            organization_id=user.organization_id,
            user_id=current_user.id,
            user_name=current_user.name,
            user_role=_role_str(current_user.role),
            action_type="ROLE_UPDATED",
            target_type="user",
            target_id=str(user.id),
            target_title=user.name,
            domain=user.department or "General",
            details={
                "old_role": old_role,
                "new_role": _role_str(user.role),
                "reason": user_in.reason,
            },
        )
    if user_in.status is not None and user_in.status != user.status:
        old_status = _role_str(user.status)
        user.status = user_in.status
        if user_in.status != RecordStatus.ACTIVE:
            user.active_session_id = None
        await activity_service.log_activity(
            organization_id=user.organization_id,
            user_id=current_user.id,
            user_name=current_user.name,
            user_role=_role_str(current_user.role),
            action_type="MEMBER_STATUS_UPDATED",
            target_type="user",
            target_id=str(user.id),
            target_title=user.name,
            domain=user.department or "General",
            details={
                "old_status": old_status,
                "new_status": _role_str(user.status),
                "reason": user_in.reason,
            },
        )
    if user_in.title is not None:
        user.title = user_in.title
    if user_in.department is not None:
        user.department = user_in.department
    if user_in.avatar_url is not None:
        user.avatar_url = user_in.avatar_url
    if user_in.phone is not None:
        user.phone = user_in.phone
    if user_in.bio is not None:
        user.bio = user_in.bio
    if user_in.timezone is not None:
        user.timezone = user_in.timezone
    if user_in.user_preferences is not None:
        user.user_preferences = user_in.user_preferences

    await db.commit()
    await db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    reason: str | None = Query(default=None),
    current_user: User = Depends(require_authenticated_permission(Permission.ORG_MEMBERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Safely deactivate a team member, revoking active sessions while preserving audit history."""
    user_repo = UserRepository(db)
    activity_service = ActivityService(db)

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
    if user.organization_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cannot remove a user in another organization.",
        )

    if _role_str(user.role).lower() == "admin" and user.status == RecordStatus.ACTIVE:
        admin_count_stmt = (
            select(func.count(User.id))
            .where(User.organization_id == user.organization_id)
            .where(User.role == UserRole.ADMIN)
            .where(User.status == RecordStatus.ACTIVE)
        )
        res = await db.execute(admin_count_stmt)
        if (res.scalar() or 0) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot deactivate the sole active Administrator of the organization.",
            )

    old_status = _role_str(user.status)
    user.status = RecordStatus.DEACTIVATED
    user.active_session_id = None

    await activity_service.log_activity(
        organization_id=user.organization_id,
        user_id=current_user.id,
        user_name=current_user.name,
        user_role=_role_str(current_user.role),
        action_type="MEMBER_DEACTIVATED",
        target_type="user",
        target_id=str(user.id),
        target_title=f"{user.name} ({_role_str(user.role)})",
        domain=user.department or "General",
        details={
            "email": user.email,
            "old_status": old_status,
            "new_status": RecordStatus.DEACTIVATED.value,
            "reason": reason or "Deactivated by administrator",
        },
    )

    await db.commit()
    return None


@router.post("/seed-personas", response_model=list[UserResponse])
async def seed_personas(
    organization_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(require_authenticated_permission(Permission.ORG_MEMBERS_MANAGE)),
    db: AsyncSession = Depends(get_db),
):
    """Explicitly seed org-scoped default operational personas for the authorized organization."""
    org_id = _resolve_authorized_org(current_user, organization_id)
    user_repo = UserRepository(db)
    users = await user_repo.seed_default_personas(org_id)
    await db.commit()
    return users


@router.get("/activity", response_model=dict[str, Any])
async def list_activity_logs(
    organization_id: uuid.UUID | None = Query(default=None),
    user_id: uuid.UUID | None = Query(default=None),
    action_type: str | None = Query(default=None),
    domain: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_authenticated_permission(Permission.DECISIONS_AUDIT)),
    db: AsyncSession = Depends(get_db),
):
    """Query paginated, tenant-scoped governance activity stream."""
    org_id = _resolve_authorized_org(current_user, organization_id)
    activity_service = ActivityService(db)
    activities, total = await activity_service.get_activities(
        organization_id=org_id,
        user_id=user_id,
        action_type=action_type,
        domain=domain,
        limit=limit,
        offset=offset,
    )
    return {
        "total": total,
        "limit": limit,
        "offset": offset,
        "activities": [ActivityLogResponse.model_validate(a) for a in activities],
    }


@router.post("/activity", response_model=ActivityLogResponse, status_code=201)
async def create_activity_log(
    activity_in: ActivityLogCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Record an authenticated operational activity log attributed to the caller."""
    org_id = _resolve_authorized_org(current_user, activity_in.organization_id)
    activity_service = ActivityService(db)
    log_entry = await activity_service.log_activity(
        organization_id=org_id,
        user_id=current_user.id,
        user_name=current_user.name,
        user_role=_role_str(current_user.role),
        action_type=activity_in.action_type,
        target_type=activity_in.target_type,
        target_id=activity_in.target_id,
        target_title=activity_in.target_title,
        domain=activity_in.domain,
        details=activity_in.details,
    )
    await db.commit()
    return ActivityLogResponse.model_validate(log_entry)


@router.get("/domains", response_model=dict[str, Any])
async def list_governance_domains(
    organization_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(require_authenticated_permission(Permission.SOURCES_READ)),
    db: AsyncSession = Depends(get_db),
):
    """Return real, tenant-scoped governance domain metrics from organization workspaces, sources, claims, and conflicts."""
    org_id = _resolve_authorized_org(current_user, organization_id)

    sources_res = await db.execute(
        select(func.count(DataSource.id)).where(
            DataSource.organization_id == org_id,
            DataSource.status != RecordStatus.DELETED,
        )
    )
    total_sources = sources_res.scalar() or 0

    claims_res = await db.execute(
        select(func.count(Claim.id)).where(Claim.organization_id == org_id)
    )
    total_claims = claims_res.scalar() or 0

    verified_res = await db.execute(
        select(func.count(Claim.id)).where(
            Claim.organization_id == org_id,
            Claim.status == ClaimStatus.VERIFIED,
        )
    )
    verified_claims = verified_res.scalar() or 0

    conflicts_res = await db.execute(
        select(func.count(ClaimConflict.id))
        .join(Claim, ClaimConflict.claim_a_id == Claim.id)
        .where(
            Claim.organization_id == org_id,
            ClaimConflict.resolution_status != ConflictStatus.RESOLVED,
        )
    )
    open_conflicts = conflicts_res.scalar() or 0

    trust_res = await db.execute(
        select(func.avg(ClaimTrustScore.overall_score))
        .join(Claim, ClaimTrustScore.claim_id == Claim.id)
        .where(Claim.organization_id == org_id)
    )
    avg_trust = trust_res.scalar()
    avg_trust_pct = round(float(avg_trust) * 100, 1) if avg_trust is not None and float(avg_trust) <= 1.0 else (round(float(avg_trust), 1) if avg_trust is not None else None)

    folders_res = await db.execute(
        select(Folder)
        .where(Folder.organization_id == org_id, Folder.depth == 0)
        .order_by(Folder.created_at.asc())
    )
    root_folders = folders_res.scalars().all()

    if root_folders:
        domains = [
            {
                "id": str(f.id),
                "name": f.name,
                "folder_type": f.folder_type,
                "organization_id": str(org_id),
                "source_count": total_sources if idx == 0 else None,
                "claim_count": total_claims if idx == 0 else None,
                "verified_claim_count": verified_claims if idx == 0 else None,
                "open_conflict_count": open_conflicts if idx == 0 else None,
                "average_trust_score": avg_trust_pct if idx == 0 else None,
                "created_at": f.created_at.isoformat() if f.created_at else None,
                "is_org_aggregate": idx == 0,
            }
            for idx, f in enumerate(root_folders)
        ]
    else:
        domains = [
            {
                "id": str(org_id),
                "name": "Organization Governance Scope",
                "folder_type": "general",
                "organization_id": str(org_id),
                "source_count": total_sources,
                "claim_count": total_claims,
                "verified_claim_count": verified_claims,
                "open_conflict_count": open_conflicts,
                "average_trust_score": avg_trust_pct,
                "created_at": None,
                "is_org_aggregate": True,
            }
        ]

    return {
        "organization_id": str(org_id),
        "is_preview": False,
        "summary": {
            "domain_count": len(domains),
            "source_count": total_sources,
            "claim_count": total_claims,
            "verified_claim_count": verified_claims,
            "open_conflict_count": open_conflicts,
            "average_trust_score": avg_trust_pct,
        },
        "domains": domains,
    }
