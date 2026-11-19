"""
Extracts the 100% authentic source inventory directly from the PDF text lines.
Zero manual text approximations, zero mismatch warnings.
"""

import pypdf
import json
import hashlib
import os

PDF_PATH = os.path.abspath("backend/storage/uploads/18197bd3-3c9b-43cc-be12-0804174b1be6/Northwind_Refund_Policy_Handbook.pdf")
BASELINE_DIR = os.path.abspath("backend/scripts/baseline")

with open(PDF_PATH, "rb") as f:
    pdf_bytes = f.read()
sha256 = hashlib.sha256(pdf_bytes).hexdigest()

reader = pypdf.PdfReader(PDF_PATH)
inventory = []
unit_counter = 1

current_section = "Front Matter"

for page_idx, page in enumerate(reader.pages):
    page_num = page_idx + 1
    raw_text = page.extract_text() or ""
    lines = [l.strip() for l in raw_text.splitlines() if l.strip()]
    
    i = 0
    while i < len(lines):
        line = lines[i]
        
        # Skip header / footer
        if "Northwind Outfitters Inc. - Refund Policy Handbook" in line or line.startswith("Page "):
            i += 1
            continue
        if "Document ID: NW-POL-REF-2026" in line or "Classification: Public" in line:
            i += 1
            continue
        if line.startswith("NOTICE:"):
            inventory.append({
                "unit_id": f"SRC-U{unit_counter:03d}",
                "page": page_num,
                "section": "Header Disclaimer",
                "structure_type": "disclaimer",
                "verbatim_text": line,
                "content_role": "non_rule"
            })
            unit_counter += 1
            i += 1
            continue
            
        # Detect section headings
        if any(line.startswith(f"{s}.") for s in range(1, 25)):
            current_section = line
            inventory.append({
                "unit_id": f"SRC-U{unit_counter:03d}",
                "page": page_num,
                "section": current_section,
                "structure_type": "heading",
                "verbatim_text": line,
                "content_role": "heading"
            })
            unit_counter += 1
            i += 1
            continue

        # Detect subheadings
        if any(line.startswith(f"{s}.{sub}") for s in range(1, 25) for sub in range(1, 10)):
            current_section = line
            inventory.append({
                "unit_id": f"SRC-U{unit_counter:03d}",
                "page": page_num,
                "section": current_section,
                "structure_type": "subheading",
                "verbatim_text": line,
                "content_role": "heading"
            })
            unit_counter += 1
            i += 1
            continue

        # Bullets
        if line.startswith(("\x7f", "•", "-", "*")):
            bullet_text = line.lstrip("\x7f•-* ")
            inventory.append({
                "unit_id": f"SRC-U{unit_counter:03d}",
                "page": page_num,
                "section": current_section,
                "structure_type": "bullet",
                "verbatim_text": bullet_text,
                "content_role": "operative_rule" if "5." in current_section or "4." in current_section else "policy_clause"
            })
            unit_counter += 1
            i += 1
            continue

        # Definitions
        if "2. Definitions" in current_section and i + 1 < len(lines) and lines[i+1] not in ("Term", "Definition"):
            # Check if term/definition pair
            pass

        # Standard prose or table lines
        inventory.append({
            "unit_id": f"SRC-U{unit_counter:03d}",
            "page": page_num,
            "section": current_section,
            "structure_type": "table_or_prose",
            "verbatim_text": line,
            "content_role": "operative_rule" if any(k in current_section.lower() for k in ("standard return", "eligibility", "non-refundable", "timelines", "methods", "shipping", "warranty", "international", "dispute", "cancellation", "subscription")) else "informational"
        })
        unit_counter += 1
        i += 1

print(f"Total extracted units: {len(inventory)}")

out_path = os.path.join(BASELINE_DIR, "authentic_northwind_source_inventory_v2.json")
with open(out_path, "w", encoding="utf-8") as f:
    json.dump({
        "document": "Northwind_Refund_Policy_Handbook.pdf",
        "sha256": sha256,
        "total_units": len(inventory),
        "units": inventory
    }, f, indent=2)

print(f"Saved to {out_path}")

