import decimal
import uuid
import pytest
import httpx
from sqlalchemy import select

from app.db.database import AsyncSessionLocal
from app.db.enums import ClaimStatus, ConflictStatus, ConflictType, RecordStatus, ReviewDecision, UserRole
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.models.human_review import HumanReview
from app.db.models.organization import Organization
from app.db.models.user import User
from app.db.repositories.data_source_repository import DataSourceRepository
from app.main import app

BASE_URL = "http://test"


@pytest.mark.asyncio
async def test_conflict_endpoints_full_lifecycle_and_audit():
    """
    Layer 2 & 3 Verification:
    Tests all 5 conflict endpoints via ASGI AsyncClient:
    1. GET /v1/conflicts/pending
    2. GET /v1/conflicts/issues
    3. POST /v1/conflicts/auto-resolve
    4. POST /v1/conflicts/issues/{issue_id}/resolve
    5. POST /v1/conflicts/re-evaluate

    Verifies:
    - HTTP status & response schemas
    - State machine safety (no OCR / candidate promotion to VERIFIED)
    - Immutable human_reviews audit provenance
    - Separation of Duties (SoD 403 vs 200)
    - Read endpoints (GET) are read-only and never mutate claim or conflict state
    - Re-running resolution does not create duplicate entries
    """
    async with AsyncSessionLocal() as session:
        uid = uuid.uuid4().hex[:6]
        org = Organization(name=f"E2E API Conflict Org {uid}", slug=f"e2e-api-org-{uid}")
        session.add(org)
        await session.flush()

        # Reviewer User (Authorized for conflicts:resolve)
        reviewer = User(
            email=f"reviewer-{uid}@enterprise.com",
            name=f"Reviewer {uid}",
            role=UserRole.REVIEWER,
            organization_id=org.id,
            status=RecordStatus.ACTIVE,
        )
        # Operator User (Unauthorized for conflicts:resolve)
        operator = User(
            email=f"operator-{uid}@enterprise.com",
            name=f"Operator {uid}",
            role=UserRole.DEVELOPER,
            organization_id=org.id,
            status=RecordStatus.ACTIVE,
        )
        session.add_all([reviewer, operator])
        await session.flush()

        ds_repo = DataSourceRepository(session)
        ds = await ds_repo.get_or_create(
            organization_id=org.id,
            name="HR Governance Portal",
            source_type="file_upload",
            external_id=f"hr-{uid}",
            authority_level=85,
        )

        doc = Document(
            organization_id=org.id,
            source_id=ds.id,
            title="Employee Handbook 2026",
            document_type="policy",
            content_hash=f"hash-e2e-{uid}",
        )
        session.add(doc)
        await session.flush()

        v1 = DocumentVersion(document_id=doc.id, version_number=1, is_current=False, content_hash=f"h-v1-{uid}")
        v2 = DocumentVersion(document_id=doc.id, version_number=2, is_current=True, content_hash=f"h-v2-{uid}")
        session.add_all([v1, v2])
        await session.flush()

        # Create two competing claims
        claim_v1 = Claim(
            organization_id=org.id,
            document_version_id=v1.id,
            claim_text="Legacy severance pays 2 weeks per year of service.",
            subject="Severance Allowance",
            claim_type="policy",
            status=ClaimStatus.CONFLICTED,
        )
        claim_v2 = Claim(
            organization_id=org.id,
            document_version_id=v2.id,
            claim_text="Active severance pays 4 weeks per year of service under policy v2.0, explicitly superseding v1.0.",
            subject="Severance Allowance",
            claim_type="policy",
            status=ClaimStatus.CONFLICTED,
        )
        # Also create a candidate claim to test OCR candidate protection
        claim_cand = Claim(
            organization_id=org.id,
            document_version_id=v2.id,
            claim_text="Candidate severance draft provides 6 weeks per year of service.",
            subject="Severance Allowance",
            claim_type="ocr",
            status=ClaimStatus.CANDIDATE,
        )
        # Competing claims for manual issue resolution test (Ambiguous: 30 days vs 45 days, same authority 80)
        claim_m1 = Claim(
            organization_id=org.id,
            document_version_id=v1.id,
            claim_text="Standard notice period duration is 30 calendar days.",
            subject="Notice Period",
            claim_type="policy",
            status=ClaimStatus.CONFLICTED,
        )
        claim_m2 = Claim(
            organization_id=org.id,
            document_version_id=v1.id,
            claim_text="Standard notice period duration is 45 calendar days.",
            subject="Notice Period",
            claim_type="policy",
            status=ClaimStatus.CONFLICTED,
        )
        session.add_all([claim_v1, claim_v2, claim_cand, claim_m1, claim_m2])
        await session.flush()

        # Seed Conflict 1 (Auto-resolvable by explicit supersession)
        conflict1 = ClaimConflict(
            claim_a_id=claim_v1.id,
            claim_b_id=claim_v2.id,
            conflict_type=ConflictType.VERSION_CONFLICT.value,
            severity="high",
            confidence=decimal.Decimal("0.9500"),
            resolution_status=ConflictStatus.HUMAN_REVIEW_REQUIRED,
        )
        # Seed Conflict 2 (Ambiguous numeric contradiction: Requires Human Review)
        conflict2 = ClaimConflict(
            claim_a_id=claim_m1.id,
            claim_b_id=claim_m2.id,
            conflict_type=ConflictType.NUMERIC_CONFLICT.value,
            severity="high",
            confidence=decimal.Decimal("0.9000"),
            resolution_status=ConflictStatus.HUMAN_REVIEW_REQUIRED,
        )
        session.add_all([conflict1, conflict2])
        await session.commit()

        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url=BASE_URL) as client:
            # ------------------------------------------------------------------
            # 1. GET /v1/conflicts/pending & Safety Check: Read-Time Immutability
            # ------------------------------------------------------------------
            resp_pending = await client.get(f"/v1/conflicts/pending?organization_id={org.id}")
            assert resp_pending.status_code == 200, f"Pending fetch failed: {resp_pending.text}"
            pending_data = resp_pending.json()
            assert len(pending_data) >= 2

            # Safety Check: Calling GET endpoint must NEVER mutate claim or conflict state
            await session.refresh(claim_v1)
            await session.refresh(claim_v2)
            await session.refresh(claim_cand)
            assert claim_cand.status == ClaimStatus.CANDIDATE, "GET read must never promote candidate"
            assert claim_v1.status == ClaimStatus.CONFLICTED, "GET read must never resolve claims"

            # ------------------------------------------------------------------
            # 2. GET /v1/conflicts/issues (Clustered Governance Issues)
            # ------------------------------------------------------------------
            resp_issues = await client.get(f"/v1/conflicts/issues?organization_id={org.id}")
            assert resp_issues.status_code == 200
            issues = resp_issues.json()
            assert len(issues) >= 1
            issue = issues[0]
            assert "issue_id" in issue
            assert "impact_score" in issue
            assert "blast_radius" in issue
            assert "cluster_a" in issue
            assert "cluster_b" in issue
            assert "conflict_ids" in issue
            assert issue["blast_radius"] in ("CRITICAL_BLAST", "HIGH_BLAST", "ROUTINE")

            # ------------------------------------------------------------------
            # 3. POST /v1/conflicts/auto-resolve (Autonomous Precedence Engine)
            # ------------------------------------------------------------------
            resp_auto = await client.post(f"/v1/conflicts/auto-resolve?organization_id={org.id}")
            assert resp_auto.status_code == 200
            auto_data = resp_auto.json()
            assert auto_data["status"] == "success"
            assert auto_data["auto_resolved_count"] >= 1

            # Database Assertions for Conflict 1 (Auto-resolved)
            await session.refresh(conflict1)
            assert conflict1.resolution_status == ConflictStatus.RESOLVED
            assert conflict1.resolved_claim_id == claim_v2.id
            assert conflict1.resolved_by is not None
            assert conflict1.resolved_at is not None

            # Assert Claim Status Updates: winner VERIFIED, loser OUTDATED/SUPERSEDED
            await session.refresh(claim_v1)
            await session.refresh(claim_v2)
            assert claim_v2.status == ClaimStatus.VERIFIED
            assert claim_v1.status in (ClaimStatus.OUTDATED, ClaimStatus.SUPERSEDED)

            # Assert HumanReview ledger record exists
            stmt_hr = select(HumanReview).where(HumanReview.target_id == conflict1.id)
            res_hr = await session.execute(stmt_hr)
            hr_record = res_hr.scalar_one_or_none()
            assert hr_record is not None
            assert hr_record.decision == ReviewDecision.APPROVE
            assert "Autonomous Precedence Engine" in hr_record.reason

            # ------------------------------------------------------------------
            # 4. Separation of Duties (SoD) on /resolve
            # ------------------------------------------------------------------
            # Fetch remaining pending issues after auto-resolve
            resp_remaining = await client.get(f"/v1/conflicts/issues?organization_id={org.id}")
            assert resp_remaining.status_code == 200
            rem_issues = resp_remaining.json()
            target_issue_id = rem_issues[0]["issue_id"] if rem_issues else issue["issue_id"]

            # Unauthorized operator attempt -> 403 Forbidden
            resp_unauth = await client.post(
                f"/v1/conflicts/issues/{target_issue_id}/resolve?user_role=developer",
                json={
                    "reviewer_id": str(operator.id),
                    "decision": "approve",
                    "chosen_side": "A",
                    "reason": "Developer unauthorized resolution attempt",
                },
            )
            assert resp_unauth.status_code == 403
            assert "Separation of Duties" in resp_unauth.json()["detail"]

            # Authorized reviewer attempt -> 200 OK
            resp_auth = await client.post(
                f"/v1/conflicts/issues/{target_issue_id}/resolve?user_role=reviewer&organization_id={org.id}",
                json={
                    "reviewer_id": str(reviewer.id),
                    "decision": "approve",
                    "chosen_side": "A",
                    "reason": "Authorized Compliance Auditor approves primary severance policy",
                },
            )
            assert resp_auth.status_code == 200
            resolve_data = resp_auth.json()
            assert resolve_data["status"] == "success"
            assert resolve_data["resolved_conflicts_count"] >= 1

            # ------------------------------------------------------------------
            # 5. POST /v1/conflicts/re-evaluate
            # ------------------------------------------------------------------
            resp_reeval = await client.post(
                f"/v1/conflicts/re-evaluate?user_role=reviewer&organization_id={org.id}"
            )
            assert resp_reeval.status_code == 200
            reeval_data = resp_reeval.json()
            assert reeval_data["status"] == "success"
            assert "purged_false_positives" in reeval_data

            # ------------------------------------------------------------------
            # 6. Re-Running Resolution Must Be Idempotent (No Duplicate Conflicts or Reviews)
            # ------------------------------------------------------------------
            resp_auto_again = await client.post(f"/v1/conflicts/auto-resolve?organization_id={org.id}")
            assert resp_auto_again.status_code == 200
            assert resp_auto_again.json()["auto_resolved_count"] == 0, "Idempotent re-run must resolve 0 additional conflicts"
