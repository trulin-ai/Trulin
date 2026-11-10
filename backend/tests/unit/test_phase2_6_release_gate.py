"""
Phase 2.6: Regression and Release Gate Unit Tests.

Verifies:
1. CI Gate Enforcement across all 7 gate families + conflict/deduplication invariants.
2. Golden-Set Gating: 66/66 operative recall, 70/70 lifecycle pass, 0 silent upgrades, 0 silent downgrades.
3. Held-Out Evaluation Suite: 35 unseen cases pass; deliberate failure cases fail closed with machine-readable codes.
4. Release-Readiness Scorecard: 100% precision, 100% coverage, 100% recall, 0 unresolved defects, 0 mutations.
5. Staging Promotion Checklist: SHA-256 integrity, span verification, explicit human approval gate.
6. Production Deployment Guardrails & Reversible Rollback Plan.
"""

import json
import os
import pytest
from pathlib import Path

from app.services.gate_contract import (
    GateFailureCode,
    SharedGateRequest,
    SharedGovernanceGateEngine,
)
from app.services.release_gate_orchestrator import (
    ReleaseGateOrchestrator,
    ReleaseDecision,
)

BASELINE_DIR = Path(__file__).resolve().parent.parent.parent / "scripts" / "baseline"


# -----------------------------------------------------------------------------
# 1. CI Gate Enforcement Tests
# -----------------------------------------------------------------------------
def test_ci_gate_enforcement_all_seven_families():
    """Validates that ReleaseGateOrchestrator enforces all 7 gate families and conflict invariants."""
    orchestrator = ReleaseGateOrchestrator()
    ci_res = orchestrator.enforce_ci_gate_families()

    assert ci_res["all_passed"] is True
    assert ci_res["total_claims_evaluated"] == 224
    assert ci_res["status_parity_verified"] is True
    assert ci_res["gate_family_counts"]["family_1_evidence_grounding"] == 224
    assert ci_res["gate_family_counts"]["family_2_predicate_normativity"] == 224
    assert ci_res["gate_family_counts"]["family_3_table_binding"] == 224
    assert ci_res["gate_family_counts"]["family_4_spo_compatibility"] == 224
    assert ci_res["gate_family_counts"]["family_5_polarity_modality"] == 224
    assert ci_res["gate_family_counts"]["family_6_conditions_scope"] == 224
    assert ci_res["gate_family_counts"]["family_7_value_fidelity"] == 224
    assert ci_res["gate_family_counts"]["family_8_conflict_invariants"] == 224


# -----------------------------------------------------------------------------
# 2. Golden-Set Gating Tests
# -----------------------------------------------------------------------------
def test_golden_set_gating_invariants():
    """Validates 66/66 operative recall, 70/70 lifecycle pass, zero silent upgrades, zero silent downgrades."""
    orchestrator = ReleaseGateOrchestrator()
    golden_res = orchestrator.run_golden_set_gating()

    assert golden_res["operative_recall"] == 1.0  # 66 / 66
    assert golden_res["operative_cases_passed"] == 66
    assert golden_res["total_operative_cases"] == 66

    assert golden_res["lifecycle_pass_rate"] == 1.0  # 70 / 70
    assert golden_res["lifecycle_cases_passed"] == 70
    assert golden_res["total_benchmark_cases"] == 70

    assert golden_res["zero_silent_upgrades"] is True
    assert golden_res["zero_silent_downgrades"] is True


# -----------------------------------------------------------------------------
# 3. Held-Out Evaluation Suite (Unseen Cases + Deliberate Fail-Closed Cases)
# -----------------------------------------------------------------------------
def test_held_out_evaluation_unseen_cases():
    """Validates that all unseen held-out multi-document cases pass without golden set contamination."""
    orchestrator = ReleaseGateOrchestrator()
    held_out_res = orchestrator.run_held_out_evaluation_suite()

    assert held_out_res["unseen_cases_evaluated"] >= 35
    assert held_out_res["unseen_cases_passed"] == held_out_res["unseen_cases_evaluated"]
    assert held_out_res["unseen_pass_rate"] == 1.0
    assert held_out_res["golden_set_contamination"] is False
    assert len(held_out_res["case_manifest"]) >= 35
    assert held_out_res["contamination_proof"]["contamination_proof_status"] == "VERIFIED_ZERO_CONTAMINATION"
    assert held_out_res["contamination_proof"]["zero_northwind_claim_ids"] is True
    assert held_out_res["contamination_proof"]["zero_northwind_evidence_spans"] is True
    assert held_out_res["contamination_proof"]["zero_northwind_source_unit_hashes"] is True


def test_held_out_fail_closed_behavior_all_families():
    """Validates that deliberate failure cases across every gate family fail-closed with exact error codes."""
    orchestrator = ReleaseGateOrchestrator()
    fail_res = orchestrator.evaluate_deliberate_failure_suite()

    assert fail_res["total_failure_cases"] == 8
    assert fail_res["total_failed_closed"] == 8
    assert fail_res["fail_closed_rate"] == 1.0

    expected_codes = {
        "F1_missing_evidence": GateFailureCode.ERR_EVIDENCE_MISSING,
        "F2_catch_all_predicate": GateFailureCode.ERR_PREDICATE_CATCH_ALL,
        "F3_wrong_table_binding": GateFailureCode.ERR_TABLE_BINDING_MISMATCH,
        "F4_spo_incompatible": GateFailureCode.ERR_SPO_INCOMPATIBLE,
        "F5_polarity_inversion": GateFailureCode.ERR_POLARITY_INVERSION,
        "F6_lost_condition": GateFailureCode.ERR_CONDITION_LOST,
        "F7_value_mismatch": GateFailureCode.ERR_VALUE_FIDELITY_MISMATCH,
        "F8_silent_upgrade": GateFailureCode.ERR_NO_SILENT_UPGRADE_VIOLATION,
    }

    for case_id, exp_code in expected_codes.items():
        case_result = next((c for c in fail_res["cases"] if c["case_id"] == case_id), None)
        assert case_result is not None, f"Missing failure case {case_id}"
        assert case_result["is_failed_closed"] is True, f"Case {case_id} should have failed closed"
        assert exp_code.value in case_result["failure_codes"], (
            f"Case {case_id} failed with {case_result['failure_codes']}, expected {exp_code.value}"
        )
        if case_id == "F8_silent_upgrade":
            assert GateFailureCode.ERR_EVIDENCE_MISSING.value not in case_result["failure_codes"]


# -----------------------------------------------------------------------------
# 4. Release-Readiness Scorecard Tests
# -----------------------------------------------------------------------------
def test_release_scorecard_metrics():
    """Validates complete release scorecard metrics and explicit GO decision."""
    orchestrator = ReleaseGateOrchestrator()
    scorecard = orchestrator.generate_release_scorecard()

    assert scorecard["certified_precision"] == 1.0  # 140 / 140 = 100%
    assert scorecard["operative_coverage"] == 1.0    # 108 / 108 = 100%
    assert scorecard["golden_recall"] == 1.0         # 66 / 66 = 100%
    assert scorecard["lifecycle_pass_rate"] == 1.0   # 70 / 70 = 100%
    assert scorecard["unresolved_defects_count"] == 0
    assert scorecard["conflict_reconciliation"]["total_conflicts"] == 452
    assert scorecard["conflict_reconciliation"]["total_pairs"] == 24976
    assert scorecard["conflict_reconciliation"]["arithmetic_delta"] == 0
    assert scorecard["provenance_fidelity"]["source_inventory_hash_integrity"]["status"] == "PASS"
    assert scorecard["provenance_fidelity"]["source_inventory_hash_integrity"]["matched"] == 126
    assert scorecard["provenance_fidelity"]["claim_evidence_span_fidelity"]["status"] == "PASS"
    assert scorecard["provenance_fidelity"]["claim_evidence_span_fidelity"]["matched"] == 224
    assert scorecard["provenance_fidelity"]["conflation_prevented"] is True
    assert scorecard["production_safety"]["rows_mutated"] == 0
    assert scorecard["release_decision"] == ReleaseDecision.GO.value


# -----------------------------------------------------------------------------
# 5. Staging Promotion Checklist Tests
# -----------------------------------------------------------------------------
def test_staging_promotion_checklist_integrity():
    """Validates artifact hashes, source verification, span audit, and human authorization lock."""
    orchestrator = ReleaseGateOrchestrator()
    checklist = orchestrator.generate_staging_promotion_checklist()

    assert checklist["all_steps_verified"] is True
    assert len(checklist["verified_artifact_hashes"]) >= 5
    assert checklist["source_inventory_126_verified"] is True
    assert checklist["span_verification_224_verified"] is True
    assert checklist["human_authorization_required"] is True
    assert checklist["human_authorization_status"] == "PENDING_USER_APPROVAL"


# -----------------------------------------------------------------------------
# 6. Production Deployment Guardrails & Reversible Rollback Plan Tests
# -----------------------------------------------------------------------------
def test_production_deployment_guardrails_and_rollback_plan():
    """Validates production write protection, immutable audit logging, and point-in-time rollback plan."""
    orchestrator = ReleaseGateOrchestrator()
    guardrails = orchestrator.generate_production_guardrails()
    rollback = orchestrator.generate_rollback_plan()

    # Guardrails
    assert guardrails["automatic_production_writes_blocked"] is True
    assert guardrails["readonly_transaction_enforced"] is True
    assert guardrails["audit_logging_enabled"] is True

    # Rollback Plan
    assert rollback["rollback_possible"] is True
    assert rollback["prior_staging_baseline"] == "phase2_5_repaired_extraction_v1.json"
    assert len(rollback["restoration_steps"]) >= 3
    assert rollback["zero_partial_writes_verified"] is True
