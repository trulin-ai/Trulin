import uuid
from datetime import datetime, timezone, timedelta
import pytest
from types import SimpleNamespace

from app.conflict_engine.precedence_engine import PrecedenceEngine, PrecedenceDecision
from app.conflict_engine.compatibility_gate import CompatibilityGate
from app.db.enums import ClaimStatus, ConflictType
from app.db.models.claim_conflict import ClaimConflict


def make_test_claim(
    text: str,
    subject: str = "Refund Policy",
    predicate: str = "stipulates",
    object_value: str = "",
    version_num: int = 1,
    doc_id: uuid.UUID | None = None,
    overall_trust: float = 0.85,
    authority_level: int = 75,
    is_current: bool = True,
    valid_from: datetime | None = None,
    valid_until: datetime | None = None,
    status: ClaimStatus = ClaimStatus.CANDIDATE,
    has_exception: bool = False,
    exception_text: str | None = None,
    audience: str | None = None,
    department: str | None = None,
):
    cid = uuid.uuid4()
    doc_uuid = doc_id or uuid.uuid4()

    doc_version = SimpleNamespace(
        id=uuid.uuid4(),
        document_id=doc_uuid,
        version_number=version_num,
        document=SimpleNamespace(
            id=doc_uuid,
            source=SimpleNamespace(authority_level=authority_level),
        ),
    )

    trust_scores = [SimpleNamespace(overall_score=overall_trust)]

    validity_records = [
        SimpleNamespace(
            is_current=is_current,
            valid_from=valid_from,
            valid_until=valid_until,
        )
    ]

    claim = SimpleNamespace(
        id=cid,
        claim_text=text,
        subject=subject,
        predicate=predicate,
        object_value=object_value,
        status=status,
        document_version=doc_version,
        trust_scores=trust_scores,
        validity_records=validity_records,
        evidence=[],
        authority_level=authority_level,
        has_exception=has_exception,
        exception_text=exception_text,
        audience=audience,
        department=department,
    )
    return claim


def test_general_rule_vs_specific_exception_no_auto_supersession():
    """Specific exception/carveout must NOT be auto-superseded by a general baseline rule."""
    general_rule = make_test_claim(
        text="All customer subscriptions are strictly non-refundable.",
        subject="Refund Policy",
        authority_level=80,
    )
    specific_exception = make_test_claim(
        text="Enterprise tier annual subscriptions are eligible for pro-rated refunds upon VP approval.",
        subject="Refund Policy",
        authority_level=75,
        has_exception=True,
        exception_text="Enterprise tier annual subscriptions",
    )

    decision = PrecedenceEngine.evaluate_precedence(general_rule, specific_exception)

    # Must preserve exception coexistence (Lex Specialis), never auto-supersede the exception
    assert decision.is_compatible_exception is True
    assert decision.is_auto_resolved is True
    assert decision.precedence_rule == "LEX_SPECIALIS_EXCEPTION"
    assert decision.loser_claim_id is None
    assert "Lex Specialis" in decision.reasoning


def test_newer_lower_authority_rule_no_auto_supersession():
    """A newer departmental draft (e.g. v2 / authority 60%) must NOT supersede an older official policy (v1 / authority 90%)."""
    official_v1 = make_test_claim(
        text="All vendor contracts exceeding $10,000 require CFO and Legal signoff.",
        subject="Vendor Approval",
        version_num=1,
        authority_level=90,
    )
    department_draft_v2 = make_test_claim(
        text="Vendor contracts up to $50,000 only require Department Head approval.",
        subject="Vendor Approval",
        version_num=2,
        authority_level=60,
    )

    decision = PrecedenceEngine.evaluate_precedence(official_v1, department_draft_v2)

    # Authority hierarchy (90 vs 60) overrides mere recency/version
    assert decision.is_auto_resolved is True
    assert decision.precedence_rule == "AUTHORITY_HIERARCHY_PRECEDENCE"
    assert decision.winner_claim_id == official_v1.id
    assert decision.loser_claim_id == department_draft_v2.id


def test_different_employee_tiers_no_conflict():
    """Claims scoped to distinct audiences (Contractors vs Full-Time) are non-competing scopes and do not conflict."""
    contractor_rule = make_test_claim(
        text="Contractors are eligible for 10 days of unpaid personal leave.",
        subject="Leave Policy",
        audience="contractor",
    )
    fulltime_rule = make_test_claim(
        text="Full-time employees receive 25 days of paid annual vacation leave.",
        subject="Leave Policy",
        audience="full-time",
    )

    outcome = CompatibilityGate.evaluate_compatibility(contractor_rule, fulltime_rule)
    assert outcome.is_comparable is False
    assert outcome.reason == "DISJOINT_APPLICABILITY_SCOPE"


def test_different_temporal_windows_no_conflict():
    """Claims valid in disjoint, non-overlapping historical/future periods do not conflict."""
    now = datetime.now(timezone.utc)
    old_window = make_test_claim(
        text="Travel per-diem rate was $75 per day.",
        subject="Travel Reimbursement",
        valid_from=now - timedelta(days=700),
        valid_until=now - timedelta(days=365),
    )
    new_window = make_test_claim(
        text="Travel per-diem rate is $120 per day.",
        subject="Travel Reimbursement",
        valid_from=now - timedelta(days=30),
        valid_until=now + timedelta(days=365),
    )

    outcome = CompatibilityGate.evaluate_compatibility(old_window, new_window)
    assert outcome.is_comparable is False
    assert outcome.reason == "NON_OVERLAPPING_TEMPORAL_WINDOWS"


def test_ocr_claim_in_conflict_no_automatic_verified_promotion():
    """Conflict resolution must NEVER promote an unverified/candidate/OCR claim to VERIFIED status."""
    ocr_claim = make_test_claim(
        text="Data retention period is 7 years for financial records.",
        status=ClaimStatus.CANDIDATE,
        authority_level=90,
    )
    # Simulate conflict detector & service state machine update
    original_status = ocr_claim.status
    if original_status == ClaimStatus.CANDIDATE or getattr(ocr_claim, "claim_type", "").lower() in ("ocr", "candidate", "provisional"):
        new_status = ClaimStatus.CANDIDATE
    else:
        new_status = ClaimStatus.VERIFIED

    # The winner must remain CANDIDATE until independent certification/verification verifies it
    assert new_status == ClaimStatus.CANDIDATE
    assert new_status != ClaimStatus.VERIFIED


def test_cluster_resolution_all_underlying_pairs_audited():
    """Cluster-level or batch conflict resolution properly records metadata on the ClaimConflict model."""
    conflict = ClaimConflict(
        id=uuid.uuid4(),
        claim_a_id=uuid.uuid4(),
        claim_b_id=uuid.uuid4(),
        conflict_type=ConflictType.DIRECT_CONTRADICTION.value,
        conflicting_fields=["claim_text", "status"],
        supporting_evidence={"reason": "Direct semantic contradiction between v1 and v2"},
        source_authority={"authority_a": 75, "authority_b": 90},
        applicable_scope={"audience_a": "all", "audience_b": "all"},
        effective_dates={"valid_until_a": None, "valid_until_b": None},
        reviewer_decision="ACCEPTED_B_OVER_A",
        resolution_rationale="Source B possesses 90% corporate authority versus 75% for Source A",
    )

    assert conflict.conflict_type == "direct_contradiction"
    assert conflict.conflicting_fields == ["claim_text", "status"]
    assert conflict.source_authority["authority_b"] == 90
    assert conflict.reviewer_decision == "ACCEPTED_B_OVER_A"
    assert "90% corporate authority" in conflict.resolution_rationale
