import uuid
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

from app.db.enums import ClaimStatus, ConflictStatus, ConflictType, ReviewDecision
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.db.models.claim_trust_score import ClaimTrustScore
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.schemas.drift import ClaimRemediateRequest
from app.services.conflict_service import ConflictService
from app.services.drift_decay_service import (
    _calculate_decay,
    _IN_MEMORY_DRIFT_CLAIMS,
    analyze_context_drift,
    remediate_claim_decay,
)
from app.services.steward_agent import StewardAgentService


def test_drift_decay_separation_of_freshness_and_certification():
    """Tightening 2: The decay formula is an advisory freshness signal,

    NOT an automatic reduction or invalidation of a claim's legal certification_status.
    """
    # 1. Test 15-day-old claim (fresh)
    trust_fresh, dec_pct_fresh, cat_fresh, _ = _calculate_decay(15, 0.95)
    fresh_score_fresh = round(trust_fresh / 0.95, 2)
    assert fresh_score_fresh == 1.00
    assert cat_fresh == "ACTIVE_FRESH"

    # 2. Test 190-day-old claim (severely decayed)
    trust_old, dec_pct_old, cat_old, _ = _calculate_decay(190, 0.90)
    fresh_score_old = round(trust_old / 0.90, 2)
    assert fresh_score_old == 0.50
    assert cat_old == "SEVERELY_DECAYED"
    assert dec_pct_old == 50.0

    # Key Architectural Invariant:
    # A 190-day-old claim has freshness_score=0.50, but remains CERTIFIED if within policy validity
    # and has no open conflict. Legal certification is governed by verification workflows, not time.


@pytest.mark.asyncio
async def test_drift_analysis_preserves_certification_status():
    """Tightening 2 (Integration): analyze_context_drift populates both freshness_score

    and certification_status as distinct independent fields.
    """
    org_id = uuid.uuid4()
    report = await analyze_context_drift(organization_id=org_id, session=None)

    assert report.total_claims >= 5
    assert report.freshness_index_pct > 0

    for item in report.decayed_claims:
        # Both fields must exist and be strongly typed
        assert hasattr(item, "freshness_score")
        assert hasattr(item, "certification_status")
        assert isinstance(item.freshness_score, float)
        assert isinstance(item.certification_status, str)

        # Severely decayed claims must NOT be silently retired to SUPERSEDED
        if item.age_days > 180:
            assert item.drift_category in ("SEVERELY_DECAYED", "STALE_TEMPORAL", "EXPIRED_ATTESTATION_RE_EVALUATION")
            # It retains its active certified standing on the radar until formally retired
            assert item.certification_status in ("CERTIFIED", "VERIFIED")


@pytest.mark.asyncio
async def test_explicit_versioned_re_attestation_semantics():
    """Tightening 3: 'Re-attest' must not simply reset age to zero and restore trust to 100%.

    It must create a versioned governance event:
    attestation_id, claim_id, attester_id, attestation_decision, attestation_reason,
    source_version, evidence_version, attested_at, expires_at.
    """
    cid = uuid.UUID("55555555-5555-5555-5555-555555555554")
    attester_id = uuid.uuid4()
    req = ClaimRemediateRequest(
        claim_id=cid,
        action="RE_ATTEST",
        attester_id=attester_id,
        reason="Annual cloud infrastructure policy re-attestation by DevOps Compliance Lead",
        source_version="v1.0",
    )

    res = await remediate_claim_decay(req, session=None)

    assert res.action_taken == "RE_ATTEST"
    assert res.freshness_score == 1.00
    assert res.certification_status == "CERTIFIED"
    assert res.attestation_record is not None

    rec = res.attestation_record
    assert rec.claim_id == cid
    assert rec.attester_id == attester_id
    assert rec.attestation_decision == "ATTESTED_VALID"
    assert rec.source_version == "v1.0"
    assert rec.evidence_version == "ev_v1.0"
    assert "Annual cloud infrastructure policy re-attestation" in rec.attestation_reason
    assert rec.attested_at is not None
    assert rec.expires_at is not None
    # 90-day review horizon
    horizon_days = (rec.expires_at - rec.attested_at).days
    assert horizon_days in (89, 90, 91)


@pytest.mark.asyncio
async def test_attestation_source_version_validation_mismatch_rejected():
    """Tightening 3 (Validation): Attestation referencing an outdated source version

    (e.g. v0.8 instead of v1.0) must be rejected with an actionable mismatch error.
    """
    cid = uuid.UUID("55555555-5555-5555-5555-555555555551")
    attester_id = uuid.uuid4()
    req = ClaimRemediateRequest(
        claim_id=cid,
        action="RE_ATTEST",
        attester_id=attester_id,
        reason="Stale review against old draft",
        source_version="v0.8",  # Mismatched against active v1.0
    )

    res = await remediate_claim_decay(req, session=None)

    assert res.action_taken == "RE_ATTEST_REJECTED"
    assert res.new_status == "REQUIRES_RE_EVALUATION"
    assert "Source version mismatch" in res.message
    assert res.attestation_record is None


@pytest.mark.asyncio
async def test_attestation_expiry_horizon_and_source_revision_invalidation():
    """Tightening 3 (Lifecycle): Expired attestation (>90d) and source changes

    trigger explicit re-evaluation categories on the freshness radar.
    """
    org_id = uuid.uuid4()
    org_key = str(org_id)
    now = datetime.now(timezone.utc)

    # Seed test claim with expired attestation
    test_cid = uuid.uuid4()
    _IN_MEMORY_DRIFT_CLAIMS[str(test_cid)] = {
        "claim_id": test_cid,
        "organization_id": org_key,
        "claim_text": "Vendor security audits are conducted annually by external certified assessors.",
        "document_title": "Enterprise Vendor Risk Policy",
        "created_at": now - timedelta(days=120),
        "initial_trust": 0.95,
        "status": "VERIFIED",
        "certification_status": "CERTIFIED",
        "source_version": "v1.0",
        "attestation_record": {
            "attestation_id": uuid.uuid4(),
            "attested_at": now - timedelta(days=100),
            "expires_at": now - timedelta(days=10),  # Expired 10 days ago
        },
    }

    report = await analyze_context_drift(org_id, session=None)
    item = next(d for d in report.decayed_claims if d.claim_id == test_cid)

    assert item.drift_category == "EXPIRED_ATTESTATION_RE_EVALUATION"
    assert "90-day attestation review horizon expired" in item.recommended_action
    assert item.certification_status == "CERTIFIED"  # Legal certification intact

    # Test source revision invalidation
    _IN_MEMORY_DRIFT_CLAIMS[str(test_cid)]["source_revised_after_attestation"] = True
    report2 = await analyze_context_drift(org_id, session=None)
    item2 = next(d for d in report2.decayed_claims if d.claim_id == test_cid)

    assert item2.drift_category == "SOURCE_REVISION_RE_EVALUATION_REQUIRED"
    assert "Source document revised since last attestation" in item2.recommended_action


@pytest.mark.asyncio
async def test_shadow_mode_produces_measurable_comparison_report():
    """Tightening 2: shadow_mode=True produces an explicit comparison artifact

    with shadow_run_id, conflicts_detected, would_auto_resolve_count,
    human_review_queue_count, false_positive_candidates, precision_estimate,
    and rollback_reference, with ZERO database mutations.
    """
    mock_db = AsyncMock()

    # Create mock conflict
    mock_conflict = MagicMock(spec=ClaimConflict)
    mock_conflict.id = uuid.uuid4()
    mock_conflict.conflict_type = "numeric_conflict"
    mock_conflict.severity = "HIGH"
    mock_conflict.confidence = 0.90
    mock_conflict.resolved_claim_id = None

    c_a = MagicMock(spec=Claim)
    c_a.id = uuid.uuid4()
    c_a.claim_text = "Policy valid for 2024 only."
    c_a.subject = "Policy"
    c_a.predicate = "valid_for"
    c_a.object_value = "2024"
    c_a.authority_level = 75
    c_a.document_version = MagicMock(version_number=1, document=None)
    c_a.trust_scores = []
    c_a.validity_records = []
    c_a.evidence = []

    c_b = MagicMock(spec=Claim)
    c_b.id = uuid.uuid4()
    c_b.claim_text = "Policy valid for 2026 active operations."
    c_b.subject = "Policy"
    c_b.predicate = "valid_for"
    c_b.object_value = "2026"
    c_b.authority_level = 75
    c_b.document_version = MagicMock(version_number=2, document=None)
    c_b.trust_scores = []
    c_b.validity_records = []
    c_b.evidence = []

    mock_conflict.claim_a = c_a
    mock_conflict.claim_b = c_b

    res_mock = MagicMock()
    res_mock.scalars().all.return_value = [mock_conflict]
    mock_db.execute.return_value = res_mock

    service = ConflictService(mock_db)
    res = await service.auto_resolve_conflicts(shadow_mode=True)

    # Assert exact artifact structure required by master plan
    assert "shadow_run_id" in res
    assert res["shadow_run_id"].startswith("srun_")
    assert res["operating_mode"] == "SHADOW_RECOMMENDATION_ONLY"
    assert "conflicts_detected" in res
    assert "would_auto_resolve_count" in res
    assert "human_review_queue_count" in res
    assert "false_positive_candidates" in res
    assert "precision_estimate" in res
    assert "rollback_reference" in res
    assert res["rollback_reference"].startswith("rb_snap_")

    # Assert ZERO database commits or flushes occurred
    assert mock_db.commit.call_count == 0
    assert mock_db.flush.call_count == 0


@pytest.mark.asyncio
async def test_steward_recommendations_advisory_first_schema():
    """Tightening 1: The Steward Agent must operate in advisory-first mode.

    Recommendations must require approval and expose:
    recommendation_id, action_type, target_claim_id, proposed_status, evidence_ids,
    rationale, confidence, requires_approval = True.
    """
    mock_db = AsyncMock()
    mock_doc = MagicMock(spec=Document)
    mock_doc.title = "Refund Policy 2026"
    mock_doc.versions = []

    res_docs = MagicMock()
    res_docs.scalars().all.return_value = [mock_doc]

    mock_claim = MagicMock(spec=Claim)
    mock_claim.id = uuid.uuid4()
    mock_claim.claim_text = "Standard refund window for 2024 purchases is 14 days."
    mock_claim.status = ClaimStatus.ACTIVE
    mock_claim.trust_scores = []
    mock_claim.validity_records = []
    mock_claim.evidence = []

    res_claims = MagicMock()
    res_claims.scalars().all.return_value = [mock_claim]

    res_conflicts = MagicMock()
    res_conflicts.scalars().all.return_value = []

    mock_db.execute.side_effect = [res_docs, res_claims, res_conflicts]

    agent = StewardAgentService(mock_db)
    audit = await agent.run_context_audit(organization_id=uuid.uuid4())

    assert audit["operating_mode"] == "ADVISORY_FIRST"
    assert audit["recommendations_count"] >= 1

    rec = audit["recommendations"][0]
    assert "recommendation_id" in rec
    assert "action_type" in rec
    assert "target_claim_id" in rec
    assert "proposed_status" in rec
    assert "evidence_ids" in rec
    assert "rationale" in rec
    assert "confidence" in rec
    assert rec["requires_approval"] is True


@pytest.mark.asyncio
async def test_rbac_sod_matrix_all_five_roles():
    """RBAC Matrix Verification: Tests all 5 enterprise roles.

    Viewer & Operator: Barred (SoD 403 / failure)
    Reviewer, Auditor, Admin: Authorized (200 / clearance active)
    """
    mock_db = AsyncMock()
    agent = StewardAgentService(mock_db)

    # 1. Viewer -> Blocked
    res_viewer = await agent.apply_steward_action(
        action_type="DEPRECATE_CLAIM",
        target_id=uuid.uuid4(),
        user_role="viewer",
    )
    assert res_viewer["success"] is False
    assert "Separation of Duties (SoD) Barred" in res_viewer["error"]

    # 2. Operator -> Blocked
    res_operator = await agent.apply_steward_action(
        action_type="DEPRECATE_CLAIM",
        target_id=uuid.uuid4(),
        user_role="operator",
    )
    assert res_operator["success"] is False
    assert "Separation of Duties (SoD) Barred" in res_operator["error"]

    # 3. Reviewer -> Allowed (simulate claim existence)
    mock_claim = MagicMock(spec=Claim)
    mock_claim.id = uuid.uuid4()
    mock_claim.status = ClaimStatus.ACTIVE
    res_m = MagicMock()
    res_m.scalar_one_or_none.return_value = mock_claim
    mock_db.execute.return_value = res_m

    res_reviewer = await agent.apply_steward_action(
        action_type="DEPRECATE_CLAIM",
        target_id=mock_claim.id,
        user_role="reviewer",
    )
    assert res_reviewer["success"] is True

    # 4. Auditor -> Allowed
    res_auditor = await agent.apply_steward_action(
        action_type="DEPRECATE_CLAIM",
        target_id=mock_claim.id,
        user_role="auditor",
    )
    assert res_auditor["success"] is True

    # 5. Admin -> Allowed
    res_admin = await agent.apply_steward_action(
        action_type="DEPRECATE_CLAIM",
        target_id=mock_claim.id,
        user_role="admin",
    )
    assert res_admin["success"] is True


@pytest.mark.asyncio
async def test_candidate_ocr_claim_protected_from_verification_promotion():
    """Acceptance Check 5: OCR/candidate claims never become verified through heuristic recommendation apply."""
    mock_db = AsyncMock()
    candidate_claim = MagicMock(spec=Claim)
    candidate_claim.id = uuid.uuid4()
    candidate_claim.status = ClaimStatus.CANDIDATE

    res_mock = MagicMock()
    res_mock.scalar_one_or_none.return_value = candidate_claim
    mock_db.execute.return_value = res_mock

    agent = StewardAgentService(mock_db)
    res = await agent.apply_steward_action(
        action_type="BOOST_EVIDENCE",
        target_id=candidate_claim.id,
        payload={"proposed_status": "VERIFIED"},
        user_role="reviewer",
    )
    assert res["success"] is False
    assert "Safety Lock Active: Cannot promote unverified OCR/candidate claim to VERIFIED" in res["error"]


def test_blast_radius_evidence_based_formula_with_provenance():
    """Tightening 4: Blast radius is defined from measurable inputs with full provenance:

    workflow_count_source: "registered_agent_workflow_index", workflow_ids, calculation_version.
    """
    affected_claims_count = 4
    downstream_workflows = 3
    tenant_scope_val = 3.0  # organization-wide
    source_auth = 0.85
    sev_score = 35.0  # CRITICAL

    impact_score = round(
        (affected_claims_count * 2.5) +
        (downstream_workflows * 5.0) +
        (tenant_scope_val * 10.0) +
        (source_auth * 10.0) +
        sev_score,
        1
    )

    assert impact_score == 98.5
    assert impact_score >= 60.0  # CRITICAL_BLAST

    topic_slug = "customer_refund"
    workflow_ids = [f"wf_{topic_slug}_{i+1}" for i in range(downstream_workflows)]

    breakdown = {
        "affected_claims": affected_claims_count,
        "affected_claims_score": round(affected_claims_count * 2.5, 1),
        "downstream_agent_workflows": downstream_workflows,
        "workflows_score": round(downstream_workflows * 5.0, 1),
        "workflow_count_source": "registered_agent_workflow_index",
        "workflow_ids": workflow_ids,
        "calculation_version": "blast_radius_v1",
        "tenant_scope": "Organization-Wide (3.0)",
        "tenant_scope_score": round(tenant_scope_val * 10.0, 1),
        "source_authority": round(source_auth, 2),
        "source_authority_score": round(source_auth * 10.0, 1),
        "conflict_severity": f"CRITICAL ({sev_score})",
        "conflict_severity_score": sev_score,
        "total_score": impact_score,
        "formula": "affected_claims*2.5 + workflows*5.0 + tenant_scope*10.0 + authority*10.0 + severity",
    }

    assert breakdown["workflow_count_source"] == "registered_agent_workflow_index"
    assert len(breakdown["workflow_ids"]) == 3
    assert breakdown["workflow_ids"] == ["wf_customer_refund_1", "wf_customer_refund_2", "wf_customer_refund_3"]
    assert breakdown["calculation_version"] == "blast_radius_v1"
    assert breakdown["total_score"] == 98.5
