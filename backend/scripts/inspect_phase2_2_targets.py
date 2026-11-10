import csv

with open('backend/scripts/baseline/claims_224_defect_classification_master.csv', 'r', encoding='utf-8') as f:
    rows = list(csv.DictReader(f))

target_ids = [19, 43, 66, 67, 78, 91, 92, 132, 224]
for r in rows:
    aid = int(r.get('audit_id', 0))
    if aid in target_ids:
        print(f"Audit #{aid:3d} | Label: {r.get('label'):10s} | Defect: {r.get('defect_type'):15s} | Subtype: {r.get('defect_subtype'):15s} | Subj: {r.get('corrected_subject'):30s} | Pred: {r.get('corrected_predicate'):25s} | Missing Conds: {r.get('missing_conditions')}")
