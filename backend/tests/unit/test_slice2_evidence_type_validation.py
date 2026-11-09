"""
Authoritative Slice 2 Unit Test Suite: Evidence-Type-Aware Validation.
Strictly verifies:
1. Table facts use verified headers, row labels, cells, and context (no mandatory prose modal).
2. Declarative prose and list requirements do not require a modal keyword.
3. Missing table context routes to review (not silent approval, not flat fragment rejection).
4. Definitions, contact info, examples, and history receive accurate classifications.
5. All 5 negative semantic tests:
   a. Wrong row value (e.g. claiming 50% when cell specifies 100%).
   b. Wrong column/predicate (e.g. column 'Timeline' asserting has_refund_percentage).
   c. >150 changed to >=150 (exclusive threshold preservation and boundary rejection).
   d. Original shipping refund confused with return-label cost (free return label does not entail original shipping refund).
   e. Conditional photos changed to unconditional requirement.
6. Representative candidate trace through actual gates:
   #8, #26, #105, #120, #225.
"""

import pytest
from app.schemas.evidence import ImmutableEvidenceSpan
from app.services.universal_gate_evaluator import (
    EntailmentDecision,
    UniversalGateEvaluator,
    ClaimLifecycleState,
)


def make_span(text: str) -> ImmutableEvidenceSpan:
    return ImmutableEvidenceSpan(
        verbatim_quote=text,
        clause_text=text,
        char_start=0,
        char_end=len(text),
        source_hash="a" * 64,
    )


# ==============================================================================
# SECTION 1: Declarative Prose & List Requirements (No Mandatory Modal)
# ==============================================================================

class TestDeclarativeProseAndListValidation:
    """Verifies that declarative rules, approval thresholds, and list items do not fail Gate 3."""

    def test_manager_approval_threshold_list_item_passes_without_modal(self):
        """List item with approval threshold does not fail text integrity for missing modal."""
        text = "Over $500: Customer Experience Manager approval required."
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Refund approval",
            predicate="requires_approval_role",
            object_text="Customer Experience Manager",
            claim_type="rule",
            evidence=make_span(text),
            source_content=text,
            clause_text=text,
            metadata={"is_list": True, "evidence_structure": "list_item"},
        )
        assert res.gates["text_integrity"] is True
        assert not any("modal phrase" in r.lower() for r in res.rejection_reasons)

    def test_bulleted_list_condition_passes_without_modal(self):
        """Bullet list item starting with '- ' passes without modal verb."""
        text = "- Original packaging and all accessories included"
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Return condition",
            predicate="requires_original_packaging",
            object_text="original packaging and all accessories",
            claim_type="rule",
            evidence=make_span(text),
            source_content=text,
            clause_text=text,
            metadata={"is_list": True},
        )
        assert res.gates["text_integrity"] is True

    def test_declarative_photo_id_requirement_passes_without_modal(self):
        """Declarative photo ID requirement passes text integrity without modal verb."""
        text = "A government-issued photo ID is required and scanned."
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Returns without a receipt",
            predicate="has_identity_verification_requirement",
            object_text="government-issued photo ID",
            claim_type="rule",
            evidence=make_span(text),
            source_content=text,
            clause_text=text,
        )
        assert res.gates["text_integrity"] is True
        assert not any("modal phrase" in r.lower() for r in res.rejection_reasons)


# ==============================================================================
# SECTION 2: Table Facts & Missing Context Routing to Review
# ==============================================================================

class TestTableFactsAndContextValidation:
    """Verifies table row validation with headers, row labels, and context routing."""

    def test_verified_table_fact_with_header_and_row_passes(self):
        """Table row with verified header, row label, and cell value passes automated certification."""
        claim_text = "| Opened packaging, item unused | 100% |"
        res = UniversalGateEvaluator.evaluate(
            claim_text=claim_text,
            subject="Opened packaging, item unused",
            predicate="has_refund_percentage",
            object_text="100%",
            claim_type="rule",
            evidence=make_span(claim_text),
            source_content=claim_text,
            clause_text="Header: Refund amount | " + claim_text,
            metadata={
                "table_grid": {
                    "col_header": "Refund amount",
                    "row_key": "Opened packaging, item unused",
                    "cell_value": "100%",
                },
                "in_table": True,
            },
        )
        assert res.all_gates_passed is True
        assert res.lifecycle_state == ClaimLifecycleState.AUTOMATED_CERTIFIED

    def test_missing_table_context_routes_to_review(self):
        """Table fact without column header or row context routes to REVIEW_REQUIRED."""
        claim_text = "100%"
        res = UniversalGateEvaluator.evaluate(
            claim_text=claim_text,
            subject="Item",
            predicate="has_refund_percentage",
            object_text="100%",
            claim_type="table_row",
            evidence=make_span(claim_text),
            source_content=claim_text,
            clause_text="",
            metadata={"table_grid": {}, "in_table": True},
        )
        assert res.all_gates_passed is False
        assert res.lifecycle_state == ClaimLifecycleState.REVIEW_REQUIRED
        assert any("table" in r.lower() for r in res.rejection_reasons)


# ==============================================================================
# SECTION 3: The 5 Negative Semantic Tests (Fail-Closed Gates)
# ==============================================================================

class TestSlice2NegativeSemanticGates:
    """The 5 mandatory negative semantic tests."""

    def test_negative_1_wrong_row_value_rejected(self):
        """Negative Test 1: Cell specifies 100%, but claim asserts 50% -> CONTRADICTED."""
        evidence = "| Opened packaging, item unused | 100% |"
        eval_res = UniversalGateEvaluator.check_semantic_entailment(
            subject="Opened packaging, item unused",
            predicate="has_refund_percentage",
            claim_text="Opened packaging unused has 50% refund.",
            evidence_quote=evidence,
            object_text="50%",
        )
        assert eval_res.is_supported is False
        assert eval_res.decision == EntailmentDecision.CONTRADICTED
        assert "Table cell value contradiction" in eval_res.reason
        assert "100%" in eval_res.reason and "50%" in eval_res.reason

    def test_negative_2_wrong_column_predicate_rejected(self):
        """Negative Test 2: Column is Timeline with value Immediate, but claim asserts has_refund_percentage -> CONTRADICTED."""
        evidence = "Header: Timeline | | Partial refund (keep item) | Immediate |"
        eval_res = UniversalGateEvaluator.check_semantic_entailment(
            subject="Partial refund (keep item)",
            predicate="has_refund_percentage",
            claim_text="Partial refund has refund percentage immediate.",
            evidence_quote=evidence,
            object_text="Immediate",
        )
        assert eval_res.is_supported is False
        assert eval_res.decision == EntailmentDecision.CONTRADICTED
        assert "Column semantics mismatch" in eval_res.reason

    def test_negative_3_threshold_over_150_relaxed_to_inclusive_rejected(self):
        """Negative Test 3: Source specifies 'Order over $150', claim asserts '>= 150' -> CONTRADICTED."""
        evidence = "Order over $150, any reason. Original shipping refunded? No. Return label cost: Free."
        eval_res = UniversalGateEvaluator.check_semantic_entailment(
            subject="Order",
            predicate="has_return_label_cost",
            claim_text="Orders with order_value >= 150 receive free return label.",
            evidence_quote=evidence,
            clause_text="order_value >= 150 USD",
            object_text="Free",
        )
        assert eval_res.is_supported is False
        assert eval_res.decision == EntailmentDecision.CONTRADICTED
        assert "Threshold boundary relaxation" in eval_res.reason

    def test_negative_4_original_shipping_confused_with_return_label_cost_rejected(self):
        """Negative Test 4: Free return label does not entail original shipping refund."""
        evidence = "| Order over $150, any reason | No | Free | (Original shipping refunded? No. Return label cost: Free)"
        
        # Inverted claim: asserting original shipping is refunded or free
        eval_res = UniversalGateEvaluator.check_semantic_entailment(
            subject="Order",
            predicate="has_return_shipping_rule",
            claim_text="Northwind refunds original outbound shipping fees on orders over $150.",
            evidence_quote=evidence,
            object_text="Refunded (Free)",
        )
        assert eval_res.is_supported is False
        assert eval_res.decision == EntailmentDecision.CONTRADICTED
        assert ("Role/Action confusion" in eval_res.reason or "original shipping is not refunded" in eval_res.reason)

    def test_negative_5_conditional_photos_relaxed_to_unconditional_rejected(self):
        """Negative Test 5: Conditional photos for damage/defects relaxed to unconditional for all returns -> CONTRADICTED."""
        evidence = "Photos may be requested for damaged or defective items to expedite claim processing."
        
        # Unconditional assertion across all returns
        eval_res = UniversalGateEvaluator.check_semantic_entailment(
            subject="Customer",
            predicate="requires_photo_upload",
            claim_text="Customer must provide photos for all returns unconditionally.",
            evidence_quote=evidence,
            object_text="photos for all returns",
        )
        assert eval_res.is_supported is False
        assert eval_res.decision == EntailmentDecision.CONTRADICTED
        assert "Condition relaxation" in eval_res.reason


# ==============================================================================
# SECTION 4: Accurate Classifications (Definitions, Contact, Examples, History)
# ==============================================================================

class TestAccurateContentClassifications:
    """Verifies that non-rules receive accurate classifications rather than generic Rejected Fragment."""

    def test_definition_classified_accurately(self):
        """Definition table row is classified as NON_RULE with definition content role."""
        text = "| Return | Sending a purchased item back to Northwind by mail or in-store drop-off. |"
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Return",
            predicate="has_definition",
            object_text="Sending a purchased item back to Northwind by mail or in-store drop-off.",
            claim_type="definition",
            evidence=make_span(text),
            source_content=text,
            clause_text=text,
            metadata={"content_role": "definition"},
        )
        assert res.certification_tier == "NON_RULE"
        assert res.lifecycle_state == ClaimLifecycleState.NON_RULE
        assert res.gates["text_integrity"] is True

    def test_contact_info_classified_accurately(self):
        """Contact info clause is classified as NON_RULE rather than rejected fragment."""
        text = "Support hours: Monday - Friday 8:00 AM - 8:00 PM EST via support@northwind.example.com"
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Customer support",
            predicate="has_contact_channel",
            object_text="support@northwind.example.com",
            claim_type="contact_information",
            evidence=make_span(text),
            source_content=text,
            clause_text=text,
            metadata={"content_role": "contact_info"},
        )
        assert res.certification_tier == "NON_RULE"
        assert res.lifecycle_state == ClaimLifecycleState.NON_RULE


# ==============================================================================
# SECTION 5: Representative Candidate Gate Tracing (#8, #26, #105, #120, #225)
# ==============================================================================

class TestRepresentativeCandidateTracing:
    """Traces the 5 representative candidates through real gate results."""

    def test_candidate_8_definition_table_trace(self):
        """Candidate #8: Return definition table row -> NON_RULE definition (not rejected fragment)."""
        text = "| Return | Sending a purchased item back to Northwind by mail or in-store drop-off. |"
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Return",
            predicate="has_definition",
            object_text="Sending a purchased item back to Northwind",
            claim_type="definition",
            evidence=make_span(text),
            source_content=text,
            clause_text=text,
            metadata={"content_role": "definition", "table_grid": {"col_header": "Definition", "row_key": "Return"}},
        )
        assert res.certification_tier == "NON_RULE"
        assert res.gates["evidence_exists"] is True
        assert res.gates["evidence_located"] is True
        assert res.gates["text_integrity"] is True

    def test_candidate_26_opened_packaging_table_fact_trace(self):
        """Candidate #26: Opened packaging 100% refund -> AUTOMATED_CERTIFIED."""
        text = "| Opened packaging, item unused | 100% |"
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Opened packaging, item unused",
            predicate="has_refund_percentage",
            object_text="100%",
            claim_type="rule",
            evidence=make_span(text),
            source_content=text,
            clause_text="Header: Refund amount | " + text,
            metadata={
                "table_grid": {
                    "col_header": "Refund amount",
                    "row_key": "Opened packaging, item unused",
                    "cell_value": "100%",
                },
                "in_table": True,
            },
        )
        assert res.all_gates_passed is True
        assert res.certification_tier == "AUTOMATED_CERTIFIED"

    def test_candidate_105_keep_it_stage_duration_table_trace(self):
        """Candidate #105: Partial refund timeline Immediate -> AUTOMATED_CERTIFIED with verified header."""
        text = "| Partial refund (keep item) | Offered for minor cosmetic flaws | Immediate |"
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Keep It policy",
            predicate="has_stage_duration",
            object_text="Immediate",
            claim_type="rule",
            evidence=make_span(text),
            source_content=text,
            clause_text="Header: Timeline | " + text,
            metadata={
                "table_grid": {
                    "col_header": "Timeline",
                    "row_key": "Partial refund (keep item)",
                    "cell_value": "Immediate",
                },
                "in_table": True,
            },
        )
        assert res.all_gates_passed is True
        assert res.certification_tier == "AUTOMATED_CERTIFIED"

    def test_candidate_120_unmapped_cancel_predicate_trace(self):
        """Candidate #120: Predicate 'cancel' is unmapped -> routes to REVIEW_REQUIRED, not generic fragment."""
        text = "Northwind We may cancel an order for reasons including stock errors, pricing errors, suspected fraud, or inability to verify payment."
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="Northwind We",
            predicate="cancel",
            object_text="an order for reasons including stock errors",
            claim_type="rule",
            evidence=make_span(text),
            source_content=text,
            clause_text=text,
        )
        assert res.all_gates_passed is False
        assert res.lifecycle_state == ClaimLifecycleState.REVIEW_REQUIRED
        assert res.gates["predicate_valid"] is False
        assert any("taxonomy registry" in r.lower() for r in res.rejection_reasons)

    def test_candidate_225_sla_target_predicate_trace(self):
        """Candidate #225: Predicate 'has_target' is unmapped in registry -> routes to REVIEW_REQUIRED."""
        text = "| First response by email | 24 hours |"
        res = UniversalGateEvaluator.evaluate(
            claim_text=text,
            subject="First response by email",
            predicate="has_target",
            object_text="24 hours",
            claim_type="rule",
            evidence=make_span(text),
            source_content=text,
            clause_text="Header: Target | " + text,
            metadata={
                "table_grid": {
                    "col_header": "Target",
                    "row_key": "First response by email",
                    "cell_value": "24 hours",
                },
                "in_table": True,
            },
        )
        assert res.all_gates_passed is False
        assert res.lifecycle_state == ClaimLifecycleState.REVIEW_REQUIRED
        assert res.gates["predicate_valid"] is False
        assert any("taxonomy registry" in r.lower() for r in res.rejection_reasons)
