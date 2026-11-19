import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.services.cross_family_evaluation_service import CrossFamilyEvaluationService

def main():
    svc = CrossFamilyEvaluationService()
    res = svc.run_full_pipeline()
    print("Pipeline Status:", res["pipeline_status"])
    print("Contamination Status:", res["contamination_audit"]["status"])
    print("Family Targets Passed:", res["family_evaluations"]["all_family_targets_passed"])
    print("Negative Controls Failed Closed:", res["negative_control_suite"]["all_negative_controls_failed_closed"])
    print("\n--- Family Scorecards ---")
    for sc in res["family_evaluations"]["scorecards"]:
        fid = sc["family_id"]
        rec = sc["actual_recall"] * 100
        trec = sc["target_recall"] * 100
        life = sc["actual_lifecycle"] * 100
        tlife = sc["target_lifecycle"] * 100
        p = sc["recall_passed"] and sc["lifecycle_passed"]
        print(f"  [{fid}] Recall: {rec:.1f}% (target >= {trec:.0f}%) | Lifecycle: {life:.1f}% (target >= {tlife:.0f}%) | Status: {'PASS' if p else 'FAIL'}")

    print("\n--- Negative Control Injected Defects ---")
    for nc in res["negative_control_suite"]["cases"]:
        cid = nc["case_id"]
        fc = nc["failed_closed"]
        exp = nc["expected_error_code"]
        act = nc["actual_errors"]
        print(f"  [{cid}] Fail-Closed: {fc} | Expected: {exp} | Actual Errors: {act}")

if __name__ == "__main__":
    main()

