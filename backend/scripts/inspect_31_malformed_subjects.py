import csv
import json

with open("backend/scripts/baseline/claims_224_defect_classification_master.csv", "r", encoding="utf-8") as f:
    reader = list(csv.DictReader(f))

malformed = [r for r in reader if "MALFORMED_SUBJECT" in r.get("defect_type", "") or r.get("label") == "wrong_subject"]
print(f"Total malformed subject claims: {len(malformed)}")

with open("backend/scripts/baseline/db_224_claims_frozen.json", "r", encoding="utf-8") as f:
    frozen = json.load(f)
frozen_by_num = {c["number"]: c for c in frozen}

for r in malformed:
    aid = int(r["audit_id"])
    fc = frozen_by_num.get(aid, {})
    orig_s = fc.get("subject", "")
    corr_s = r.get("corrected_subject", "")
    subtype = r.get("defect_subtype", "")
    unit_id = r.get("source_unit_id", "")
    text = fc.get("claim_text", "")[:60]
    print(f"Audit #{aid:3d} | Orig: {orig_s!r:<25} | Corrected: {corr_s!r:<30} | Subtype: {subtype:<25} | Unit: {unit_id} | Text: {text}")

