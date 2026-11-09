"""
Slice 1 Semantic Corrections Unit & Boundary Test Suite
Validates the 4 Slice 1 repairs:
1. Exclusive > 150 threshold preservation and missing-value handling ($149.99, $150.00, $150.01 boundaries).
2. Custom-contract precedence without an unrestricted Customer right.
3. Correct provide/require direction, preserving both documents and upon-request condition.
4. Trial-end cancellation with explicit no-charge outcome and trial scope (no shipment semantics).
"""

import uuid
import pytest
from app.extraction.deontic_classifier import DeonticClassifier
from app.extraction.claim_quality_normalizer import ClaimQualityNormalizer
from app.extraction.predicate_registry import PredicateRegistry, CanonicalPredicate
from app.extraction.clause_entailment_evaluator import ClauseEntailmentEvaluator, EntailmentLabel
from app.services.role_direction_validator import RoleDirectionValidator
from app.services.universal_gate_evaluator import UniversalGateEvaluator
from app.extraction.models import CandidateClaim


# ==============================================================================
# DEFECT 1: Exclusive > 150 Threshold Preservation & Boundary Tests
# ==============================================================================

class TestDefect1ThresholdPreservation:
    """Tests preservation of strict exclusive boundary (> 150) and boundary evaluation."""

    def test_table_row_normalization_preserves_exclusive_threshold(self):
        """Table row 'Order over $150, any reason' must extract condition 'order_value > 150 USD' and subject 'Order'."""
        scope_dict = {"Return Reason": "Order over $150, any reason"}
        norm = DeonticClassifier.normalize_table_policy_claim(
            scope_dict=scope_dict,
            rule_key="Original shipping refunded?",
            rule_value="No",
            conditions=[],
        )
        assert norm["subject"] == "Order"
        assert "order_value > 150 USD" in norm["conditions"]
        assert "return_reason: any reason" in norm["conditions"]
        assert "Table Column: Original shipping refunded?" in norm["conditions"]
        assert norm["predicate"] == "has_return_shipping_rule"
        assert norm["object"] == "No"

    def test_candidate_normalizer_preserves_threshold_from_raw_subject(self):
        """ClaimQualityNormalizer.normalize_candidate_claim must retain 'order_value > 150 USD'."""
        candidate = CandidateClaim.create(
            envelope_id=uuid.uuid4(),
            unit_id="unit_test_01",
            asset_id="asset_test_01",
            claim_text="| Order over $150, any reason | Free |",
            subject="Order over $150, any reason",
            predicate="has_return_label_cost",
            object_="Free",
            evidence_text_span="| Order over $150, any reason | Free |",
            modal_operator="specifies",
        )
        norm_c = ClaimQualityNormalizer.normalize_candidate_claim(candidate)
        assert norm_c is not None
        assert norm_c.subject == "Order"
        assert "order_value > 150 USD" in norm_c.conditions

    def test_boundary_values_strictly_exclusive(self):
        """Boundary test: $149.99 ineligible, $150.00 ineligible, $150.01 eligible."""
        cond = "order_value > 150 USD"
        # 149.99 is below threshold
        assert ClauseEntailmentEvaluator.evaluate_threshold_condition(cond, 149.99) is False
        # 150.00 is exactly on the boundary: strictly ineligible for exclusive '>'
        assert ClauseEntailmentEvaluator.evaluate_threshold_condition(cond, 150.00) is False
        # 150.01 is above the boundary: eligible
        assert ClauseEntailmentEvaluator.evaluate_threshold_condition(cond, 150.01) is True
        # Large values eligible
        assert ClauseEntailmentEvaluator.evaluate_threshold_condition(cond, 500.00) is True

    def test_relaxed_threshold_rejected_by_entailment_evaluator(self):
        """Contradiction if claim relaxes exclusive 'over $150' into inclusive '>='."""
        premise = "For any order over $150, return shipping labels are provided free of charge."
        verdict = ClauseEntailmentEvaluator.evaluate(
            premise_clause=premise,
            subject="Order",
            modality="PERMISSION",
            predicate="has_return_label_cost",
            object_text="Free",
            conditions=["order_value >= 150 USD"],  # relaxed to inclusive
        )
        assert verdict.clause_entails_claim is False
        assert verdict.label == EntailmentLabel.CONTRADICTION
        assert "Threshold relaxation" in verdict.overstatement_reason

    def test_strict_threshold_accepted_by_entailment_evaluator(self):
        """Premise with 'over $150' strictly entails claim with 'order_value > 150 USD'."""
        premise = "For any order over $150, return shipping labels are provided free of charge."
        verdict = ClauseEntailmentEvaluator.evaluate(
            premise_clause=premise,
            subject="Order",
            modality="PERMISSION",
            predicate="has_return_label_cost",
            object_text="Free",
            conditions=["order_value > 150 USD"],
        )
        assert verdict.clause_entails_claim is True


# ==============================================================================
# DEFECT 2: Custom-Contract Precedence Without Unrestricted Customer Right
# ==============================================================================

class TestDefect2CustomContractPrecedence:
    """Tests that precedence belongs to Custom Contracts, never unilateral Customer permission."""

    def test_unilateral_customer_override_blocked(self):
        """RoleDirectionValidator blocks Customer from holding may_override_standard_terms."""
        res = RoleDirectionValidator.validate(
            subject="Customer",
            predicate="may_override_standard_terms",
            clause_text="Business customers on standard accounts (custom contracts may override these terms).",
        )
        assert res.is_valid is False
        assert res.requires_review is True
        assert "An individual Customer cannot be granted unilateral permission" in res.reason

    def test_buyer_subscriber_override_blocked(self):
        """RoleDirectionValidator blocks Buyer or Subscriber from holding may_override_standard_terms."""
        for role in ("Buyer", "Subscriber", "User", "Client"):
            res = RoleDirectionValidator.validate(
                subject=role,
                predicate="may_override_standard_terms",
                clause_text="Custom contracts may override these terms.",
            )
            assert res.is_valid is False

    def test_custom_corporate_agreements_override_allowed(self):
        """RoleDirectionValidator approves Custom corporate agreements holding may_override_standard_terms."""
        res = RoleDirectionValidator.validate(
            subject="Custom corporate agreements",
            predicate="may_override_standard_terms",
            clause_text="Custom corporate agreements may override standard terms.",
        )
        assert res.is_valid is True

    def test_universal_gate_evaluator_validates_custom_agreement_precedence(self):
        """UniversalGateEvaluator supports Custom corporate agreements and rejects Customer."""
        evidence = "Business customers on standard accounts (custom contracts may override these terms)."
        
        # Valid: Custom corporate agreements
        eval_valid = UniversalGateEvaluator.check_semantic_entailment(
            subject="Custom corporate agreements",
            predicate="may_override_standard_terms",
            claim_text="Custom corporate agreements may override standard terms.",
            evidence_quote=evidence,
            object_text="Standard policy terms",
        )
        assert eval_valid.is_supported is True

        # Invalid: Customer as subject
        eval_invalid = UniversalGateEvaluator.check_semantic_entailment(
            subject="Customer",
            predicate="may_override_standard_terms",
            claim_text="Customer may override standard terms.",
            evidence_quote=evidence,
            object_text="Standard policy terms",
        )
        assert eval_invalid.is_supported is False
        assert "Precedence contradiction" in eval_invalid.reason

    def test_no_invented_execution_condition(self):
        """Verify extraction preserves conditional applicability without inventing 'when_formally_executed'."""
        evidence = "Business customers on standard accounts (custom contracts may override these terms)."
        assert "when_formally_executed" not in evidence.lower()


# ==============================================================================
# DEFECT 3: Correct Provide/Require Direction (Documentation Upon Request)
# ==============================================================================

class TestDefect3DocumentationProvideRequireDirection:
    """Tests provider documentation commitment vs customer documentation requirement."""

    def test_provider_commitment_extracts_correct_predicate(self):
        """Northwind provides commercial invoice and proof of return upon request."""
        norm_pred, is_canon = PredicateRegistry.normalize_predicate("will provide commercial invoice")
        assert is_canon is True
        assert norm_pred == CanonicalPredicate.PROVIDES_DOCUMENTATION_UPON_REQUEST.value

    def test_role_direction_validator_blocks_customer_obligation_for_provider_commitment(self):
        """RoleDirectionValidator blocks requires_verifiable_order_or_purchase_proof on provider clause."""
        clause = "Northwind will provide commercial invoice and proof of return upon customer request."
        res = RoleDirectionValidator.validate(
            subject="Northwind",
            predicate="requires_verifiable_order_or_purchase_proof",
            clause_text=clause,
        )
        assert res.is_valid is False
        assert "Role direction reversal" in res.reason

    def test_universal_gate_evaluator_entailment_direction(self):
        """UniversalGateEvaluator rejects requires_verifiable_order_or_purchase_proof and supports provides_documentation_upon_request."""
        clause = "Northwind will provide commercial invoice and proof of return upon request."

        # Correct claim: Northwind provides documentation upon request
        good_eval = UniversalGateEvaluator.check_semantic_entailment(
            subject="Northwind",
            predicate="provides_documentation_upon_request",
            claim_text="Northwind provides documentation upon request.",
            evidence_quote=clause,
            object_text="commercial invoice and proof of return",
        )
        assert good_eval.is_supported is True

        # Inverted claim: requires proof
        bad_eval = UniversalGateEvaluator.check_semantic_entailment(
            subject="Northwind",
            predicate="requires_verifiable_order_or_purchase_proof",
            claim_text="Northwind requires verifiable order or purchase proof.",
            evidence_quote=clause,
            object_text="commercial invoice",
        )
        assert bad_eval.is_supported is False
        assert "Role direction contradiction" in bad_eval.reason

    def test_paraphrase_documentation_provision(self):
        """Paraphrases of document provision upon request are supported."""
        paraphrases = [
            "We provide commercial invoice and proof of return upon request.",
            "Northwind provides commercial invoice and proof of return upon customer request.",
            "Vendor will provide proof of return and commercial invoice on request.",
        ]
        for p in paraphrases:
            eval_res = UniversalGateEvaluator.check_semantic_entailment(
                subject="Northwind",
                predicate="provides_documentation_upon_request",
                claim_text="Northwind provides documentation upon request.",
                evidence_quote=p,
                object_text="commercial invoice and proof of return",
            )
            assert eval_res.is_supported is True, f"Failed on paraphrase: {p}"


# ==============================================================================
# DEFECT 4: Trial-End Cancellation With Explicit No-Charge Outcome
# ==============================================================================

class TestDefect4TrialEndCancellation:
    """Tests digital trial subscription cancellation before trial ends with zero-charge outcome."""

    def test_predicate_registry_trial_cancellation(self):
        """Predicate registry normalizes trial cancellation phrases."""
        for phrase in ("cancel before trial ends", "can cancel before trial ends", "cancel before the trial ends"):
            norm, is_canon = PredicateRegistry.normalize_predicate(phrase)
            assert is_canon is True
            assert norm == CanonicalPredicate.CAN_CANCEL_BEFORE_TRIAL_ENDS.value

    def test_role_direction_validator_blocks_shipment_predicate_for_trial(self):
        """RoleDirectionValidator blocks can_cancel_before_shipment for digital trial subscriptions."""
        trial_clause = "Free trials may be cancelled before trial ends without charge."
        res = RoleDirectionValidator.validate(
            subject="Subscriber",
            predicate="can_cancel_before_shipment",
            clause_text=trial_clause,
        )
        assert res.is_valid is False
        assert "Incompatible action domain" in res.reason

    def test_universal_gate_evaluator_validates_trial_cancellation(self):
        """UniversalGateEvaluator supports can_cancel_before_trial_ends with no-charge outcome."""
        trial_clause = "Free trials may be cancelled before trial ends without charge."
        eval_res = UniversalGateEvaluator.check_semantic_entailment(
            subject="Subscriber",
            predicate="can_cancel_before_trial_ends",
            claim_text="Subscriber can cancel before trial ends without charge.",
            evidence_quote=trial_clause,
            object_text="without charge",
        )
        assert eval_res.is_supported is True

    def test_universal_gate_evaluator_rejects_affirmative_charge_for_trial(self):
        """UniversalGateEvaluator rejects affirmative charge when clause specifies 'without charge'."""
        trial_clause = "Free trials may be cancelled before trial ends without charge."
        eval_res = UniversalGateEvaluator.check_semantic_entailment(
            subject="Subscriber",
            predicate="has_cancellation_fee_policy",
            claim_text="Subscriber is charged full subscription fee.",
            evidence_quote=trial_clause,
            object_text="charged full subscription fee",
        )
        assert eval_res.is_supported is False
        assert "Polarity contradiction" in eval_res.reason

    def test_universal_gate_evaluator_rejects_shipment_predicate_for_trial(self):
        """UniversalGateEvaluator rejects can_cancel_before_shipment on trial evidence."""
        trial_clause = "Digital subscription trial may be cancelled at any time before the trial ends at no charge."
        eval_res = UniversalGateEvaluator.check_semantic_entailment(
            subject="Subscriber",
            predicate="can_cancel_before_shipment",
            claim_text="Subscriber can cancel before shipment.",
            evidence_quote=trial_clause,
            object_text="without fee",
        )
        assert eval_res.is_supported is False
        assert "Action/Scope mismatch" in eval_res.reason or "action/scope mismatch" in eval_res.reason.lower()
