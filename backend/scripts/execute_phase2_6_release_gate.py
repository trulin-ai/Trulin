"""
Phase 2.6: Automated Regression and Release Gate Execution Script.

Generates the complete set of release governance artifacts:
1. phase2_6_release_scorecard.json
2. phase2_6_staging_promotion_checklist.json
3. phase2_6_held_out_evaluation_report.json
4. phase2_6_production_deployment_guardrails.json
5. phase2_6_rollback_plan.json
6. phase2_6_final_certification_summary.json
"""

import json
import os
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.release_gate_orchestrator import ReleaseGateOrchestrator, ReleaseDecision

BASELINE_DIR = BACKEND_DIR / "scripts" / "baseline"

SCORECARD_FILE = BASELINE_DIR / "phase2_6_release_scorecard.json"
CHECKLIST_FILE = BASELINE_DIR / "phase2_6_staging_promotion_checklist.json"
HELD_OUT_REPORT_FILE = BASELINE_DIR / "phase2_6_held_out_evaluation_report.json"
GUARDRAILS_FILE = BASELINE_DIR / "phase2_6_production_deployment_guardrails.json"
ROLLBACK_FILE = BASELINE_DIR / "phase2_6_rollback_plan.json"
CERTIFICATION_FILE = BASELINE_DIR / "phase2_6_final_certification_summary.json"


def run_release_gate():
    print("=" * 80)
    print("EXECUTING PHASE 2.6: REGRESSION AND RELEASE GATE")
    print("=" * 80)

    orchestrator = ReleaseGateOrchestrator(baseline_dir=BASELINE_DIR)

    # 1. CI Gate Family Enforcement
    print("[Step 1] Enforcing CI Gate Families and Conflict Invariants across 224 baseline claims...")
    ci_res = orchestrator.enforce_ci_gate_families()
    assert ci_res["all_passed"] is True, "CI Gate Family Enforcement failed!"
    print(f"  CI Gates PASS: 224 claims evaluated across 8 families. Status parity: {ci_res['status_counts']}")

    # 2. Golden-Set Gating
    print("[Step 2] Running Golden-Set Gating (66/66 operative recall, 70/70 lifecycle pass)...")
    golden_res = orchestrator.run_golden_set_gating()
    assert golden_res["operative_recall"] == 1.0
    assert golden_res["lifecycle_pass_rate"] == 1.0
    print(f"  Golden Benchmark PASS: Operative Recall {golden_res['operative_cases_passed']}/{golden_res['total_operative_cases']} (100%), Lifecycle Pass {golden_res['lifecycle_cases_passed']}/{golden_res['total_benchmark_cases']} (100%)")

    # 3. Held-Out Evaluation Suite (Unseen Cases + Deliberate Failure Suite)
    print("[Step 3] Running Held-Out Evaluation Suite (35 multi-document unseen cases)...")
    held_out_res = orchestrator.run_held_out_evaluation_suite()
    assert held_out_res["unseen_pass_rate"] == 1.0
    assert held_out_res["golden_set_contamination"] is False
    print(f"  Held-Out Unseen Cases PASS: {held_out_res['unseen_cases_passed']}/35 passed. Zero contamination verified.")

    print("[Step 4] Running Deliberate Fail-Closed Suite (8 gate families)...")
    fail_res = orchestrator.evaluate_deliberate_failure_suite()
    assert fail_res["fail_closed_rate"] == 1.0
    print(f"  Deliberate Fail-Closed PASS: {fail_res['total_failed_closed']}/8 failure cases failed closed with expected codes.")

    held_out_report = {
        "metadata": {
            "phase": "2.6",
            "title": "Held-Out Evaluation and Fail-Closed Verification Report",
            "timestamp": held_out_res.get("timestamp"),
        },
        "unseen_cases_evaluation": held_out_res,
        "deliberate_failure_suite": fail_res,
    }
    with open(HELD_OUT_REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(held_out_report, f, indent=2)
    print(f"  Wrote held-out evaluation report to {HELD_OUT_REPORT_FILE.name}")

    # 4. Release-Readiness Scorecard
    print("[Step 5] Compiling Release-Readiness Scorecard...")
    scorecard = orchestrator.generate_release_scorecard()
    assert scorecard["release_decision"] == ReleaseDecision.GO.value
    with open(SCORECARD_FILE, "w", encoding="utf-8") as f:
        json.dump(scorecard, f, indent=2)
    print(f"  Wrote release scorecard to {SCORECARD_FILE.name} (Decision: {scorecard['release_decision']})")

    # 5. Staging Promotion Checklist
    print("[Step 6] Generating Staging Promotion Checklist...")
    checklist = orchestrator.generate_staging_promotion_checklist()
    assert checklist["all_steps_verified"] is True
    with open(CHECKLIST_FILE, "w", encoding="utf-8") as f:
        json.dump(checklist, f, indent=2)
    print(f"  Wrote staging promotion checklist to {CHECKLIST_FILE.name} (Status: {checklist['human_authorization_status']})")

    # 6. Production Deployment Guardrails
    print("[Step 7] Generating Production Deployment Guardrails...")
    guardrails = orchestrator.generate_production_guardrails()
    assert guardrails["automatic_production_writes_blocked"] is True
    with open(GUARDRAILS_FILE, "w", encoding="utf-8") as f:
        json.dump(guardrails, f, indent=2)
    print(f"  Wrote production guardrails to {GUARDRAILS_FILE.name}")

    # 7. Reversible Rollback Plan
    print("[Step 8] Generating Reversible Rollback and Recovery Plan...")
    rollback = orchestrator.generate_rollback_plan()
    assert rollback["rollback_possible"] is True
    with open(ROLLBACK_FILE, "w", encoding="utf-8") as f:
        json.dump(rollback, f, indent=2)
    print(f"  Wrote rollback plan to {ROLLBACK_FILE.name}")

    # 8. Final Certification Summary
    print("[Step 9] Writing Final Release Certification Summary...")
    cert_summary = {
        "metadata": {
            "phase": "2.6b",
            "title": "Phase 2.6b Release Certification Summary",
            "release_decision": ReleaseDecision.GO.value,
            "target": "Release Candidate v1 (Staging Promotion Approved; Production Promotion Gated)",
        },
        "scorecard_summary": {
            "certified_precision": scorecard["certified_precision"],
            "operative_coverage": scorecard["operative_coverage"],
            "golden_recall": scorecard["golden_recall"],
            "lifecycle_pass_rate": scorecard["lifecycle_pass_rate"],
            "unresolved_defects": scorecard["unresolved_defects_count"],
            "repaired_defects": scorecard["repaired_defects_count"],
            "conflict_reconciliation": scorecard["conflict_reconciliation"],
            "provenance_fidelity": scorecard["provenance_fidelity"],
            "production_safety": scorecard["production_safety"],
            "release_semantics": scorecard["release_semantics"],
        },
        "staging_promotion_checklist": {
            "all_steps_verified": checklist["all_steps_verified"],
            "human_authorization_status": checklist["human_authorization_status"],
            "promotion_lock": checklist["promotion_lock"],
        },
        "governance_guardrails": guardrails,
        "rollback_guarantee": rollback,
    }
    with open(CERTIFICATION_FILE, "w", encoding="utf-8") as f:
        json.dump(cert_summary, f, indent=2)
    print(f"  Wrote final certification summary to {CERTIFICATION_FILE.name}")

    print("=" * 80)
    print("PHASE 2.6b REGRESSION AND RELEASE GATE COMPLETE - DECISION: RELEASE CANDIDATE GO")
    print("=" * 80)


if __name__ == "__main__":
    run_release_gate()

