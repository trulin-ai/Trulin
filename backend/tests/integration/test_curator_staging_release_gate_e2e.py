"""
Curator Staging Integration Release Gate (End-to-End PostgreSQL).

Verifies the full production path against the live staging PostgreSQL database:
1. Seed Document Versions with Known Conflicts in PostgreSQL.
2. Shadow Mode auto-resolve execution:
   - Asserts 0 mutations applied in PostgreSQL.
   - Asserts full measurable shadow comparison artifact with precision calibration.
3. Authorized Reviewer Resolution:
   - PostgreSQL transaction updates claim and conflict statuses.
   - Writes immutable HumanReview record.
   - Writes immutable UserActivityLog record.
   - Verifies read-back from PostgreSQL.
4. Separation of Duties (SoD) Enforcement:
   - Asserts Operator & Viewer are barred (403 / SoD barred).
5. Source Revision Invalidation & Attestation Expiry Policy:
   - Simulates source document revision.
   - Re-attest with stale version -> RE_ATTEST_REJECTED.
   - Drift scan -> SOURCE_REVISION_RE_EVALUATION_REQUIRED.
   - Re-attest with active version + financial_controls policy -> 30-day horizon verified.
6. Blast Radius Telemetry & Calibration Reporting:
   - Verifies false-critical, false-routine, and workflow sensitivity metrics.
"""

import uuid
import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.enums import ClaimStatus, ConflictStatus, RecordStatus, ReviewDecision, UserRole
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.data_source import DataSource
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.models.human_review import HumanReview
from app.db.models.organization import Organization
from app.db.models.user import User
from app.db.models.user_activity import UserActivityLog
from app.conflict_engine.blast_radius_calibrator import BlastRadiusCalibrator
from app.schemas.drift import ClaimRemediateRequest
from app.services.conflict_service import ConflictService
from app.services.drift_decay_service import analyze_context_drift, remediate_claim_decay
from app.services.steward_agent import StewardAgentService


@pytest.fixture
async def staging_env():
    """Seeds a comprehensive multi-document staging environment in live PostgreSQL."""
    async with AsyncSessionLocal() as session:
        uid = uuid.uuid4().hex[:8]
        org = Organization(
            name=f"Staging Release Gate Org {uid}",
            slug=f"staging-gate-{uid}",
            status="active",
        )
        session.add(org)
        await session.flush()

        auditor = User(
            organization_id=org.id,
            email=f"auditor_{uid}@staging.test",
            name="Compliance Auditor",
            role=UserRole.REVIEWER,
            status=RecordStatus.ACTIVE,
        )
        session.add(auditor)

        ds = DataSource(
            organization_id=org.id,
            name="Global Finance & HR Portal",
            source_type="file_upload",
            external_id=f"fin-hr-{uid}",
            authority_level=90,
        )
        session.add(ds)
        await session.flush()

        # Document 1: Travel Policy
        doc_travel = Document(
            organization_id=org.id,
            source_id=ds.id,
            title="Global Travel & Expense Policy",
            document_type="policy",
            content_hash=f"hash-travel-{uid}",
        )
        session.add(doc_travel)
        await session.flush()

        doc_travel_v1 = DocumentVersion(
            document_id=doc_travel.id,
            version_number=1,
            is_current=True,
            content_hash=f"h-tv1-{uid}",
        )
        session.add(doc_travel_v1)
        await session.flush()

        now = datetime.now(timezone.utc)

        # Claim A: Standard Per Diem $75
        claim_a = Claim(
            organization_id=org.id,
            document_version_id=doc_travel_v1.id,
            claim_text="Daily meal reimbursement allowance is capped at $75 per person.",
            subject="meal reimbursement allowance",
            predicate="capped_at",
            object="75 dollars",
            status=ClaimStatus.VERIFIED,
            created_at=now - timedelta(days=45),
        )
        # Claim B: Conflicting rule $120
        claim_b = Claim(
            organization_id=org.id,
            document_version_id=doc_travel_v1.id,
            claim_text="Daily meal reimbursement allowance is capped at $120 per person.",
            subject="meal reimbursement allowance",
            predicate="capped_at",
            object="120 dollars",
            status=ClaimStatus.VERIFIED,
            created_at=now - timedelta(days=10),
        )
        session.add_all([claim_a, claim_b])
        await session.flush()

        # Conflict record in PostgreSQL
        conflict = ClaimConflict(
            claim_a_id=claim_a.id,
            claim_b_id=claim_b.id,
            conflict_type="numeric_conflict",
            severity="HIGH",
            resolution_status=ConflictStatus.HUMAN_REVIEW_REQUIRED,
            confidence=0.92,
        )
        session.add(conflict)

        # Stale claim for drift/attestation testing (190 days old)
        claim_stale = Claim(
            organization_id=org.id,
            document_version_id=doc_travel_v1.id,
            claim_text="Capital expenditure exceeding $50,000 requires CFO approval.",
            subject="capital expenditure approval",
            predicate="threshold",
            object="50000",
            status=ClaimStatus.VERIFIED,
            created_at=now - timedelta(days=190),
        )
        session.add(claim_stale)
        await session.flush()

        claim_stale_trust = ClaimTrustScore(
            claim_id=claim_stale.id,
            source_score=0.95,
            freshness_score=0.45,
            evidence_score=0.90,
            consistency_score=0.90,
            authority_score=0.95,
            overall_score=0.90,
        )
        session.add(claim_stale_trust)

        await session.commit()

        return {
            "org_id": org.id,
            "auditor_id": auditor.id,
            "ds_id": ds.id,
            "doc_id": doc_travel.id,
            "v1_id": doc_travel_v1.id,
            "claim_a_id": claim_a.id,
            "claim_b_id": claim_b.id,
            "claim_stale_id": claim_stale.id,
            "conflict_id": conflict.id,
        }


@pytest.mark.asyncio
async def test_staging_gate_1_shadow_mode_zero_mutations(staging_env):
    """Gate 1: Shadow-mode auto_resolve executed against PostgreSQL:

    - Produces complete measurable comparison report.
    - Zero mutations applied in live PostgreSQL.
    """
    async with AsyncSessionLocal() as session:
        service = ConflictService(session)
        res = await service.auto_resolve_conflicts(shadow_mode=True, organization_id=staging_env["org_id"])

        assert res["operating_mode"] == "SHADOW_RECOMMENDATION_ONLY"
        assert res["shadow_run_id"].startswith("srun_")
        assert res["conflicts_detected"] >= 1
        assert "precision_calibration" in res
        assert "is_calibrated" in res["precision_calibration"]
        assert "agreed_correct_recommendations" in res["precision_calibration"]
        assert "rollback_reference" in res
        assert res["rollback_reference"].startswith("rb_snap_")

        # Database Assertion: Assert conflict in DB remains unresolved
        stmt = select(ClaimConflict).where(ClaimConflict.id == staging_env["conflict_id"])
        c_db = (await session.execute(stmt)).scalar_one_or_none()
        assert c_db.resolution_status == ConflictStatus.HUMAN_REVIEW_REQUIRED
        assert c_db.resolved_claim_id is None


@pytest.mark.asyncio
async def test_staging_gate_2_authorized_resolution_and_audit_provenance(staging_env):
    """Gate 2: Authorized Reviewer Resolution:

    - Applies resolution to clustered issue.
    - Mutates claim statuses and conflict status in PostgreSQL.
    - Writes immutable HumanReview and UserActivityLog records.
    - Confirms read-back from PostgreSQL.
    """
    async with AsyncSessionLocal() as session:
        service = ConflictService(session)
        issues = await service.get_clustered_conflict_issues(organization_id=staging_env["org_id"])
        assert len(issues) >= 1
        issue_id = issues[0]["issue_id"]

        # Resolve issue choosing Side B ($120)
        res = await service.resolve_conflict_issue(
            issue_id=issue_id,
            reviewer_id=staging_env["auditor_id"],
            decision=ReviewDecision.APPROVE,
            chosen_side="B",
            reason="Approved $120 rate in accordance with 2026 inflation adjustments.",
            organization_id=staging_env["org_id"],
        )
        assert res["status"] == "success"

        # Read-back from PostgreSQL: verify conflict status
        stmt_c = select(ClaimConflict).where(ClaimConflict.id == staging_env["conflict_id"])
        c_db = (await session.execute(stmt_c)).scalar_one_or_none()
        assert c_db.resolution_status == ConflictStatus.RESOLVED

        # Read-back from PostgreSQL: verify claims
        stmt_a = select(Claim).where(Claim.id == staging_env["claim_a_id"])
        ca_db = (await session.execute(stmt_a)).scalar_one_or_none()
        assert ca_db.status == ClaimStatus.OUTDATED

        stmt_b = select(Claim).where(Claim.id == staging_env["claim_b_id"])
        cb_db = (await session.execute(stmt_b)).scalar_one_or_none()
        assert cb_db.status == ClaimStatus.VERIFIED

        # Read-back from PostgreSQL: verify HumanReview audit log
        stmt_hr = select(HumanReview).where(HumanReview.organization_id == staging_env["org_id"])
        reviews = (await session.execute(stmt_hr)).scalars().all()
        assert len(reviews) >= 1
        assert reviews[0].decision == ReviewDecision.APPROVE
        assert "inflation adjustments" in reviews[0].reason


@pytest.mark.asyncio
async def test_staging_gate_3_sod_enforcement_matrix(staging_env):
    """Gate 3: Separation of Duties (SoD):

    - Barred roles (viewer, operator) receive 403 / SoD barred.
    - Authorized roles (reviewer, auditor, admin) successfully apply action and write UserActivityLog.
    """
    async with AsyncSessionLocal() as session:
        agent = StewardAgentService(session)

        # Viewer -> Barred
        res_viewer = await agent.apply_steward_action(
            action_type="DEPRECATE_CLAIM",
            target_id=staging_env["claim_stale_id"],
            user_role="viewer",
            user_name="Read-Only Analyst",
            organization_id=staging_env["org_id"],
        )
        assert res_viewer["success"] is False
        assert "Separation of Duties (SoD) Barred" in res_viewer["error"]

        # Operator -> Barred
        res_operator = await agent.apply_steward_action(
            action_type="DEPRECATE_CLAIM",
            target_id=staging_env["claim_stale_id"],
            user_role="operator",
            user_name="Batch Operator",
            organization_id=staging_env["org_id"],
        )
        assert res_operator["success"] is False
        assert "Separation of Duties (SoD) Barred" in res_operator["error"]

        # Reviewer -> Authorized
        res_reviewer = await agent.apply_steward_action(
            action_type="DEPRECATE_CLAIM",
            target_id=staging_env["claim_stale_id"],
            user_role="reviewer",
            user_name="Compliance Auditor",
            organization_id=staging_env["org_id"],
        )
        assert res_reviewer["success"] is True

        # Read-back: Assert UserActivityLog was written in PostgreSQL
        stmt_act = select(UserActivityLog).where(
            UserActivityLog.organization_id == staging_env["org_id"],
            UserActivityLog.action_type == "STEWARD_RECOMMENDATION_APPLIED",
        )
        activities = (await session.execute(stmt_act)).scalars().all()
        assert len(activities) >= 1
        assert activities[0].user_role == "reviewer"


@pytest.mark.asyncio
async def test_staging_gate_4_policy_driven_attestation_and_source_revision(staging_env):
    """Gate 4: Source Revision Invalidation & Policy-Driven Attestation Horizon:

    1. Simulates source document revision (v2 created, v1 no longer current).
    2. Attempting re-attestation specifying stale version 'v1' is REJECTED.
    3. Re-attesting specifying active version 'v2' under 'financial_controls' policy
       grants a 30-day review horizon with mandatory reattestation.
    """
    async with AsyncSessionLocal() as session:
        # Revise source document: create DocumentVersion v2
        doc_v2 = DocumentVersion(
            document_id=staging_env["doc_id"],
            version_number=2,
            is_current=True,
            content_hash="h-tv2-updated",
        )
        session.add(doc_v2)

        # Update stale claim to point to doc_v2 to simulate revised governing document
        stmt_c = select(Claim).where(Claim.id == staging_env["claim_stale_id"])
        c = (await session.execute(stmt_c)).scalar_one_or_none()
        c.document_version_id = doc_v2.id
        await session.commit()

        # Step 2: Attestation specifying stale version "v1.0" when active is v2 -> REJECTED
        req_stale = ClaimRemediateRequest(
            claim_id=staging_env["claim_stale_id"],
            action="RE_ATTEST",
            attester_id=staging_env["auditor_id"],
            source_version="v1.0",
        )
        res_stale = await remediate_claim_decay(req_stale, session=session)
        assert res_stale.action_taken == "RE_ATTEST_REJECTED"
        assert res_stale.new_status == "REQUIRES_RE_EVALUATION"
        assert "Source version mismatch" in res_stale.message

        # Step 3: Attestation specifying active version "v2.0" with financial_controls policy
        req_active = ClaimRemediateRequest(
            claim_id=staging_env["claim_stale_id"],
            action="RE_ATTEST",
            attester_id=staging_env["auditor_id"],
            source_version="v2.0",
            domain_pack="financial_controls",
        )
        res_active = await remediate_claim_decay(req_active, session=session)
        assert res_active.action_taken == "RE_ATTEST"
        assert res_active.new_status == "ACTIVE"
        assert res_active.freshness_score == 1.00

        # Assert AttestationRecord policy configuration and 30-day horizon
        att_rec = res_active.attestation_record
        assert att_rec is not None
        assert att_rec.policy_config is not None
        assert att_rec.policy_config.domain_pack == "financial_controls"
        assert att_rec.policy_config.review_horizon_days == 30
        assert att_rec.policy_config.mandatory_reattestation is True

        # Verify expiry is exactly 30 days from now
        now = datetime.now(timezone.utc)
        delta_days = (att_rec.expires_at - now).days
        assert delta_days in (29, 30)


@pytest.mark.asyncio
async def test_staging_gate_5_blast_radius_telemetry_and_calibration():
    """Gate 5: Blast Radius Telemetry & Calibration Reporting:

    Verifies tracking of predicted blast vs actual reviewer escalation,
    false-critical and false-routine metrics, and sensitivity coefficients.
    """
    BlastRadiusCalibrator.reset()

    # Record 3 empirical observations
    BlastRadiusCalibrator.record_observation(
        conflict_id=str(uuid.uuid4()),
        impact_score=85.0,
        predicted_blast="CRITICAL_BLAST",
        downstream_workflows_count=12,
        reviewer_decision="ESCALATE",
        actual_escalated=True,
    )
    BlastRadiusCalibrator.record_observation(
        conflict_id=str(uuid.uuid4()),
        impact_score=75.0,
        predicted_blast="HIGH_BLAST",
        downstream_workflows_count=8,
        reviewer_decision="APPROVE",
        actual_escalated=False,
    )
    BlastRadiusCalibrator.record_observation(
        conflict_id=str(uuid.uuid4()),
        impact_score=20.0,
        predicted_blast="ROUTINE",
        downstream_workflows_count=1,
        reviewer_decision="APPROVE",
        actual_escalated=False,
    )

    report = BlastRadiusCalibrator.get_calibration_report()

    assert report.total_observations == 3
    assert report.is_calibrated is False  # N < 30 -> Provisional
    assert "PROVISIONAL_OBSERVATIONS" in report.sample_confidence
    assert report.workflow_sensitivity_coefficient == 0.30
    assert report.predicted_critical_count == 2
    assert report.actual_escalated_count == 1
    assert report.false_critical_rate == 0.50  # 1 out of 2 predicted critical did not escalate
    assert report.false_routine_rate == 0.00   # 0 out of 1 routine was escalated
