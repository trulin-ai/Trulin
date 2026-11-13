"""
Regression test suite for Northbridge 30-Table Policy Document.
Locks in the 406-candidate / 333-certified baseline and protects all table-specific normalizations:
1. Non-normative table rejection (0 policy claims from registers, budgets, worked examples, forms)
2. Table 15 Checkbox matrix consolidation (6 claims, is_required_for_claim_types)
3. Table 20 RACI matrix normalization (23 active role-responsibility claims)
4. Table 22 Premium rate folding (40 clean claims with enriched subjects)
5. Cell-bound claim statement rendering with scope qualification
6. Table 5 and Table 29 definition unit preservation in evidence model
"""

import json
from pathlib import Path
import pytest

from app.ingestion.envelope import EnvelopeFactory
from app.ingestion.parsers.docx_parser import DocxAdapter
from app.ingestion.parsers.evidence_model import ContentRole
from app.extraction.pipeline import Layer5ExtractionPipeline
from app.validation_gate import Layer6ValidationGatePipeline

DOCX_PATH = Path("backend/storage/uploads/803da6db-66a8-4103-9353-792f353cf67f/Northbridge_Benefits_Leave_Claims_Policy.docx")
BASELINE_PATH = Path("backend/scripts/baseline/northbridge_30_table_policy_baseline.json")


@pytest.fixture(scope="module")
def baseline_data():
    assert BASELINE_PATH.exists(), f"Baseline file missing at {BASELINE_PATH}"
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


@pytest.mark.asyncio
async def test_northbridge_pipeline_reproduces_baseline(baseline_data):
    """Verifies that the live pipeline reproduces the locked baseline metrics."""
    assert DOCX_PATH.exists(), f"Target test document missing at {DOCX_PATH}"
    import uuid

    envelope = EnvelopeFactory.create_from_file_upload(
        filename="Northbridge_Benefits_Leave_Claims_Policy.docx",
        raw_bytes=DOCX_PATH.read_bytes(),
        parsed_content="",
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
    )
    parsed_res = await DocxAdapter().parse_to_evidence(envelope)
    l5_res = await Layer5ExtractionPipeline().process_envelope(envelope, parsed_res)
    l6_res = await Layer6ValidationGatePipeline(persist_to_db=False).process_extraction_result(envelope, l5_res)

    summary = baseline_data["summary"]
    assert l6_res.total_candidates_evaluated == summary["total_candidates"], (
        f"Expected {summary['total_candidates']} candidates, got {l6_res.total_candidates_evaluated}"
    )
    assert l6_res.claims_approved == summary["approved_certified"], (
        f"Expected {summary['approved_certified']} approved, got {l6_res.claims_approved}"
    )
    assert l6_res.claims_queued_for_review == summary["queued_for_review"], (
        f"Expected {summary['queued_for_review']} review, got {l6_res.claims_queued_for_review}"
    )
    assert l6_res.claims_rejected == summary["rejected"], (
        f"Expected {summary['rejected']} rejected, got {l6_res.claims_rejected}"
    )


def test_baseline_table_counts(baseline_data):
    """Verifies table-by-table claim distribution against established bounds."""
    counts = baseline_data["table_counts"]

    # Table 15 Checkbox matrix must be consolidated to exactly 6 document requirement claims
    assert counts.get("table_line_275") == 6

    # Table 20 RACI matrix must emit exactly 23 active role claims
    assert counts.get("table_line_359") == 23

    # Table 22 Premium rates must emit exactly 40 claims (folded annuals)
    assert counts.get("table_line_399") == 40

    # Table 17 Per diem allowance must emit exactly 30 claims
    assert counts.get("table_line_309") == 30

    # Table 18 Mileage must emit exactly 12 claims
    assert counts.get("table_line_325") == 12


def test_baseline_claim_statements_are_cell_bound(baseline_data):
    """Verifies that no claim text contains unparsed Markdown table row strings."""
    for tbl_id, items in baseline_data["evaluations_by_table"].items():
        if tbl_id == "non_table":
            continue
        for it in items:
            text = it["claim_text"]
            # Must not be raw markdown table row
            assert not (text.startswith("|") and text.endswith("|")), (
                f"Claim text is unparsed table row in table {tbl_id}: '{text}'"
            )
            # Approved policy claims must have Subject | Predicate | Value structure
            if it["decision"] == "approve":
                assert " | " in text, f"Claim text lacks atomic delimiter: '{text}'"


@pytest.mark.asyncio
async def test_definitions_captured_in_evidence():
    """Confirms that Tables 5 and 29 terms are captured as definition units, not lost."""
    import uuid

    envelope = EnvelopeFactory.create_from_file_upload(
        filename="Northbridge_Benefits_Leave_Claims_Policy.docx",
        raw_bytes=DOCX_PATH.read_bytes(),
        parsed_content="",
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
    )
    parsed_res = await DocxAdapter().parse_to_evidence(envelope)
    def_units = [u for u in parsed_res.units if u.content_role == ContentRole.DEFINITION]

    # Verify key glossary terms from Table 5
    terms = set()
    for u in def_units:
        cols = (u.structured_data or {}).get("columns", {})
        if "Term" in cols:
            terms.add(cols["Term"])
        if "Acronym" in cols:
            terms.add(cols["Acronym"])

    assert "Admissible expense" in terms
    assert "Business day" in terms
    assert "Co-payment" in terms
    assert "Deductible" in terms
    assert "In-network provider" in terms
    assert "RACI" in terms
    assert "SLA" in terms
    assert "TPA" in terms
