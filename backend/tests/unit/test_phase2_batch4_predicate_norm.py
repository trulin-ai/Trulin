"""
Red-Green Unit Tests for Phase 2.2 Batch 4: Predicate Normalization (#43, #66).
Validates:
1. Form specification fields (#43): Field requirements are extracted with predicate
   'must_provide_information' with structured example value, NOT 'is_required_for_refund_request' with object 'Yes'.
2. Soft SLA timeline estimates (#66): Soft qualified estimates ('Usually within 24 hours')
   are extracted with predicate 'has_posting_sla_estimate', NOT strict deontic 'has_posting_duration'.
"""

import uuid
import pytest
from app.extraction.extractors.deterministic_extractor import DeterministicSchemaExtractor
from app.ingestion.parsers.evidence_model import ContentRole, ParsedEvidenceUnit


def test_batch4_43_form_specification_predicate_normalization():
    """
    Audit #43 (SRC-P08-04): Form table row '| Email on order | jane.doe@example.com | Yes |'
    Must extract predicate 'must_provide_information' rather than 'is_required_for_refund_request' with object 'Yes'.
    """
    unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="test-43",
        block_type="table_row",
        content_text="| Email on order | jane.doe@example.com | Yes |",
        content_role=ContentRole.POLICY_RULE,
        hierarchical_context=["6. Return Process", "6.4 Information required for return request"],
        locator={"line_start": 1, "line_end": 2, "page_number": 8},
        structured_data={
            "columns": {
                "Required Information": "Email on order",
                "Example Format": "jane.doe@example.com",
                "Mandatory?": "Yes",
            }
        },
    )
    claims = DeterministicSchemaExtractor.extract_from_unit(unit)
    assert len(claims) >= 1, f"No claims extracted from form row: {claims}"
    c = claims[0]

    # Negative check: Must not conflate into generic boolean requirement with object 'Yes'
    assert c.predicate != "is_required_for_refund_request", "Extracted legacy 'is_required_for_refund_request'!"
    assert c.object != "Yes", "Object is raw boolean 'Yes' instead of structured field specification!"

    # Positive check: Normalized predicate and preserved example metadata
    assert c.predicate == "must_provide_information", f"Expected 'must_provide_information', got '{c.predicate}'"
    assert "email" in str(c.object).lower() or "email" in str(c.subject).lower()
    sv = c.structured_values or {}
    assert sv.get("example_instance") == "jane.doe@example.com" or "jane.doe@example.com" in str(sv)


def test_batch4_66_soft_sla_estimate_predicate_normalization():
    """
    Audit #66 (SRC-P10-04): PayPal timeline '| PayPal | PayPal balance | Usually within 24 hours |'
    Must extract predicate 'has_posting_sla_estimate' for qualified soft estimate, NOT deontic 'has_posting_duration'.
    """
    unit = ParsedEvidenceUnit.create(
        envelope_id=uuid.uuid4(),
        asset_id="test-66",
        block_type="table_row",
        content_text="| PayPal | PayPal balance | Usually within 24 hours |",
        content_role=ContentRole.POLICY_RULE,
        hierarchical_context=["8. Refund Methods and Timelines"],
        locator={"line_start": 1, "line_end": 2, "page_number": 10},
        structured_data={
            "columns": {
                "Payment Method": "PayPal",
                "Refund Destination": "PayPal balance",
                "Typical Timeline": "Usually within 24 hours",
            }
        },
    )
    claims = DeterministicSchemaExtractor.extract_from_unit(unit)
    timeline_claims = [c for c in claims if "24 hours" in str(c.object).lower() or "usually" in str(c.object).lower()]

    assert len(timeline_claims) >= 1, f"No timeline claims extracted: {claims}"
    tc = timeline_claims[0]

    # Negative check: Soft estimate must not be typed as strict deontic duration
    assert tc.predicate != "has_posting_duration", "Misclassified as strict deontic 'has_posting_duration'!"

    # Positive check: Normalized to soft SLA estimate
    assert tc.predicate == "has_posting_sla_estimate", f"Expected 'has_posting_sla_estimate', got '{tc.predicate}'"
    assert "24 hours" in tc.object

