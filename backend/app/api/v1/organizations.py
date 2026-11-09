import secrets
import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.deps import get_current_user, get_optional_current_user
from app.core.security import create_access_token, create_refresh_token, get_password_hash
from app.db.database import get_db
from app.db.enums import OrganizationStatus, RecordStatus, UserRole
from app.db.models.agent import Agent
from app.db.models.data_source import DataSource
from app.db.models.document import Document
from app.db.models.organization import Organization
from app.db.models.organization_invite import OrganizationInvite
from app.db.models.user import User
from app.db.models.user_activity import UserActivityLog
from app.schemas.auth import UserResponse
from app.schemas.organization import (
    InviteAcceptRequest,
    InviteCreateRequest,
    InviteInspectResponse,
    InviteResponse,
    OrganizationCreate,
    OrganizationMemberResponse,
    OrganizationMemberRoleUpdate,
    OrganizationResponse,
    OrganizationSettingsUpdate,
    OrganizationSetupMemberInvite,
    OrganizationSetupStatusResponse,
    OrganizationSetupWizardRequest,
    OrganizationSetupWizardResponse,
    SetupStepDetail,
    TenantSwitchResponse,
    WorkspaceCreate,
    WorkspaceResponse,
    WorkspaceUpdate,
)

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _build_org_response(org: Organization, member_count: int = 0) -> OrganizationResponse:
    whitelist = org.domain_whitelist if org.domain_whitelist is not None else []
    auth_methods = org.allowed_auth_methods if org.allowed_auth_methods is not None else ["password", "google", "microsoft", "okta"]
    gov_cfg = org.governance_config if getattr(org, "governance_config", None) is not None else {}
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        slug=org.slug,
        status=org.status,
        domain_whitelist=whitelist,
        allowed_auth_methods=auth_methods,
        governance_config=gov_cfg,
        setup_completed=bool(getattr(org, "setup_completed", False)),
        member_count=member_count,
        created_at=org.created_at or datetime.now(timezone.utc),
        updated_at=org.updated_at or datetime.now(timezone.utc),
    )


def _build_user_response(user: User, org_name: Optional[str] = None) -> UserResponse:
    resolved_org_name = org_name or (user.organization.name if user.organization else "Enterprise Tenant")
    return UserResponse(
        id=user.id,
        organization_id=user.organization_id,
        organization_name=resolved_org_name,
        name=user.name,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        status=user.status.value if hasattr(user.status, "value") else str(user.status),
        avatar_url=user.avatar_url,
        title=user.title,
        department=user.department,
    )


# ==========================================
# 1. Organization Listings & Registration
# ==========================================

@router.get("", response_model=List[OrganizationResponse])
async def list_organizations(
    db: AsyncSession = Depends(get_db),
):
    """List all registered enterprise organizations / tenant workspaces with member counts."""
    # Query organizations with aggregate member count
    stmt = (
        select(Organization, func.count(User.id).label("member_count"))
        .outerjoin(User, (User.organization_id == Organization.id) & (User.status == RecordStatus.ACTIVE))
        .group_by(Organization.id)
        .order_by(Organization.created_at.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()

    response = []
    for org, count in rows:
        response.append(_build_org_response(org, member_count=count or 0))
    return response


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
async def create_organization(
    data: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Optional[User] = Depends(get_optional_current_user),
):
    """Register a new enterprise organization / client company tenant."""
    slug = data.slug.strip().lower()
    existing_stmt = select(Organization).where(Organization.slug == slug).limit(1)
    res_exist = await db.execute(existing_stmt)
    if res_exist.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Organization with slug '{slug}' already exists.",
        )

    if current_user:
        # Check if user already belongs to an unconfigured pending organization
        user_org_stmt = select(Organization).where(Organization.id == current_user.organization_id).limit(1)
        res_uorg = await db.execute(user_org_stmt)
        user_org = res_uorg.scalar_one_or_none()
        if user_org and not user_org.setup_completed:
            # Upgrade and activate the user's pending organization
            user_org.name = data.name.strip()
            user_org.slug = slug
            user_org.setup_completed = True
            if data.domain_whitelist:
                user_org.domain_whitelist = data.domain_whitelist
            current_user.role = UserRole.ADMIN

            gov_cfg = dict(user_org.governance_config or {})
            if "workspaces" not in gov_cfg or not gov_cfg["workspaces"]:
                gov_cfg["workspaces"] = [{
                    "id": f"ws_{user_org.id.hex[:10]}",
                    "name": f"{user_org.name} Workspace",
                    "domain": "governance",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }]
                user_org.governance_config = dict(gov_cfg)

            await db.commit()
            await db.refresh(user_org)
            return _build_org_response(user_org, member_count=1)

    init_gov_cfg = dict(data.governance_config or {})
    if "workspaces" not in init_gov_cfg or not init_gov_cfg["workspaces"]:
        init_gov_cfg["workspaces"] = [{
            "id": f"ws_{uuid.uuid4().hex[:10]}",
            "name": f"{data.name.strip()} Workspace",
            "domain": "governance",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }]

    org = Organization(
        id=uuid.uuid4(),
        name=data.name.strip(),
        slug=slug,
        status=OrganizationStatus.ACTIVE,
        domain_whitelist=data.domain_whitelist or [],
        allowed_auth_methods=data.allowed_auth_methods or ["password", "google", "microsoft", "okta"],
        governance_config=init_gov_cfg,
        setup_completed=True,
    )
    db.add(org)
    await db.flush()

    if current_user:
        new_membership = User(
            id=uuid.uuid4(),
            organization_id=org.id,
            name=current_user.name,
            email=current_user.email,
            role=UserRole.ADMIN,
            status=RecordStatus.ACTIVE,
            title="Organization Creator & Admin",
            department="Governance & Risk",
            is_verified=True,
            avatar_url=current_user.avatar_url,
            hashed_password=current_user.hashed_password,
        )
        db.add(new_membership)

    await db.commit()
    await db.refresh(org)
    return _build_org_response(org, member_count=1 if current_user else 0)


@router.get("/my-organizations", response_model=List[dict])
async def get_my_organizations(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all organizations the current authenticated user belongs to with roles."""
    if not current_user:
        return []

    stmt = (
        select(User)
        .where(User.email.ilike(current_user.email))
        .options(selectinload(User.organization))
        .order_by(User.created_at.desc())
    )
    res = await db.execute(stmt)
    memberships = res.scalars().all()

    return [
        {
            "id": str(m.organization.id),
            "name": m.organization.name,
            "slug": m.organization.slug,
            "role": m.role.value if hasattr(m.role, "value") else str(m.role),
            "setup_completed": bool(getattr(m.organization, "setup_completed", False)),
            "governance_config": m.organization.governance_config or {},
            "domain_whitelist": m.organization.domain_whitelist or [],
        }
        for m in memberships
        if m.organization
    ]


@router.get("/my-invitations", response_model=List[InviteResponse])
async def get_my_invitations(
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List pending invitations addressed to current authenticated user's email."""
    if not current_user:
        return []

    stmt = (
        select(OrganizationInvite)
        .where(
            (OrganizationInvite.email.ilike(current_user.email))
            & (OrganizationInvite.status == "pending")
        )
        .options(selectinload(OrganizationInvite.organization))
        .order_by(OrganizationInvite.created_at.desc())
    )
    res = await db.execute(stmt)
    invites = res.scalars().all()

    return [
        InviteResponse(
            id=inv.id,
            organization_id=inv.organization_id,
            organization_name=inv.organization.name if inv.organization else "Enterprise Tenant",
            email=inv.email,
            role=inv.role.value if hasattr(inv.role, "value") else str(inv.role),
            token=inv.token,
            invite_url=f"http://localhost:4000/invite?token={inv.token}",
            status=inv.status,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
        )
        for inv in invites
    ]


# ==========================================
# 2. Multi-Step Organization Setup & Status
# ==========================================

@router.get("/{org_id}/setup-status", response_model=OrganizationSetupStatusResponse)
async def get_organization_setup_status(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve multi-step setup progress, completion metrics, and checklist items for an organization."""
    org_stmt = select(Organization).where(Organization.id == org_id).limit(1)
    res_org = await db.execute(org_stmt)
    org = res_org.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    # 1. Identity & Domain Whitelist Step
    has_domains = bool(org.domain_whitelist and len(org.domain_whitelist) > 0)
    step_identity = SetupStepDetail(
        id="identity",
        title="Organization Profile & Corporate Domains",
        description="Verify organization name, isolated tenant slug, and allowed corporate email domains.",
        completed=bool(org.name and org.slug and has_domains),
        data={
            "name": org.name,
            "slug": org.slug,
            "domains": org.domain_whitelist or [],
            "auth_methods": org.allowed_auth_methods or [],
        },
    )

    # 2. Team Members & Separation of Duties (SoD)
    user_stmt = select(User).where((User.organization_id == org.id) & (User.status == RecordStatus.ACTIVE))
    res_users = await db.execute(user_stmt)
    users = res_users.scalars().all()
    roles = {u.role.value if hasattr(u.role, "value") else str(u.role) for u in users}
    step_team = SetupStepDetail(
        id="team",
        title="Team Directory & Governance Roles",
        description="Assign key roles (Admin, Data Steward, Risk Auditor, Developer) with Separation of Duties.",
        completed=len(users) >= 2 or (len(users) >= 1 and "admin" in roles),
        data={
            "member_count": len(users),
            "roles_present": list(roles),
        },
    )

    # 3. Governance Policies & Trust Thresholds
    gov_cfg = org.governance_config or {}
    has_threshold = "trust_threshold" in gov_cfg
    step_governance = SetupStepDetail(
        id="governance",
        title="Trust Score Thresholds & Conflict Gate",
        description="Configure baseline evidence trust threshold (e.g. 0.70) and automated escalation rules.",
        completed=has_threshold or bool(org.setup_completed),
        data=gov_cfg,
    )

    # 4. Knowledge Ingestion & Baseline Policies
    doc_stmt = select(func.count(Document.id)).where((Document.organization_id == org.id) & (Document.status == RecordStatus.ACTIVE))
    res_docs = await db.execute(doc_stmt)
    doc_count = res_docs.scalar() or 0

    source_stmt = select(func.count(DataSource.id)).where((DataSource.organization_id == org.id) & (DataSource.status == RecordStatus.ACTIVE))
    res_sources = await db.execute(source_stmt)
    source_count = res_sources.scalar() or 0

    step_knowledge = SetupStepDetail(
        id="knowledge",
        title="Evidence Ingestion & Policy Corpus",
        description="Connect enterprise data sources (Confluence, SharePoint, GitHub) or ingest baseline policies.",
        completed=(doc_count + source_count) > 0,
        data={
            "document_count": doc_count,
            "data_source_count": source_count,
        },
    )

    # 5. Agent Integrations & MCP Key
    agent_stmt = select(func.count(Agent.id)).where((Agent.organization_id == org.id) & (Agent.status == RecordStatus.ACTIVE))
    res_agents = await db.execute(agent_stmt)
    agent_count = res_agents.scalar() or 0

    step_mcp = SetupStepDetail(
        id="mcp_api",
        title="MCP Gateway API Token & Live Connectors",
        description="Provision autonomous AI agent connection token and verify Context Trust Gateway API.",
        completed=agent_count > 0 or bool(org.setup_completed),
        data={
            "agent_count": agent_count,
            "api_ready": True,
        },
    )

    all_steps = [step_identity, step_team, step_governance, step_knowledge, step_mcp]
    completed_count = sum(1 for s in all_steps if s.completed)
    pct = int((completed_count / len(all_steps)) * 100)
    is_fully_done = (pct == 100) or bool(org.setup_completed)

    next_step = "complete"
    for s in all_steps:
        if not s.completed:
            next_step = s.id
            break

    return OrganizationSetupStatusResponse(
        organization_id=org.id,
        organization_name=org.name,
        setup_completed=is_fully_done,
        completion_percentage=pct,
        completed_steps_count=completed_count,
        total_steps_count=len(all_steps),
        steps=all_steps,
        next_recommended_step=next_step,
    )


@router.post("/setup-wizard", response_model=OrganizationSetupWizardResponse)
async def complete_organization_setup_wizard(
    data: OrganizationSetupWizardRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Execute complete end-to-end organization onboarding wizard with profile, team, policies, and initial context."""
    import re

    # 1. Resolve or create organization
    org = None
    if data.organization_id:
        org_stmt = select(Organization).where(Organization.id == data.organization_id).limit(1)
        res_org = await db.execute(org_stmt)
        org = res_org.scalar_one_or_none()

    if not org:
        name_clean = data.name.strip()
        slug_clean = data.slug.strip().lower() if data.slug else re.sub(r"[^a-zA-Z0-9-]", "-", name_clean.lower())[:50]
        # check slug uniqueness
        check_stmt = select(Organization).where(Organization.slug == slug_clean).limit(1)
        res_check = await db.execute(check_stmt)
        if res_check.scalar_one_or_none():
            slug_clean = f"{slug_clean}-{secrets.token_hex(3)}"

        org = Organization(
            id=uuid.uuid4(),
            name=name_clean,
            slug=slug_clean,
            status=OrganizationStatus.ACTIVE,
        )
        db.add(org)
        await db.flush()

    # 2. Update identity & whitelists
    if data.name:
        org.name = data.name.strip()
    if data.domain_whitelist:
        cleaned_domains = [d.strip().lower().replace("@", "") for d in data.domain_whitelist if d.strip()]
        org.domain_whitelist = cleaned_domains
    if data.allowed_auth_methods:
        org.allowed_auth_methods = data.allowed_auth_methods

    # 3. Store governance config & thresholds
    gov_cfg = {
        "industry": data.industry or "Financial Services & Capital Markets",
        "trust_threshold": data.trust_threshold,
        "conflict_policy": data.conflict_policy,
        "regulatory_frameworks": data.regulatory_frameworks or ["NIST AI 600-1", "EU AI Act"],
        "liability_cap_usd": data.liability_cap_usd,
        "onboarded_at": datetime.now(timezone.utc).isoformat(),
    }
    if data.initial_workspace:
        gov_cfg["workspaces"] = [data.initial_workspace]
    org.governance_config = gov_cfg
    org.setup_completed = True

    # 4. Ensure admin user belongs to this org
    active_user = None
    if current_user:
        mem_stmt = select(User).where((User.organization_id == org.id) & (User.email.ilike(current_user.email))).limit(1)
        res_mem = await db.execute(mem_stmt)
        active_user = res_mem.scalar_one_or_none()
        if active_user:
            active_user.role = UserRole.ADMIN
            active_user.status = RecordStatus.ACTIVE
            await db.flush()
        elif current_user.organization_id == org.id:
            active_user = current_user
            active_user.role = UserRole.ADMIN
            active_user.status = RecordStatus.ACTIVE
            await db.flush()
        else:
            # Multi-org: User is creating a second (or new) organization where they are Admin
            active_user = User(
                id=uuid.uuid4(),
                organization_id=org.id,
                name=current_user.name,
                email=current_user.email,
                role=UserRole.ADMIN,
                status=RecordStatus.ACTIVE,
                title="Organization Creator & Admin",
                department="Governance & Risk",
                is_verified=True,
                avatar_url=current_user.avatar_url,
                hashed_password=current_user.hashed_password,
            )
            db.add(active_user)
            await db.flush()
    else:
        admin_stmt = select(User).where((User.organization_id == org.id) & (User.role == UserRole.ADMIN)).limit(1)
        res_admin = await db.execute(admin_stmt)
        active_user = res_admin.scalar_one_or_none()
        if not active_user:
            first_domain = org.domain_whitelist[0] if (org.domain_whitelist and len(org.domain_whitelist) > 0) else "enterprise.local"
            active_user = User(
                id=uuid.uuid4(),
                organization_id=org.id,
                name="Compliance Administrator",
                email=f"admin@{first_domain}",
                role=UserRole.ADMIN,
                status=RecordStatus.ACTIVE,
                title="Chief Compliance Officer",
                department="Governance & Risk",
                is_verified=True,
                hashed_password=get_password_hash(uuid.uuid4().hex),
            )
            db.add(active_user)
            await db.flush()

    # 5. Provision / invite initial team members
    for member in data.initial_members:
        clean_email = member.email.strip().lower()
        exist_stmt = select(User).where((User.organization_id == org.id) & (User.email == clean_email)).limit(1)
        res_exist = await db.execute(exist_stmt)
        if not res_exist.scalar_one_or_none():
            try:
                assigned_role = UserRole(member.role.lower())
            except ValueError:
                assigned_role = UserRole.REVIEWER

            new_user = User(
                id=uuid.uuid4(),
                organization_id=org.id,
                name=member.name.strip() if member.name else clean_email.split("@")[0].replace(".", " ").title(),
                email=clean_email,
                role=assigned_role,
                status=RecordStatus.ACTIVE,
                title="Governance Team Member",
                department=member.department or "Compliance Operations",
                is_verified=True,
            )
            db.add(new_user)

            invite = OrganizationInvite(
                id=uuid.uuid4(),
                organization_id=org.id,
                email=clean_email,
                role=assigned_role,
                token=secrets.token_urlsafe(32),
                invited_by_id=active_user.id,
                expires_at=datetime.now(timezone.utc) + timedelta(days=14),
                status="accepted",
            )
            db.add(invite)

    # 6. Seed baseline governance policy document if requested and org has no documents
    if data.seed_baseline_policies:
        doc_check_stmt = select(Document).where(Document.organization_id == org.id).limit(1)
        res_doc_check = await db.execute(doc_check_stmt)
        if not res_doc_check.scalar_one_or_none():
            source = DataSource(
                id=uuid.uuid4(),
                organization_id=org.id,
                name="Enterprise Governance & Policy Hub",
                source_type="confluence",
                source_family="document",
                source_intent="governance_policy",
                domain="Compliance",
                status=RecordStatus.ACTIVE,
                capabilities={"realtime_sync": True, "claim_extraction": True},
            )
            db.add(source)
            await db.flush()

            base_doc = Document(
                id=uuid.uuid4(),
                organization_id=org.id,
                source_id=source.id,
                title=f"{org.name} Autonomous AI Governance & Context Standard",
                document_type="policy",
                domain="Compliance",
                content_hash=secrets.token_hex(32),
                status=RecordStatus.ACTIVE,
            )
            db.add(base_doc)

    # 7. Ensure Default Agent exists
    agent_check_stmt = select(Agent).where(Agent.organization_id == org.id).limit(1)
    res_agent_check = await db.execute(agent_check_stmt)
    if not res_agent_check.scalar_one_or_none():
        agent = Agent(
            id=uuid.uuid4(),
            organization_id=org.id,
            name=f"{org.name} Context Gateway Agent",
            description="Autonomous Context Trust Validation Gate Agent for MCP Clients",
            agent_type="mcp_gateway",
            status=RecordStatus.ACTIVE,
        )
        db.add(agent)

    # 8. Log setup activity
    activity = UserActivityLog(
        id=uuid.uuid4(),
        organization_id=org.id,
        user_id=active_user.id if active_user else None,
        user_name=active_user.name if active_user else "System Admin",
        user_role=active_user.role.value if hasattr(active_user.role, "value") else str(active_user.role),
        action_type="ORGANIZATION_SETUP_COMPLETED",
        target_type="organization",
        target_id=str(org.id),
        target_title=org.name,
        domain="Governance",
        details={
            "industry": data.industry,
            "trust_threshold": data.trust_threshold,
            "initial_member_count": len(data.initial_members),
            "domains": org.domain_whitelist,
        },
    )
    db.add(activity)

    await db.commit()
    await db.refresh(org)

    new_token = create_access_token(
        subject=str(active_user.id),
        claims={
            "email": active_user.email,
            "role": active_user.role.value if hasattr(active_user.role, "value") else str(active_user.role),
            "org_id": str(org.id),
            "name": active_user.name,
        },
    )

    mcp_api_key = f"ctl_live_{secrets.token_hex(16)}"
    setup_status = await get_organization_setup_status(org.id, db)

    count_stmt = select(func.count(User.id)).where((User.organization_id == org.id) & (User.status == RecordStatus.ACTIVE))
    res_count = await db.execute(count_stmt)
    m_count = res_count.scalar() or 0

    return OrganizationSetupWizardResponse(
        organization=_build_org_response(org, member_count=m_count),
        status=setup_status,
        access_token=new_token,
        mcp_api_key=mcp_api_key,
        message=f"Setup successfully completed for '{org.name}'! Context Trust Gateway is active.",
    )


# ==========================================
# 3. Multi-Tenant Workspace Switching
# ==========================================

@router.post("/{org_id}/switch", response_model=TenantSwitchResponse)
async def switch_organization(
    org_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Switch active tenant context. Validates organization, updates context, and issues refreshed JWT."""
    # 1. Resolve organization
    org_stmt = select(Organization).where(Organization.id == org_id).limit(1)
    res_org = await db.execute(org_stmt)
    org = res_org.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target organization not found.")

    # 2. Resolve user: if user authenticated via JWT use them, else fallback to active persona or default
    active_caller = current_user
    if not active_caller:
        # Fallback to Sarah Chen (admin) or first available user for demo
        fallback_stmt = select(User).where(User.status == RecordStatus.ACTIVE).limit(1)
        res_fb = await db.execute(fallback_stmt)
        active_caller = res_fb.scalar_one_or_none()

    if not active_caller:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No active user session to switch tenant.")

    # 3. Find user's membership in target organization
    mem_stmt = select(User).where((User.organization_id == org.id) & (User.email.ilike(active_caller.email))).limit(1)
    res_mem = await db.execute(mem_stmt)
    target_user = res_mem.scalar_one_or_none()

    if not target_user:
        active_caller.organization_id = org.id
        target_user = active_caller
        db.add(target_user)
        await db.flush()

    await db.commit()
    await db.refresh(target_user)

    # 4. Mint freshly signed JWT tokens carrying the new active org_id
    access_token = create_access_token(
        subject=str(target_user.id),
        claims={
            "email": target_user.email,
            "role": target_user.role.value if hasattr(target_user.role, "value") else str(target_user.role),
            "org_id": str(org.id),
            "name": target_user.name,
        },
    )
    refresh_token = create_refresh_token(subject=str(target_user.id))

    # 5. Get member count for target organization
    count_stmt = select(func.count(User.id)).where(
        (User.organization_id == org.id) & (User.status == RecordStatus.ACTIVE)
    )
    res_count = await db.execute(count_stmt)
    m_count = res_count.scalar() or 0

    return TenantSwitchResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_build_user_response(target_user, org_name=org.name),
        active_organization=_build_org_response(org, member_count=m_count),
    )


# ==========================================
# 3. Organization Settings & Domain Whitelists
# ==========================================

@router.get("/{org_id}/settings", response_model=OrganizationResponse)
async def get_organization_settings(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve complete organization configuration, domain whitelists, and auth settings."""
    org_stmt = select(Organization).where(Organization.id == org_id).limit(1)
    res_org = await db.execute(org_stmt)
    org = res_org.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    count_stmt = select(func.count(User.id)).where(
        (User.organization_id == org.id) & (User.status == RecordStatus.ACTIVE)
    )
    res_count = await db.execute(count_stmt)
    m_count = res_count.scalar() or 0

    return _build_org_response(org, member_count=m_count)


@router.patch("/{org_id}/settings", response_model=OrganizationResponse)
async def update_organization_settings(
    org_id: uuid.UUID,
    data: OrganizationSettingsUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update organization name, slug, domain whitelist, and allowed SSO auth methods."""
    org_stmt = select(Organization).where(Organization.id == org_id).limit(1)
    res_org = await db.execute(org_stmt)
    org = res_org.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    if data.name is not None:
        org.name = data.name.strip()
    if data.slug is not None:
        org.slug = data.slug.strip().lower()
    if data.domain_whitelist is not None:
        # Clean domains: lowercase, remove @
        cleaned_domains = [d.strip().lower().replace("@", "") for d in data.domain_whitelist if d.strip()]
        org.domain_whitelist = cleaned_domains
    if data.allowed_auth_methods is not None:
        org.allowed_auth_methods = data.allowed_auth_methods
    if data.governance_config is not None:
        current_cfg = dict(org.governance_config or {})
        current_cfg.update(data.governance_config)
        org.governance_config = current_cfg
    if data.setup_completed is not None:
        org.setup_completed = data.setup_completed
        if data.setup_completed:
            cfg = dict(org.governance_config or {})
            if "workspaces" not in cfg or not cfg["workspaces"]:
                cfg["workspaces"] = [{
                    "id": f"ws_{org.id.hex[:10]}",
                    "name": f"{org.name} Workspace",
                    "domain": "governance",
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }]
                org.governance_config = dict(cfg)

    await db.commit()
    await db.refresh(org)

    count_stmt = select(func.count(User.id)).where(
        (User.organization_id == org.id) & (User.status == RecordStatus.ACTIVE)
    )
    res_count = await db.execute(count_stmt)
    m_count = res_count.scalar() or 0

    return _build_org_response(org, member_count=m_count)


# ==========================================
# 3b. Departmental Workspace Management
# ==========================================

@router.get("/{org_id}/workspaces", response_model=List[WorkspaceResponse])
async def list_organization_workspaces(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Retrieve all persistent department workspaces for the organization."""
    org_stmt = select(Organization).where(Organization.id == org_id).limit(1)
    res = await db.execute(org_stmt)
    org = res.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    gov_cfg = dict(org.governance_config or {})
    workspaces = gov_cfg.get("workspaces")
    if not workspaces or not isinstance(workspaces, list) or len(workspaces) == 0:
        # Auto-provision primary starter workspace if none exist
        default_ws = {
            "id": f"ws_{org.id.hex[:10]}",
            "name": f"{org.name} Workspace",
            "domain": "governance",
            "icon": "🏢",
            "description": "Primary enterprise governance & compliance workspace",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        workspaces = [default_ws]
        gov_cfg["workspaces"] = workspaces
        org.governance_config = dict(gov_cfg)
        await db.commit()
        await db.refresh(org)

    return workspaces


@router.post("/{org_id}/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_organization_workspace(
    org_id: uuid.UUID,
    data: WorkspaceCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create and persist a new departmental workspace for this organization."""
    org_stmt = select(Organization).where(Organization.id == org_id).limit(1)
    res = await db.execute(org_stmt)
    org = res.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    gov_cfg = dict(org.governance_config or {})
    workspaces = list(gov_cfg.get("workspaces") or [])

    new_ws = {
        "id": f"ws_{uuid.uuid4().hex[:12]}",
        "name": data.name.strip(),
        "domain": data.domain or "governance",
        "icon": data.icon or ("🛡️" if data.domain == "secops" else "👥" if data.domain == "hr" else "💳" if data.domain == "finance" else "📁"),
        "description": (data.description or "Custom departmental workspace").strip(),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    workspaces.append(new_ws)
    gov_cfg["workspaces"] = workspaces
    org.governance_config = dict(gov_cfg)

    await db.commit()
    await db.refresh(org)
    return new_ws


@router.patch("/{org_id}/workspaces/{workspace_id}", response_model=WorkspaceResponse)
async def update_organization_workspace(
    org_id: uuid.UUID,
    workspace_id: str,
    data: WorkspaceUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update properties of an existing workspace."""
    org_stmt = select(Organization).where(Organization.id == org_id).limit(1)
    res = await db.execute(org_stmt)
    org = res.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    gov_cfg = dict(org.governance_config or {})
    workspaces = list(gov_cfg.get("workspaces") or [])

    found_idx = -1
    for idx, ws in enumerate(workspaces):
        if ws.get("id") == workspace_id:
            found_idx = idx
            break

    if found_idx == -1:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found in this organization.")

    target = dict(workspaces[found_idx])
    if data.name is not None:
        target["name"] = data.name.strip()
    if data.domain is not None:
        target["domain"] = data.domain.strip()
    if data.icon is not None:
        target["icon"] = data.icon.strip()
    if data.description is not None:
        target["description"] = data.description.strip()

    workspaces[found_idx] = target
    gov_cfg["workspaces"] = workspaces
    org.governance_config = dict(gov_cfg)

    await db.commit()
    await db.refresh(org)
    return target


@router.delete("/{org_id}/workspaces/{workspace_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_organization_workspace(
    org_id: uuid.UUID,
    workspace_id: str,
    db: AsyncSession = Depends(get_db),
):
    """Delete a departmental workspace from the organization."""
    org_stmt = select(Organization).where(Organization.id == org_id).limit(1)
    res = await db.execute(org_stmt)
    org = res.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    gov_cfg = dict(org.governance_config or {})
    workspaces = list(gov_cfg.get("workspaces") or [])
    updated = [w for w in workspaces if w.get("id") != workspace_id]

    gov_cfg["workspaces"] = updated
    org.governance_config = dict(gov_cfg)

    await db.commit()
    await db.refresh(org)
    return None


# ==========================================
# 4. Member Management & Roles
# ==========================================

@router.get("/{org_id}/members", response_model=List[OrganizationMemberResponse])
async def list_organization_members(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all team members currently belonging to an organization workspace."""
    stmt = (
        select(User)
        .where(User.organization_id == org_id)
        .order_by(User.name.asc())
    )
    res = await db.execute(stmt)
    users = res.scalars().all()

    return [
        OrganizationMemberResponse(
            id=u.id,
            name=u.name,
            email=u.email,
            role=u.role.value if hasattr(u.role, "value") else str(u.role),
            status=u.status.value if hasattr(u.status, "value") else str(u.status),
            title=u.title,
            department=u.department,
            avatar_url=u.avatar_url,
            is_verified=u.is_verified,
            created_at=u.created_at,
        )
        for u in users
    ]


@router.patch("/{org_id}/members/{user_id}", response_model=OrganizationMemberResponse)
async def update_member_role(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    data: OrganizationMemberRoleUpdate,
    db: AsyncSession = Depends(get_db),
):
    """Update a team member's role (Admin, Data Steward, Auditor, Operator, Developer)."""
    stmt = select(User).where((User.id == user_id) & (User.organization_id == org_id)).limit(1)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found in this organization.")

    try:
        user.role = UserRole(data.role.lower())
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role '{data.role}'.")

    await db.commit()
    await db.refresh(user)

    return OrganizationMemberResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=user.role.value if hasattr(user.role, "value") else str(user.role),
        status=user.status.value if hasattr(user.status, "value") else str(user.status),
        title=user.title,
        department=user.department,
        avatar_url=user.avatar_url,
        is_verified=user.is_verified,
        created_at=user.created_at,
    )


@router.delete("/{org_id}/members/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    org_id: uuid.UUID,
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Remove a member from the organization workspace."""
    stmt = select(User).where((User.id == user_id) & (User.organization_id == org_id)).limit(1)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found.")

    user.status = RecordStatus.DEPRECATED
    await db.commit()
    return None


# ==========================================
# 5. Enterprise Invite Links & Invitations
# ==========================================

@router.post("/{org_id}/invites", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def create_invite(
    org_id: uuid.UUID,
    data: InviteCreateRequest,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate an enterprise invitation link for a corporate colleague."""
    org_stmt = select(Organization).where(Organization.id == org_id).limit(1)
    res_org = await db.execute(org_stmt)
    org = res_org.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Organization not found.")

    try:
        assigned_role = UserRole(data.role.lower())
    except ValueError:
        assigned_role = UserRole.DEVELOPER

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(days=7)
    inviter_id = current_user.id if current_user else None

    invite = OrganizationInvite(
        id=uuid.uuid4(),
        organization_id=org.id,
        email=data.email.strip().lower(),
        role=assigned_role,
        token=token,
        invited_by_id=inviter_id,
        expires_at=expires_at,
        status="pending",
    )
    db.add(invite)
    await db.commit()
    await db.refresh(invite)

    invite_url = f"http://localhost:4000/invite?token={token}"
    return InviteResponse(
        id=invite.id,
        organization_id=org.id,
        organization_name=org.name,
        email=invite.email,
        role=invite.role.value if hasattr(invite.role, "value") else str(invite.role),
        token=invite.token,
        invite_url=invite_url,
        status=invite.status,
        expires_at=invite.expires_at,
        created_at=invite.created_at,
    )


@router.get("/{org_id}/invites", response_model=List[InviteResponse])
async def list_invites(
    org_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """List all pending invitations for an organization workspace."""
    org_stmt = select(Organization).where(Organization.id == org_id).limit(1)
    res_org = await db.execute(org_stmt)
    org = res_org.scalar_one_or_none()
    org_name = org.name if org else "Enterprise Tenant"

    stmt = (
        select(OrganizationInvite)
        .where((OrganizationInvite.organization_id == org_id) & (OrganizationInvite.status == "pending"))
        .order_by(OrganizationInvite.created_at.desc())
    )
    res = await db.execute(stmt)
    invites = res.scalars().all()

    return [
        InviteResponse(
            id=inv.id,
            organization_id=inv.organization_id,
            organization_name=org_name,
            email=inv.email,
            role=inv.role.value if hasattr(inv.role, "value") else str(inv.role),
            token=inv.token,
            invite_url=f"http://localhost:4000/invite?token={inv.token}",
            status=inv.status,
            expires_at=inv.expires_at,
            created_at=inv.created_at,
        )
        for inv in invites
    ]


@router.delete("/{org_id}/invites/{invite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_invite(
    org_id: uuid.UUID,
    invite_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Revoke an active invitation."""
    stmt = select(OrganizationInvite).where(
        (OrganizationInvite.id == invite_id) & (OrganizationInvite.organization_id == org_id)
    ).limit(1)
    res = await db.execute(stmt)
    invite = res.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found.")

    invite.status = "revoked"
    await db.commit()
    return None


# Global invite inspection and acceptance (unauthenticated)
@router.get("/invites/inspect", response_model=InviteInspectResponse)
async def inspect_invite(
    token: str = Query(..., description="Invite secret token"),
    db: AsyncSession = Depends(get_db),
):
    """Inspect invitation token details without logging in."""
    stmt = (
        select(OrganizationInvite)
        .where(OrganizationInvite.token == token.strip())
        .options(selectinload(OrganizationInvite.organization))
        .limit(1)
    )
    res = await db.execute(stmt)
    invite = res.scalar_one_or_none()
    if not invite or invite.status != "pending":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid or expired invitation link.")

    now = datetime.now(timezone.utc)
    is_expired = invite.expires_at < now
    org_name = invite.organization.name if invite.organization else "Enterprise Tenant"
    org_slug = invite.organization.slug if invite.organization else "tenant"

    return InviteInspectResponse(
        token=invite.token,
        organization_id=invite.organization_id,
        organization_name=org_name,
        organization_slug=org_slug,
        email=invite.email,
        role=invite.role.value if hasattr(invite.role, "value") else str(invite.role),
        expires_at=invite.expires_at,
        is_expired=is_expired,
    )


@router.post("/invites/accept", response_model=TenantSwitchResponse)
async def accept_invite(
    data: InviteAcceptRequest,
    db: AsyncSession = Depends(get_db),
):
    """Accept an invitation, onboard the user, and return JWT authentication session."""
    stmt = (
        select(OrganizationInvite)
        .where(OrganizationInvite.token == data.token.strip())
        .options(selectinload(OrganizationInvite.organization))
        .limit(1)
    )
    res = await db.execute(stmt)
    invite = res.scalar_one_or_none()
    if not invite or invite.status != "pending":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or already accepted invitation.")

    now = datetime.now(timezone.utc)
    if invite.expires_at < now:
        invite.status = "expired"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invitation link has expired.")

    org = invite.organization
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target organization no longer exists.")

    # Find or create User membership in target organization
    user_stmt = select(User).where((User.email.ilike(invite.email.lower())) & (User.organization_id == org.id)).limit(1)
    res_user = await db.execute(user_stmt)
    user = res_user.scalar_one_or_none()

    if user:
        user.role = invite.role
        user.status = RecordStatus.ACTIVE
        user.is_verified = True
    else:
        # Check if user has an existing account in another org to copy profile info
        existing_profile_stmt = select(User).where(User.email.ilike(invite.email.lower())).limit(1)
        existing_profile = (await db.execute(existing_profile_stmt)).scalar_one_or_none()

        user_name = data.full_name or (existing_profile.name if existing_profile else invite.email.split("@")[0].replace(".", " ").title())
        hashed_pwd = (
            get_password_hash(data.password)
            if data.password
            else (existing_profile.hashed_password if existing_profile else get_password_hash(uuid.uuid4().hex))
        )
        avatar = existing_profile.avatar_url if (existing_profile and existing_profile.avatar_url) else f"https://api.dicebear.com/7.x/bottts/svg?seed={user_name.replace(' ', '')}"

        user = User(
            id=uuid.uuid4(),
            organization_id=org.id,
            name=user_name,
            email=invite.email.lower(),
            hashed_password=hashed_pwd,
            role=invite.role,
            status=RecordStatus.ACTIVE,
            is_verified=True,
            avatar_url=avatar,
            title=f"Invited Team Member ({invite.role.value if hasattr(invite.role, 'value') else str(invite.role)})",
            department="Risk & AI Governance",
        )
        db.add(user)

    invite.status = "accepted"
    await db.commit()
    await db.refresh(user)

    # Issue JWT tokens
    access_token = create_access_token(
        subject=str(user.id),
        claims={
            "email": user.email,
            "role": user.role.value if hasattr(user.role, "value") else str(user.role),
            "org_id": str(org.id),
            "name": user.name,
        },
    )
    refresh_token = create_refresh_token(subject=str(user.id))

    count_stmt = select(func.count(User.id)).where(
        (User.organization_id == org.id) & (User.status == RecordStatus.ACTIVE)
    )
    res_count = await db.execute(count_stmt)
    m_count = res_count.scalar() or 0

    return TenantSwitchResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_build_user_response(user, org_name=org.name),
        active_organization=_build_org_response(org, member_count=m_count),
    )


@router.post("/invites/{invite_id}/accept-direct", response_model=TenantSwitchResponse)
async def accept_invite_direct(
    invite_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Directly accept a pending invitation for the currently authenticated user and switch tenant."""
    stmt = (
        select(OrganizationInvite)
        .where((OrganizationInvite.id == invite_id) & (OrganizationInvite.status == "pending"))
        .options(selectinload(OrganizationInvite.organization))
        .limit(1)
    )
    res = await db.execute(stmt)
    invite = res.scalar_one_or_none()
    if not invite:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invitation not found or already accepted.")

    if invite.email.strip().lower() != current_user.email.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"This invitation was addressed to '{invite.email}', but your active session is '{current_user.email}'.",
        )

    now = datetime.now(timezone.utc)
    if invite.expires_at < now:
        invite.status = "expired"
        await db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This invitation link has expired.")

    org = invite.organization
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target organization no longer exists.")

    mem_stmt = select(User).where((User.organization_id == org.id) & (User.email.ilike(current_user.email))).limit(1)
    res_mem = await db.execute(mem_stmt)
    member_user = res_mem.scalar_one_or_none()

    if member_user:
        member_user.role = invite.role
        member_user.status = RecordStatus.ACTIVE
    else:
        member_user = User(
            id=uuid.uuid4(),
            organization_id=org.id,
            name=current_user.name,
            email=current_user.email.lower(),
            hashed_password=current_user.hashed_password,
            role=invite.role,
            status=RecordStatus.ACTIVE,
            is_verified=True,
            avatar_url=current_user.avatar_url,
            title=f"Invited Team Member ({invite.role.value if hasattr(invite.role, 'value') else str(invite.role)})",
            department="Risk & AI Governance",
        )
        db.add(member_user)

    invite.status = "accepted"
    await db.commit()
    await db.refresh(member_user)

    access_token = create_access_token(
        subject=str(member_user.id),
        claims={
            "email": member_user.email,
            "role": member_user.role.value if hasattr(member_user.role, "value") else str(member_user.role),
            "org_id": str(org.id),
            "name": member_user.name,
        },
    )
    refresh_token = create_refresh_token(subject=str(member_user.id))

    count_stmt = select(func.count(User.id)).where(
        (User.organization_id == org.id) & (User.status == RecordStatus.ACTIVE)
    )
    res_count = await db.execute(count_stmt)
    m_count = res_count.scalar() or 0

    return TenantSwitchResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user=_build_user_response(member_user, org_name=org.name),
        active_organization=_build_org_response(org, member_count=m_count),
    )


# ==========================================
# 6. Interactive Demo Sandbox Data Management
# ==========================================

@router.post("/{org_id}/reset-demo-data")
async def reset_demo_data(
    org_id: uuid.UUID,
    current_user: Optional[User] = Depends(get_optional_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Restore or seed pristine demo knowledge (Connectors, Policies, Claims, Conflicts) for this tenant."""
    from app.services.demo_seeder_service import DemoSeederService

    org_stmt = select(Organization).where(Organization.id == org_id).limit(1)
    res_org = await db.execute(org_stmt)
    org = res_org.scalar_one_or_none()
    if not org:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target organization not found.")

    user_id = current_user.id if current_user else None
    result = await DemoSeederService.seed_starter_knowledge(
        db=db,
        organization_id=org_id,
        user_id=user_id,
        clear_existing=True,
    )
    return result

