import json
import os
import sys

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
BASELINE_JSON = os.path.join(BACKEND_DIR, "scripts", "northwind_candidates_baseline_frozen.json")
EXPORT_JSON = os.path.join(BACKEND_DIR, "scripts", "northwind_candidates_export.json")
REPORT_JSON = os.path.join(BACKEND_DIR, "scripts", "candidate_reconciliation_report.json")

def main():
    with open(BASELINE_JSON, "r", encoding="utf-8") as f:
        baseline = json.load(f)
    with open(EXPORT_JSON, "r", encoding="utf-8") as f:
        exported = json.load(f)

    print(f"Total Baseline Candidates: {len(baseline)}")
    print(f"Total Export Candidates: {len(exported)}")

    base_by_quote = {}
    for i, c in enumerate(baseline):
        q = (c.get("verbatim_source_quote") or "").strip()
        base_by_quote.setdefault(q, []).append((i + 1, c))

    exp_by_quote = {}
    for i, c in enumerate(exported):
        q = (c.get("verbatim_source_quote") or "").strip()
        exp_by_quote.setdefault(q, []).append((i + 1, c))

    retained_exact = []
    revised_semantics = []
    newly_recovered = []

    for q, exp_list in exp_by_quote.items():
        if q in base_by_quote:
            base_list = base_by_quote[q]
            for (e_idx, ec) in exp_list:
                matched_bc = None
                for (b_idx, bc) in base_list:
                    if bc.get("predicate") == ec.get("predicate") and bc.get("subject") == ec.get("subject"):
                        matched_bc = (b_idx, bc)
                        break
                if matched_bc:
                    retained_exact.append({
                        "baseline_order": matched_bc[0],
                        "export_order": e_idx,
                        "subject": ec.get("subject"),
                        "predicate": ec.get("predicate"),
                        "verbatim_source_quote": q[:80],
                        "decision": ec.get("gate_evaluation", {}).get("lifecycle_decision"),
                    })
                else:
                    revised_semantics.append({
                        "baseline_order": base_list[0][0],
                        "export_order": e_idx,
                        "before": {
                            "subject": base_list[0][1].get("subject"),
                            "modality": base_list[0][1].get("modality"),
                            "predicate": base_list[0][1].get("predicate"),
                            "object": str(base_list[0][1].get("object"))[:60],
                        },
                        "after": {
                            "subject": ec.get("subject"),
                            "modality": ec.get("modality"),
                            "predicate": ec.get("predicate"),
                            "object": str(ec.get("object"))[:60],
                        },
                        "verbatim_source_quote": q[:80],
                        "decision": ec.get("gate_evaluation", {}).get("lifecycle_decision"),
                    })
        else:
            for (e_idx, ec) in exp_list:
                newly_recovered.append({
                    "export_order": e_idx,
                    "subject": ec.get("subject"),
                    "predicate": ec.get("predicate"),
                    "object": str(ec.get("object"))[:60],
                    "verbatim_source_quote": q[:80],
                    "decision": ec.get("gate_evaluation", {}).get("lifecycle_decision"),
                })

    reconciliation_summary = {
        "baseline_candidate_count": len(baseline),
        "exported_candidate_count": len(exported),
        "retained_exact_count": len(retained_exact),
        "revised_semantics_count": len(revised_semantics),
        "newly_recovered_count": len(newly_recovered),
        "retained_exact": retained_exact,
        "revised_semantics": revised_semantics,
        "newly_recovered": newly_recovered,
    }

    with open(REPORT_JSON, "w", encoding="utf-8") as f:
        json.dump(reconciliation_summary, f, indent=2)

    print(f"Retained Exact: {len(retained_exact)}")
    print(f"Semantically Revised / Repaired: {len(revised_semantics)}")
    print(f"Newly Discovered / Recovered: {len(newly_recovered)}")
    print(f"Reconciliation Report written to: {REPORT_JSON}")

if __name__ == "__main__":
    main()

