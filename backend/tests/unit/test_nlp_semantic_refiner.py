"""
Unit Test Suite for NLPSemanticRefiner (Pass 2 Unified Architecture).

Validates:
1. Pronoun and anaphora resolution for ambiguous subjects.
2. Connective prefix stripping and canonical entity normalization.
3. Preservation of 2D table matrix coordinates, values, and conditions.
4. Subordinate condition isolation into candidate.conditions.
5. Predicate alignment against the controlled PredicateRegistryService.
6. End-to-end integration within UnifiedExtractionPipeline.
"""

import uuid
import pytest

from app.db.enums import SourceIntent
from app.extraction.models import (
    CandidateClaim,
    ExtractionStrategyType,
    TableGridBinding,
)
from app.extraction.nlp_refiner import NLPSemanticRefiner
from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions
from app.taxonomy.registry import PredicateRegistryService


@pytest.fixture
def mock_envelope_id():
    return uuid.uuid4()


def test_refiner_resolves_pronoun_from_heading_context(mock_envelope_id):
    """Test that ambiguous pronouns ('they') resolve to the canonical role from heading context."""
    cand = CandidateClaim.create(
        envelope_id=mock_envelope_id,
        unit_id="u_001",
        asset_id="doc_test",
        claim_text="They must submit written notice 30 days prior to departure.",
        subject="they",
        predicate="must_notify",
        object_="30 days written notice",
        evidence_text_span="They must submit written notice 30 days prior to departure.",
        locator={
            "heading_path": ["# Employment Resignation Policy", "## Resignation Notice Period"],
            "document_type": "employment_policy",
        },
    )

    refined = NLPSemanticRefiner.refine_candidate(cand)
    assert refined.subject == "Employee"
    assert refined.nlp_enrichment.get("coreference_resolved") is True
    assert refined.nlp_enrichment.get("original_pronoun") == "they"


def test_refiner_strips_connective_prefixes(mock_envelope_id):
    """Test that leading sentence connectives ('Furthermore, the customer') are cleaned."""
    cand = CandidateClaim.create(
        envelope_id=mock_envelope_id,
        unit_id="u_002",
        asset_id="doc_test",
        claim_text="Furthermore, the customer must retain original packaging for all refunds.",
        subject="Furthermore, the customer",
        predicate="must_retain",
        object_="original packaging",
        evidence_text_span="Furthermore, the customer must retain original packaging for all refunds.",
    )

    refined = NLPSemanticRefiner.refine_candidate(cand)
    assert refined.subject in ("Customer", "Customers")
    assert refined.nlp_enrichment.get("nlp_refined") is True


def test_refiner_preserves_table_matrix_integrity(mock_envelope_id):
    """Test that table matrix claims retain grid coordinates, scalar value, unit, and conditions."""
    grid = TableGridBinding(
        table_id="tbl_notice",
        row_key="Level C",
        column_header="Confirmed Notice Period",
        cell_value="60 days",
        normalized_value=60.0,
        normalized_unit="days",
    )
    cand = CandidateClaim.create(
        envelope_id=mock_envelope_id,
        unit_id="u_003",
        asset_id="doc_test",
        claim_text="Level C Middle Management have 60 days notice upon confirmation.",
        subject="Middle Management",
        predicate="has_confirmed_notice_duration",
        object_="60 days",
        value=60.0,
        unit="days",
        conditions=["Confirmed status", "Table Column: Confirmed Notice Period"],
        scope={"Level": "Level C", "Group": "Middle Management"},
        table_binding=grid,
        extraction_strategy=ExtractionStrategyType.TABLE_AWARE,
        evidence_text_span="| Level C | Middle Management | 60 days | 15 days |",
    )

    refined = NLPSemanticRefiner.refine_candidate(cand)
    assert refined.value == 60.0
    assert refined.unit == "days"
    assert "Confirmed status" in refined.conditions
    assert refined.table_binding is not None
    assert refined.scope.get("Level") == "Level C"


def test_refiner_aligns_predicate_to_registry(mock_envelope_id):
    """Test that informal predicates are aligned to controlled registry vocabulary."""
    cand = CandidateClaim.create(
        envelope_id=mock_envelope_id,
        unit_id="u_004",
        asset_id="doc_test",
        claim_text="Customer must provide written notice 30 days prior.",
        subject="Customer",
        predicate="must_notify",
        object_="written notice 30 days prior",
        evidence_text_span="Customer must provide written notice 30 days prior.",
    )

    refined = NLPSemanticRefiner.refine_candidate(cand)
    assert refined.predicate == "requires_written_notice"
    assert PredicateRegistryService.exists(refined.predicate) is True


@pytest.mark.asyncio
async def test_end_to_end_dual_pass_unified_pipeline():
    """Verify end-to-end execution of UnifiedExtractionPipeline with Pass 1 + Pass 2 NLP refiner."""
    doc_text = """# Employment & Operational Governance Handbook

## Notice Period Duration
| Level | Group | Confirmed Notice Period | Probationers Notice Period |
| Level C | Middle Management | 60 days | 15 days |

## Hardware Returns
Customers must initiate product return requests within 30 days of delivery.
Furthermore, the customer must provide original sales receipts for all returned equipment.
"""
    options = UnifiedPipelineOptions(
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        document_type="policy",
        source_intent=SourceIntent.GOVERNANCE_POLICY,
    )

    result = await UnifiedExtractionPipeline.execute(
        filename="governance_handbook.md",
        raw_bytes=doc_text.encode("utf-8"),
        options=options,
        parsed_content=doc_text,
    )

    assert len(result.raw_candidates) > 0
    assert len(result.candidates) > 0

    # 1. Verify table-derived claim
    table_claims = [c for c in result.candidates if c.value == 60.0]
    assert len(table_claims) >= 1
    t_claim = table_claims[0]
    assert t_claim.unit == "days"
    assert "Confirmed status" in t_claim.conditions

    # 2. Verify narrative-derived claim
    receipt_claims = [c for c in result.candidates if "receipt" in str(c.object).lower() or "receipt" in c.claim_text.lower()]
    assert len(receipt_claims) >= 1
    r_claim = receipt_claims[0]
    assert r_claim.subject in ("Customer", "Customers")
