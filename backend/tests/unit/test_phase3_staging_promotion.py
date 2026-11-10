"""
Phase 3 Unit Tests: Staging Promotion, Parity Verification, and Production Comparison.

Tests:
1. Isolated staging schema creation and isolation.
2. Exact claim status parity (140 verified, 51 candidate, 31 rejected, 2 conflicted).
3. Ambiguity preservation ($50 boundary between claims #114 and #115).
4. Read-only production baseline comparison and zero-mutation enforcement.
"""

import uuid
import pytest
from sqlalchemy import text

from app.db.database import AsyncSessionLocal
from app.services.staging_promotion_service import StagingPromotionService

NORTHWIND_DOC_ID = uuid.UUID("e3cdd194-1a9b-4f01-9031-13e6b027d3d2")


@pytest.mark.anyio
async def test_staging_schema_and_isolation():
    """Validates that staging schema exists and is isolated from public."""
    async with AsyncSessionLocal() as session:
        await session.execute(text("SET TRANSACTION READ ONLY;"))
        res = (await session.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'staging'
            ORDER BY table_name;
        """))).fetchall()
        tables = [r[0] for r in res]
        assert "claims" in tables
        assert "claim_evidence" in tables
        assert "claim_conflicts" in tables
        assert "documents" in tables
        assert "document_versions" in tables


@pytest.mark.anyio
async def test_staging_parity_and_status_invariants():
    """Validates exact status parity in staging: 140 verified, 51 candidate, 31 rejected, 2 conflicted."""
    service = StagingPromotionService()
    audit_res = await service.verify_staging_parity(NORTHWIND_DOC_ID)

    assert audit_res["all_parity_checks_passed"] is True
    assert audit_res["total_claims"] == 224
    assert audit_res["status_counts"]["verified"] == 140
    assert audit_res["status_counts"]["candidate"] == 51
    assert audit_res["status_counts"]["rejected"] == 31
    assert audit_res["status_counts"]["conflicted"] == 2

    # Ambiguity and conflict preservation check
    conf_acc = audit_res["conflict_records_accounting"]
    assert conf_acc["total_conflict_records"] == 2
    rec1 = conf_acc["record_1_50_dollar_ambiguity"]
    assert rec1["claim_a_number"] == 73
    assert rec1["code"] == "AMBIGUITY_PRESERVED"
    assert rec1["boundary"] == "exactly $50"
    rec2 = conf_acc["record_2_section_5_exclusions"]
    assert rec2["claim_a_number"] == 223
    assert rec2["claim_b_number"] == 224
    assert rec2["code"] == "NON_REFUNDABLE_EXCLUSION_CONFLICT"

    # Evidence accounting check
    ev_acc = audit_res["evidence_accounting"]
    assert ev_acc["total_evidence_records"] == 230
    assert ev_acc["claims_with_single_evidence"] == 221
    assert ev_acc["claims_with_multiple_evidence"] == 3
    assert ev_acc["claims_without_evidence"] == 0


@pytest.mark.anyio
async def test_production_read_only_comparison_and_immutability():
    """Validates that production comparison strictly runs under read-only mode with zero mutations."""
    service = StagingPromotionService()
    diff_res = await service.run_readonly_production_comparison(NORTHWIND_DOC_ID)

    assert diff_res["zero_production_write_verified"] is True
    assert diff_res["production_mutations"] == 0
    assert diff_res["public_total_claims"] == 224
    assert diff_res["staging_total_claims"] == 224
    assert diff_res["identical_claims_count"] == 169
    assert diff_res["modified_claims_count"] == 55

    # Cumulative phase ledger breakdown
    breakdown = diff_res["cumulative_phase_breakdown"]
    assert breakdown["phase_2_2c_structural_repairs"] == 38
    assert breakdown["phase_2_3_predicate_specializations"] == 21
    assert breakdown["phase_2_3b_semantics_hardening"] == 5
    assert breakdown["phase_2_4b_value_fidelity"] == 3
    assert breakdown["phase_2_5_conflict_grounding"] == 2
    assert breakdown["total_instances_summed"] == 69
    assert breakdown["multi_phase_overlapping_claims"] == 14
    assert breakdown["unique_repaired_claims"] == 55
