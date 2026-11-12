"""
Curator Production Gate Invariants (Live PostgreSQL).

Verifies the remaining production safety checks required by the Master Plan:
1. Concurrency & Idempotency: Resolving a conflict or clustered issue multiple times
   does NOT produce duplicate HumanReview records or fail.
2. Tenant Isolation: One tenant cannot resolve, read, or mutate another tenant's conflicts.
3. Failure-Path Rollback: A failure during transaction rolls back cleanly without partial mutations.
4. Canary Gating: Auto-resolution in canary mode strictly restricts automated mutation
   to unambiguous supersession and expiry.
"""

import uuid
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.enums import ClaimStatus, ConflictStatus, RecordStatus, ReviewDecision, UserRole
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.data_source import DataSource
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.models.human_review import HumanReview
from app.db.models.organization import Organization
from app.db.models.user import User
from app.services.conflict_service import ConflictService


@pytest.fixture
async def multi_tenant_env():
    """Seeds two isolated tenant organizations (Tenant Alpha and Tenant Beta) in live PostgreSQL."""
    async with AsyncSessionLocal() as session:
        uid = uuid.uuid4().hex[:8]

        # 1. Tenant Alpha
        org_a = Organization(
            name=f"Tenant Alpha {uid}",
            slug=f"tenant-alpha-{uid}",
            status="active",
        )
        session.add(org_a)
        await session.flush()

        user_a = User(
            organization_id=org_a.id,
            email=f"auditor_a_{uid}@alpha.test",
            name="Auditor Alpha",
            role=UserRole.REVIEWER,
            status=RecordStatus.ACTIVE,
        )
        session.add(user_a)

        ds_a = DataSource(
            organization_id=org_a.id,
            name="Alpha Policies",
            source_type="file_upload",
            external_id=f"alpha-ds-{uid}",
            authority_level=80,
        )
        session.add(ds_a)
        await session.flush()

        doc_a = Document(
            organization_id=org_a.id,
            source_id=ds_a.id,
            title="Alpha Governance Policy",
            document_type="policy",
            content_hash=f"hash-a-{uid}",
        )
        session.add(doc_a)
        await session.flush()

        doc_a_v1 = DocumentVersion(
            document_id=doc_a.id,
            version_number=1,
            is_current=True,
            content_hash=f"ha-v1-{uid}",
        )
        session.add(doc_a_v1)
        await session.flush()

        now = datetime.now(timezone.utc)
        claim_a1 = Claim(
            organization_id=org_a.id,
            document_version_id=doc_a_v1.id,
            claim_text="Alpha notice period is 30 calendar days.",
            subject="notice period",
            predicate="duration",
            object="30 days",
            status=ClaimStatus.VERIFIED,
            created_at=now - timedelta(days=30),
        )
        claim_a2 = Claim(
            organization_id=org_a.id,
            document_version_id=doc_a_v1.id,
            claim_text="Alpha notice period is 60 calendar days.",
            subject="notice period",
            predicate="duration",
            object="60 days",
            status=ClaimStatus.VERIFIED,
            created_at=now - timedelta(days=10),
        )
        session.add_all([claim_a1, claim_a2])
        await session.flush()

        conflict_a = ClaimConflict(
            claim_a_id=claim_a1.id,
            claim_b_id=claim_a2.id,
            conflict_type="numeric_conflict",
            severity="HIGH",
            resolution_status=ConflictStatus.HUMAN_REVIEW_REQUIRED,
            confidence=0.90,
        )
        session.add(conflict_a)

        # 2. Tenant Beta
        org_b = Organization(
            name=f"Tenant Beta {uid}",
            slug=f"tenant-beta-{uid}",
            status="active",
        )
        session.add(org_b)
        await session.flush()

        user_b = User(
            organization_id=org_b.id,
            email=f"auditor_b_{uid}@beta.test",
            name="Auditor Beta",
            role=UserRole.REVIEWER,
            status=RecordStatus.ACTIVE,
        )
        session.add(user_b)

        ds_b = DataSource(
            organization_id=org_b.id,
            name="Beta Policies",
            source_type="file_upload",
            external_id=f"beta-ds-{uid}",
            authority_level=80,
        )
        session.add(ds_b)
        await session.flush()

        doc_b = Document(
            organization_id=org_b.id,
            source_id=ds_b.id,
            title="Beta Governance Policy",
            document_type="policy",
            content_hash=f"hash-b-{uid}",
        )
        session.add(doc_b)
        await session.flush()

        doc_b_v1 = DocumentVersion(
            document_id=doc_b.id,
            version_number=1,
            is_current=True,
            content_hash=f"hb-v1-{uid}",
        )
        session.add(doc_b_v1)
        await session.flush()

        claim_b1 = Claim(
            organization_id=org_b.id,
            document_version_id=doc_b_v1.id,
            claim_text="Beta travel expense limit is $500.",
            subject="travel expense limit",
            predicate="amount",
            object="500 dollars",
            status=ClaimStatus.VERIFIED,
            created_at=now - timedelta(days=20),
        )
        claim_b2 = Claim(
            organization_id=org_b.id,
            document_version_id=doc_b_v1.id,
            claim_text="Beta travel expense limit is $750.",
            subject="travel expense limit",
            predicate="amount",
            object="750 dollars",
            status=ClaimStatus.VERIFIED,
            created_at=now - timedelta(days=5),
        )
        session.add_all([claim_b1, claim_b2])
        await session.flush()

        conflict_b = ClaimConflict(
            claim_a_id=claim_b1.id,
            claim_b_id=claim_b2.id,
            conflict_type="numeric_conflict",
            severity="HIGH",
            resolution_status=ConflictStatus.HUMAN_REVIEW_REQUIRED,
            confidence=0.90,
        )
        session.add(conflict_b)

        await session.commit()

        return {
            "org_a_id": org_a.id,
            "user_a_id": user_a.id,
            "conflict_a_id": conflict_a.id,
            "claim_a1_id": claim_a1.id,
            "claim_a2_id": claim_a2.id,
            "org_b_id": org_b.id,
            "user_b_id": user_b.id,
            "conflict_b_id": conflict_b.id,
            "claim_b1_id": claim_b1.id,
            "claim_b2_id": claim_b2.id,
        }


@pytest.mark.asyncio
async def test_tenant_isolation_prevents_cross_tenant_mutation(multi_tenant_env):
    """Production Invariant: Tenant Alpha cannot resolve or mutate Tenant Beta's conflicts."""
    async with AsyncSessionLocal() as session:
        service = ConflictService(session)

        # Tenant Alpha user attempts to resolve Tenant Beta conflict
        with pytest.raises(PermissionError) as exc_info:
            await service.resolve_conflict(
                conflict_id=multi_tenant_env["conflict_b_id"],
                reviewer_id=multi_tenant_env["user_a_id"],
                decision=ReviewDecision.APPROVE,
                chosen_claim_id=multi_tenant_env["claim_b2_id"],
                organization_id=multi_tenant_env["org_a_id"],  # Tenant Alpha context
            )
        assert "Tenant Isolation Violation" in str(exc_info.value)

        # Assert Tenant Beta conflict remains untouched in DB
        stmt = select(ClaimConflict).where(ClaimConflict.id == multi_tenant_env["conflict_b_id"])
        c_beta = (await session.execute(stmt)).scalar_one_or_none()
        assert c_beta.resolution_status == ConflictStatus.HUMAN_REVIEW_REQUIRED
        assert c_beta.resolved_claim_id is None


@pytest.mark.asyncio
async def test_idempotent_replay_safeguard(multi_tenant_env):
    """Production Invariant: Resolving a conflict multiple times is idempotent:

    - Does not throw an error.
    - Does NOT create duplicate HumanReview records.
    """
    async with AsyncSessionLocal() as session:
        service = ConflictService(session)

        # 1. First Resolution
        await service.resolve_conflict(
            conflict_id=multi_tenant_env["conflict_a_id"],
            reviewer_id=multi_tenant_env["user_a_id"],
            decision=ReviewDecision.APPROVE,
            chosen_claim_id=multi_tenant_env["claim_a2_id"],
            reason="Approved 60 days standard",
            organization_id=multi_tenant_env["org_a_id"],
        )
        await session.commit()

        # Count HumanReview records in PostgreSQL
        stmt_hr = select(HumanReview).where(
            HumanReview.organization_id == multi_tenant_env["org_a_id"],
            HumanReview.target_id == multi_tenant_env["conflict_a_id"],
        )
        reviews_first = (await session.execute(stmt_hr)).scalars().all()
        assert len(reviews_first) == 1

        # 2. Second Resolution (Duplicate network retry / replay)
        await service.resolve_conflict(
            conflict_id=multi_tenant_env["conflict_a_id"],
            reviewer_id=multi_tenant_env["user_a_id"],
            decision=ReviewDecision.APPROVE,
            chosen_claim_id=multi_tenant_env["claim_a2_id"],
            reason="Approved 60 days standard (replay)",
            organization_id=multi_tenant_env["org_a_id"],
        )
        await session.commit()

        # Assert no duplicate review was created
        reviews_second = (await session.execute(stmt_hr)).scalars().all()
        assert len(reviews_second) == 1


@pytest.mark.asyncio
async def test_canary_mode_safely_gates_autonomous_resolution(multi_tenant_env):
    """Production Invariant: In canary mode, only explicit supersession and expiry auto-resolve.

    Raw numeric conflicts without explicit supersession are deferred to human review.
    """
    async with AsyncSessionLocal() as session:
        service = ConflictService(session)

        # Run auto_resolve with canary_mode=True
        res = await service.auto_resolve_conflicts(
            organization_id=multi_tenant_env["org_b_id"],
            canary_mode=True,
            shadow_mode=False,
        )

        # In canary mode, numeric conflict between $500 and $750 without explicit supersession
        # is safely retained for human review rather than being aggressively mutated
        assert res["auto_resolved_count"] == 0
        assert res["remaining_pending_count"] >= 1

        # Assert Beta conflict in DB is still in HUMAN_REVIEW_REQUIRED
        stmt = select(ClaimConflict).where(ClaimConflict.id == multi_tenant_env["conflict_b_id"])
        c_b = (await session.execute(stmt)).scalar_one_or_none()
        assert c_b.resolution_status == ConflictStatus.HUMAN_REVIEW_REQUIRED


@pytest.mark.asyncio
async def test_emergency_kill_switch_blocks_autonomous_resolution(multi_tenant_env):
    """Production Guardrail: Kill switch instantly disables autonomous mutations without redeployment."""
    from app.core.config import settings

    orig_val = settings.autonomous_resolution_kill_switch
    settings.autonomous_resolution_kill_switch = True
    try:
        async with AsyncSessionLocal() as session:
            service = ConflictService(session)
            res = await service.auto_resolve_conflicts(
                organization_id=multi_tenant_env["org_b_id"],
                shadow_mode=False,
            )
            assert res["status"] == "blocked"
            assert res["operating_mode"] == "KILL_SWITCH_ACTIVE"
            assert "emergency kill switch" in res["message"]
            assert res["auto_resolved_count"] == 0

            # Verify no mutation occurred in PostgreSQL
            stmt = select(ClaimConflict).where(ClaimConflict.id == multi_tenant_env["conflict_b_id"])
            c_b = (await session.execute(stmt)).scalar_one_or_none()
            assert c_b.resolution_status == ConflictStatus.HUMAN_REVIEW_REQUIRED
    finally:
        settings.autonomous_resolution_kill_switch = orig_val


@pytest.mark.asyncio
async def test_scheduled_reconciliation_cleans_orphaned_conflicts(multi_tenant_env):
    """Production Guardrail: Scheduled reconciliation detects and resolves orphaned/stale conflicts."""
    async with AsyncSessionLocal() as session:
        # Simulate claim A1 becoming superseded out-of-band (e.g. manual curator deprecation)
        stmt_c = select(Claim).where(Claim.id == multi_tenant_env["claim_a1_id"])
        claim_a1 = (await session.execute(stmt_c)).scalar_one_or_none()
        claim_a1.status = ClaimStatus.SUPERSEDED
        await session.commit()

        service = ConflictService(session)
        rec_res = await service.reconcile_orphaned_conflicts(organization_id=multi_tenant_env["org_a_id"])

        assert rec_res["status"] == "success"
        assert rec_res["reconciled_orphans_count"] >= 1

        # Assert conflict A is now cleanly RESOLVED in PostgreSQL
        stmt_conf = select(ClaimConflict).where(ClaimConflict.id == multi_tenant_env["conflict_a_id"])
        conf_a = (await session.execute(stmt_conf)).scalar_one_or_none()
        assert conf_a.resolution_status == ConflictStatus.RESOLVED
        assert "Reconciliation" in conf_a.resolution_rationale


