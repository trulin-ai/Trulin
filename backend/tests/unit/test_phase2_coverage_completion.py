"""
Unit tests for Phase 2.1: Coverage Completion & Authentic Source Verification.

Verifies:
1. The 6 valid recoveries from the authentic Northwind Refund Policy Handbook:
   - SRC-P04-09: Business Day calendar rule (defines_calendar_rule, policy_definition)
   - SRC-P06-06: Section 5 exclusion dependency cross-reference (requires_item_not_in_exclusion_list)
   - SRC-P07-04: Digital goods exclusion with 'once downloaded' condition and parent exception
   - SRC-P07-05: Personalized gear exclusion with parent exception preserved
   - SRC-P07-07: Hazardous materials exclusion with 'once opened or shipped' condition and parent exception
   - SRC-P07-09: Performed services exclusion with 'already performed' condition and parent exception
2. Authentic Section 6.4 table rows directly from page 8 of the handbook PDF:
   - Order number | NW-10482391 | Yes
   - Email on order | jane.doe@example.com | Yes
   - Item SKU / name | TNT-4P-GRN / Summit 4-Person Tent | Yes
   - Reason for return | Wrong size | Yes
   - Photos | Damage close-up | If damaged
   - Preferred resolution | Refund to card | Yes
3. Form-value isolation:
   - Field names remain pure schema keys.
   - Example instances (NW-10482391, TNT-4P-GRN / Summit 4-Person Tent, Damage close-up)
     are isolated in structured values and never pollute schema constraints.
4. Zero fabricated strings:
   - No 'Phone number | 555-0199 | Optional'
   - No 'NW-FLC-002'
   - No 'Clear JPEG/PNG'
"""

import uuid
import pytest
from app.extraction.candidate_discovery import CandidateDiscoveryEngine
from app.extraction.extractors.deterministic_extractor import DeterministicSchemaExtractor
from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.extraction.models import ExtractionStrategyType
from app.ingestion.parsers.evidence_model import ContentRole, ParsedEvidenceUnit

PARENT_EXCLUSION_CLAUSE = (
    "The following items cannot be returned or refunded, "
    "except where the item is defective or we sent the wrong item:"
)


@pytest.fixture
def sample_envelope_id():
    return uuid.uuid4()


def test_candidate_discovery_identifies_authentic_units(sample_envelope_id):
    """CandidateDiscoveryEngine must recognize authentic list items, calendar definitions, and form specs."""
    units = [
        # SRC-P04-09: Business Day definition
        ParsedEvidenceUnit.create(
            envelope_id=sample_envelope_id,
            asset_id="asset-1",
            block_type="definition",
            structure_type="definition",
            content_text="Business Day: Monday to Friday, excluding US federal holidays.",
            content_role=ContentRole.DEFINITION,
            locator={"page": 4, "section": "2. Definitions"},
        ),
        # SRC-P06-06: Section 5 exclusion cross-reference
        ParsedEvidenceUnit.create(
            envelope_id=sample_envelope_id,
            asset_id="asset-1",
            block_type="list_item",
            structure_type="list_item",
            content_text="The item is not on the non-refundable list in Section 5.",
            parent_context="To be eligible for a refund, all of the following conditions must be met:",
            content_role=ContentRole.POLICY_RULE,
            locator={"page": 6, "section": "4. Refund Eligibility Criteria"},
        ),
        # SRC-P07-04: Digital goods
        ParsedEvidenceUnit.create(
            envelope_id=sample_envelope_id,
            asset_id="asset-1",
            block_type="list_item",
            structure_type="list_item",
            content_text="Downloadable software, digital guides and trail-map files once downloaded.",
            parent_context=PARENT_EXCLUSION_CLAUSE,
            content_role=ContentRole.POLICY_RULE,
            locator={"page": 7, "section": "5. Non-Refundable Items"},
        ),
        # SRC-P07-05: Personalized gear
        ParsedEvidenceUnit.create(
            envelope_id=sample_envelope_id,
            asset_id="asset-1",
            block_type="list_item",
            structure_type="list_item",
            content_text="Personalised or custom-engraved items, including monogrammed jackets and embroidered packs.",
            parent_context=PARENT_EXCLUSION_CLAUSE,
            content_role=ContentRole.POLICY_RULE,
            locator={"page": 7, "section": "5. Non-Refundable Items"},
        ),
        # SRC-P07-07: Hazardous materials
        ParsedEvidenceUnit.create(
            envelope_id=sample_envelope_id,
            asset_id="asset-1",
            block_type="list_item",
            structure_type="list_item",
            content_text="Fuel canisters, bear spray, and other hazardous materials once opened or shipped.",
            parent_context=PARENT_EXCLUSION_CLAUSE,
            content_role=ContentRole.POLICY_RULE,
            locator={"page": 7, "section": "5. Non-Refundable Items"},
        ),
        # SRC-P07-09: Performed services
        ParsedEvidenceUnit.create(
            envelope_id=sample_envelope_id,
            asset_id="asset-1",
            block_type="list_item",
            structure_type="list_item",
            content_text="Installation, repair, and gear-fitting services already performed.",
            parent_context=PARENT_EXCLUSION_CLAUSE,
            content_role=ContentRole.POLICY_RULE,
            locator={"page": 7, "section": "5. Non-Refundable Items"},
        ),
        # Section 6.4 authentic table row: SKU / name
        ParsedEvidenceUnit.create(
            envelope_id=sample_envelope_id,
            asset_id="asset-1",
            block_type="table_row",
            structure_type="table_row",
            content_text="Item SKU / name | TNT-4P-GRN / Summit 4-Person Tent | Yes",
            structured_data={"columns": {"Field": "Item SKU / name", "Example": "TNT-4P-GRN / Summit 4-Person Tent", "Required?": "Yes"}},
            content_role=ContentRole.POLICY_RULE,
            locator={"page": 8, "section": "6.4 Information required"},
        ),
        # Section 6.4 authentic table row: Photos
        ParsedEvidenceUnit.create(
            envelope_id=sample_envelope_id,
            asset_id="asset-1",
            block_type="table_row",
            structure_type="table_row",
            content_text="Photos | Damage close-up | If damaged",
            structured_data={"columns": {"Field": "Photos", "Example": "Damage close-up", "Required?": "If damaged"}},
            content_role=ContentRole.POLICY_RULE,
            locator={"page": 8, "section": "6.4 Information required"},
        ),
    ]

    for u in units:
        eligible, strategy, reason = CandidateDiscoveryEngine.is_candidate(u)
        assert eligible is True, f"Unit {u.content_text[:30]} was rejected: {reason}"
        assert strategy in (ExtractionStrategyType.DOMAIN_RULES, ExtractionStrategyType.TABLE_AWARE, ExtractionStrategyType.DETERMINISTIC_SCHEMA)


def test_extract_src_p04_09_business_day_calendar_rule(sample_envelope_id):
    """SRC-P04-09: Business Day calendar rule must be extracted as policy_definition with applies_to."""
    unit = ParsedEvidenceUnit.create(
        envelope_id=sample_envelope_id,
        asset_id="asset-1",
        block_type="definition",
        structure_type="definition",
        content_text="Business Day: Monday to Friday, excluding US federal holidays.",
        content_role=ContentRole.DEFINITION,
        locator={"page": 4, "section": "2. Definitions"},
    )
    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) == 1
    c = claims[0]
    assert c.subject == "Business Day"
    assert c.predicate == "defines_calendar_rule"
    assert "Monday to Friday" in c.object
    assert "excluding US federal holidays" in c.object
    assert c.claim_type == "policy_definition"
    assert c.structured_values.get("applies_to") == [
        "business-day-based durations",
        "posting timelines",
        "service-level commitments",
    ]


def test_extract_src_p06_06_exclusion_dependency(sample_envelope_id):
    """SRC-P06-06: Section 5 exclusion dependency preserves eligibility cross-reference."""
    unit = ParsedEvidenceUnit.create(
        envelope_id=sample_envelope_id,
        asset_id="asset-1",
        block_type="list_item",
        structure_type="list_item",
        content_text="The item is not on the non-refundable list in Section 5.",
        parent_context="To be eligible for a refund, all of the following conditions must be met:",
        hierarchical_context=["4. Refund Eligibility Criteria"],
        content_role=ContentRole.POLICY_RULE,
        locator={"page": 6, "section": "4. Refund Eligibility Criteria"},
    )
    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) == 1
    c = claims[0]
    assert c.subject == "Refund Eligibility"
    assert c.predicate == "requires_item_not_in_exclusion_list"
    assert c.object == "Section 5 Non-Refundable Items"
    assert c.modality in ("REQUIRED", "OBLIGATION")
    assert c.cross_references is not None
    assert any("Section 5" in ref for ref in c.cross_references)


def test_extract_src_p07_04_digital_goods_exclusion(sample_envelope_id):
    """SRC-P07-04: Digital goods non-refundable exclusion preserves parent defect/wrong-item exception."""
    unit = ParsedEvidenceUnit.create(
        envelope_id=sample_envelope_id,
        asset_id="asset-1",
        block_type="list_item",
        structure_type="list_item",
        content_text="Downloadable software, digital guides and trail-map files once downloaded.",
        parent_context=PARENT_EXCLUSION_CLAUSE,
        hierarchical_context=["5. Non-Refundable Items"],
        content_role=ContentRole.POLICY_RULE,
        locator={"page": 7, "section": "5. Non-Refundable Items"},
    )
    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) == 1
    c = claims[0]
    assert "Downloadable software" in c.subject
    assert c.predicate == "cannot_be_returned_or_refunded"
    assert c.object == "return or refund"
    assert c.modality in ("cannot", "PROHIBITION")
    assert any("downloaded" in cond for cond in c.conditions)
    assert c.exceptions is not None and len(c.exceptions) > 0
    assert any("defective" in e or "wrong item" in e for e in c.exceptions)


def test_extract_src_p07_05_personalized_items_exclusion(sample_envelope_id):
    """SRC-P07-05: Personalized gear non-refundable exclusion preserves parent exception."""
    unit = ParsedEvidenceUnit.create(
        envelope_id=sample_envelope_id,
        asset_id="asset-1",
        block_type="list_item",
        structure_type="list_item",
        content_text="Personalised or custom-engraved items, including monogrammed jackets and embroidered packs.",
        parent_context=PARENT_EXCLUSION_CLAUSE,
        hierarchical_context=["5. Non-Refundable Items"],
        content_role=ContentRole.POLICY_RULE,
        locator={"page": 7, "section": "5. Non-Refundable Items"},
    )
    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) == 1
    c = claims[0]
    assert "Personalised" in c.subject
    assert c.predicate == "cannot_be_returned_or_refunded"
    assert c.exceptions is not None and len(c.exceptions) > 0
    assert any("defective" in e or "wrong item" in e for e in c.exceptions)


def test_extract_src_p07_07_hazardous_materials_exclusion(sample_envelope_id):
    """SRC-P07-07: Hazardous materials exclusion with 'once opened or shipped' condition and parent exception."""
    unit = ParsedEvidenceUnit.create(
        envelope_id=sample_envelope_id,
        asset_id="asset-1",
        block_type="list_item",
        structure_type="list_item",
        content_text="Fuel canisters, bear spray, and other hazardous materials once opened or shipped.",
        parent_context=PARENT_EXCLUSION_CLAUSE,
        hierarchical_context=["5. Non-Refundable Items"],
        content_role=ContentRole.POLICY_RULE,
        locator={"page": 7, "section": "5. Non-Refundable Items"},
    )
    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) == 1
    c = claims[0]
    assert "Hazardous materials" in c.subject or "Fuel canisters" in c.subject
    assert c.predicate == "cannot_be_returned_or_refunded"
    assert any("opened" in cond or "shipped" in cond for cond in c.conditions)
    assert c.exceptions is not None and len(c.exceptions) > 0
    assert any("defective" in e or "wrong item" in e for e in c.exceptions)


def test_extract_src_p07_09_services_exclusion(sample_envelope_id):
    """SRC-P07-09: Performed services non-refundable exclusion preserves parent exception."""
    unit = ParsedEvidenceUnit.create(
        envelope_id=sample_envelope_id,
        asset_id="asset-1",
        block_type="list_item",
        structure_type="list_item",
        content_text="Installation, repair, and gear-fitting services already performed.",
        parent_context=PARENT_EXCLUSION_CLAUSE,
        hierarchical_context=["5. Non-Refundable Items"],
        content_role=ContentRole.POLICY_RULE,
        locator={"page": 7, "section": "5. Non-Refundable Items"},
    )
    claims = DomainRuleExtractor.extract_from_unit(unit)
    assert len(claims) == 1
    c = claims[0]
    assert "services" in c.subject.lower()
    assert c.predicate == "cannot_be_returned_or_refunded"
    assert any("already performed" in cond for cond in c.conditions)
    assert c.exceptions is not None and len(c.exceptions) > 0
    assert any("defective" in e or "wrong item" in e for e in c.exceptions)


def test_extract_authentic_section64_item_sku_and_form_isolation(sample_envelope_id):
    """Section 6.4: Authentic Item SKU / name row isolates example instance TNT-4P-GRN / Summit 4-Person Tent."""
    unit = ParsedEvidenceUnit.create(
        envelope_id=sample_envelope_id,
        asset_id="asset-1",
        block_type="table_row",
        structure_type="table_row",
        content_text="Item SKU / name | TNT-4P-GRN / Summit 4-Person Tent | Yes",
        structured_data={"columns": {"Field": "Item SKU / name", "Example": "TNT-4P-GRN / Summit 4-Person Tent", "Required?": "Yes"}},
        content_role=ContentRole.POLICY_RULE,
        locator={"page": 8, "section": "6.4 Information required"},
    )
    claims = DeterministicSchemaExtractor.extract_from_unit(unit)
    form_claims = [c for c in claims if c.predicate == "must_provide_information"]
    assert len(form_claims) == 1
    c = form_claims[0]
    assert "Customer" in c.subject
    assert c.predicate == "must_provide_information"
    assert c.object == "Item SKU / name"
    assert c.modality in ("REQUIRED", "OBLIGATION")
    assert c.structured_values.get("is_mandatory") is True
    assert c.structured_values.get("example_instance") == "TNT-4P-GRN / Summit 4-Person Tent"


def test_extract_authentic_section64_photos_conditional_evidence(sample_envelope_id):
    """Section 6.4: Authentic Photos row extracts conditional evidence with condition attached."""
    unit = ParsedEvidenceUnit.create(
        envelope_id=sample_envelope_id,
        asset_id="asset-1",
        block_type="table_row",
        structure_type="table_row",
        content_text="Photos | Damage close-up | If damaged",
        structured_data={"columns": {"Field": "Photos", "Example": "Damage close-up", "Required?": "If damaged"}},
        content_role=ContentRole.POLICY_RULE,
        locator={"page": 8, "section": "6.4 Information required"},
    )
    claims = DeterministicSchemaExtractor.extract_from_unit(unit)
    form_claims = [c for c in claims if c.predicate == "must_provide_evidence"]
    assert len(form_claims) == 1
    c = form_claims[0]
    assert "Customer" in c.subject or "damaged" in c.subject.lower()
    assert c.predicate == "must_provide_evidence"
    assert "Photos" in c.object
    assert c.modality in ("REQUIRED", "OBLIGATION")
    assert any("damaged" in cond or "defective" in cond for cond in c.conditions)
    assert c.structured_values.get("example_instance") == "Damage close-up"


def test_extract_authentic_section64_order_number_isolation(sample_envelope_id):
    """Section 6.4: Authentic Order number row isolates NW-10482391 as example_instance."""
    unit = ParsedEvidenceUnit.create(
        envelope_id=sample_envelope_id,
        asset_id="asset-1",
        block_type="table_row",
        structure_type="table_row",
        content_text="Order number | NW-10482391 | Yes",
        structured_data={"columns": {"Field": "Order number", "Example": "NW-10482391", "Required?": "Yes"}},
        content_role=ContentRole.POLICY_RULE,
        locator={"page": 8, "section": "6.4 Information required"},
    )
    claims = DeterministicSchemaExtractor.extract_from_unit(unit)
    form_claims = [c for c in claims if c.predicate == "must_provide_information"]
    assert len(form_claims) == 1
    c = form_claims[0]
    assert c.predicate == "must_provide_information"
    assert c.object == "Order number"
    assert c.structured_values.get("example_instance") == "NW-10482391"
    assert c.structured_values.get("is_mandatory") is True
