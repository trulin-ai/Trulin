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
from app.db.repositories.data_source_repository import DataSourceRepository
from app.schemas.drift import ClaimRemediateRequest
from app.services.conflict_service import ConflictService
from app.services.drift_decay_service import analyze_context_drift, remediate_claim_decay
from app.services.steward_agent import StewardAgentService


async def setup_curator_test_env():
    """Sets up an isolated test organization, user, data source, document, and claims."""
    async with AsyncSessionLocal() as session:
        uid = uuid.uuid4().hex[:8]
        org = Organization(name=f"Curator Governance Org {uid}", slug=f"curator-gov-{uid}")
        session.add(org)
        await session.flush()

        auditor = User(
            organization_id=org.id,
            email=f"auditor_{uid}@governance.test",
            name="Chief Compliance Auditor",
            role=UserRole.REVIEWER,
            status=RecordStatus.ACTIVE,
        )
        session.add(auditor)

        ds = DataSource(
            organization_id=org.id,
            name="Enterprise Travel Portal",
            source_type="file_upload",
            external_id=f"travel-{uid}",
            authority_level=85,
        )
        session.add(ds)
        await session.flush()

        doc = Document(
            organization_id=org.id,
            source_id=ds.id,
            title="Enterprise Travel Policy 2026",
            document_type="policy",
            content_hash=f"hash-travel-{uid}",
        )
        session.add(doc)
        await session.flush()

        doc_ver = DocumentVersion(
            document_id=doc.id,
            version_number=1,
            is_current=True,
            content_hash=f"h-v1-{uid}",
        )
        session.add(doc_ver)
        await session.flush()

        now = datetime.now(timezone.utc)
        # 1. Active Verified Claim (190 days old to test drift separation)
        old_claim = Claim(
            organization_id=org.id,
            document_version_id=doc_ver.id,
            claim_text="Flight reimbursement capped at economy class for domestic travel under 6 hours.",
            status=ClaimStatus.VERIFIED,
            created_at=now - timedelta(days=190),
        )
        session.add(old_claim)
        await session.flush()

        old_claim_trust = ClaimTrustScore(
            claim_id=old_claim.id,
            source_score=0.90,
            freshness_score=0.50,
            evidence_score=0.90,
            consistency_score=0.90,
            authority_score=0.90,
            overall_score=0.90,
        )
        session.add(old_claim_trust)

        # 2. Candidate / OCR Claim (unverified)
        candidate_claim = Claim(
            organization_id=org.id,
            document_version_id=doc_ver.id,
            claim_text="Provisional meal per diem is $75 per calendar day during international travel.",
            status=ClaimStatus.CANDIDATE,
            created_at=now - timedelta(days=10),
        )
        session.add(candidate_claim)

        # 3. Pair of Conflicting Claims
        cfl_a = Claim(
            organization_id=org.id,
            document_version_id=doc_ver.id,
            claim_text="Lodging allowance is max $200 per night without VP pre-approval.",
            status=ClaimStatus.VERIFIED,
            created_at=now - timedelta(days=20),
        )
        cfl_b = Claim(
            organization_id=org.id,
            document_version_id=doc_ver.id,
            claim_text="Lodging allowance is max $350 per night without VP pre-approval.",
            status=ClaimStatus.VERIFIED,
            created_at=now - timedelta(days=5),
        )
        session.add_all([cfl_a, cfl_b])
        await session.flush()

        conflict = ClaimConflict(
            claim_a_id=cfl_a.id,
            claim_b_id=cfl_b.id,
            conflict_type="numeric_conflict",
            severity="HIGH",
            resolution_status=ConflictStatus.HUMAN_REVIEW_REQUIRED,
            confidence=0.95,
        )
        session.add(conflict)

        await session.commit()

        return {
            "org_id": org.id,
            "auditor_id": auditor.id,
            "doc_id": doc.id,
            "old_claim_id": old_claim.id,
            "candidate_claim_id": candidate_claim.id,
            "cfl_a_id": cfl_a.id,
            "cfl_b_id": cfl_b.id,
            "conflict_id": conflict.id,
        }


@pytest.mark.asyncio
async def test_stale_claim_flagged_for_decay_but_retains_certification():
    """Acceptance Check 1: A stale claim is flagged as SEVERELY_DECAYED on the freshness radar,

    but its legal certification_status remains VERIFIED and is NOT automatically mutated or retired.
    """
    env = await setup_curator_test_env()
    async with AsyncSessionLocal() as session:
        drift_report = await analyze_context_drift(organization_id=env["org_id"], session=session)

        # Find the 190-day-old claim
        old_decay_item = next((d for d in drift_report.decayed_claims if d.claim_id == env["old_claim_id"]), None)
        assert old_decay_item is not None
        assert old_decay_item.drift_category == "SEVERELY_DECAYED"
        assert old_decay_item.freshness_score == 0.50
        # Independent certification status must still be VERIFIED
        assert old_decay_item.certification_status == "VERIFIED"

        # Confirm in database that status was NOT mutated
        res = await session.execute(select(Claim).where(Claim.id == env["old_claim_id"]))
        c = res.scalar_one()
        assert c.status == ClaimStatus.VERIFIED


@pytest.mark.asyncio
async def test_sod_enforcement_for_steward_recommendations():
    """Acceptance Check 2: An unauthorized role (e.g.

    operator, viewer) cannot apply recommendations.
    Only authorized roles (reviewer, compliance_officer, admin, cco) can apply them.
    """
    env = await setup_curator_test_env()
    async with AsyncSessionLocal() as session:
        agent = StewardAgentService(session)

        # 1. Attempt with unauthorized role 'operator' -> Must be rejected
        res_unauth = await agent.apply_steward_action(
            action_type="DEPRECATE_CLAIM",
            target_id=env["old_claim_id"],
            reviewer_id=env["auditor_id"],
            user_name="Junior Operator",
            user_role="operator",
            organization_id=env["org_id"],
        )
        assert res_unauth["success"] is False
        assert "Separation of Duties (SoD) Barred" in res_unauth["error"]

        # 2. Attempt with authorized role 'reviewer' -> Must succeed
        res_auth = await agent.apply_steward_action(
            action_type="DEPRECATE_CLAIM",
            target_id=env["old_claim_id"],
            reviewer_id=env["auditor_id"],
            user_name="Chief Compliance Auditor",
            user_role="reviewer",
            organization_id=env["org_id"],
        )
        assert res_auth["success"] is True

        # Confirm in database that claim status is now OUTDATED
        res = await session.execute(select(Claim).where(Claim.id == env["old_claim_id"]))
        c = res.scalar_one()
        assert c.status == ClaimStatus.OUTDATED


@pytest.mark.asyncio
async def test_applied_action_writes_immutable_audit_records():
    """Acceptance Check 3: Every applied steward action writes an immutable review

    and user activity record to Postgres.
    """
    env = await setup_curator_test_env()
    async with AsyncSessionLocal() as session:
        agent = StewardAgentService(session)

        res = await agent.apply_steward_action(
            action_type="RESOLVE_CONFLICT",
            target_id=env["conflict_id"],
            payload={"suggested_winner_id": str(env["cfl_b_id"]), "rationale": "Audit precedence applied"},
            reviewer_id=env["auditor_id"],
            user_name="Chief Compliance Auditor",
            user_role="reviewer",
            organization_id=env["org_id"],
        )
        assert res["success"] is True

        # Verify HumanReview written
        stmt_rev = select(HumanReview).where(HumanReview.target_id == env["conflict_id"])
        res_rev = await session.execute(stmt_rev)
        review_record = res_rev.scalar_one_or_none()
        assert review_record is not None
        assert review_record.decision == ReviewDecision.APPROVE
        assert review_record.reviewer_id == env["auditor_id"]

        # Verify UserActivityLog written
        stmt_act = select(UserActivityLog).where(UserActivityLog.target_id == str(env["conflict_id"]))
        res_act = await session.execute(stmt_act)
        activity_record = res_act.scalar_one_or_none()
        assert activity_record is not None
        assert activity_record.action_type == "STEWARD_RECOMMENDATION_APPLIED"


@pytest.mark.asyncio
async def test_candidate_ocr_claim_never_promoted_to_verified_via_recommendation():
    """Acceptance Check 5: OCR/candidate claims never become verified through heuristic recommendation apply.

    Safety lock must prevent promotion.
    """
    env = await setup_curator_test_env()
    async with AsyncSessionLocal() as session:
        agent = StewardAgentService(session)

        # Attempt to promote candidate claim
        res = await agent.apply_steward_action(
            action_type="BOOST_EVIDENCE",
            target_id=env["candidate_claim_id"],
            payload={"proposed_status": "VERIFIED"},
            reviewer_id=env["auditor_id"],
            user_name="Chief Compliance Auditor",
            user_role="reviewer",
            organization_id=env["org_id"],
        )
        assert res["success"] is False
        assert "Safety Lock Active: Cannot promote unverified OCR/candidate claim to VERIFIED" in res["error"]

        # Verify claim remains CANDIDATE in DB
        res_claim = await session.execute(select(Claim).where(Claim.id == env["candidate_claim_id"]))
        c = res_claim.scalar_one()
        assert c.status == ClaimStatus.CANDIDATE


@pytest.mark.asyncio
async def test_explicit_versioned_re_attestation_semantics():
    """Acceptance Check 4: Re-Attest creates a versioned governance event recording

    attestation_id, attester_id, decision, reason, source_version, and 90-day expires_at.
    """
    env = await setup_curator_test_env()
    async with AsyncSessionLocal() as session:
        req = ClaimRemediateRequest(
            claim_id=env["old_claim_id"],
            action="RE_ATTEST",
            attester_id=env["auditor_id"],
            reason="Formal annual travel policy re-attestation",
            source_version="v1.0",
        )
        res = await remediate_claim_decay(req, session=session)

        assert res.action_taken == "RE_ATTEST"
        assert res.freshness_score == 1.00
        assert res.certification_status == "CERTIFIED"
        assert res.attestation_record is not None
        assert res.attestation_record.attester_id == env["auditor_id"]
        assert res.attestation_record.attestation_decision == "ATTESTED_VALID"
        assert res.attestation_record.source_version == "v1.0"
        # Expires in approximately 90 days
        delta = res.attestation_record.expires_at - res.attestation_record.attested_at
        assert delta.days in (89, 90, 91)

        # Verify HumanReview attestation record in database
        stmt_rev = select(HumanReview).where(HumanReview.id == res.attestation_record.attestation_id)
        res_rev = await session.execute(stmt_rev)
        rev = res_rev.scalar_one_or_none()
        assert rev is not None
        assert rev.target_type == "claim_attestation"
        assert rev.decision == ReviewDecision.APPROVE


@pytest.mark.asyncio
async def test_blast_radius_is_evidence_based_with_five_measurable_inputs():
    """Acceptance Check 6: Blast radius is calculated using the 5 measurable inputs:

    affected_claims + downstream_agent_workflows + tenant_scope + source_authority + conflict_severity.
    """
    env = await setup_curator_test_env()
    async with AsyncSessionLocal() as session:
        service = ConflictService(session)
        issues = await service.get_clustered_conflict_issues(organization_id=env["org_id"])

        assert len(issues) >= 1
        issue = issues[0]

        assert issue["impact_score"] > 0
        assert issue["blast_radius"] in ("CRITICAL_BLAST", "HIGH_BLAST", "ROUTINE")

        breakdown = issue.get("blast_radius_breakdown")
        assert breakdown is not None
        # Verify all 5 measurable inputs are explicitly reported
        assert "affected_claims" in breakdown
        assert "downstream_agent_workflows" in breakdown
        assert "tenant_scope" in breakdown
        assert "source_authority" in breakdown
        assert "conflict_severity" in breakdown
        assert "formula" in breakdown
        assert breakdown["total_score"] == issue["impact_score"]
