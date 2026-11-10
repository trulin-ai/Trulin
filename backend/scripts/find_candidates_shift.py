import json

with open("backend/scripts/baseline/authoritative_source_inventory_126_units.json", "r", encoding="utf-8") as f:
    data = json.load(f)

op_units = [u for u in data["units"] if u["page"] < 20 and u["content_role"] == "operative_rule"]
print(f"Total op_units on p.3-19: {len(op_units)}")

# Let's check which ones have NO baseline claim or are pure preambles/instructions
for u in op_units:
    text = u["verbatim_text"]
    # Check if text is a section preamble or UI instruction
    if "following conditions must be met" in text or "cannot be returned or refunded, except" in text or "Navigate to" in text or "Bring item, original packaging" in text:
        print(f"Candidate non-rule: {u['unit_id']}: {text[:70]}")

