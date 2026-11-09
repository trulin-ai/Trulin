import json
import hashlib
import os
import sys

BACKEND_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, BACKEND_DIR)

EXPORT_JSON = os.path.join(BACKEND_DIR, "scripts", "northwind_candidates_export.json")
BASELINE_JSON = os.path.join(BACKEND_DIR, "scripts", "northwind_candidates_baseline_frozen.json")
PDF_PATH = os.path.join(BACKEND_DIR, "storage", "uploads", "18197bd3-3c9b-43cc-be12-0804174b1be6", "Northwind_Refund_Policy_Handbook.pdf")

def main():
    with open(EXPORT_JSON, "r", encoding="utf-8") as f:
        exported = json.load(f)

    with open(BASELINE_JSON, "r", encoding="utf-8") as f:
        baseline = json.load(f)

    # 1. Source SHA-256
    with open(PDF_PATH, "rb") as f:
        pdf_bytes = f.read()
    source_sha256 = hashlib.sha256(pdf_bytes).hexdigest()
    print(f"FREEZE SNAPSHOT:")
    print(f"  Source PDF Path: {PDF_PATH}")
    print(f"  Source PDF Size: {len(pdf_bytes)} bytes")
    print(f"  Source SHA-256: {source_sha256}")
    print(f"  Pipeline Run ID (Export): {exported[0].get('pipeline_run_id') if exported else 'N/A'}")
    print(f"  Export Total Candidates: {len(exported)}")
    print(f"  Baseline Total Candidates: {len(baseline)}")

    # 2. Search for the exact candidates user cited
    # User cited:
    # #24: Immediate in-store refund processing and bank posting time
    # #80: Merged cancellation-status/refund-outcome table fragment
    # #81: Price-adjustment opportunity after price drop
    # #86: Request for first-charge refund after forgetting to cancel trial
    # #87: Permission to pause Trailhead Box for up to 3 months
    # #77: Attaches under-$40 claim to cosmetic-flaw table row
    # #55: Customer -> offers_store_credit_bonus
    # #25: Order vs Order number
    # #68-#69: Shipping threshold Order
    # #19-#23: Approval roles
    # #157: Orphan 'This is / limited_to'
    # #222: Revision history labeled Example / Case study
    
    print("\n" + "="*80)
    print("DETAILED TRACE OF USER-CITED TARGET CANDIDATES")
    print("="*80)

    # Let's inspect by text matching across exported and baseline
    find_specs = [
        ("IN_STORE_POSTING", lambda c: "in-store" in str(c.get("verbatim_source_quote", "")).lower() and "immediate" in str(c.get("verbatim_source_quote", "")).lower()),
        ("PRICE_DROP", lambda c: "price drop" in str(c.get("verbatim_source_quote", "")).lower() or "price adjustment" in str(c.get("claim_text", "")).lower()),
        ("TRIAL_FORGOT_CANCEL", lambda c: "forgot to cancel" in str(c.get("verbatim_source_quote", "")).lower() or "first charge" in str(c.get("verbatim_source_quote", "")).lower()),
        ("PAUSE_TRAILHEAD", lambda c: "pause" in str(c.get("verbatim_source_quote", "")).lower() and "trailhead" in str(c.get("verbatim_source_quote", "")).lower()),
        ("COSMETIC_FLAW_ROW", lambda c: "cosmetic flaw" in str(c.get("verbatim_source_quote", "")).lower() or "keep item" in str(c.get("verbatim_source_quote", "")).lower()),
        ("KEEP_IT_UNDER_40", lambda c: "under $40" in str(c.get("verbatim_source_quote", "")).lower()),
        ("TWO_INSTANCES_LIMIT", lambda c: "two instances" in str(c.get("verbatim_source_quote", "")).lower()),
        ("STORE_CREDIT_BONUS", lambda c: "5% bonus" in str(c.get("verbatim_source_quote", "")).lower() or "offers_store_credit_bonus" in str(c.get("predicate", ""))),
        ("ORDER_NUMBER_REQ", lambda c: "order number" in str(c.get("verbatim_source_quote", "")).lower() or "order number" in str(c.get("claim_text", "")).lower()),
        ("EMAIL_ON_ORDER", lambda c: "email on order" in str(c.get("verbatim_source_quote", "")).lower() or "verified northwind account email" in str(c.get("verbatim_source_quote", "")).lower()),
        ("APPROVAL_ROLES", lambda c: "approval required" in str(c.get("verbatim_source_quote", "")).lower() or "requires_approval_role" in str(c.get("predicate", ""))),
        ("CASH_50", lambda c: "cash" in str(c.get("verbatim_source_quote", "")).lower() and "50" in str(c.get("verbatim_source_quote", "")).lower()),
        ("REVISION_HISTORY", lambda c: "4.0 mar 1" in str(c.get("verbatim_source_quote", "")).lower() or "gold member window" in str(c.get("verbatim_source_quote", "")).lower()),
    ]

    for tag, matcher in find_specs:
        print(f"\n--- MATCHING SPEC: {tag} ---")
        matches_exp = [(idx + 1, c) for idx, c in enumerate(exported) if matcher(c)]
        for idx, c in matches_exp:
            ge = c.get("gate_evaluation", {})
            conds = c.get("conditions", [])
            cond_str = f" WHERE {'; '.join(str(x) for x in conds)}" if conds else ""
            assertion = f"{c.get('subject')} [{c.get('modality', 'CAN')}] {c.get('predicate')} {c.get('object')}{cond_str}"
            print(f"  EXPORT #{idx} [ID {c.get('candidate_id', '')[:8]}] [{c.get('evidence_structure')}/{c.get('content_role')}]:")
            print(f"    Assertion: {assertion}")
            print(f"    Evidence Quote: {repr(c.get('verbatim_source_quote', ''))}")
            print(f"    Claim Text: {repr(c.get('claim_text', ''))}")
            print(f"    Decision: {ge.get('lifecycle_decision')} [{ge.get('decision_code')}]")
            print(f"    Reason: {ge.get('decision_reason')}")

if __name__ == "__main__":
    main()

