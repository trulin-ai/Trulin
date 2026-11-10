"""
Red-Green Unit Tests for Phase 2.2 Batch 3: Scope Inversion Repair (#224).
Validates:
Section 5 'Non-Refundable Items' parent exception for items returned >90 days after delivery
is extracted with negative polarity ('cannot_be_returned_or_refunded'), NOT affirmative eligibility.
"""

import uuid
import pytest
from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.ingestion.parsers.evidence_model import ContentRole, ParsedEvidenceUnit


def test_batch3_224_non_refundable_items_over_90_days_prohibition():
    """
    Audit #224 (SRC-P07-06): 'Items returned more than 90 days after delivery.'
    Under Section 5 'Non-Refundable Items', must extract predicate 'cannot_be_returned_or_refunded'
    with PROHIBITION modality, NOT affirmative 'has_refund_eligibility'.
    """
    text = "Items returned more than 90 days after delivery."
    unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="test-224",
        block_type="clause",
        content_text=text,
        content_role=ContentRole.POLICY_RULE,
        hierarchical_context=["5. Non-Refundable Items"],
        locator={"line_start": 1, "line_end": 2, "page_number": 7},
    )
    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) >= 1, "No claim extracted for Section 5 item"
    c = claims[0]

    # Negative check: Affirmative eligibility inversion must NOT occur
    assert c.predicate != "has_refund_eligibility", "Inverted to affirmative 'has_refund_eligibility'!"
    assert c.modality != "POLICY_FACT" or c.predicate == "cannot_be_returned_or_refunded", "Modality inverted to affirmative fact!"

    # Positive check: Prohibition predicate and modality
    assert c.predicate == "cannot_be_returned_or_refunded", f"Expected 'cannot_be_returned_or_refunded', got '{c.predicate}'"
    assert c.modality in ("PROHIBITION", "cannot"), f"Expected PROHIBITION modality, got '{c.modality}'"

