"""
Phase 2.3: Predicate Registry Cleanup and Type Compatibility Execution Script.
Executes:
1. Complete predicate inventory and classification audit across all 224 staging claims.
2. Eliminates all catch-all and deprecated predicates (has_validity_rule, has_summary, generic has_refund_eligibility, cancel, scheduled, appeal).
3. Attaches typed temporal/operational predicates.
4. Validates 100% SPO compatibility under TypeCompatibilityMatrix.
5. Saves:
   - backend/scripts/baseline/phase2_3_predicate_audit.json
   - backend/scripts/baseline/phase2_3_repaired_extraction_v1.json
   - backend/scripts/baseline/phase2_3_claim_level_diff.json
"""

import json
import os
import sys

# Ensure backend root is on sys.path
BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BACKEND_DIR)

from app.extraction.predicate_registry import CanonicalPredicate, PredicateRegistry
from app.extraction.type_compatibility import EntityType, TypeCompatibilityMatrix

BASELINE_DIR = os.path.join(BACKEND_DIR, "scripts", "baseline")

# Specific predicate cleanups for Phase 2.3
PREDICATE_CLEANUPS = {
    2: {
        "predicate": "has_return_window",
        "reason": "Specialized from has_summary to typed temporal return_window"
    },
    3: {
        "predicate": "has_posting_duration",
        "reason": "Specialized from has_summary to typed temporal posting_duration"
    },
    4: {
        "predicate": "has_return_shipping_rule",
        "reason": "Specialized from has_summary to typed return_shipping_rule"
    },
    5: {
        "predicate": "has_fee_rule",
        "reason": "Specialized from has_summary to typed fee_rule"
    },
    6: {
        "predicate": "cannot_be_returned_or_refunded",
        "reason": "Specialized from has_summary to canonical exclusion predicate"
    },
    12: {
        "subject": "Final Sale items",
        "predicate": "cannot_be_returned_or_refunded",
        "object": "cannot be returned",
        "reason": "Specialized generic has_refund_eligibility to canonical prohibition"
    },
    21: {
        "predicate": "has_usage_limit",
        "reason": "Specialized generic has_refund_eligibility to typed usage_limit"
    },
    24: {
        "predicate": "has_partial_refund_rule",
        "reason": "Specialized catch-all has_validity_rule to typed partial_refund_rule"
    },
    31: {
        "subject": "Washed, altered or stained items",
        "predicate": "cannot_be_returned_or_refunded",
        "reason": "Specialized generic has_refund_eligibility to canonical prohibition"
    },
    37: {
        "subject": "Custom products",
        "predicate": "cannot_be_returned_or_refunded",
        "object": "cannot be resold",
        "reason": "Specialized catch-all has_validity_rule to canonical prohibition"
    },
    94: {
        "predicate": "has_scheduling_requirement",
        "reason": "Specialized deprecated verb 'scheduled' to typed scheduling_requirement"
    },
    97: {
        "predicate": "has_drop_off_options",
        "reason": "Specialized catch-all has_validity_rule to typed drop_off_options"
    },
    108: {
        "subject": "Shipped order",
        "predicate": "must_be_handled_as_return",
        "reason": "Specialized generic has_refund_eligibility to typed operational requirement"
    },
    118: {
        "predicate": "may_cancel_order",
        "reason": "Specialized deprecated verb 'cancel' to canonical provider permission"
    },
    127: {
        "predicate": "has_trial_refund_window",
        "reason": "Specialized generic has_refund_window to typed trial_refund_window"
    },
    129: {
        "predicate": "cannot_be_refunded_for_cash",
        "reason": "Specialized generic has_refund_eligibility to canonical cash prohibition"
    },
    134: {
        "predicate": "has_purchaser_notification_policy",
        "reason": "Specialized generic has_refund_eligibility to typed notification policy"
    },
    152: {
        "predicate": "has_third_party_policy_rule",
        "reason": "Specialized generic has_refund_eligibility to typed marketplace seller rule"
    },
    175: {
        "predicate": "has_refusal_refund_rule",
        "reason": "Specialized generic has_refund_eligibility to typed customs refusal rule"
    },
    198: {
        "predicate": "may_appeal_restrictions",
        "reason": "Specialized deprecated verb 'appeal' to canonical customer permission"
    },
    199: {
        "predicate": "has_retention_policy",
        "reason": "Specialized generic has_refund_eligibility to typed data retention policy"
    },
    223: {
        "subject": "Perishable goods past 14 days from delivery",
        "predicate": "cannot_be_returned_or_refunded",
        "reason": "Specialized generic has_refund_eligibility to canonical prohibition"
    }
}


def run_phase2_3():
    print("=" * 80)
    print("EXECUTING PHASE 2.3: PREDICATE REGISTRY CLEANUP & TYPE COMPATIBILITY")
    print("=" * 80)

    # 1. Load Phase 2.2c staging dataset
    in_path = os.path.join(BASELINE_DIR, "phase2_2c_repaired_extraction_v1.json")
    with open(in_path, "r", encoding="utf-8") as f:
        claims = json.load(f)
    print(f"Loaded {len(claims)} claims from {in_path}")

    # 2. Inventory and Audit all predicates before modification
    before_audit = {}
    for c in claims:
        aid = c["number"]
        pred = c["predicate"]
        p_class = PredicateRegistry.get_predicate_class(pred)
        before_audit[aid] = {
            "audit_id": aid,
            "subject": c["subject"],
            "predicate": pred,
            "object": c["object"],
            "classification_before": p_class,
            "is_catch_all": p_class == "catch_all",
            "is_deprecated": p_class == "deprecated"
        }

    # 3. Apply targeted predicate cleanups
    repaired_claims = []
    diff_records = []
    after_audit = {}

    for c in claims:
        aid = c["number"]
        orig_c = dict(c)
        
        new_c = dict(c)
        if aid in PREDICATE_CLEANUPS:
            cleanup = PREDICATE_CLEANUPS[aid]
            if "subject" in cleanup:
                new_c["subject"] = cleanup["subject"]
            if "predicate" in cleanup:
                new_c["predicate"] = cleanup["predicate"]
            if "object" in cleanup:
                new_c["object"] = cleanup["object"]
            new_c["predicate_repair_reason"] = cleanup["reason"]

        # Validate SPO Compatibility
        compat_res = TypeCompatibilityMatrix.evaluate_compatibility(
            subject=new_c["subject"],
            predicate=new_c["predicate"],
            object_text=str(new_c.get("object", "")),
            clause_text=new_c.get("claim_text", "")
        )
        assert compat_res.is_compatible, f"Claim #{aid} failed SPO compatibility: {compat_res.reason}"

        # Validate Predicate is strictly Canonical
        final_class = PredicateRegistry.get_predicate_class(new_c["predicate"])
        assert final_class == "canonical", f"Claim #{aid} predicate '{new_c['predicate']}' is not canonical! Got: {final_class}"

        new_c["spo_compatibility"] = {
            "is_compatible": compat_res.is_compatible,
            "subject_category": compat_res.subject_category.value if hasattr(compat_res.subject_category, "value") else str(compat_res.subject_category),
            "predicate_family": compat_res.predicate_family
        }
        new_c["predicate_classification"] = final_class

        repaired_claims.append(new_c)

        # Audit record
        after_audit[aid] = {
            **before_audit[aid],
            "predicate_after": new_c["predicate"],
            "classification_after": final_class,
            "subject_after": new_c["subject"],
            "object_after": new_c["object"],
            "repair_applied": aid in PREDICATE_CLEANUPS,
            "repair_reason": PREDICATE_CLEANUPS.get(aid, {}).get("reason")
        }

        # Check diff vs Phase 2.2c
        changed = (
            orig_c["subject"] != new_c["subject"] or
            orig_c["predicate"] != new_c["predicate"] or
            orig_c["object"] != new_c["object"]
        )
        if changed:
            diff_records.append({
                "audit_id": aid,
                "claim_id": c.get("id"),
                "source_unit_id": c.get("source_unit_id"),
                "before": {
                    "subject": orig_c["subject"],
                    "predicate": orig_c["predicate"],
                    "object": orig_c["object"],
                    "predicate_class": before_audit[aid]["classification_before"]
                },
                "after": {
                    "subject": new_c["subject"],
                    "predicate": new_c["predicate"],
                    "object": new_c["object"],
                    "predicate_class": final_class,
                    "reason": PREDICATE_CLEANUPS[aid]["reason"]
                }
            })

    print(f"\n[Phase 2.3 Verification] Total claims modified: {len(diff_records)}")
    print(f"[Phase 2.3 Verification] Unchanged claims: {len(repaired_claims) - len(diff_records)}")

    # Assert zero catch-alls remain in entire dataset
    for c in repaired_claims:
        p = c["predicate"]
        p_class = PredicateRegistry.get_predicate_class(p)
        assert p_class == "canonical", f"Defect escape: Claim #{c['number']} predicate '{p}' is {p_class}"

    print("[Phase 2.3 PASS] Exactly 0 catch-all, deprecated, or invalid predicates remain across all 224 claims!")
    print("[Phase 2.3 PASS] 100% of claims pass TypeCompatibilityMatrix evaluation!")

    # Save deliverables
    audit_path = os.path.join(BASELINE_DIR, "phase2_3_predicate_audit.json")
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump(after_audit, f, indent=2)
    print(f"[Saved Deliverable] {audit_path}")

    claims_out_path = os.path.join(BASELINE_DIR, "phase2_3_repaired_extraction_v1.json")
    with open(claims_out_path, "w", encoding="utf-8") as f:
        json.dump(repaired_claims, f, indent=2)
    print(f"[Saved Deliverable] {claims_out_path}")

    diff_out_path = os.path.join(BASELINE_DIR, "phase2_3_claim_level_diff.json")
    with open(diff_out_path, "w", encoding="utf-8") as f:
        json.dump(diff_records, f, indent=2)
    print(f"[Saved Deliverable] {diff_out_path}")


if __name__ == "__main__":
    run_phase2_3()

