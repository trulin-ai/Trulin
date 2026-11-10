"""
Red-Green Unit Tests for Phase 2.2 Batch 2: Missing Conditions (#19, #67).
Validates:
1. Receipt-less returns (#19): Multi-clause conditions are parsed; unparsed raw sentence blob in object is eliminated.
2. Apple Pay / Google Pay (#67): 'Same as card' table cell is parsed as a timeline reference pointer, not an independent duration.
"""

import uuid
import pytest
from app.extraction.extractors.deterministic_extractor import DeterministicSchemaExtractor
from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.ingestion.parsers.evidence_model import ContentRole, ParsedEvidenceUnit


def test_batch2_19_receiptless_returns_structured_conditions():
    """
    Audit #19 (SRC-P05-08): Receipt-less returns must parse object as store credit remedy
    and extract in-store condition rather than dumping the full raw sentence into object.
    """
    text = (
        "Returns without proof of purchase are accepted in-store only, "
        "for store credit at the lowest price the item was sold in the last 90 days."
    )
    unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="test-19",
        block_type="clause",
        content_text=text,
        content_role=ContentRole.POLICY_RULE,
        hierarchical_context=["3. Return Requirements", "3.2 Receipt-less returns"],
        locator={"line_start": 1, "line_end": 2, "page_number": 3},
    )
    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) >= 1, "No claim extracted for receipt-less returns"
    c = claims[0]

    # Negative check: unparsed sentence blob must not be dumped into object
    assert c.object != text, "Object is still the unparsed raw sentence blob!"

    # Positive check: structured object and in-store condition
    assert "store credit" in c.object.lower(), f"Expected store credit in object, got '{c.object}'"
    assert "lowest price" in c.object.lower() or "90 days" in c.object.lower(), f"Expected price/time qualification in object, got '{c.object}'"
    assert any("in-store" in cond.lower() for cond in (c.conditions or [])), f"Missing 'in-store only' condition in {c.conditions}"


def test_batch2_67_same_as_card_timeline_reference_qualifier():
    """
    Audit #67 (SRC-P10-03): Table cell 'Same as card' must be typed as a timeline reference pointer,
    NOT as a standalone posting or stage duration.
    """
    unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="test-67",
        block_type="table_row",
        content_text="| Apple Pay / Google Pay | Underlying card | Same as card |",
        content_role=ContentRole.POLICY_RULE,
        hierarchical_context=["8. Refund Methods and Timelines"],
        locator={"line_start": 1, "line_end": 2, "page_number": 10},
        structured_data={
            "columns": {
                "Payment Method": "Apple Pay / Google Pay",
                "Refund Destination": "Underlying card",
                "Typical Timeline": "Same as card",
            }
        },
    )
    claims = DeterministicSchemaExtractor.extract_from_unit(unit)
    timeline_claims = [c for c in claims if "timeline" in str(c.conditions).lower() or "same as card" in str(c.object).lower() or "timeline" in c.predicate.lower()]

    assert len(timeline_claims) >= 1, f"No timeline reference claim found: {claims}"
    tc = timeline_claims[0]

    # Negative check: Must not be classified as standalone stage or posting duration
    assert tc.predicate != "has_stage_duration", "Misclassified as standalone 'has_stage_duration'!"
    assert tc.predicate != "has_posting_duration", "Misclassified as standalone 'has_posting_duration'!"

    # Positive check: Classified as timeline reference pointer
    assert tc.predicate == "references_underlying_payment_timeline", f"Expected 'references_underlying_payment_timeline', got '{tc.predicate}'"

