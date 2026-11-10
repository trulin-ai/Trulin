"""
Unit Test Suite for Phase 1: Layer 4 Structured Evidence Units.
Verifies that:
1. ParsedEvidenceUnit contains all extended structural fields:
   table_id, row_id, column_headers, cells, parent_context, section_path, char_start, char_end, resolved_references.
2. Tables are not flattened; cells and column headers remain a 2D matrix.
3. Apple Pay / Google Pay 'Same as card' resolves as a timeline_reference pointing to underlying_card_posting_duration.
4. Buy Now Pay Later resolves to provider_timelines.
5. Cross-references (e.g. 'see Section 13') resolve as cross_reference links.
6. Prose units preserve parent_context and physical character offsets.
"""

import uuid
import pytest
from app.db.enums import SourceFamily, SourceIntent
from app.ingestion.envelope import EnvelopeFactory
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.parsers.evidence_model import ContentRole, ParsedEvidenceUnit


@pytest.fixture
def sample_policy_markdown():
    return """# Refund and Payment Policy

## 8. Refund Methods and Payment Types
Refunds are issued to the original form of payment whenever possible.

| Original payment | Refund method | Notes |
| --- | --- | --- |
| Visa / Mastercard | Original card | 3-5 business days to post |
| Apple Pay / Google Pay | Underlying card | Same as card |
| Buy Now Pay Later | Provider reduces balance | Provider timelines apply |
| Gift card | Store credit | See Section 13 |

For damaged items valued under $40.00, we may issue a refund without return ("Keep It" policy).
"""


@pytest.mark.asyncio
async def test_phase1_table_matrix_preservation(sample_policy_markdown):
    raw_bytes = sample_policy_markdown.encode("utf-8")
    env = EnvelopeFactory.create_from_file_upload(
        filename="policy.md",
        raw_bytes=raw_bytes,
        parsed_content=sample_policy_markdown,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        source_family=SourceFamily.DOCUMENT,
    )

    result = await DocumentParser.parse(env)
    assert len(result.units) > 0

    table_units = [u for u in result.units if u.structure_type == "table_row"]
    assert len(table_units) == 4

    # Check first row (Visa / Mastercard)
    visa_unit = table_units[0]
    assert visa_unit.table_id is not None
    assert visa_unit.row_id is not None
    assert visa_unit.column_headers == ["Original payment", "Refund method", "Notes"]
    assert visa_unit.cells["Original payment"] == "Visa / Mastercard"
    assert visa_unit.cells["Refund method"] == "Original card"
    assert "Refunds are issued to the original form of payment" in (visa_unit.parent_context or "")
    assert visa_unit.char_start is not None
    assert visa_unit.char_end is not None


@pytest.mark.asyncio
async def test_phase1_apple_pay_reference_resolution(sample_policy_markdown):
    """REG-SEM-007 Acceptance Test: 'Same as card' resolves as reference, not standalone duration."""
    raw_bytes = sample_policy_markdown.encode("utf-8")
    env = EnvelopeFactory.create_from_file_upload(
        filename="policy.md",
        raw_bytes=raw_bytes,
        parsed_content=sample_policy_markdown,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        source_family=SourceFamily.DOCUMENT,
    )

    result = await DocumentParser.parse(env)
    apple_pay_unit = next(u for u in result.units if "Apple Pay" in u.content_text)

    assert apple_pay_unit.structure_type == "table_row"
    assert apple_pay_unit.cells["Notes"] == "Same as card"
    assert apple_pay_unit.cells["Refund method"] == "Underlying card"

    # Must contain timeline_reference pointing to underlying card
    assert len(apple_pay_unit.resolved_references) >= 1
    ref = apple_pay_unit.resolved_references[0]
    assert ref["reference_type"] == "timeline_reference"
    assert ref["target"] == "underlying_card_posting_duration"
    assert ref["source_text"] == "Same as card"


@pytest.mark.asyncio
async def test_phase1_external_and_cross_references(sample_policy_markdown):
    raw_bytes = sample_policy_markdown.encode("utf-8")
    env = EnvelopeFactory.create_from_file_upload(
        filename="policy.md",
        raw_bytes=raw_bytes,
        parsed_content=sample_policy_markdown,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        source_family=SourceFamily.DOCUMENT,
    )

    result = await DocumentParser.parse(env)

    # Buy Now Pay Later
    bnpl_unit = next(u for u in result.units if "Buy Now Pay Later" in u.content_text)
    assert any(r["reference_type"] == "external_provider_timeline" for r in bnpl_unit.resolved_references)

    # Gift card cross reference
    gift_unit = next(u for u in result.units if "Gift card" in u.content_text)
    cross_refs = [r for r in gift_unit.resolved_references if r["reference_type"] == "cross_reference"]
    assert len(cross_refs) == 1
    assert cross_refs[0]["target_section"] == "Section 13"


@pytest.mark.asyncio
async def test_phase1_prose_keep_it_isolation(sample_policy_markdown):
    """REG-SEM-005 Acceptance Test: Prose Keep It under-$40 rule is isolated from table rows."""
    raw_bytes = sample_policy_markdown.encode("utf-8")
    env = EnvelopeFactory.create_from_file_upload(
        filename="policy.md",
        raw_bytes=raw_bytes,
        parsed_content=sample_policy_markdown,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        source_family=SourceFamily.DOCUMENT,
    )

    result = await DocumentParser.parse(env)
    keep_it_unit = next(u for u in result.units if "Keep It" in u.content_text)

    # Must be separate prose clause with distinct physical offsets
    assert keep_it_unit.structure_type in ("prose_clause", "paragraph")
    assert keep_it_unit.table_id is None
    assert "under $40.00" in keep_it_unit.content_text
    assert keep_it_unit.char_start > 0

