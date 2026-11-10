"""
Phase 2.2c Generator: Produces phase2_2c_claim_level_diff.json and phase2_2c_repaired_extraction_v1.json.
Embeds corrected locators, exact verbatim evidence spans, and explicit audit trail.
"""

import json
import os

BASELINE_DIR = "backend/scripts/baseline"

# 1. Load locator audit containing the byte-for-byte verified locators
locator_audit_path = os.path.join(BASELINE_DIR, "phase2_2c_locator_audit.json")
with open(locator_audit_path, "r", encoding="utf-8") as f:
    locator_audit = json.load(f)

# 2. Load Phase 2.2 repaired extraction
repaired_path = os.path.join(BASELINE_DIR, "phase2_2_repaired_extraction_v1.json")
with open(repaired_path, "r", encoding="utf-8") as f:
    repaired_claims = json.load(f)

# 3. Load frozen baseline
frozen_path = os.path.join(BASELINE_DIR, "db_224_claims_frozen.json")
with open(frozen_path, "r", encoding="utf-8") as f:
    frozen_claims = json.load(f)
frozen_by_id = {c["number"]: c for c in frozen_claims}

# 4. Load master CSV defect classification
import csv
master_csv_path = os.path.join(BASELINE_DIR, "claims_224_defect_classification_master.csv")
master_by_id = {}
with open(master_csv_path, "r", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        master_by_id[int(row["audit_id"])] = row

corrected_repaired_claims = []
corrected_diff_records = []

for c in repaired_claims:
    aid = c["number"]
    fc = frozen_by_id[aid]
    
    if aid in [int(k) for k in locator_audit.keys()]:
        loc_info = locator_audit[str(aid)]
        
        # Build corrected locator
        corrected_locator = {
            "page": loc_info["page"],
            "section": loc_info["section"],
            "table_id": loc_info["table_id"],
            "row_id": loc_info["row_id"],
            "start": loc_info["char_start"],
            "end": loc_info["char_end"],
            "source_unit_id": loc_info["source_unit_id"],
        }
        
        # Build updated claim object
        updated_claim = {
            **c,
            "locators": [corrected_locator],
            "evidence_quotes": [loc_info["clean_span"]],
            "source_unit_id": loc_info["source_unit_id"],
        }
        corrected_repaired_claims.append(updated_claim)
        
        # Build corrected diff record
        m_row = master_by_id.get(aid, {})
        old_loc = fc.get("locators", [{}])[0] if fc.get("locators") else {}
        
        old_span = fc.get("evidence_quotes", [fc.get("claim_text")])[0] if fc.get("evidence_quotes") else fc.get("claim_text")
        
        diff_record = {
            "audit_id": aid,
            "claim_id": c.get("id"),
            "source_unit_id": loc_info["source_unit_id"],
            "defect_type": m_row.get("defect_type"),
            "defect_subtype": m_row.get("defect_subtype"),
            "repair_rule": c.get("repair_rule"),
            "locator_audit": {
                "old_locator": {
                    "page": old_loc.get("page"),
                    "section": old_loc.get("section"),
                    "start": old_loc.get("start"),
                    "end": old_loc.get("end"),
                    "source_unit_id": m_row.get("source_unit_id")
                },
                "corrected_locator": corrected_locator,
                "old_span": old_span,
                "corrected_span": loc_info["clean_span"],
                "verification_result": "BYTE_FOR_BYTE_VERIFIED",
                "char_offsets_in_pdf": f"{loc_info['char_start']}:{loc_info['char_end']}"
            },
            "before": {
                "subject": fc.get("subject"),
                "predicate": fc.get("predicate"),
                "object": fc.get("object"),
                "modality": fc.get("modality"),
                "conditions": fc.get("conditions"),
                "status": fc.get("status"),
                "evidence_span": old_span
            },
            "after": {
                "subject": c.get("subject"),
                "predicate": c.get("predicate"),
                "object": c.get("object"),
                "modality": c.get("modality"),
                "conditions": c.get("conditions"),
                "status": c.get("status"),
                "evidence_span": loc_info["clean_span"]
            }
        }
        corrected_diff_records.append(diff_record)
    else:
        # Untargeted claims preserve their baseline properties
        corrected_repaired_claims.append(c)

print(f"Generated {len(corrected_diff_records)} corrected diff records.")
print(f"Total claims in corrected staging extraction: {len(corrected_repaired_claims)}")

# Save phase2_2c_repaired_extraction_v1.json
out_claims_path = os.path.join(BASELINE_DIR, "phase2_2c_repaired_extraction_v1.json")
with open(out_claims_path, "w", encoding="utf-8") as f:
    json.dump(corrected_repaired_claims, f, indent=2)
print(f"Saved: {out_claims_path}")

# Save phase2_2c_claim_level_diff.json
out_diff_path = os.path.join(BASELINE_DIR, "phase2_2c_claim_level_diff.json")
with open(out_diff_path, "w", encoding="utf-8") as f:
    json.dump(corrected_diff_records, f, indent=2)
print(f"Saved: {out_diff_path}")

