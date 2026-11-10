"""
Phase 2.2c Provenance and Locator Correction Engine.
Audits all 38 changed claims against docs/Northwind_Refund_Policy_Handbook.pdf.
Extracts:
- exact verbatim evidence span (100% byte-for-byte in source text)
- exact page
- exact section name / number
- table ID and row ID (where applicable)
- exact char_start and char_end offsets in the authoritative document text
- exact source-unit ID from authoritative inventory
"""

import json
import os
import re
import sys
import pypdf

PDF_PATH = "docs/Northwind_Refund_Policy_Handbook.pdf"
reader = pypdf.PdfReader(PDF_PATH)

# Extract full text and build page character offset index
full_doc_text = ""
page_spans = {}

for page_idx, page in enumerate(reader.pages):
    page_num = page_idx + 1
    page_text = page.extract_text()
    start_offset = len(full_doc_text)
    end_offset = start_offset + len(page_text)
    page_spans[page_num] = {
        "page": page_num,
        "start": start_offset,
        "end": end_offset,
        "text": page_text
    }
    full_doc_text += page_text

print(f"Total document extracted length: {len(full_doc_text)} characters across {len(reader.pages)} pages.")

# Load authoritative inventory
inv_path = "backend/scripts/baseline/authoritative_source_inventory_126_units.json"
with open(inv_path, "r", encoding="utf-8") as f:
    inv = json.load(f)
units_by_id = {u["unit_id"]: u for u in inv["units"]}

# Load 38 claims from phase2_2_claim_level_diff.json
diff_path = "backend/scripts/baseline/phase2_2_claim_level_diff.json"
with open(diff_path, "r", encoding="utf-8") as f:
    diff_records = json.load(f)

# Load frozen baseline
frozen_path = "backend/scripts/baseline/db_224_claims_frozen.json"
with open(frozen_path, "r", encoding="utf-8") as f:
    frozen_claims = json.load(f)
frozen_by_id = {c["number"]: c for c in frozen_claims}

print(f"Loaded {len(diff_records)} diff records.")

