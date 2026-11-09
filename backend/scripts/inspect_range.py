import json

with open('backend/scripts/northwind_candidates_baseline_frozen.json', 'r', encoding='utf-8') as f:
    records = json.load(f)

for idx in range(20, 36):
    r = records[idx - 1]
    print(f"#{idx}: Struct={r.get('evidence_structure')} | Role={r.get('content_role')} | S={r.get('subject')} | P={r.get('predicate')} | O={str(r.get('object'))[:30]} | Text={str(r.get('claim_text'))[:60]}")

