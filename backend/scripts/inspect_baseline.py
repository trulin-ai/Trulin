import json

with open('backend/scripts/northwind_candidates_baseline_frozen.json', 'r', encoding='utf-8') as f:
    records = json.load(f)

for idx in [1, 8, 26, 73, 74, 92, 93, 105, 120, 130, 137, 181, 225]:
    if idx <= len(records):
        r = records[idx - 1]
        print(f"=== #{idx} ===")
        print(f"Structure: {r.get('evidence_structure')} | Role: {r.get('content_role')}")
        print(f"S: {r.get('subject')} | P: {r.get('predicate')} | O: {r.get('object')}")
        print(f"Conds: {r.get('conditions')}")
        ge = r.get("gate_evaluation", {})
        print(f"Decision: {ge.get('lifecycle_decision')} | Code: {ge.get('decision_code')}")
        print(f"Reason: {ge.get('decision_reason')}")
        print(f"Gates: {ge.get('gates')}")
        print(f"Claim text: {str(r.get('claim_text'))[:90]}")
        print(f"Quote: {str(r.get('verbatim_source_quote'))[:90]}")
        print()

