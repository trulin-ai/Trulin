"""
Phase 2.3: Predicate Registry Cleanup and Type Compatibility Test Suite.
Validates:
1. Catch-all predicate blocking (has_validity_rule, has_summary, generic catch-alls).
2. Typed predicate subtype presence and categorization in PredicateRegistry.
3. Subject-Predicate-Object semantic type compatibility matrix enforcement.
4. Table-header-to-predicate binding integrity and mismatch detection.
"""

import pytest

from app.extraction.predicate_registry import CanonicalPredicate, PredicateRegistry
from app.extraction.type_compatibility import EntityType, TypeCompatibilityMatrix
from app.services.claim_gate_evaluator import ClaimGateEvaluator


def test_catch_all_predicates_blocked_from_certification():
    """
    Catch-all predicates must be rejected by ClaimGateEvaluator for canonical certification.
    """
    catch_alls = [
        "has_validity_rule",
        "has_summary",
        "governs_contract_validity",
        "complies_with",
        "cancel",
        "scheduled",
        "appeal",
    ]
    for pred in catch_alls:
        res = ClaimGateEvaluator.evaluate(
            claim_text="Standard return policy governs customer eligibility.",
            subject="Customer",
            predicate=pred,
            object_val="standard policy",
            status="candidate",
            claim_type="rule",
        )
        assert res.predicate_valid is False, f"Catch-all predicate '{pred}' should have failed predicate_valid gate"
        assert res.all_9_gates_passed is False
        assert res.certification_tier != "AUTOMATED_CERTIFIED"


def test_typed_temporal_predicate_subtypes_in_registry():
    """
    Verify all required typed temporal and duration predicates exist in CanonicalPredicate.
    """
    required_typed_predicates = [
        "has_return_window",
        "has_posting_duration",
        "has_posting_sla_estimate",
        "has_cancellation_window",
        "has_price_adjustment_window",
        "has_reporting_window",
        "has_trial_refund_window",
        "has_content_view_refund_window",
        "has_refund_processing_duration",
    ]
    canonical_values = {p.value for p in CanonicalPredicate}
    for req in required_typed_predicates:
        assert req in canonical_values, f"Required typed predicate '{req}' missing from CanonicalPredicate"


def test_predicate_classification_taxonomy():
    """
    Verify classification of predicates into canonical, alias, catch_all, deprecated, and invalid.
    """
    assert PredicateRegistry.get_predicate_class("has_return_window") == "canonical"
    assert PredicateRegistry.get_predicate_class("has_posting_sla_estimate") == "canonical"
    assert PredicateRegistry.get_predicate_class("has_content_view_refund_window") == "canonical"
    assert PredicateRegistry.get_predicate_class("has_refund_processing_duration") == "canonical"
    assert PredicateRegistry.get_predicate_class("cannot_be_cancelled") == "canonical"
    assert PredicateRegistry.get_predicate_class("has_validity_rule") == "catch_all"
    assert PredicateRegistry.get_predicate_class("has_summary") == "catch_all"
    assert PredicateRegistry.get_predicate_class("cancel") == "deprecated"
    assert PredicateRegistry.get_predicate_class("scheduled") == "deprecated"
    assert PredicateRegistry.get_predicate_class("completely_bogus_xyz") == "invalid"


def test_subject_predicate_object_compatibility():
    """
    Verify TypeCompatibilityMatrix blocks semantically impossible combinations and accepts valid triples.
    """
    # 1. Customer cannot offer or grant store credit bonus (Customer receives, merchant offers)
    for pred in ("offers_store_credit_bonus", "grants_store_credit_bonus"):
        res_actor = TypeCompatibilityMatrix.evaluate_compatibility(
            subject="Customer",
            predicate=pred,
            object_text="5% bonus",
        )
        assert res_actor.is_compatible is False
        assert res_actor.blocked_rule in ("BLOCK-ACTOR-001", "BLOCK-CUSTOMER-ROLE")

    # 2. Price adjustment cannot be labeled as a return window
    res_price = TypeCompatibilityMatrix.evaluate_compatibility(
        subject="Price adjustment",
        predicate="has_return_window",
        object_text="14 days",
    )
    assert res_price.is_compatible is False
    assert res_price.blocked_rule == "BLOCK-TEMPORAL-001"

    # 3. Bank posting duration cannot be labeled as a return window
    res_bank = TypeCompatibilityMatrix.evaluate_compatibility(
        subject="Bank posting",
        predicate="has_return_window",
        object_text="3-5 business days",
    )
    assert res_bank.is_compatible is False
    assert res_bank.blocked_rule == "BLOCK-TEMPORAL-002"

    # 4. Payment instrument cannot bear behavioral legal obligations
    for inst in ("Apple Pay", "Credit card", "Debit card"):
        for pred in ("is_responsible_for", "must_comply"):
            res_inst = TypeCompatibilityMatrix.evaluate_compatibility(
                subject=inst,
                predicate=pred,
                object_text="shipping fees or legal terms",
            )
            assert res_inst.is_compatible is False
            assert res_inst.blocked_rule == "BLOCK-INSTRUMENT-ROLE"

    # 5. Valid combinations should pass cleanly
    res_valid1 = TypeCompatibilityMatrix.evaluate_compatibility(
        subject="Camping tents and sleeping bags",
        predicate="has_return_window",
        object_text="60 days",
    )
    assert res_valid1.is_compatible is True
    assert res_valid1.requires_review is False

    res_valid2 = TypeCompatibilityMatrix.evaluate_compatibility(
        subject="Refund speed",
        predicate="has_refund_processing_duration",
        object_text="3-5 business days after we receive and inspect the return",
    )
    assert res_valid2.is_compatible is True

    res_valid3 = TypeCompatibilityMatrix.evaluate_compatibility(
        subject="Video course",
        predicate="has_content_view_refund_window",
        object_text="within 7 days",
    )
    assert res_valid3.is_compatible is True


def test_table_header_to_predicate_binding():
    """
    Verify table header binding rules correctly map column headers to typed predicates
    and detect header-predicate mismatches.
    """
    binding_map = {
        "Return Window": "has_return_window",
        "Typical Duration": "has_posting_duration",
        "Refund speed": "has_refund_processing_duration",
        "Return label cost": "has_return_label_cost",
        "Original shipping refunded?": "has_return_shipping_rule",
        "Can it be cancelled?": "has_cancellation_eligibility",
        "Warranty period": "has_warranty_period",
        "Remedy": "has_warranty_remedy",
        "Required?": "must_provide_information",
    }
    for header, expected_pred in binding_map.items():
        bound_pred = PredicateRegistry.bind_table_header_to_predicate(header)
        assert bound_pred == expected_pred, f"Header '{header}' expected '{expected_pred}', got '{bound_pred}'"

    # Mismatch check: Column header 'Return label cost' paired with 'has_return_window' must be flagged
    assert PredicateRegistry.validate_table_header_predicate_match("Return label cost", "has_return_window") is False
    assert PredicateRegistry.validate_table_header_predicate_match("Return label cost", "has_return_label_cost") is True
    assert PredicateRegistry.validate_table_header_predicate_match("Refund speed", "has_refund_processing_duration") is True

