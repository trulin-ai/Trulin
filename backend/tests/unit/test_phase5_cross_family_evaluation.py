"""
Unit test suite for Phase 5 Step 5.3: Automated Cross-Family Evaluation Pipeline.

Validates:
1. Contamination control audit (zero document / text span leakage across families).
2. Per-family evaluation scorecards meeting tiered targets (FAM-1, FAM-2, FAM-3, FAM-4).
3. Fail-closed negative control suites across all 8 Universal Gate Families.
4. End-to-end cross-family pipeline execution and report persistence.
"""

import json
from pathlib import Path
import pytest

from app.services.cross_family_evaluation_service import (
    CrossFamilyEvaluationService,
)
from app.services.gate_contract import GateFailureCode


@pytest.fixture
def eval_service():
    return CrossFamilyEvaluationService()


def test_cross_family_contamination_control(eval_service):
    """Asserts that no documents or verbatim text spans leak across family boundaries."""
    audit = eval_service.verify_contamination()
    assert audit["status"] == "PASS"
    assert audit["cross_family_document_isolation"] is True
    assert audit["cross_family_text_span_isolation"] is True
    assert len(audit["document_violations"]) == 0
    assert len(audit["span_violations"]) == 0
    assert audit["total_documents_checked"] == 12
    assert audit["total_units_checked"] == 250


def test_per_family_scorecard_targets(eval_service):
    """Asserts that all 4 document families satisfy their approved tiered quality targets."""
    res = eval_service.evaluate_all_families()
    assert res["all_family_targets_passed"] is True
    assert len(res["scorecards"]) == 4

    expected_targets = {
        "FAM-1": {"target_rec": 0.90, "target_life": 0.95},
        "FAM-2": {"target_rec": 0.95, "target_life": 0.98},
        "FAM-3": {"target_rec": 0.95, "target_life": 0.98},
        "FAM-4": {"target_rec": 0.90, "target_life": 0.95},
    }

    total_op = 0
    for sc in res["scorecards"]:
        fid = sc["family_id"]
        assert fid in expected_targets
        assert sc["actual_recall"] >= expected_targets[fid]["target_rec"]
        assert sc["actual_lifecycle"] >= expected_targets[fid]["target_life"]
        assert sc["recall_passed"] is True
        assert sc["lifecycle_passed"] is True
        total_op += sc["total_operative_units"]

    # Assert all 46 operative units accounted for across 4 families
    assert total_op == 46


def test_fail_closed_negative_control_suite(eval_service):
    """Asserts that all 8 negative control injected defects fail closed with exact error codes."""
    res = eval_service.run_negative_control_suite()
    assert res["all_negative_controls_failed_closed"] is True
    assert res["total_cases_evaluated"] == 8
    assert res["failed_closed_count"] == 8

    expected_codes = {
        "NEG-FAM1-01": GateFailureCode.ERR_VALUE_FIDELITY_MISMATCH.value,
        "NEG-FAM1-02": GateFailureCode.ERR_ACTOR_ROLE_INVERSION.value,
        "NEG-FAM2-01": GateFailureCode.ERR_POLARITY_INVERSION.value,
        "NEG-FAM2-02": GateFailureCode.ERR_CONDITION_LOST.value,
        "NEG-FAM3-01": GateFailureCode.ERR_TABLE_BINDING_MISMATCH.value,
        "NEG-FAM3-02": GateFailureCode.ERR_EVIDENCE_MISSING.value,
        "NEG-FAM4-01": GateFailureCode.ERR_PREDICATE_CATCH_ALL.value,
        "NEG-FAM4-02": GateFailureCode.ERR_NO_SILENT_UPGRADE_VIOLATION.value,
    }

    for case in res["cases"]:
        cid = case["case_id"]
        assert cid in expected_codes
        assert case["gate_passed"] is False
        assert case["failed_closed"] is True
        assert case["expected_error_code"] == expected_codes[cid]
        assert expected_codes[cid] in case["actual_errors"]


def test_full_pipeline_orchestration(eval_service):
    """Asserts that the complete cross-family evaluation pipeline executes cleanly and writes report."""
    pipeline_res = eval_service.run_full_pipeline()
    assert pipeline_res["pipeline_status"] == "PASS"
    assert pipeline_res["contamination_audit"]["status"] == "PASS"
    assert pipeline_res["family_evaluations"]["all_family_targets_passed"] is True
    assert pipeline_res["negative_control_suite"]["all_negative_controls_failed_closed"] is True

    # Verify report file written to disk
    report_file = eval_service.baseline_dir / "phase5_cross_family_evaluation_report.json"
    assert report_file.exists()
    with open(report_file, "r", encoding="utf-8") as f:
        saved_data = json.load(f)
    assert saved_data["pipeline_status"] == "PASS"

