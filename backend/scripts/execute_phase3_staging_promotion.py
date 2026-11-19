"""
Phase 3: Staging Promotion and Production Comparison Script.

Executes:
Step 1: Promotion to isolated staging database/schema.
Step 2: Staging parity verification.
Step 3: Read-only production baseline comparison.
"""

import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.services.staging_promotion_service import StagingPromotionService

BASELINE_DIR = BACKEND_DIR / "scripts" / "baseline"
NORTHWIND_DOC_ID = uuid.UUID("e3cdd194-1a9b-4f01-9031-13e6b027d3d2")

PROMOTION_REPORT_FILE = BASELINE_DIR / "phase3_staging_promotion_report.json"
VERIFICATION_AUDIT_FILE = BASELINE_DIR / "phase3_staging_verification_audit.json"
DIFF_REPORT_FILE = BASELINE_DIR / "phase3_production_diff_report.json"


async def main():
    print("=" * 80)
    print("EXECUTING PHASE 3: CONTROLLED MIGRATION & STAGING PROMOTION (STAGING FIRST)")
    print("=" * 80)

    service = StagingPromotionService(baseline_dir=BASELINE_DIR)

    # -------------------------------------------------------------------------
    # Step 1: Promote to isolated staging database / schema
    # -------------------------------------------------------------------------
    print("\n[Step 1] Promoting Phase 2.5 repaired extraction to isolated 'staging' schema...")
    promotion_res = await service.promote_to_staging(NORTHWIND_DOC_ID)
    assert promotion_res["status"] == "SUCCESS"
    assert promotion_res["claims_inserted"] == 224
    assert promotion_res["public_mutations"] == 0
    print(f"  [SUCCESS] 224 claims promoted into schema 'staging'. Zero mutations on 'public'.")

    with open(PROMOTION_REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(promotion_res, f, indent=2)
    print(f"  Wrote promotion report to {PROMOTION_REPORT_FILE.name}")

    # -------------------------------------------------------------------------
    # Step 2: Verify staging parity
    # -------------------------------------------------------------------------
    print("\n[Step 2] Verifying staging parity and status preservation...")
    audit_res = await service.verify_staging_parity(NORTHWIND_DOC_ID)
    assert audit_res["all_parity_checks_passed"] is True, "Staging parity check failed!"
    print(f"  [SUCCESS] Parity verified:")
    print(f"    - Total claims: {audit_res['total_claims']}")
    print(f"    - Status counts: {audit_res['status_counts']}")
    print(f"    - Evidence accounting: {audit_res['evidence_accounting']['total_evidence_records']} records ({audit_res['evidence_accounting']['formula']})")
    print(f"    - Conflict records: {audit_res['conflict_records_accounting']['total_conflict_records']}")
    print(f"      * Record 1 ($50 ambiguity): Claim #73 vs FAQ Q7 / SRC-P20-02 ({audit_res['conflict_records_accounting']['record_1_50_dollar_ambiguity']['code']})")
    print(f"      * Record 2 (Section 5 exclusions): Claim #223 vs Claim #224 ({audit_res['conflict_records_accounting']['record_2_section_5_exclusions']['code']})")
    print(f"    - Source inventory hashes: {audit_res['provenance_integrity']['source_inventory_hashes_matched']}")

    with open(VERIFICATION_AUDIT_FILE, "w", encoding="utf-8") as f:
        json.dump(audit_res, f, indent=2)
    print(f"  Wrote staging verification audit to {VERIFICATION_AUDIT_FILE.name}")

    # -------------------------------------------------------------------------
    # Step 3: Run read-only production comparison
    # -------------------------------------------------------------------------
    print("\n[Step 3] Running read-only production comparison (SET TRANSACTION READ ONLY;)...")
    diff_res = await service.run_readonly_production_comparison(NORTHWIND_DOC_ID)
    assert diff_res["zero_production_write_verified"] is True
    assert diff_res["production_mutations"] == 0
    phase_breakdown = diff_res["cumulative_phase_breakdown"]
    print(f"  [SUCCESS] Production comparison complete (Zero mutations):")
    print(f"    - Public claims count: {diff_res['public_total_claims']}")
    print(f"    - Staging claims count: {diff_res['staging_total_claims']}")
    print(f"    - Identical claims: {diff_res['identical_claims_count']}")
    print(f"    - Modified / repaired claims: {diff_res['modified_claims_count']}")
    print(f"    - Cumulative phase instances: {phase_breakdown['total_instances_summed']}")
    print(f"      * Phase 2.2c structural repairs: {phase_breakdown['phase_2_2c_structural_repairs']}")
    print(f"      * Phase 2.3 predicate specializations: {phase_breakdown['phase_2_3_predicate_specializations']}")
    print(f"      * Phase 2.3b semantics hardening: {phase_breakdown['phase_2_3b_semantics_hardening']}")
    print(f"      * Phase 2.4b value fidelity: {phase_breakdown['phase_2_4b_value_fidelity']}")
    print(f"      * Phase 2.5 conflict grounding: {phase_breakdown['phase_2_5_conflict_grounding']}")
    print(f"      * Multi-phase overlapping repairs: {phase_breakdown['multi_phase_overlapping_claims']}")
    print(f"      * Unique repaired claims: {phase_breakdown['unique_repaired_claims']}")

    with open(DIFF_REPORT_FILE, "w", encoding="utf-8") as f:
        json.dump(diff_res, f, indent=2)
    print(f"  Wrote production diff report to {DIFF_REPORT_FILE.name}")

    print("\n" + "=" * 80)
    print("PHASE 3 STAGING PROMOTION & VERIFICATION COMPLETE (AWAITING HUMAN APPROVAL)")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(main())

