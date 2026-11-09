"""
Unit tests for Clause Entailment Evaluator (Sprint AF-10).
Validates directional NLI semantic entailment, deontic escalation detection,
condition omission detection, and integration with CanonicalClaimV3.gates.
"""

import pytest
from app.extraction.clause_entailment_evaluator import (
    ClauseEntailmentEvaluator,
    EntailmentLabel,
)
from app.schemas.canonical_claim_v3 import (
    ActionTaxonomy,
    CanonicalClaimV3,
    CounterpartyPayload,
    EvidenceV3,
    GatesV3,
    ModalityV3,
    ObjectPayload,
    PredicatePayload,
    ProvenanceV3,
    SubjectPayload,
)


def test_valid_obligation_entailment():
    premise = "Customer must pay all undisputed fees within thirty (30) days from invoice date."
    verdict = ClauseEntailmentEvaluator.evaluate(
        premise_clause=premise,
        subject="Customer",
        modality="MUST",
        predicate="must_pay_within_30_days",
        object_text="all undisputed fees within 30 days",
        conditions=["from invoice date"],
    )
    assert verdict.clause_entails_claim is True
    assert verdict.label == EntailmentLabel.ENTAILMENT
    assert verdict.confidence_score >= 0.85
    assert verdict.is_overstatement is False


def test_valid_permission_entailment():
    premise = "Customer may order Products for use by its Affiliates under this Agreement."
    verdict = ClauseEntailmentEvaluator.evaluate(
        premise_clause=premise,
        subject="Customer",
        modality="MAY",
        predicate="may_order_for_affiliate",
        object_text="Products for use by its Affiliates",
    )
    assert verdict.clause_entails_claim is True
    assert verdict.label == EntailmentLabel.ENTAILMENT
    assert verdict.deontic_alignment == "MATCH"


def test_deontic_escalation_detection():
    # Premise says Customer 'may', but claim asserts Customer 'MUST'
    premise = "Customer may terminate this Agreement without cause upon 60 days written notice."
    verdict = ClauseEntailmentEvaluator.evaluate(
        premise_clause=premise,
        subject="Customer",
        modality="MUST",
        predicate="may_terminate_without_cause",
        object_text="this Agreement upon 60 days notice",
    )
    assert verdict.clause_entails_claim is False
    assert verdict.label == EntailmentLabel.NEUTRAL
    assert verdict.is_overstatement is True
    assert verdict.deontic_alignment == "ESCALATION"
    assert "discretionary permission" in verdict.overstatement_reason


def test_polarity_contradiction_detection():
    # Premise prohibits reverse engineering, claim asserts right/duty
    premise = "Customer must not reverse engineer, decompile, or disassemble any Products or Deliverables."
    verdict = ClauseEntailmentEvaluator.evaluate(
        premise_clause=premise,
        subject="Customer",
        modality="MAY",
        predicate="prohibited_from_reverse_engineering",
        object_text="reverse engineer Products",
    )
    assert verdict.clause_entails_claim is False
    assert verdict.label == EntailmentLabel.CONTRADICTION
    assert "prohibits action" in verdict.overstatement_reason


def test_restrictive_condition_dropping():
    # Premise has strict condition 'solely in connection with', but claim has empty conditions
    premise = "Customer may transfer perpetual licenses solely in connection with the transfer of hardware to which they were assigned."
    verdict = ClauseEntailmentEvaluator.evaluate(
        premise_clause=premise,
        subject="Customer",
        modality="MAY",
        predicate="may_transfer_perpetual_license",
        object_text="perpetual licenses",
        conditions=[],  # Dropped condition!
    )
    assert verdict.clause_entails_claim is False
    assert verdict.label == EntailmentLabel.NEUTRAL
    assert verdict.is_overstatement is True
    assert "condition dropped" in verdict.overstatement_reason.lower()


def test_actor_inversion_detection():
    # Premise binds Customer to pay, claim asserts Microsoft must pay
    premise = "Customer will pay Microsoft all invoiced amounts within 30 days."
    verdict = ClauseEntailmentEvaluator.evaluate(
        premise_clause=premise,
        subject="Microsoft",
        modality="MUST",
        predicate="must_pay_within_30_days",
        object_text="all invoiced amounts to Customer",
    )
    assert verdict.clause_entails_claim is False
    assert verdict.label == EntailmentLabel.CONTRADICTION
    assert "Actor inversion" in verdict.overstatement_reason


def test_evaluate_claim_v3_wires_gate():
    claim = CanonicalClaimV3(
        claim_id="DOC057:v3:test01",
        document_id="DOC-057",
        clause_id="sec-1-a",
        document_type="contract",
        subject=SubjectPayload(raw_text="Microsoft", canonical_entity="Microsoft", entity_type="PARTY"),
        counterparty=CounterpartyPayload(raw_text="Customer", canonical_entity="Customer", relationship="BENEFICIARY"),
        modality=ModalityV3.MAY,
        predicate=PredicatePayload(raw_text="grants", normalized_action="grants_product_license", action_taxonomy=ActionTaxonomy.LICENSE.value),
        object=ObjectPayload(raw_text="license to use Products", normalized_object="license to use Products"),
        evidence=EvidenceV3(
            verbatim_quote="Microsoft grants Customer a nonexclusive and limited license to use the Products ordered.",
            clause_text="Microsoft grants Customer a nonexclusive and limited license to use the Products ordered as provided in this Agreement.",
            page=1,
            char_start=100,
            char_end=200,
        ),
        provenance=ProvenanceV3(),
        gates=GatesV3(span_exists=True, subject_valid=True, predicate_valid=True),
    )

    verdict = ClauseEntailmentEvaluator.evaluate_claim_v3(claim)
    assert verdict.clause_entails_claim is True
    assert claim.gates.clause_entails_claim is True
    assert claim.evidence.entailment_score >= 0.85


def test_polarity_inversion_cancellation_not_charged():
    """Candidate #38 protection: 'will not be charged' cannot entail affirmative fee/charge duty."""
    verdict = ClauseEntailmentEvaluator.evaluate(
        premise_clause="If you cancel before the trial ends, you will not be charged any subscription fee.",
        subject="Customer",
        modality="MAY",
        predicate="has_cancellation_fee_policy",
        object_text="be charged subscription fee",
    )
    assert verdict.clause_entails_claim is False
    assert verdict.label == EntailmentLabel.CONTRADICTION
    assert verdict.deontic_alignment == "POLARITY_INVERSION"


def test_polarity_inversion_final_sale_cannot_return():
    """Candidate #4 protection: 'cannot be returned' cannot entail affirmative refund eligibility."""
    verdict = ClauseEntailmentEvaluator.evaluate(
        premise_clause="Items marked 'Final Sale' at the time of purchase cannot be returned or exchanged.",
        subject="Customer",
        modality="MAY",
        predicate="has_refund_eligibility",
        object_text="Final Sale items for refund",
    )
    assert verdict.clause_entails_claim is False
    assert verdict.label == EntailmentLabel.CONTRADICTION
    assert verdict.deontic_alignment == "POLARITY_INVERSION"

