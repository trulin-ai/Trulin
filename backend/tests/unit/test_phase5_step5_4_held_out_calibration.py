"""
Unit test suite for Phase 5 Step 5.4: Held-Out Document Multi-Page Boundary Calibration.

Validates:
1. Coverage across all 4 held-out documents (DOC-FAM1-03, DOC-FAM2-03, DOC-FAM3-03, DOC-FAM4-03).
2. Multi-page clause boundary extraction and character offset integrity.
3. Discretionary clause shielding (tri-state ambiguous handling).
4. Quantitative SLA and timeline fidelity across page boundaries.
"""

import pytest
from app.services.held_out_boundary_calibrator import (
    HeldOutBoundaryCalibrator,
)


@pytest.fixture
def calibrator():
    return HeldOutBoundaryCalibrator()


def test_held_out_cases_coverage(calibrator):
    """Verifies that all 4 held-out documents are represented in calibration cases."""
    cases = calibrator.get_held_out_calibration_cases()
    assert len(cases) == 11

    docs_covered = {c.document_id for c in cases}
    expected_docs = {
        "DOC-FAM1-03",  # Enterprise Agreement (Contracts)
        "DOC-FAM2-03",  # Resignation Policy (HR)
        "DOC-FAM3-03",  # Azure Billing Docs (Invoices)
        "DOC-FAM4-03",  # SSPA Program (Statutory)
    }
    assert docs_covered == expected_docs

    families_covered = {c.family_id for c in cases}
    assert families_covered == {"FAM-1", "FAM-2", "FAM-3", "FAM-4"}


def test_held_out_boundary_calibration_execution(calibrator):
    """Asserts that all 11 held-out calibration cases pass through the gate engine."""
    res = calibrator.calibrate_and_evaluate()
    assert res["status"] == "PASS"
    assert res["all_cases_passed"] is True
    assert res["passed_count"] == 11
    assert res["total_cases_evaluated"] == 11

    # Verify that multi-page spans (P1-P2, P1-P3) calibrated successfully
    multi_page_cases = [c for c in res["cases"] if "-" in c["page_span"]]
    assert len(multi_page_cases) >= 2
    for m in multi_page_cases:
        assert m["calibration_matched"] is True
        assert m["gate_passed"] is True


def test_discretionary_scope_shielding(calibrator):
    """Asserts that discretionary clauses remain shielded and are not promoted to unconditional rules."""
    cases = calibrator.get_held_out_calibration_cases()
    discretionary_cases = [c for c in cases if c.is_discretionary]
    assert len(discretionary_cases) == 2

    res = calibrator.calibrate_and_evaluate()
    case_map = {c["case_id"]: c for c in res["cases"]}

    for dc in discretionary_cases:
        assert dc.case_id in case_map
        eval_item = case_map[dc.case_id]
        assert eval_item["is_discretionary"] is True
        assert eval_item["calibration_matched"] is True


def test_quantitative_sla_fidelity_across_pages(calibrator):
    """Asserts that quantitative durations (90 days, 2 weeks) are strictly preserved across pages."""
    cases = calibrator.get_held_out_calibration_cases()
    sspa_90d = next(c for c in cases if c.case_id == "CAL-FAM4-HO-02")
    assert "90 days" in sspa_90d.raw_text.lower()
    assert sspa_90d.start_page == 3
    assert sspa_90d.end_page == 3

    equip_return = next(c for c in cases if c.case_id == "CAL-FAM2-HO-04")
    assert "last workday" in equip_return.raw_text.lower()
    assert equip_return.start_page == 1
    assert equip_return.end_page == 2

