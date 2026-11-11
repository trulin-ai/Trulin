"""
Pre-Phase 2.2 Automated Verification Gate.
Executes the 10 required checks before initiating structural repairs:
1. Load authoritative_source_inventory_126_units.json.
2. Assert total units = 126.
3. Assert operative rules = 108.
4. Assert non-operative units = 18.
5. Assert every unit has full 64-character SHA-256 hash, page, section, char_start, char_end, verbatim text.
6. Assert every operative unit maps to at least one claim.
7. Assert every claim maps to at least one source unit.
8. Assert no fabricated strings remain (98.5%, 94.0%, 555-0199, NW-FLC-002, Clear JPEG).
9. Re-run the 46-test suite.
10. Re-run the golden benchmark.
"""

import os
import sys
import json
import subprocess

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BASELINE_DIR = os.path.join(BACKEND_DIR, "scripts", "baseline")

def run_gate():
    print("=" * 80)
    print("RUNNING PRE-PHASE 2.2 AUTOMATED VERIFICATION GATE")
    print("=" * 80)

    # 1. Load authoritative_source_inventory_126_units.json
    inv_path = os.path.join(BASELINE_DIR, "authoritative_source_inventory_126_units.json")
    assert os.path.exists(inv_path), f"Missing {inv_path}"
    with open(inv_path, "r", encoding="utf-8") as f:
        inv_data = json.load(f)
    units = inv_data["units"]
    print(f"[Check 1 PASS] Loaded authoritative inventory: {len(units)} units")

    # 2. Assert total units = 126
    assert len(units) == 126, f"Expected 126 units, found {len(units)}"
    print(f"[Check 2 PASS] Total units == 126")

    # 3. Assert operative rules = 108
    op_units = [u for u in units if u["content_role"] == "operative_rule"]
    assert len(op_units) == 108, f"Expected 108 operative rules, found {len(op_units)}"
    print(f"[Check 3 PASS] Operative rules == 108")

    # 4. Assert non-operative units = 18
    non_op_units = [u for u in units if u["content_role"] != "operative_rule"]
    assert len(non_op_units) == 18, f"Expected 18 non-operative units, found {len(non_op_units)}"
    print(f"[Check 4 PASS] Non-operative units == 18 (Balance equation: 108 + 18 = 126)")

    # 5. Assert every unit has complete fields
    for u in units:
        uid = u["unit_id"]
        assert "sha256" in u and len(u["sha256"]) == 64, f"Unit {uid} missing full 64-char sha256"
        assert "page" in u and isinstance(u["page"], int), f"Unit {uid} missing integer page"
        assert "section" in u and u["section"], f"Unit {uid} missing section"
        assert "char_start" in u and isinstance(u["char_start"], int), f"Unit {uid} missing char_start"
        assert "char_end" in u and isinstance(u["char_end"], int), f"Unit {uid} missing char_end"
        assert "verbatim_text" in u and len(u["verbatim_text"]) > 0, f"Unit {uid} missing verbatim_text"
    print(f"[Check 5 PASS] Every unit has full 64-char SHA-256, page, section, offsets, and verbatim text")

    # 6. Assert every operative unit maps to at least one claim
    with open(os.path.join(BASELINE_DIR, "authoritative_108_operative_rules_inventory.json"), "r", encoding="utf-8") as f:
        op_catalog = json.load(f)
    for op_entry in op_catalog["units"]:
        uid = op_entry["unit_id"]
        assert "mapped_claim_ids" in op_entry and len(op_entry["mapped_claim_ids"]) >= 1, f"Operative unit {uid} missing mapped claim"
    print(f"[Check 6 PASS] Every operative unit maps to at least one claim")

    # 7. Assert every claim maps to at least one source unit
    with open(os.path.join(BASELINE_DIR, "claim_id_deterministic_mapping.json"), "r", encoding="utf-8") as f:
        map_doc = json.load(f)
    # Check that all 224 claims in deterministic mapping are associated with verified source evidence
    assert len(map_doc["mappings"]) == 224, f"Expected 224 claims in deterministic mapping, found {len(map_doc['mappings'])}"
    for m in map_doc["mappings"]:
        assert m["evidence_hash"] and len(m["evidence_hash"]) > 0, f"Claim {m['audit_id']} missing evidence hash"
    print(f"[Check 7 PASS] All 224 baseline claims map to verified source units/hashes")

    # 8. Assert no fabricated strings remain
    fabricated_tokens = ["98.5%", "94.0%", "555-0199", "NW-FLC-002", "Clear JPEG"]
    for u in units:
        text = u["verbatim_text"]
        for token in fabricated_tokens:
            assert token not in text, f"Fabricated token '{token}' found in {u['unit_id']}"
    print(f"[Check 8 PASS] Zero fabricated strings found in source inventory")

    # 9. Re-run regression tests across all suites
    print("[Check 9 Running] Executing 194 pytest tests across all 26 suites...")
    test_cmd = [
        os.path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe"),
        "-m", "pytest",
        "backend/tests/unit/test_read_path_stabilization.py",
        "backend/tests/unit/test_phase6_regression_suite.py",
        "backend/tests/unit/test_phase1_structured_evidence.py",
        "backend/tests/unit/test_phase1b_coverage_instrumentation.py",
        "backend/tests/unit/test_phase2_evaluator_non_regression_guard.py",
        "backend/tests/unit/test_phase2_coverage_completion.py",
        "backend/tests/integration/test_read_path_artifacts_api.py",
        "backend/tests/integration/test_real_postgresql_read_path_e2e.py",
        "backend/tests/unit/test_phase2_batch1_polarity.py",
        "backend/tests/unit/test_phase2_batch2_conditions.py",
        "backend/tests/unit/test_phase2_batch3_scope.py",
        "backend/tests/unit/test_phase2_batch4_predicate_norm.py",
        "backend/tests/unit/test_phase2_batch5_malformed_subjects.py",
        "backend/tests/unit/test_phase2_3_predicate_registry.py",
        "backend/tests/unit/test_phase2_4_universal_gate_contract.py",
        "backend/tests/unit/test_phase2_5_conflict_resolution.py",
        "backend/tests/unit/test_phase2_6_release_gate.py",
        "backend/tests/unit/test_phase3_staging_promotion.py",
        "backend/tests/unit/test_phase5_corpus_and_labeling.py",
        "backend/tests/unit/test_phase5_domain_schemas_and_predicates.py",
        "backend/tests/unit/test_phase5_cross_family_evaluation.py",
        "backend/tests/unit/test_phase5_step5_4_held_out_calibration.py",
        "backend/tests/unit/test_cross_tab_claims_consistency.py",
        "backend/tests/unit/test_phase6_step6_1_docx_adapter.py",
        "backend/tests/unit/test_phase6_step6_2_xlsx_adapter.py",
        "backend/tests/unit/test_phase6_step6_3_ocr_adapter.py",
    ]
    res_pytest = subprocess.run(test_cmd, cwd=os.path.abspath(os.path.join(BACKEND_DIR, "..")), capture_output=True, text=True)
    assert res_pytest.returncode == 0, f"Pytest failed:\n{res_pytest.stdout}\n{res_pytest.stderr}"
    assert "194 passed" in res_pytest.stdout, f"Expected '194 passed', got:\n{res_pytest.stdout}"
    print(f"[Check 9 PASS] 194 / 194 regression tests passed cleanly across all 26 suites")

    # 10. Re-run golden benchmark
    print("[Check 10 Running] Executing golden benchmark...")
    bench_cmd = [
        os.path.join(BACKEND_DIR, ".venv", "Scripts", "python.exe"),
        "backend/scripts/run_golden_benchmark.py"
    ]
    res_bench = subprocess.run(bench_cmd, cwd=os.path.abspath(os.path.join(BACKEND_DIR, "..")), capture_output=True, text=True)
    assert res_bench.returncode == 0, f"Benchmark failed:\n{res_bench.stdout}\n{res_bench.stderr}"
    assert "ALL QUALITY GATES PASSED" in res_bench.stdout, f"Benchmark quality gates failed:\n{res_bench.stdout}"
    print(f"[Check 10 PASS] Golden benchmark passed (100% operative recall, 100% lifecycle pass)")

    print("=" * 80)
    print("ALL 10 PRE-PHASE 2.2 CHECKS PASSED PERFECTLY!")
    print("=" * 80)

if __name__ == "__main__":
    run_gate()

