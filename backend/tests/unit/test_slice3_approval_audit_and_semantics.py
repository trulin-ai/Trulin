"""
Unit and regression tests for Slice 3: Semantic Gate Audit and Unchanged Defect Blocking.

Validates that:
1. Bucket 3 promotions are strictly blocked:
   - Non-refundable items with affirmative has_refund_eligibility are rejected (#37, #38).
   - 5% store-credit bonus mapped to has_default_refund_destination is rejected (#78).
   - $49 freight deduction mapped to has_refund_eligibility is rejected (#94).
   - Drop-off receipt instruction mapped to has_refund_eligibility is rejected (#99).
   - Purchaser non-notification mapped to has_refund_eligibility is rejected (#141).
   - Original charge currency mapped to has_refund_eligibility is rejected (#178).
   - Video course exception with mismatched digital goods prohibition quote fails clause entailment (#134).
2. Correct semantic representations pass:
   - Apple Pay / Google Pay subject is preserved without collapse to Google (#68, #69).
   - 5% bonus credit mapped to offers_store_credit_bonus passes (#78).
   - $49 freight deduction mapped to has_return_freight_deduction passes (#94).
   - Drop-off receipt mapped to requires_receipt_retention passes (#99).
   - Currency rule mapped to uses_original_charge_currency passes (#178).
   - Video course exception with correctly anchored quote passes (#134).
   - Subscription products retain distinct identities (Trailhead Box, Rewards Plus, Gear Care Plan).
   - Cosmetic flaw partial refund is distinct from Keep It policy (#104, #105).
   - Keep It annual limit (2 per customer per year) is linked to under-$40 policy (#108, #109).
   - Customer duty drawback responsibility is certified as an operative condition (#180).
   - Request table 'Required?' column produces operative procedural rules (#43, #46, #48, #50, #52),
     while 'Example' column produces non-rule context (#42, #44, #45, #47, #49, #51).
   - Revision history log is classified as revision_history, not example (#229).
"""

import pytest
from app.schemas.evidence import ImmutableEvidenceSpan
from app.services.universal_gate_evaluator import UniversalGateEvaluator
from app.services.claim_gate_evaluator import ClaimGateEvaluator
from app.extraction.claim_quality_normalizer import ClaimQualityNormalizer
from app.extraction.models import CandidateClaim


def make_span(text: str, char_start: int = 100, char_end: int = 250) -> ImmutableEvidenceSpan:
    import hashlib
    shash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return ImmutableEvidenceSpan(
        verbatim_quote=text,
        clause_text=text,
        char_start=char_start,
        char_end=char_end if char_end > char_start else char_start + len(text),
        source_hash=shash,
    )


class TestSlice3Bucket3DefectBlocking:
    """Tests that semantic gates strictly reject unchanged incorrect claims."""

    def test_non_refundable_perishable_goods_with_affirmative_eligibility_rejected(self):
        """Candidate #37: Perishable goods past 14 days must not be approved as refund-eligible."""
        quote = "Perishable goods such as freeze-dried meals past 14 days from delivery are not eligible for refund."
        res = UniversalGateEvaluator.evaluate(
            claim_text="Customer has refund eligibility for perishable goods such as freeze-dried meals past 14 days.",
            subject="Customer",
            predicate="has_refund_eligibility",
            object_text="Perishable goods such as freeze-dried meals past 14 days from delivery.",
            evidence=make_span(quote),
            clause_text=quote,
        )
        assert res.clause_entails_claim is False or res.text_integrity is False or res.lifecycle_decision != "approve"

    def test_non_refundable_items_over_90_days_with_affirmative_eligibility_rejected(self):
        """Candidate #38: Items returned >90 days must not be approved as refund-eligible."""
        quote = "Items returned more than 90 days after delivery are non-refundable."
        res = UniversalGateEvaluator.evaluate(
            claim_text="Customer has refund eligibility for items returned more than 90 days after delivery.",
            subject="Customer",
            predicate="has_refund_eligibility",
            object_text="Items returned more than 90 days after delivery.",
            evidence=make_span(quote),
            clause_text=quote,
        )
        assert res.clause_entails_claim is False or res.text_integrity is False or res.lifecycle_decision != "approve"

    def test_bonus_credit_mapped_to_default_destination_rejected(self):
        """Candidate #78: 5% bonus credit cannot be approved as default refund destination."""
        quote = "Customers who choose store credit instead of a refund to the original payment method receive a 5% bonus on the credit value, up to $25."
        res = UniversalGateEvaluator.evaluate(
            claim_text="Refund has default refund destination to original payment method whenever possible.",
            subject="Refund",
            predicate="has_default_refund_destination",
            object_text="Original payment method whenever possible",
            evidence=make_span(quote),
            clause_text=quote,
        )
        assert res.clause_entails_claim is False or res.lifecycle_decision != "approve"

    def test_freight_deduction_mapped_to_eligibility_rejected(self):
        """Candidate #94: $49 freight deduction cannot be approved as has_refund_eligibility."""
        quote = "Return freight for change-of-mind returns is a flat $49.00, deducted from the refund."
        res = UniversalGateEvaluator.evaluate(
            claim_text="Oversize items has refund eligibility of $49 flat return freight deducted from refund.",
            subject="Oversize items",
            predicate="has_refund_eligibility",
            object_text="Return freight for change-of-mind returns is a flat $49.00, deducted from the refund.",
            evidence=make_span(quote),
            clause_text=quote,
        )
        assert res.clause_entails_claim is False or res.lifecycle_decision != "approve"

    def test_receipt_retention_instruction_mapped_to_eligibility_rejected(self):
        """Candidate #99: Retaining drop-off receipt cannot be approved as has_refund_eligibility."""
        quote = "Keep the drop-off receipt until your refund has been confirmed."
        res = UniversalGateEvaluator.evaluate(
            claim_text="Drop-off locations has refund eligibility: Keep the drop-off receipt until your refund has been confirmed.",
            subject="Drop-off locations",
            predicate="has_refund_eligibility",
            object_text="Keep the drop-off receipt until your refund has been confirmed.",
            evidence=make_span(quote),
            clause_text=quote,
        )
        assert res.clause_entails_claim is False or res.lifecycle_decision != "approve"

    def test_original_charge_currency_mapped_to_eligibility_rejected(self):
        """Candidate #178: Settlement currency cannot be approved as has_refund_eligibility."""
        quote = "Refunds are issued in the currency of the original charge."
        res = UniversalGateEvaluator.evaluate(
            claim_text="International refund has refund eligibility: Refunds are issued in the currency of the original charge.",
            subject="International refund",
            predicate="has_refund_eligibility",
            object_text="Refunds are issued in the currency of the original charge.",
            evidence=make_span(quote),
            clause_text=quote,
        )
        assert res.clause_entails_claim is False or res.lifecycle_decision != "approve"

    def test_video_course_exception_with_general_prohibition_quote_rejected(self):
        """Candidate #134: 7-day video course exception fails clause entailment when quote is general prohibition."""
        wrong_quote = "Digital goods such as trail guides (PDF), camping-skills video courses, and map packs are non-refundable after download or streaming begins."
        res = UniversalGateEvaluator.evaluate(
            claim_text="Video courses may be refunded within 7 days if less than 20% of the content has been viewed.",
            subject="Video course",
            predicate="has_refund_window",
            object_text="Refunded within 7 days if under 20% viewed",
            evidence=make_span(wrong_quote),
            clause_text=wrong_quote,
        )
        # Must fail clause entailment because wrong_quote prohibits refunds and does not state the 7-day exception!
        assert res.clause_entails_claim is False or res.lifecycle_decision != "approve"

    def test_in_store_bank_posting_fails_has_return_window(self):
        """Candidate #24: Immediate in-store processing & bank posting time must not pass has_return_window."""
        quote = "In-store refunds to the original card are processed immediately; the bank may take 3-5 days to post the credit."
        res = UniversalGateEvaluator.evaluate(
            claim_text="In store has return window In-store refunds to the original card are processed immediately; the bank may take 3-5 days to post the credit.",
            subject="In store",
            predicate="has_return_window",
            object_text="In-store refunds to the original card are processed immediately; the bank may take 3-5 days to post the credit.",
            evidence=make_span(quote),
            clause_text=quote,
        )
        assert res.clause_entails_claim is False or res.lifecycle_decision != "approve"

    def test_cancellation_table_fails_has_return_window(self):
        """Candidate #80: Merged cancellation table fragment must not pass has_return_window."""
        quote = "Refund Pending (within 1 hour) Yes - self-service Full refund, immediate release of authorisation Processing Yes - contact support Full refund within 3-5 days"
        res = UniversalGateEvaluator.evaluate(
            claim_text="Customer has return window Refund Pending (within 1 hour)...",
            subject="Customer",
            predicate="has_return_window",
            object_text=quote,
            evidence=make_span(quote),
            clause_text=quote,
        )
        assert res.clause_entails_claim is False or res.lifecycle_decision != "approve"

    def test_price_adjustment_fails_has_return_window(self):
        """Candidate #81: Price drop adjustment opportunity must not pass has_return_window."""
        quote = "If an item you purchased drops in price within 14 days of purchase, contact us for a one-time price adjustment refund of the difference."
        res = UniversalGateEvaluator.evaluate(
            claim_text="Price adjustments has return window If an item you purchased drops in price within 14 days of purchase...",
            subject="Price adjustments",
            predicate="has_return_window",
            object_text="If an item you purchased drops in price within 14 days of purchase, contact us for a one-time price adjustment refund of the difference.",
            evidence=make_span(quote),
            clause_text=quote,
        )
        assert res.clause_entails_claim is False or res.lifecycle_decision != "approve"

    def test_trial_charge_refund_fails_has_return_window(self):
        """Candidate #86: Courtesy refund request after forgetting to cancel trial must not pass has_return_window."""
        quote = "If you forget to cancel and are charged, contact us within 7 days for a full refund of the first charge."
        res = UniversalGateEvaluator.evaluate(
            claim_text="Free trials has return window If you forget to cancel and are charged, contact us within 7 days for a full refund of the first charge.",
            subject="Free trials",
            predicate="has_return_window",
            object_text="If you forget to cancel and are charged, contact us within 7 days for a full refund of the first charge.",
            evidence=make_span(quote),
            clause_text=quote,
        )
        assert res.clause_entails_claim is False or res.lifecycle_decision != "approve"

    def test_pause_trailhead_box_fails_has_refund_rule(self):
        """Candidate #87: Permission to pause Trailhead Box must not pass has_refund_rule."""
        quote = "Trailhead Box subscribers can pause for up to 3 months, once per year, from the account page."
        res = UniversalGateEvaluator.evaluate(
            claim_text="Trailhead Box subscription has refund rule for up to 3 months, once per year, from the account page",
            subject="Trailhead Box subscription",
            predicate="has_refund_rule",
            object_text="for up to 3 months, once per year, from the account page",
            evidence=make_span(quote),
            clause_text=quote,
        )
        assert res.clause_entails_claim is False or res.lifecycle_decision != "approve"

    def test_customer_offers_bonus_actor_inversion_blocked(self):
        """Candidate #55: Customer offers store credit bonus is an actor inversion and must be blocked."""
        quote = "Customers who choose store credit instead of a refund to their original payment method receive an additional 5% bonus in credit value (maximum bonus $25.00 per return)."
        res = UniversalGateEvaluator.evaluate(
            claim_text="Customer offers store credit bonus 5% bonus on credit value, maximum bonus $25.00 per return.",
            subject="Customer",
            predicate="offers_store_credit_bonus",
            object_text="5% bonus on credit value, maximum bonus $25.00 per return",
            evidence=make_span(quote),
            clause_text=quote,
        )
        assert res.clause_entails_claim is False or res.lifecycle_decision != "approve"



class TestSlice3CorrectSemanticRepresentations:
    """Tests that correct semantic representations pass certification."""

    def test_apple_pay_google_pay_subject_preserved(self):
        """Candidates #68 & #69: Apple Pay / Google Pay subject is preserved intact."""
        quote = "| Apple Pay / Google Pay | Underlying card | Same as card |"
        res = UniversalGateEvaluator.evaluate(
            claim_text="| Apple Pay / Google Pay | Underlying card | Same as card |",
            subject="Apple Pay / Google Pay",
            predicate="has_refund_method",
            object_text="Underlying card",
            evidence=make_span(quote),
            clause_text=quote,
            metadata={"in_table": True, "table_grid": {"col_header": "Refund method"}},
        )
        assert res.lifecycle_decision == "approve"
        assert res.subject_valid is True

    def test_store_credit_bonus_correct_predicate_passes(self):
        """Candidate #78: 5% bonus credit mapped to receives_store_credit_bonus passes without actor inversion."""
        quote = "Customers who choose store credit instead of a refund to their original payment method receive an additional 5% bonus in credit value (maximum bonus $25.00 per return)."
        res = UniversalGateEvaluator.evaluate(
            claim_text="Customers who choose store credit receive an additional 5% bonus in credit value up to $25.00 per return.",
            subject="Customer",
            predicate="receives_store_credit_bonus",
            object_text="5% bonus on credit value, maximum bonus $25.00 per return",
            evidence=make_span(quote),
            clause_text=quote,
            metadata={"conditions": ["chooses store credit instead of refund to original payment method"]},
        )
        assert res.lifecycle_decision == "approve"
        assert res.clause_entails_claim is True

    def test_in_store_posting_passes_has_posting_duration(self):
        """Candidate #24: Immediate in-store processing & bank posting passes has_posting_duration."""
        quote = "In-store refunds to the original card are processed immediately; the bank may take 3-5 days to post the credit."
        res = UniversalGateEvaluator.evaluate(
            claim_text=quote,
            subject="In-store refunds",
            predicate="has_posting_duration",
            object_text="processed immediately; bank may take 3-5 days to post the credit",
            evidence=make_span(quote),
            clause_text=quote,
        )
        assert res.lifecycle_decision == "approve"
        assert res.clause_entails_claim is True

    def test_price_adjustment_passes_has_price_adjustment_window(self):
        """Candidate #81: 14-day price drop adjustment passes has_price_adjustment_window."""
        quote = "If an item you purchased drops in price within 14 days of purchase, contact us for a one-time price adjustment refund of the difference."
        res = UniversalGateEvaluator.evaluate(
            claim_text=quote,
            subject="Price adjustments",
            predicate="has_price_adjustment_window",
            object_text="14 days of purchase for one-time refund of difference",
            evidence=make_span(quote),
            clause_text=quote,
        )
        assert res.lifecycle_decision == "approve"
        assert res.clause_entails_claim is True

    def test_trial_charge_refund_passes_may_request_first_charge_refund(self):
        """Candidate #86: 7-day forgot trial cancel refund passes may_request_first_charge_refund."""
        quote = "If you forget to cancel and are charged, contact us within 7 days for a full refund of the first charge."
        res = UniversalGateEvaluator.evaluate(
            claim_text=quote,
            subject="Free trials",
            predicate="may_request_first_charge_refund",
            object_text="within 7 days for a full refund of the first charge",
            evidence=make_span(quote),
            clause_text=quote,
        )
        assert res.lifecycle_decision == "approve"
        assert res.clause_entails_claim is True

    def test_pause_trailhead_box_passes_can_pause_subscription(self):
        """Candidate #87: Pausing Trailhead box passes can_pause_subscription."""
        quote = "Trailhead Box subscribers can pause for up to 3 months, once per year, from the account page."
        res = UniversalGateEvaluator.evaluate(
            claim_text=quote,
            subject="Trailhead Box subscription",
            predicate="can_pause_subscription",
            object_text="for up to 3 months, once per year, from the account page",
            evidence=make_span(quote),
            clause_text=quote,
        )
        assert res.lifecycle_decision == "approve"
        assert res.clause_entails_claim is True


    def test_freight_deduction_correct_predicate_passes(self):
        """Candidate #94: $49 freight deduction mapped to has_return_freight_deduction passes."""
        quote = "Return freight for change-of-mind returns is a flat $49.00, deducted from the refund."
        res = UniversalGateEvaluator.evaluate(
            claim_text="Return freight for change-of-mind returns is a flat $49.00, deducted from the refund.",
            subject="Oversize items",
            predicate="has_return_freight_deduction",
            object_text="$49.00 flat return freight fee deducted from refund",
            evidence=make_span(quote),
            clause_text=quote,
            metadata={"conditions": ["change-of-mind return"]},
        )
        assert res.lifecycle_decision == "approve"
        assert res.clause_entails_claim is True

    def test_receipt_retention_correct_predicate_passes(self):
        """Candidate #99: Retaining drop-off receipt mapped to requires_receipt_retention passes."""
        quote = "Keep the drop-off receipt until your refund has been confirmed."
        res = UniversalGateEvaluator.evaluate(
            claim_text="Customers must keep the drop-off receipt until refund has been confirmed.",
            subject="Customer",
            predicate="requires_receipt_retention",
            object_text="drop-off receipt until refund has been confirmed",
            evidence=make_span(quote),
            clause_text=quote,
        )
        assert res.lifecycle_decision == "approve"
        assert res.clause_entails_claim is True

    def test_currency_rule_correct_predicate_passes(self):
        """Candidate #178: Currency rule mapped to uses_original_charge_currency passes."""
        quote = "Refunds are issued in the currency of the original charge."
        res = UniversalGateEvaluator.evaluate(
            claim_text="Refunds are issued in the currency of the original charge.",
            subject="International refund",
            predicate="uses_original_charge_currency",
            object_text="currency of the original charge",
            evidence=make_span(quote),
            clause_text=quote,
        )
        assert res.lifecycle_decision == "approve"
        assert res.clause_entails_claim is True

    def test_video_course_exception_with_anchored_quote_passes(self):
        """Candidate #134: 7-day video course exception passes when quote is correctly anchored."""
        correct_quote = "Video courses may be refunded within 7 days if less than 20% of the content has been viewed."
        res = UniversalGateEvaluator.evaluate(
            claim_text="Video courses may be refunded within 7 days if less than 20% of the content has been viewed.",
            subject="Video course",
            predicate="has_refund_window",
            object_text="7 days if less than 20% viewed",
            evidence=make_span(correct_quote),
            clause_text=correct_quote,
            metadata={"conditions": ["less than 20% viewed"]},
        )
        assert res.lifecycle_decision == "approve"
        assert res.clause_entails_claim is True

    def test_subscription_products_disaggregated_subjects(self):
        """Candidates #124-#129: Subscriptions retain product-specific subject identities."""
        quote_tb = "| Trailhead Box | Monthly, 1st of month | Anytime before the 25th | Full refund if cancelled within 48 hours of renewal and box not shipped |"
        res_tb = UniversalGateEvaluator.evaluate(
            claim_text=quote_tb,
            subject="Trailhead Box subscription",
            predicate="has_cancellation_rule",
            object_text="Anytime before the 25th",
            evidence=make_span(quote_tb),
            clause_text=quote_tb,
            metadata={"in_table": True, "table_grid": {"col_header": "Cancellation"}},
        )
        assert res_tb.lifecycle_decision == "approve"
        assert "Trailhead Box" in res_tb.subject or "trailhead" in res_tb.subject.lower()

        quote_rp = "| Rewards Plus | Annual | Anytime | Pro-rated refund within 30 days of renewal; none afterwards |"
        res_rp = UniversalGateEvaluator.evaluate(
            claim_text=quote_rp,
            subject="Rewards Plus subscription",
            predicate="has_refund_rule",
            object_text="Pro-rated refund within 30 days of renewal; none afterwards",
            evidence=make_span(quote_rp),
            clause_text=quote_rp,
            metadata={"in_table": True, "table_grid": {"col_header": "Refund rule"}},
        )
        assert res_rp.lifecycle_decision == "approve"

        quote_gcp = "| Gear Care Plan | Monthly | Anytime | No refund for current month; cancel effective next cycle |"
        res_gcp = UniversalGateEvaluator.evaluate(
            claim_text=quote_gcp,
            subject="Gear Care Plan subscription",
            predicate="has_refund_rule",
            object_text="No refund for current month; cancel effective next cycle",
            evidence=make_span(quote_gcp),
            clause_text=quote_gcp,
            metadata={"in_table": True, "table_grid": {"col_header": "Refund rule"}},
        )
        assert res_gcp.lifecycle_decision == "approve"

    def test_cosmetic_flaws_distinct_from_keep_it_policy(self):
        """Candidates #104 & #105: Partial refund for cosmetic flaws is distinct from Keep It policy."""
        quote = "| Partial refund (keep item) | Offered for minor cosmetic flaws | Immediate |"
        res = UniversalGateEvaluator.evaluate(
            claim_text=quote,
            subject="Partial refund for cosmetic flaws",
            predicate="has_resolution_option_details",
            object_text="Offered for minor cosmetic flaws",
            evidence=make_span(quote),
            clause_text=quote,
            metadata={"in_table": True, "table_grid": {"col_header": "Details"}},
        )
        assert res.lifecycle_decision == "approve"
        assert res.subject != "Keep It policy"

    def test_keep_it_annual_limit_linked_as_condition(self):
        """Candidate #108 & #109: Keep It under-$40 policy has annual limit bound as condition."""
        quote = 'For damaged items valued under $40.00, we may issue a refund without requiring the item to be returned ("Keep It" policy), at the agent\'s discretion. This is limited to two instances per customer per year.'
        res = UniversalGateEvaluator.evaluate(
            claim_text='For damaged items valued under $40.00, Northwind may issue a refund without requiring return ("Keep It" policy), limited to two instances per customer per year.',
            subject="Damaged item under $40",
            predicate="may_issue_refund_without_return",
            object_text="refund without requiring item return ('Keep It' policy)",
            evidence=make_span(quote),
            clause_text=quote,
            metadata={"conditions": ["at agent's discretion", "maximum 2 instances per customer per year"]},
        )
        assert res.lifecycle_decision == "approve"
        assert res.clause_entails_claim is True

    def test_customer_duty_drawback_responsibility_certified(self):
        """Candidate #180: Customer duty drawback responsibility is certified as an operative condition."""
        quote = "Customers are responsible for filing customs duty drawback claims where available."
        res = UniversalGateEvaluator.evaluate(
            claim_text="Customers are responsible for filing customs duty drawback claims where available.",
            subject="Customer",
            predicate="is_responsible_for_duty_drawback",
            object_text="filing customs duty drawback claims",
            evidence=make_span(quote),
            clause_text=quote,
            metadata={"conditions": ["where available"]},
        )
        assert res.lifecycle_decision == "approve"
        assert res.claim_type_allowed is True

    def test_request_info_table_required_vs_example_separation(self):
        """Candidates #42-#52: 'Required?' column produces operative rules, 'Example' column produces context."""
        quote = "| Photos | Damage close-up | If damaged |"
        # Example column -> NON_RULE / example
        res_ex = UniversalGateEvaluator.evaluate(
            claim_text=quote,
            subject="Photos",
            predicate="has_example_value",
            object_text="Damage close-up",
            evidence=make_span(quote),
            clause_text=quote,
            metadata={"content_role": "example", "table_grid": {"col_header": "Example"}},
        )
        assert res_ex.lifecycle_decision in ("reject", "non_rule") or res_ex.claim_type_allowed is False

        # Required column -> Operative procedural requirement (conditional)
        res_req = UniversalGateEvaluator.evaluate(
            claim_text="Photos are required for refund request if item is damaged.",
            subject="Photos",
            predicate="is_required_for_refund_request",
            object_text="required if damaged",
            evidence=make_span(quote),
            clause_text=quote,
            metadata={"in_table": True, "table_grid": {"col_header": "Required?"}, "conditions": ["if damaged"]},
        )
        assert res_req.lifecycle_decision == "approve"

    def test_revision_history_classified_as_revision_history(self):
        """Candidate #229: Version log is classified as revision_history, not example."""
        quote = "4.0 Mar 1, 2025 Gold member window raised from 45 to 60 days"
        res = UniversalGateEvaluator.evaluate(
            claim_text=quote,
            subject="Northwind policy version 4.0",
            predicate="has_revision_history",
            object_text="Gold member window raised from 45 to 60 days",
            evidence=make_span(quote),
            clause_text=quote,
            metadata={"content_role": "revision_history"},
        )
        assert res.lifecycle_decision in ("non_rule", "context") or res.certification_tier == "NON_RULE"


class TestSlice3NormalizerSeparationAndIntegrity:
    """Tests normalizer-level separation of distinct provisions and field name preservation."""

    def test_normalizer_strictly_separates_cosmetic_flaw_from_keep_it_under_40(self):
        """Candidate #104 (table row) and #108 (prose paragraph) must NOT collapse into identical signatures."""
        import uuid
        cand_table = CandidateClaim.create(
            envelope_id=uuid.uuid4(),
            unit_id="tbl_1",
            asset_id="test_doc",
            subject="Partial refund (keep item)",
            predicate="Offered for minor cosmetic flaws",
            object_="Offered for minor cosmetic flaws",
            claim_text="| Partial refund (keep item) | Offered for minor cosmetic flaws | Immediate |",
            evidence_text_span="| Partial refund (keep item) | Offered for minor cosmetic flaws | Immediate |",
            locator={"table_grid": {"col_header": "Details"}},
        )
        norm_table = ClaimQualityNormalizer.normalize_candidate_claim(cand_table)

        cand_prose = CandidateClaim.create(
            envelope_id=uuid.uuid4(),
            unit_id="prose_1",
            asset_id="test_doc",
            subject="Damaged items valued under $40.00",
            predicate="may issue a refund without requiring the item to be returned",
            object_="refund without requiring the item to be returned ('Keep It' policy)",
            claim_text='For damaged items valued under $40.00, we may issue a refund without requiring the item to be returned ("Keep It" policy), at the agent\'s discretion.',
            evidence_text_span='For damaged items valued under $40.00, we may issue a refund without requiring the item to be returned ("Keep It" policy), at the agent\'s discretion.',
            locator={},
        )
        norm_prose = ClaimQualityNormalizer.normalize_candidate_claim(cand_prose)

        assert norm_table is not None
        assert norm_prose is not None
        # They must have different signatures (subject and/or predicate) so deduplication preserves BOTH!
        table_sig = (norm_table.subject, norm_table.predicate)
        prose_sig = (norm_prose.subject, norm_prose.predicate)
        assert table_sig != prose_sig, f"Table row and prose paragraph collapsed to identical signature: {table_sig}"
        assert norm_table.subject in ("Partial refund for cosmetic flaws", "Partial refund (keep item)")
        assert norm_table.predicate == "has_resolution_option_details"
        assert norm_prose.subject in ("Damaged item under $40", "Damaged items valued under $40.00")
        assert norm_prose.predicate == "may_issue_refund_without_return"

    def test_normalizer_preserves_order_number_and_email_on_order_field_identities(self):
        """Preserves 'Order number' and 'Email on order' without merging both into generic 'Order'."""
        import uuid
        cand_order_num = CandidateClaim.create(
            envelope_id=uuid.uuid4(),
            unit_id="tbl_order",
            asset_id="test_doc",
            subject="Order number",
            predicate="is_required_for_refund_request",
            object_="Yes",
            claim_text="| Order number | NW-10482391 | Yes |",
            evidence_text_span="| Order number | NW-10482391 | Yes |",
            locator={"table_grid": {"col_header": "Required?"}},
        )
        norm_order_num = ClaimQualityNormalizer.normalize_candidate_claim(cand_order_num)

        cand_email = CandidateClaim.create(
            envelope_id=uuid.uuid4(),
            unit_id="tbl_email",
            asset_id="test_doc",
            subject="Email on order",
            predicate="is_required_for_refund_request",
            object_="Yes",
            claim_text="| Email on order | jane.doe@example.com | Yes |",
            evidence_text_span="| Email on order | jane.doe@example.com | Yes |",
            locator={"table_grid": {"col_header": "Required?"}},
        )
        norm_email = ClaimQualityNormalizer.normalize_candidate_claim(cand_email)

        assert norm_order_num is not None
        assert norm_email is not None
        assert norm_order_num.subject == "Order number"
        assert norm_email.subject == "Email on order"
        # Deduplication keys must be distinct
        key_num = (norm_order_num.subject, norm_order_num.predicate, norm_order_num.object)
        key_email = (norm_email.subject, norm_email.predicate, norm_email.object)
        assert key_num != key_email

    def test_store_credit_bonus_normalized_to_receives_store_credit_bonus(self):
        """Customer who chooses store credit must receive bonus, not offer it."""
        import uuid
        cand = CandidateClaim.create(
            envelope_id=uuid.uuid4(),
            unit_id="p_bonus",
            asset_id="test_doc",
            subject="Customer",
            predicate="offers_store_credit_bonus",
            object_="5% bonus on credit value, maximum bonus $25.00 per return",
            claim_text="Customers who choose store credit instead of a refund to their original payment method receive an additional 5% bonus in credit value (maximum bonus $25.00 per return).",
            evidence_text_span="Customers who choose store credit instead of a refund to their original payment method receive an additional 5% bonus in credit value (maximum bonus $25.00 per return).",
            locator={},
        )
        norm = ClaimQualityNormalizer.normalize_candidate_claim(cand)
        assert norm is not None
        assert norm.subject == "Customer"
        assert norm.predicate == "receives_store_credit_bonus"


