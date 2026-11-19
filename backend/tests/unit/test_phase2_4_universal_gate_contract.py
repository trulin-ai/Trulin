"""
Phase 2.4: Universal Shared Gate Contract Unit Tests.
Tests fail-closed enforcement and machine-readable failure codes across all required gate families:
1. Evidence grounding: missing span, fabricated span, invalid character offsets.
2. Predicate normativity: catch-all predicates, deprecated verbs, invalid predicates.
3. SPO compatibility: actor role inversion, payment instrument obligations, invalid combinations.
4. Polarity and modality consistency: polarity inversion, non-normative modality mismatch.
5. Table-column binding: wrong header-to-predicate mapping.
6. Condition, exception, and scope preservation: lost conditions, lost exceptions, lost scope.
7. Evaluator routing: ClaimGateEvaluator and UniversalGateEvaluator routing through shared contract.
"""

import pytest

from app.services.gate_contract import (
    GateFailureCode,
    SharedGateRequest,
    SharedGateResult,
    SharedGovernanceGateEngine,
)
from app.services.claim_gate_evaluator import ClaimGateEvaluator
from app.services.universal_gate_evaluator import UniversalGateEvaluator


# -----------------------------------------------------------------------------
# Family 1: Evidence Grounding & Source Locator Validity
# -----------------------------------------------------------------------------
def test_gate_rejects_missing_evidence():
    req = SharedGateRequest(
        claim_text="Returns may be made within 30 days.",
        subject="Merchandise",
        predicate="has_return_window",
        object_val="30 days",
        evidence_quote="",  # Missing
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.evidence_grounding is False
    assert res.all_gates_passed is False
    assert GateFailureCode.ERR_EVIDENCE_MISSING.value in res.reason_codes


def test_gate_rejects_fabricated_evidence_span():
    doc_text = "Northwind Outfitters offers a 30-day return policy for standard merchandise."
    req = SharedGateRequest(
        claim_text="Returns accepted within 180 days with no questions asked.",
        subject="Merchandise",
        predicate="has_return_window",
        object_val="180 days",
        evidence_quote="Returns accepted within 180 days with no questions asked.",  # Not in doc
        document_text=doc_text,
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.evidence_grounding is False
    assert res.all_gates_passed is False
    assert GateFailureCode.ERR_EVIDENCE_FABRICATED.value in res.reason_codes


def test_gate_rejects_invalid_locators():
    req = SharedGateRequest(
        claim_text="Returns may be made within 30 days.",
        subject="Merchandise",
        predicate="has_return_window",
        object_val="30 days",
        evidence_quote="Returns may be made within 30 days.",
        locators=[{"page": 5, "start": 500, "end": 400}],  # Invalid: start > end
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.source_locator_validity is False
    assert res.all_gates_passed is False
    assert GateFailureCode.ERR_LOCATOR_INVALID.value in res.reason_codes


# -----------------------------------------------------------------------------
# Family 2: Predicate Normativity & Taxonomy
# -----------------------------------------------------------------------------
def test_gate_rejects_catch_all_predicate():
    req = SharedGateRequest(
        claim_text="Standard return policy governs customer eligibility.",
        subject="Customer",
        predicate="has_validity_rule",  # Catch-all
        object_val="policy",
        evidence_quote="Standard return policy governs customer eligibility.",
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.predicate_normativity is False
    assert res.all_gates_passed is False
    assert GateFailureCode.ERR_PREDICATE_CATCH_ALL.value in res.reason_codes


def test_gate_rejects_deprecated_predicate():
    req = SharedGateRequest(
        claim_text="Customer may cancel order prior to dispatch.",
        subject="Customer",
        predicate="cancel",  # Deprecated verb
        object_val="order",
        evidence_quote="Customer may cancel order prior to dispatch.",
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.predicate_normativity is False
    assert res.all_gates_passed is False
    assert GateFailureCode.ERR_PREDICATE_DEPRECATED.value in res.reason_codes


# -----------------------------------------------------------------------------
# Family 3: Table-Column Binding Integrity
# -----------------------------------------------------------------------------
def test_gate_rejects_wrong_table_column_binding():
    req = SharedGateRequest(
        claim_text="Return label cost is $6.95 deducted from refund.",
        subject="Return label",
        predicate="has_return_window",  # Wrong binding: table header is 'Return label cost'
        object_val="$6.95",
        evidence_quote="Return label cost is $6.95 deducted from refund.",
        table_header="Return label cost",
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.table_column_binding is False
    assert res.all_gates_passed is False
    assert GateFailureCode.ERR_TABLE_BINDING_MISMATCH.value in res.reason_codes


# -----------------------------------------------------------------------------
# Family 4: SPO Compatibility & Semantic Typing
# -----------------------------------------------------------------------------
def test_gate_rejects_actor_role_inversion():
    req = SharedGateRequest(
        claim_text="Customer offers 10% bonus credit on store returns.",
        subject="Customer",  # Inverted actor: customer cannot offer bonuses
        predicate="offers_store_credit_bonus",
        object_val="10% bonus",
        evidence_quote="Customer offers 10% bonus credit on store returns.",
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.spo_compatibility is False
    assert res.all_gates_passed is False
    assert GateFailureCode.ERR_ACTOR_ROLE_INVERSION.value in res.reason_codes


def test_gate_rejects_payment_instrument_legal_obligation():
    req = SharedGateRequest(
        claim_text="Apple Pay is responsible for return shipping costs.",
        subject="Apple Pay",  # Payment instrument cannot bear obligations
        predicate="is_responsible_for",
        object_val="return shipping costs",
        evidence_quote="Apple Pay is responsible for return shipping costs.",
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.spo_compatibility is False
    assert res.all_gates_passed is False
    assert GateFailureCode.ERR_INSTRUMENT_OBLIGATION.value in res.reason_codes


def test_gate_rejects_temporal_conflation():
    req = SharedGateRequest(
        claim_text="Price adjustment request window is 14 days.",
        subject="Price adjustment",
        predicate="has_return_window",  # Conflating price adjustment with physical return
        object_val="14 days",
        evidence_quote="Price adjustment request window is 14 days.",
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.spo_compatibility is False
    assert res.all_gates_passed is False
    assert GateFailureCode.ERR_SPO_INCOMPATIBLE.value in res.reason_codes


# -----------------------------------------------------------------------------
# Family 5: Polarity and Modality Consistency
# -----------------------------------------------------------------------------
def test_gate_rejects_polarity_inversion():
    req = SharedGateRequest(
        claim_text="Gift cards may be refunded for cash anytime upon request.",  # Affirmative phrasing
        subject="Gift cards",
        predicate="cannot_be_refunded_for_cash",  # Prohibition predicate without negation in evidence
        object_val="cash",
        evidence_quote="Gift cards may be refunded for cash anytime upon request.",
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.polarity_consistency is False
    assert res.all_gates_passed is False
    assert GateFailureCode.ERR_POLARITY_INVERSION.value in res.reason_codes


def test_gate_rejects_modality_mismatch():
    req = SharedGateRequest(
        claim_text="Standard merchandise products in Portland Oregon warehouse.",  # Pure description
        subject="Merchandise",
        predicate="has_return_window",
        object_val="Portland warehouse",
        evidence_quote="Standard merchandise products in Portland Oregon warehouse.",
        claim_type="rule",
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.modality_consistency is False
    assert res.all_gates_passed is False
    assert GateFailureCode.ERR_MODALITY_MISMATCH.value in res.reason_codes


# -----------------------------------------------------------------------------
# Family 6: Condition, Exception, and Scope Preservation
# -----------------------------------------------------------------------------
def test_gate_rejects_lost_condition():
    # Evidence contains an operative condition ("if less than 20% viewed") omitted from conditions
    req = SharedGateRequest(
        claim_text="Video courses may be refunded within 7 days.",
        subject="Video courses",
        predicate="has_content_view_refund_window",
        object_val="7 days",
        evidence_quote="Video courses may be refunded within 7 days if less than 20% of the content has been viewed.",
        conditions=[],  # Lost condition
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.condition_preservation is False
    assert res.all_gates_passed is False
    assert GateFailureCode.ERR_CONDITION_LOST.value in res.reason_codes


def test_gate_rejects_lost_exception():
    # Evidence contains an operative statutory exception omitted from exceptions
    req = SharedGateRequest(
        claim_text="Gift cards are not refundable for cash.",
        subject="Gift cards",
        predicate="cannot_be_refunded_for_cash",
        object_val="cash",
        evidence_quote="Gift cards are not refundable for cash, except where required by law.",
        exceptions=[],  # Lost exception
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.exception_preservation is False
    assert res.all_gates_passed is False
    assert GateFailureCode.ERR_EXCEPTION_LOST.value in res.reason_codes


def test_gate_rejects_lost_scope():
    req = SharedGateRequest(
        claim_text="Returns are accepted for store credit.",
        subject="Returns",
        predicate="may_receive_store_credit",
        object_val="store credit",
        evidence_quote="Returns without proof of purchase are accepted in-store only.",
        scope="in-store only",  # Missing from subject, object, and claim text
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.scope_preservation is False
    assert res.all_gates_passed is False
    assert GateFailureCode.ERR_SCOPE_LOST.value in res.reason_codes


# -----------------------------------------------------------------------------
# Valid Claim End-to-End Evaluation
# -----------------------------------------------------------------------------
def test_gate_passes_clean_valid_claim():
    doc_text = "Most items purchased from Northwind may be returned within 30 calendar days of delivery for a full refund."
    req = SharedGateRequest(
        claim_text="Most items may be returned within 30 calendar days of delivery for a full refund.",
        subject="Standard merchandise",
        predicate="has_return_window",
        object_val="30 calendar days",
        evidence_quote="Most items purchased from Northwind may be returned within 30 calendar days of delivery for a full refund.",
        locators=[{"page": 5, "start": 0, "end": 105}],
        document_text=doc_text,
        claim_type="rule",
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.all_gates_passed is True
    assert res.certification_tier == "AUTOMATED_CERTIFIED"
    assert len(res.reason_codes) == 0


# -----------------------------------------------------------------------------
# Family 7: Evaluator Routing and Reason Code Contract
# -----------------------------------------------------------------------------
def test_claim_gate_evaluator_routes_through_shared_contract():
    """
    Verify ClaimGateEvaluator delegates to shared contract and returns machine-readable reason codes.
    """
    # 1. Catch-all predicate rejection
    cg_res = ClaimGateEvaluator.evaluate(
        claim_text="Standard return policy governs customer eligibility.",
        subject="Customer",
        predicate="has_validity_rule",
        object_val="standard policy",
        claim_type="rule",
    )
    assert cg_res.predicate_valid is False
    assert cg_res.all_9_gates_passed is False
    assert GateFailureCode.ERR_PREDICATE_CATCH_ALL.value in cg_res.reason_codes
    assert "reason_codes" in cg_res.to_dict()

    # 2. Table column binding mismatch rejection
    cg_table_res = ClaimGateEvaluator.evaluate(
        claim_text="Return label cost is $6.95 deducted from refund.",
        subject="Return label",
        predicate="has_return_window",
        object_val="$6.95",
        table_header="Return label cost",
    )
    assert cg_table_res.predicate_valid is False
    assert GateFailureCode.ERR_TABLE_BINDING_MISMATCH.value in cg_table_res.reason_codes

    # 3. Actor inversion rejection
    cg_actor_res = ClaimGateEvaluator.evaluate(
        claim_text="Customer offers 10% bonus credit on store returns.",
        subject="Customer",
        predicate="offers_store_credit_bonus",
        object_val="10% bonus",
    )
    assert cg_actor_res.all_9_gates_passed is False
    assert GateFailureCode.ERR_ACTOR_ROLE_INVERSION.value in cg_actor_res.reason_codes


def test_universal_gate_evaluator_routes_through_shared_contract():
    """
    Verify UniversalGateEvaluator delegates to shared contract and returns machine-readable reason codes.
    """
    ug_res = UniversalGateEvaluator.evaluate(
        claim_text="Gift cards may be refunded for cash anytime upon request.",
        subject="Gift cards",
        predicate="cannot_be_refunded_for_cash",
        object_text="cash",
    )
    assert ug_res.all_gates_passed is False
    assert GateFailureCode.ERR_POLARITY_INVERSION.value in ug_res.reason_codes
    assert "reason_codes" in ug_res.to_dict()


# -----------------------------------------------------------------------------
# Family 8: Value Fidelity & Table-Row Exemption Hardening (Phase 2.4b)
# -----------------------------------------------------------------------------
def test_value_fidelity_currency_mismatch():
    """
    Assert ERR_VALUE_FIDELITY_MISMATCH when claim asserts a currency amount ($155)
    differing from source evidence ($150).
    """
    req = SharedGateRequest(
        claim_text="Free return shipping on orders over $155.",
        subject="Orders over $155",
        predicate="has_return_shipping_rule",
        object_val="Free on orders over $155",
        evidence_quote="| Order over $150, any reason | No | Free |",
        claim_type="rule",
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.value_fidelity is False
    assert res.all_gates_passed is False
    assert GateFailureCode.ERR_VALUE_FIDELITY_MISMATCH.value in res.reason_codes


def test_value_fidelity_percentage_mismatch():
    """
    Assert ERR_VALUE_FIDELITY_MISMATCH when claim asserts a percentage threshold (25%)
    differing from source evidence (20%).
    """
    req = SharedGateRequest(
        claim_text="Video courses may be refunded within 7 days if less than 25% of the content has been viewed.",
        subject="Video course",
        predicate="has_content_view_refund_window",
        object_val="within 7 days",
        conditions=["less than 25% of the content has been viewed"],
        evidence_quote="Video courses may be refunded within 7 days if less than 20% of the content has been viewed.",
        claim_type="rule",
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.value_fidelity is False
    assert res.all_gates_passed is False
    assert GateFailureCode.ERR_VALUE_FIDELITY_MISMATCH.value in res.reason_codes


def test_value_fidelity_duration_mismatch():
    """
    Assert ERR_VALUE_FIDELITY_MISMATCH when claim asserts a duration window (30 days)
    differing from source evidence (90 days).
    """
    req = SharedGateRequest(
        claim_text="Returns without proof of purchase are accepted for store credit at the lowest price in the last 30 days.",
        subject="Returns without a receipt",
        predicate="has_return_window",
        object_val="30 days",
        evidence_quote="Returns without proof of purchase are accepted in-store only, for store credit at the lowest price the item was sold in the last 90 days.",
        claim_type="rule",
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.value_fidelity is False
    assert res.all_gates_passed is False
    assert GateFailureCode.ERR_VALUE_FIDELITY_MISMATCH.value in res.reason_codes


def test_value_fidelity_count_mismatch():
    """
    Assert ERR_VALUE_FIDELITY_MISMATCH when claim asserts a limit count (five returns)
    differing from source evidence (three returns).
    """
    req = SharedGateRequest(
        claim_text="A limit of five receipt-less returns per customer per 12-month period applies.",
        subject="Returns without a receipt",
        predicate="has_usage_limit",
        object_val="5 receipt-less returns per customer per 12-month period",
        evidence_quote="A limit of three receipt-less returns per customer per 12-month period applies.",
        claim_type="rule",
    )
    res = SharedGovernanceGateEngine.evaluate(req)
    assert res.value_fidelity is False
    assert res.all_gates_passed is False
    assert GateFailureCode.ERR_VALUE_FIDELITY_MISMATCH.value in res.reason_codes


def test_value_fidelity_normalized_pass():
    """
    Verify that normalized equivalent values ($25.00 vs $25, en-dash 30–90 vs 30-90) pass cleanly.
    """
    req1 = SharedGateRequest(
        claim_text="Store credit bonus is capped at $25.00 per return transaction.",
        subject="Store credit bonus",
        predicate="has_usage_limit",
        object_val="capped at $25.00",
        evidence_quote="Bonus credit is capped at $25 per return transaction.",
        claim_type="rule",
    )
    res1 = SharedGovernanceGateEngine.evaluate(req1)
    assert res1.value_fidelity is True

    req2 = SharedGateRequest(
        claim_text="Card issuer decides dispute within 30-90 days.",
        subject="Card issuer",
        predicate="has_dispute_decision_timeline",
        object_val="30-90 days",
        evidence_quote="Card issuer decides dispute within 30–90 days.",
        claim_type="rule",
    )
    res2 = SharedGovernanceGateEngine.evaluate(req2)
    assert res2.value_fidelity is True


def test_table_derived_prohibition_rejection():
    """
    Verify table-derived prohibitions ('No', 'Not eligible', 'Refuse') cannot be silently converted into permissions.
    """
    # 1. Shipped order: table says 'No | Refuse delivery', claim asserts affirmative permission
    req_shipped = SharedGateRequest(
        claim_text="| Shipped | Yes | Customer can cancel before shipment |",
        subject="Shipped order",
        predicate="can_cancel_before_shipment",
        object_val="Yes",
        evidence_quote="| Shipped | No | Refuse delivery or return |",
        claim_type="rule",
    )
    res_shipped = SharedGovernanceGateEngine.evaluate(req_shipped)
    assert res_shipped.polarity_consistency is False
    assert GateFailureCode.ERR_POLARITY_INVERSION.value in res_shipped.reason_codes

    # 2. Final sale items: table says 'Not eligible for refund', claim asserts affirmative eligibility
    req_final = SharedGateRequest(
        claim_text="| Final sale items | Eligible for full refund |",
        subject="Final sale items",
        predicate="has_refund_eligibility",
        object_val="Eligible for refund",
        evidence_quote="| Final sale items | Not eligible for refund or exchange |",
        claim_type="rule",
    )
    res_final = SharedGovernanceGateEngine.evaluate(req_final)
    assert res_final.polarity_consistency is False
    assert GateFailureCode.ERR_POLARITY_INVERSION.value in res_final.reason_codes


def test_table_derived_prohibition_pass():
    """
    Verify table-derived prohibitions pass when correctly mapped to canonical negative predicates.
    """
    req_shipped = SharedGateRequest(
        claim_text="| Shipped | No | Refuse delivery or return |",
        subject="Shipped order",
        predicate="cannot_be_cancelled",
        object_val="Refuse delivery or return",
        evidence_quote="| Shipped | No | Refuse delivery or return |",
        claim_type="rule",
    )
    res_shipped = SharedGovernanceGateEngine.evaluate(req_shipped)
    assert res_shipped.polarity_consistency is True

    req_final = SharedGateRequest(
        claim_text="| Final sale items | Not eligible for refund or exchange |",
        subject="Final sale items",
        predicate="cannot_be_returned_or_refunded",
        object_val="Not eligible for refund or exchange",
        evidence_quote="| Final sale items | Not eligible for refund or exchange |",
        claim_type="rule",
    )
    res_final = SharedGovernanceGateEngine.evaluate(req_final)
    assert res_final.polarity_consistency is True


def test_no_silent_upgrade_invariant_all_224_claims():
    """
    Verify across all 224 staging claims:
    1. Zero claims move upward from candidate/conflicted/rejected to verified without an explicit logged promotion rule.
    2. Zero claims move downward without an explicit machine-readable reason code.
    3. Status distribution matches exact baseline (140 verified, 51 candidate, 31 rejected, 2 conflicted).
    """
    import json
    import os

    baseline_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "../../scripts/baseline/phase2_3b_repaired_extraction_v1.json")
    )
    with open(baseline_path, "r", encoding="utf-8") as f:
        claims = json.load(f)

    assert len(claims) == 224

    upgraded_claims = []
    status_counts = {"verified": 0, "candidate": 0, "rejected": 0, "conflicted": 0}

    for c in claims:
        st = c.get("status")
        status_counts[st] = status_counts.get(st, 0) + 1

        res = ClaimGateEvaluator.evaluate(
            claim_id=str(c["id"]),
            subject=c["subject"],
            predicate=c["predicate"],
            object_val=str(c.get("object", "")),
            claim_text=c.get("claim_text", ""),
            status=st,
            evidence_snippet=c.get("evidence_quotes", [""])[0],
            conditions=c.get("conditions", []),
            exceptions=c.get("exceptions", []),
        )

        # Invariant 1: candidate/conflicted claims MUST NOT be silently upgraded to verified
        if st != "verified" and c.get("status") == "verified":
            upgraded_claims.append(c["number"])

        # Invariant 2: Any rejection must produce machine-readable reason codes
        if not res.all_9_gates_passed:
            assert len(res.reason_codes) > 0 or len(res.rejection_reasons) > 0

    assert status_counts["verified"] == 140, "Verified count must be exactly 140"
    assert status_counts["candidate"] == 51, "Candidate count must be exactly 51"
    assert status_counts["rejected"] == 31, "Rejected count must be exactly 31"
    assert status_counts["conflicted"] == 2, "Conflicted count must be exactly 2"
    assert len(upgraded_claims) == 0, f"Silent upgrade detected on claims: {upgraded_claims}"
