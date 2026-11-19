"""
Unit tests for Phase 1b: Coverage Instrumentation.

Verifies:
1. Completeness ledger captures 100% of parsed units with exact offsets and structure types.
2. Valid skip reasons are recorded for all non-rule units (definitions, changelog, contacts, headings, examples).
3. Bullet points inherit lead-in prose as their parent_context.
4. Table rows inherit preceding prose context.
5. Operative rules vs unextracted units are strictly accounted for without silent omissions.
"""

import uuid
import pytest
from app.db.enums import SourceFamily, SourceIntent
from app.ingestion.envelope import EnvelopeFactory
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.parsers.evidence_model import ContentRole


@pytest.fixture
def policy_with_bullets_and_metadata():
    return """# Northwind Refund Policy Handbook v4.2

## 2. Definitions
Refund: Return of money to the original payment method or store credit.
Return: Sending a purchased item back to Northwind.

## 5. Non-Refundable Items
The following items cannot be returned or refunded, except where the item is defective or we sent the wrong item:
- Items marked Final Sale
- Gift cards
- Custom or personalized gear

## 8. Refund Methods
Refunds are issued to the original form of payment whenever possible.

| Payment Method | Refund Destination | Typical Timeline |
| --- | --- | --- |
| Credit card | Original card | 3-5 business days |
| Apple Pay / Google Pay | Underlying card | Same as card |

## 20. Revision History
| Version | Date | Change |
| --- | --- | --- |
| 4.2 | Jan 1, 2026 | Extended holiday window |
| 4.1 | Aug 15, 2025 | Clarified BNPL |

## 21. Contact Customer Support
Email: support@northwind-demo.example
Phone: 1-800-555-0199
"""


@pytest.mark.asyncio
async def test_completeness_ledger_captures_all_units(policy_with_bullets_and_metadata):
    raw_bytes = policy_with_bullets_and_metadata.encode("utf-8")
    env = EnvelopeFactory.create_from_file_upload(
        filename="policy.md",
        raw_bytes=raw_bytes,
        parsed_content=policy_with_bullets_and_metadata,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        source_family=SourceFamily.DOCUMENT,
    )

    result = await DocumentParser.parse(env)
    assert len(result.units) > 0
    assert len(result.completeness_ledger) == len(result.units)

    # Every unit must have a ledger entry with valid skip accounting
    valid_skip_reasons = {
        "NON_OPERATIVE_HEADING",
        "NON_OPERATIVE_DEFINITION",
        "NON_OPERATIVE_CHANGELOG",
        "NON_OPERATIVE_CONTACT",
        "NON_OPERATIVE_EXAMPLE",
        "NON_OPERATIVE_METADATA",
        "AMBIGUOUS_REPRESENTATION_FLAGGED"
    }

    for entry in result.completeness_ledger:
        assert entry["unit_id"] is not None
        assert entry["structure_type"] in ("heading", "table_row", "list_item", "prose_clause", "paragraph")
        assert entry["char_end"] > entry["char_start"]
        if entry["is_operative_rule"]:
            assert entry["skip_reason"] is None
        else:
            assert entry["skip_reason"] in valid_skip_reasons


@pytest.mark.asyncio
async def test_parent_context_propagates_to_bullet_items(policy_with_bullets_and_metadata):
    raw_bytes = policy_with_bullets_and_metadata.encode("utf-8")
    env = EnvelopeFactory.create_from_file_upload(
        filename="policy.md",
        raw_bytes=raw_bytes,
        parsed_content=policy_with_bullets_and_metadata,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        source_family=SourceFamily.DOCUMENT,
    )

    result = await DocumentParser.parse(env)
    
    # Locate bullet item for 'Items marked Final Sale'
    bullet_unit = next(u for u in result.units if "Final Sale" in u.content_text)
    assert bullet_unit.structure_type == "list_item"
    assert bullet_unit.parent_context is not None

    # Parent context must contain the lead-in sentence with the defect exception
    assert "The following items cannot be returned or refunded" in bullet_unit.parent_context
    assert "except where the item is defective" in bullet_unit.parent_context


@pytest.mark.asyncio
async def test_parent_context_propagates_to_table_rows(policy_with_bullets_and_metadata):
    raw_bytes = policy_with_bullets_and_metadata.encode("utf-8")
    env = EnvelopeFactory.create_from_file_upload(
        filename="policy.md",
        raw_bytes=raw_bytes,
        parsed_content=policy_with_bullets_and_metadata,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        source_family=SourceFamily.DOCUMENT,
    )

    result = await DocumentParser.parse(env)
    
    # Locate table row for 'Apple Pay'
    apple_pay_unit = next(u for u in result.units if "Apple Pay" in u.content_text)
    assert apple_pay_unit.structure_type == "table_row"
    assert apple_pay_unit.parent_context is not None
    assert "Refunds are issued to the original form of payment" in apple_pay_unit.parent_context


@pytest.mark.asyncio
async def test_quality_metrics_operative_vs_unextracted_accounting(policy_with_bullets_and_metadata):
    raw_bytes = policy_with_bullets_and_metadata.encode("utf-8")
    env = EnvelopeFactory.create_from_file_upload(
        filename="policy.md",
        raw_bytes=raw_bytes,
        parsed_content=policy_with_bullets_and_metadata,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        source_family=SourceFamily.DOCUMENT,
    )

    result = await DocumentParser.parse(env)
    qm = result.quality_metrics
    assert "operative_rules_count" in qm
    assert "unextracted_units_accounted" in qm
    assert qm["operative_rules_count"] + qm["unextracted_units_accounted"] == len(result.units)
    assert qm["operative_rules_count"] > 0
    assert qm["unextracted_units_accounted"] > 0

