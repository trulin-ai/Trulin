"""
Red-Green Unit Tests for Phase 2.2 Batch 1: Polarity & Modality Inversion (#78, #132).
Proves that negative modals ('cannot be cancelled', 'cannot be applied retroactively')
are not inverted to affirmative permissions ('can_cancel_before_shipment')
or degraded to generic catch-all rules ('has_validity_rule').
"""

import uuid
import pytest
from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.ingestion.parsers.evidence_model import ContentRole, ParsedEvidenceUnit


def make_test_unit(text: str, hier: list = None) -> ParsedEvidenceUnit:
    return ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id=f"test-{uuid.uuid4().hex[:6]}",
        block_type="clause",
        content_text=text,
        content_role=ContentRole.POLICY_RULE,
        hierarchical_context=hier or ["Return & Refund Policy"],
        locator={"line_start": 1, "line_end": 2, "page_number": 1},
    )


def test_batch1_132_gift_card_cancellation_prohibition_polarity():
    """
    Audit #132 (SRC-P15-02): 'Gift card purchases cannot be cancelled once the code is delivered by email.'
    Must extract predicate 'cannot_be_cancelled' with PROHIBITION modality, NOT affirmative 'can_cancel_before_shipment'.
    """
    sentence = "Gift card purchases cannot be cancelled once the code is delivered by email."
    unit = make_test_unit(sentence, hier=["15. Gift Cards", "15.1 Cancellation"])
    claims = DomainRuleExtractor.extract_from_unit(unit)

    assert len(claims) >= 1, "No claim extracted from gift card cancellation rule"
    c = claims[0]

    # Negative check: Affirmative inversion must NOT occur
    assert c.predicate != "can_cancel_before_shipment", "Polarity inverted to affirmative can_cancel_before_shipment!"
    assert c.modality != "PERMISSION", "Modality inverted to PERMISSION!"

    # Positive check: Correct prohibition predicate and condition
    assert c.predicate == "cannot_be_cancelled", f"Expected 'cannot_be_cancelled', got '{c.predicate}'"
    assert c.modality in ("PROHIBITION", "cannot"), f"Expected PROHIBITION modality, got '{c.modality}'"
    assert any("code is delivered" in str(cond).lower() for cond in (c.conditions or [])) or "code is delivered" in str(c.object_).lower(), (
        f"Missing condition 'once the code is delivered by email' in {c}"
    )


def test_batch1_78_bonus_credit_retroactive_prohibition_polarity():
    """
    Audit #78 (SRC-P10-07): 'Bonus credit cannot be applied retroactively once a refund has been issued to the card.'
    Must extract predicate 'cannot_be_applied_retroactively' with PROHIBITION modality, NOT generic 'has_validity_rule'.
    """
    sentence = "Bonus credit cannot be applied retroactively once a refund has been issued to the card."
    unit = make_test_unit(sentence, hier=["10. Store Credit Bonus", "10.2 Restrictions"])
    claims = DomainRuleExtractor.extract_from_unit(unit)

    assert len(claims) >= 1, "No claim extracted from bonus credit restriction"
    c = claims[0]

    # Negative check: Must not degrade to generic banned predicate
    assert c.predicate != "has_validity_rule", "Degraded to banned generic predicate 'has_validity_rule'!"

    # Positive check: Negative modality and predicate preserved
    assert c.predicate == "cannot_be_applied_retroactively", f"Expected 'cannot_be_applied_retroactively', got '{c.predicate}'"
    assert c.modality in ("PROHIBITION", "cannot"), f"Expected PROHIBITION modality, got '{c.modality}'"
    assert any("refund has been issued" in str(cond).lower() for cond in (c.conditions or [])) or "refund has been issued" in str(c.object_).lower(), (
        f"Missing condition 'once a refund has been issued to the card' in {c}"
    )

