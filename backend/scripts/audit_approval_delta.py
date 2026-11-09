import json
import os
import sys

def generate_approval_delta_audit():
    with open('backend/scripts/northwind_candidates_baseline_frozen.json', 'r', encoding='utf-8') as f:
        baseline = json.load(f)
    with open('backend/scripts/northwind_candidates_export.json', 'r', encoding='utf-8') as f:
        exported = json.load(f)

    # 1. Inspect all 10 transition candidates (from reject/review -> approve)
    transition_indices = [37, 38, 78, 94, 99, 130, 141, 159, 206, 210]

    def render_plain_assertion(cand):
        s = cand.get('subject') or 'UNKNOWN_SUBJECT'
        p = cand.get('predicate') or 'UNKNOWN_PREDICATE'
        o = cand.get('object') or ''
        m = cand.get('modality') or 'OBLIGATION'
        conds = cand.get('conditions') or []
        cond_str = f" [CONDITION: {'; '.join(str(c) for c in conds)}]" if conds else ""
        return f"{s} [{m}] {p} -> {o}{cond_str}"

    audit_records = []

    # Map all candidates
    base_map = {c.get('baseline_order_index', i + 1): c for i, c in enumerate(baseline)}
    exp_map = {c.get('baseline_order_index', i + 1): c for i, c in enumerate(exported)}

    all_target_indices = sorted(set(
        transition_indices +
        [68, 69, 78, 94, 99, 134, 178, 124, 125, 126, 127, 128, 129, 104, 105, 108, 109, 92, 93, 2, 3, 4, 5, 6, 13, 14, 15, 16, 17, 180, 42, 43, 45, 46, 47, 48, 49, 50, 51, 52, 229]
    ))

    for idx in all_target_indices:
        b = base_map.get(idx, {})
        e = exp_map.get(idx, {})

        b_dec = b.get('gate_evaluation', {}).get('lifecycle_decision')
        e_dec = e.get('gate_evaluation', {}).get('lifecycle_decision')
        b_code = b.get('gate_evaluation', {}).get('decision_code')
        e_code = e.get('gate_evaluation', {}).get('decision_code')

        plain_baseline = render_plain_assertion(b)
        plain_export = render_plain_assertion(e)

        quote = e.get('verbatim_source_quote') or b.get('verbatim_source_quote') or ''

        # Classify bucket
        if idx in [130, 92, 93]:
            category = "Bucket 2: Correct semantic revision"
        elif idx in [210]:
            category = "Bucket 1: Correct evidence-aware recovery"
        elif idx in [37, 38, 78, 94, 99, 141, 159, 206]:
            category = "Bucket 3: Approval of an unchanged incorrect claim (transitioned, MUST BLOCK)"
        elif idx in [68, 69, 134, 178, 124, 125, 126, 127, 128, 129, 104, 105]:
            category = "Bucket 3: Approval of an unchanged incorrect claim (pre-existing, MUST BLOCK)"
        elif idx in [43, 46, 48, 50, 52, 180]:
            category = "Bucket 6: Operative rule incorrectly rejected as non-rule / fragment"
        elif idx in [42, 44, 45, 47, 49, 51, 229]:
            category = "Bucket 4: Reclassification of non-executable context"
        elif idx in [2, 3, 4, 5, 6]:
            category = "Bucket 7: Legitimate review queue item (unconstrained summary predicate)"
        elif idx in [13, 14, 15, 16, 17]:
            category = "Bucket 1: Correct evidence-aware recovery (table return window)"
        else:
            category = "Other"

        audit_records.append({
            "baseline_order_index": idx,
            "category": category,
            "source_evidence_quote": quote,
            "baseline": {
                "candidate_id": b.get("candidate_id"),
                "subject": b.get("subject"),
                "predicate": b.get("predicate"),
                "object": b.get("object"),
                "conditions": b.get("conditions"),
                "lifecycle_decision": b_dec,
                "decision_code": b_code,
                "plain_assertion": plain_baseline,
            },
            "exported": {
                "candidate_id": e.get("candidate_id"),
                "subject": e.get("subject"),
                "predicate": e.get("predicate"),
                "object": e.get("object"),
                "conditions": e.get("conditions"),
                "lifecycle_decision": e_dec,
                "decision_code": e_code,
                "plain_assertion": plain_export,
            },
            "transition": f"{b_dec} -> {e_dec}",
            "reasons": e.get("gate_evaluation", {}).get("decision_reason") or b.get("gate_evaluation", {}).get("decision_reason")
        })

    with open('backend/scripts/approval_delta_audit_report.json', 'w', encoding='utf-8') as f:
        json.dump(audit_records, f, indent=2)

    print(f"Generated audit report for {len(audit_records)} candidates in backend/scripts/approval_delta_audit_report.json.")

if __name__ == '__main__':
    generate_approval_delta_audit()
