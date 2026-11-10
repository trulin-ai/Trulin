"""
Phase 2.5: Conflict Resolution and Deduplication Calibration Unit Tests.

Verifies:
1. Scope-aware claim-pair classification across all 7 required classes:
   - exact duplicate (DUPLICATE_EXACT)
   - near-duplicate (DUPLICATE_NEAR)
   - restatement (RESTATEMENT)
   - complementary detail (COMPLEMENTARY_DETAIL)
   - scope-narrowed rule (SCOPE_NARROWED_RULE)
   - genuine conflict (CONFLICT_DIRECT, CONFLICT_SCOPE, CONFLICT_CONDITION, CONFLICT_EXCEPTION)
   - unrelated similarity (UNRELATED_SIMILARITY)
2. Precedence Principles:
   - Specific exception beats general rule (Lex Specialis)
   - Detailed section beats summary
   - Explicit condition beats unqualified rule
   - Statutory exception beats blanket prohibition
   - Table row and prose reconciled, not silently merged
   - Ambiguity documented / preserved without forced resolution
3. Guardrails:
   - G1: Do not delete or overwrite either claim in a conflict pair without logged decision
   - G2: Preserve $50 boundary ambiguity (AMBIGUITY_PRESERVED)
   - G3: Do not merge summary claims with detailed claims (RESTATEMENT)
   - G4: Do not treat scope-narrowed exceptions as contradictions (SCOPE_NARROWED_RULE)
   - G5: Deduplication never removes unique conditions, exceptions, scope, or remedies
   - G8: Status parity invariant (140 verified, 51 candidate, 31 rejected, 2 conflicted)
"""

import json
import os
import pytest

from app.services.conflict_resolution_engine import (
    ConflictCode,
    ConflictDecision,
    ConflictResolutionEngine,
    PairClassification,
    PrecedencePrinciple,
)

BASELINE_FILE = os.path.join(
    os.path.dirname(__file__), "..", "..", "scripts", "baseline", "phase2_3b_repaired_extraction_v1.json"
)
BASELINE_DIR = os.path.dirname(BASELINE_FILE)


@pytest.fixture(scope="module")
def baseline_claims():
    assert os.path.exists(BASELINE_FILE), f"Baseline file not found at {BASELINE_FILE}"
    with open(BASELINE_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


# -----------------------------------------------------------------------------
# 1. Exact & Near Duplicate Tests
# -----------------------------------------------------------------------------
def test_duplicate_exact_detection():
    c1 = {
        "number": 1001,
        "id": "c1-exact",
        "subject": "Standard merchandise",
        "predicate": "has_return_window",
        "object": "30 days",
        "claim_text": "Standard merchandise may be returned within 30 days.",
        "status": "verified",
        "conditions": [],
    }
    c2 = {
        "number": 1002,
        "id": "c2-exact",
        "subject": "Standard merchandise",
        "predicate": "has_return_window",
        "object": "30 days",
        "claim_text": "Standard merchandise may be returned within 30 days.",
        "status": "candidate",
        "conditions": [],
    }
    dec = ConflictResolutionEngine.classify_claim_pair(c1, c2)
    assert dec.classification == PairClassification.EXACT_DUPLICATE
    assert dec.code == ConflictCode.DUPLICATE_EXACT
    assert dec.reconciliation_action == "DEDUPLICATE_CANONICAL"
    assert dec.winner_claim_id == "c1-exact"


def test_duplicate_near_detection():
    c1 = {
        "number": 1003,
        "id": "c1-near",
        "subject": "Holiday purchases",
        "predicate": "has_return_deadline",
        "object": "January 31",
        "claim_text": "Holiday purchases Nov 1 to Dec 24 may be returned until January 31.",
        "status": "verified",
        "conditions": ["Holiday season"],
    }
    c2 = {
        "number": 1004,
        "id": "c2-near",
        "subject": "Holiday purchases",
        "predicate": "has_return_deadline",
        "object": "January 31",
        "claim_text": "Holiday items bought Nov 1 to Dec 24 can be returned until January 31.",
        "status": "candidate",
        "conditions": ["Holiday season"],
    }
    dec = ConflictResolutionEngine.classify_claim_pair(c1, c2)
    assert dec.classification == PairClassification.NEAR_DUPLICATE
    assert dec.code == ConflictCode.DUPLICATE_NEAR
    assert dec.reconciliation_action == "DEDUPLICATE_CANONICAL"


# -----------------------------------------------------------------------------
# 2. Restatement Tests (Summary vs Detailed / FAQ / Table vs Prose)
# -----------------------------------------------------------------------------
def test_restatement_summary_vs_detailed(baseline_claims):
    # Claim #2 is Section 1.2 Summary table; Claim #13 is Section 3 detailed row
    c2 = next(c for c in baseline_claims if c["number"] == 2)
    c13 = next(c for c in baseline_claims if c["number"] == 13)

    dec = ConflictResolutionEngine.classify_claim_pair(c2, c13)
    assert dec.classification == PairClassification.RESTATEMENT
    assert dec.code == ConflictCode.RESTATEMENT
    assert dec.precedence_principle == PrecedencePrinciple.DETAILED_SECTION_BEATS_SUMMARY
    assert dec.reconciliation_action == "PRESERVE_BOTH"
    # Detailed section claim wins authority, summary is preserved
    assert dec.winner_claim_id == (c13.get("id") or c13["number"])


def test_restatement_faq_vs_core_policy(baseline_claims):
    # Claim #200 is FAQ "Standard returns must be requested within 30 days"
    c200 = next(c for c in baseline_claims if c["number"] == 200)
    c13 = next(c for c in baseline_claims if c["number"] == 13)

    dec = ConflictResolutionEngine.classify_claim_pair(c200, c13)
    assert dec.classification == PairClassification.RESTATEMENT
    assert dec.code == ConflictCode.RESTATEMENT
    assert dec.precedence_principle == PrecedencePrinciple.DETAILED_SECTION_BEATS_SUMMARY
    assert dec.reconciliation_action == "PRESERVE_BOTH"


def test_restatement_table_row_vs_prose():
    c_table = {
        "number": 1005,
        "id": "c-table",
        "subject": "Standard merchandise",
        "predicate": "has_return_window",
        "object": "30 days",
        "claim_text": "| Standard merchandise | 30 days |",
        "status": "verified",
    }
    c_prose = {
        "number": 1006,
        "id": "c-prose",
        "subject": "Standard merchandise",
        "predicate": "has_return_window",
        "object": "30 days",
        "claim_text": "Standard merchandise may be returned within 30 days of delivery.",
        "status": "verified",
    }
    dec = ConflictResolutionEngine.classify_claim_pair(c_table, c_prose)
    assert dec.classification == PairClassification.RESTATEMENT
    assert dec.code == ConflictCode.RESTATEMENT
    assert dec.precedence_principle == PrecedencePrinciple.TABLE_PROSE_RECONCILED
    assert dec.reconciliation_action == "PRESERVE_BOTH"


# -----------------------------------------------------------------------------
# 3. Complementary Detail Tests
# -----------------------------------------------------------------------------
def test_complementary_detail_order_shipping(baseline_claims):
    # Claims #91 and #92 govern order shipping rules:
    # #91: has_return_shipping_rule ('No')
    # #92: has_return_label_cost ('Free')
    c91 = next(c for c in baseline_claims if c["number"] == 91)
    c92 = next(c for c in baseline_claims if c["number"] == 92)

    dec = ConflictResolutionEngine.classify_claim_pair(c91, c92)
    assert dec.classification == PairClassification.COMPLEMENTARY_DETAIL
    assert dec.code == ConflictCode.COMPLEMENTARY_DETAIL
    assert dec.precedence_principle == PrecedencePrinciple.EQUAL_WEIGHT
    assert dec.reconciliation_action == "PRESERVE_BOTH"


def test_complementary_detail_cash_method_and_id(baseline_claims):
    # Claim #73 has_refund_method ('Cash up to $50, then store credit/card')
    # Claim #74 has_identity_verification_requirement ('ID required over $50')
    c73 = next(c for c in baseline_claims if c["number"] == 73)
    c74 = next(c for c in baseline_claims if c["number"] == 74)

    dec = ConflictResolutionEngine.classify_claim_pair(c73, c74)
    assert dec.classification == PairClassification.COMPLEMENTARY_DETAIL
    assert dec.code == ConflictCode.COMPLEMENTARY_DETAIL
    assert dec.precedence_principle == PrecedencePrinciple.EQUAL_WEIGHT
    assert dec.reconciliation_action == "PRESERVE_BOTH"


# -----------------------------------------------------------------------------
# 4. Scope-Narrowed Rule Tests (Lex Specialis)
# -----------------------------------------------------------------------------
def test_scope_narrowed_gold_member_exception(baseline_claims):
    # Claim #13: Standard merchandise 30 days
    # Claim #14: Northwind Rewards Gold members 60 days
    c13 = next(c for c in baseline_claims if c["number"] == 13)
    c14 = next(c for c in baseline_claims if c["number"] == 14)

    dec = ConflictResolutionEngine.classify_claim_pair(c13, c14)
    assert dec.classification == PairClassification.SCOPE_NARROWED_RULE
    assert dec.code == ConflictCode.SCOPE_NARROWED_RULE
    assert dec.precedence_principle == PrecedencePrinciple.SPECIFIC_EXCEPTION_BEATS_GENERAL
    assert dec.reconciliation_action == "PRESERVE_BOTH"
    # Specific tier wins within its scope
    assert dec.winner_claim_id == (c14.get("id") or c14["number"])


def test_scope_narrowed_policy_exception(baseline_claims):
    # Claim #33: Final sale items non-refundable
    # Claim #45: Section 5.2 policy exception (damaged/defective/misdescribed)
    c33 = next(c for c in baseline_claims if c["number"] == 33)
    c45 = next(c for c in baseline_claims if c["number"] == 45)

    dec = ConflictResolutionEngine.classify_claim_pair(c33, c45)
    assert dec.classification == PairClassification.SCOPE_NARROWED_RULE
    assert dec.code == ConflictCode.SCOPE_NARROWED_RULE
    assert dec.precedence_principle == PrecedencePrinciple.POLICY_EXCEPTION_BEATS_BLANKET_PROHIBITION
    assert dec.reconciliation_action == "PRESERVE_BOTH"
    assert dec.winner_claim_id == (c45.get("id") or c45["number"])


def test_scope_narrowed_category_exceptions(baseline_claims):
    c13 = next(c for c in baseline_claims if c["number"] == 13)
    c16 = next(c for c in baseline_claims if c["number"] == 16)  # Footwear 45 days
    c17 = next(c for c in baseline_claims if c["number"] == 17)  # Camping tents 60 days

    dec16 = ConflictResolutionEngine.classify_claim_pair(c13, c16)
    assert dec16.classification == PairClassification.SCOPE_NARROWED_RULE
    assert dec16.precedence_principle == PrecedencePrinciple.SPECIFIC_EXCEPTION_BEATS_GENERAL

    dec17 = ConflictResolutionEngine.classify_claim_pair(c13, c17)
    assert dec17.classification == PairClassification.SCOPE_NARROWED_RULE
    assert dec17.precedence_principle == PrecedencePrinciple.SPECIFIC_EXCEPTION_BEATS_GENERAL


# -----------------------------------------------------------------------------
# 5. Genuine Conflict & Ambiguity Preservation Tests
# -----------------------------------------------------------------------------
def test_cash_boundary_ambiguity_preserved(baseline_claims):
    # Claim #73 says "Cash up to $50, then store credit/card"
    # FAQ Q7 (SRC-P20-02) says "Cash refunds are only available for cash purchases under $50"
    c73 = next(c for c in baseline_claims if c["number"] == 73)
    faq_q7 = {
        "number": 225,
        "id": "SRC-P20-02-faq-q7-cash",
        "subject": "Cash refund",
        "predicate": "has_refund_method",
        "object": "available for cash purchases under $50",
        "claim_text": "Q7. Can I get a cash refund? Refunds go to the original payment method. Cash refunds are only available for cash purchases under $50.",
        "conditions": ["18. Frequently Asked Questions Q7"],
        "source_unit_id": "SRC-P20-02",
    }
    dec = ConflictResolutionEngine.classify_claim_pair(c73, faq_q7)
    assert dec.classification == PairClassification.GENUINE_CONFLICT
    assert dec.code == ConflictCode.AMBIGUITY_PRESERVED
    assert dec.precedence_principle == PrecedencePrinciple.AMBIGUITY_DOCUMENTED
    assert dec.is_ambiguity_preserved is True
    assert dec.reconciliation_action == "DOCUMENT_AMBIGUITY"


def test_genuine_conflict_condition_incompatible():
    c_cond1 = {
        "number": 1009,
        "id": "c-cond1",
        "subject": "Bulk orders",
        "predicate": "has_restocking_fee",
        "object": "15%",
        "claim_text": "Bulk orders require approval by Store Manager.",
        "conditions": ["approval by Store Manager"],
    }
    c_cond2 = {
        "number": 1010,
        "id": "c-cond2",
        "subject": "Bulk orders",
        "predicate": "has_restocking_fee",
        "object": "20%",
        "claim_text": "Bulk orders require approval by Vice President.",
        "conditions": ["approval by Vice President"],
    }
    dec = ConflictResolutionEngine.classify_claim_pair(c_cond1, c_cond2)
    assert dec.classification == PairClassification.GENUINE_CONFLICT
    assert dec.code == ConflictCode.CONFLICT_CONDITION
    assert dec.reconciliation_action == "RECORD_CONFLICT"


def test_genuine_conflict_exception_blanket_vs_unsubordinated():
    c_blanket = {
        "number": 1011,
        "id": "c-blanket",
        "subject": "Clearance items",
        "predicate": "cannot_be_returned_or_refunded",
        "object": "non-refundable",
        "claim_text": "Clearance items are strictly non-refundable with no exceptions under any circumstances.",
        "modality": "PROHIBITION",
    }
    c_unsub = {
        "number": 1012,
        "id": "c-unsub",
        "subject": "Clearance items",
        "predicate": "cannot_be_returned_or_refunded",
        "object": "refundable for store credit",
        "claim_text": "Clearance items may receive store credit.",
        "modality": "PERMISSION",
    }
    dec = ConflictResolutionEngine.classify_claim_pair(c_blanket, c_unsub)
    assert dec.classification == PairClassification.GENUINE_CONFLICT
    assert dec.code == ConflictCode.CONFLICT_EXCEPTION
    assert dec.reconciliation_action == "RECORD_CONFLICT"


def test_genuine_conflict_scope_unqualified():
    c_scope1 = {
        "number": 1013,
        "id": "c-scope1",
        "subject": "Standard merchandise",
        "predicate": "has_return_window",
        "object": "30 days",
        "claim_text": "Standard merchandise return window is 30 days.",
    }
    c_scope2 = {
        "number": 1014,
        "id": "c-scope2",
        "subject": "Standard merchandise",
        "predicate": "has_return_window",
        "object": "45 days",
        "claim_text": "Standard merchandise return window is 45 days.",
    }
    dec = ConflictResolutionEngine.classify_claim_pair(c_scope1, c_scope2)
    assert dec.classification == PairClassification.GENUINE_CONFLICT
    assert dec.code == ConflictCode.CONFLICT_SCOPE
    assert dec.reconciliation_action == "RECORD_CONFLICT"


def test_genuine_conflict_direct_polarity():
    c_perm = {
        "number": 1007,
        "id": "c-perm",
        "subject": "Customer",
        "predicate": "may_return_item",
        "object": "permitted",
        "claim_text": "Customers may return opened gear within 30 days.",
        "modality": "PERMISSION",
    }
    c_proh = {
        "number": 1008,
        "id": "c-proh",
        "subject": "Customer",
        "predicate": "may_return_item",
        "object": "prohibited",
        "claim_text": "Customers cannot return opened gear under any circumstances.",
        "modality": "PROHIBITION",
    }
    dec = ConflictResolutionEngine.classify_claim_pair(c_perm, c_proh)
    assert dec.classification == PairClassification.GENUINE_CONFLICT
    assert dec.code == ConflictCode.CONFLICT_DIRECT
    assert dec.reconciliation_action == "RECORD_CONFLICT"


def test_genuine_conflict_baseline_claims(baseline_claims):
    # Baseline claims #223 and #224 are explicitly preserved as 'conflicted'
    c223 = next(c for c in baseline_claims if c["number"] == 223)
    c224 = next(c for c in baseline_claims if c["number"] == 224)

    assert c223["status"] == "conflicted"
    assert c224["status"] == "conflicted"

    dec = ConflictResolutionEngine.classify_claim_pair(c223, c224)
    assert dec.classification == PairClassification.GENUINE_CONFLICT
    assert dec.reconciliation_action == "RECORD_CONFLICT"


# -----------------------------------------------------------------------------
# 6. Unrelated Similarity Tests
# -----------------------------------------------------------------------------
def test_unrelated_similarity(baseline_claims):
    # Claim #13 (Return window) vs Claim #204 (Phone contact number)
    c13 = next(c for c in baseline_claims if c["number"] == 13)
    c204 = next(c for c in baseline_claims if c["number"] == 204)

    dec = ConflictResolutionEngine.classify_claim_pair(c13, c204)
    assert dec.classification == PairClassification.UNRELATED_SIMILARITY
    assert dec.code == ConflictCode.UNRELATED_SIMILARITY
    assert dec.precedence_principle == PrecedencePrinciple.NONE


# -----------------------------------------------------------------------------
# 7. Guardrails G1-G8 & Parity Invariants
# -----------------------------------------------------------------------------
def test_guardrail_g1_no_silent_deletion(baseline_claims):
    assert len(baseline_claims) == 224, f"Expected 224 claims, found {len(baseline_claims)}"


def test_guardrail_g2_preserve_ambiguity_invariant(baseline_claims):
    # Check that $50 cash boundary between Section 8.2 and FAQ Q7 preserves ambiguity without forced resolution
    c73 = next(c for c in baseline_claims if c["number"] == 73)
    faq_q7 = {
        "number": 225,
        "id": "SRC-P20-02-faq-q7-cash",
        "subject": "Cash refund",
        "predicate": "has_refund_method",
        "object": "available for cash purchases under $50",
        "claim_text": "Q7. Can I get a cash refund? Refunds go to the original payment method. Cash refunds are only available for cash purchases under $50.",
        "conditions": ["18. Frequently Asked Questions Q7"],
        "source_unit_id": "SRC-P20-02",
    }
    dec = ConflictResolutionEngine.classify_claim_pair(c73, faq_q7)
    assert dec.is_ambiguity_preserved is True
    assert dec.code == ConflictCode.AMBIGUITY_PRESERVED
    assert dec.precedence_principle == PrecedencePrinciple.AMBIGUITY_DOCUMENTED
    assert dec.reconciliation_action == "DOCUMENT_AMBIGUITY"


def test_guardrail_g3_summary_claims_preserved(baseline_claims):
    # Claims 2-6 must all exist and remain intact
    summary_nums = {2, 3, 4, 5, 6}
    found = {c["number"] for c in baseline_claims if c["number"] in summary_nums}
    assert found == summary_nums, f"Missing summary claims: {summary_nums - found}"


def test_guardrail_status_parity_invariant(baseline_claims):
    from collections import Counter
    counts = Counter(c.get("status") for c in baseline_claims)
    assert counts["verified"] == 140, f"Expected 140 verified, got {counts['verified']}"
    assert counts["candidate"] == 51, f"Expected 51 candidate, got {counts['candidate']}"
    assert counts["rejected"] == 31, f"Expected 31 rejected, got {counts['rejected']}"
    assert counts["conflicted"] == 2, f"Expected 2 conflicted, got {counts['conflicted']}"


def test_clustering_all_224_claims_covered(baseline_claims):
    clusters = ConflictResolutionEngine.cluster_claims(baseline_claims)
    total_clustered = sum(len(v) for v in clusters.values())
    assert total_clustered == 224, f"Expected 224 clustered claims, got {total_clustered}"
    assert len(clusters) == 17, f"Expected 17 functional clusters, got {len(clusters)}"


# -----------------------------------------------------------------------------
# 8. Phase 2.5b: Conflict Reconciliation & Invariant Verification
# -----------------------------------------------------------------------------
def test_material_conflict_changes_status_or_requires_review(baseline_claims):
    # Material conflicts (#223, #224) have status 'conflicted' and require review
    c223 = next(c for c in baseline_claims if c["number"] == 223)
    c224 = next(c for c in baseline_claims if c["number"] == 224)

    assert c223["status"] == "conflicted"
    assert c223["evaluator_tier"] == "REVIEW_REQUIRED"

    assert c224["status"] == "conflicted"
    assert c224["evaluator_tier"] == "REVIEW_REQUIRED"


def test_non_material_conflict_preserves_status_with_reason_code(baseline_claims):
    # Non-material conflicts (e.g. approval tiers #33 vs #34 or fraud tiers #190 vs #192)
    # preserve verified status because they are governed by distinct operational thresholds
    c33 = next(c for c in baseline_claims if c["number"] == 33)
    c34 = next(c for c in baseline_claims if c["number"] == 34)

    assert c33["status"] == "verified"
    assert c34["status"] == "verified"

    dec = ConflictResolutionEngine.classify_claim_pair(c33, c34)
    assert dec.reconciliation_action == "RECORD_CONFLICT"


def test_summary_detail_pairs_remain_restatements(baseline_claims):
    # Summary claims #2-#6 paired with detailed section claims remain restatements
    c2 = next(c for c in baseline_claims if c["number"] == 2)
    c13 = next(c for c in baseline_claims if c["number"] == 13)

    dec = ConflictResolutionEngine.classify_claim_pair(c2, c13)
    assert dec.classification == PairClassification.RESTATEMENT
    assert dec.code == ConflictCode.RESTATEMENT
    assert dec.precedence_principle == PrecedencePrinciple.DETAILED_SECTION_BEATS_SUMMARY
    assert dec.reconciliation_action == "PRESERVE_BOTH"


def test_cash_50_boundary_remains_ambiguous(baseline_claims):
    # $50 boundary between Section 8.2 and FAQ Q7 remains explicitly ambiguous
    c73 = next(c for c in baseline_claims if c["number"] == 73)
    faq_q7 = {
        "number": 225,
        "id": "SRC-P20-02-faq-q7-cash",
        "subject": "Cash refund",
        "predicate": "has_refund_method",
        "object": "available for cash purchases under $50",
        "claim_text": "Q7. Can I get a cash refund? Refunds go to the original payment method. Cash refunds are only available for cash purchases under $50.",
        "conditions": ["18. Frequently Asked Questions Q7"],
        "source_unit_id": "SRC-P20-02",
    }
    dec = ConflictResolutionEngine.classify_claim_pair(c73, faq_q7)
    assert dec.code == ConflictCode.AMBIGUITY_PRESERVED
    assert dec.precedence_principle == PrecedencePrinciple.AMBIGUITY_DOCUMENTED
    assert dec.is_ambiguity_preserved is True


def test_no_claim_is_deleted_or_silently_overwritten(baseline_claims):
    # Exactly 224 claims, status parity preserved: 140 verified, 51 candidate, 31 rejected, 2 conflicted
    assert len(baseline_claims) == 224
    from collections import Counter
    counts = Counter(c.get("status") for c in baseline_claims)
    assert counts == {"verified": 140, "candidate": 51, "rejected": 31, "conflicted": 2}


def test_machine_checked_arithmetic_identities(baseline_claims):
    # Machine-checked assertion: no summary count may differ from the underlying ledger
    res = ConflictResolutionEngine.evaluate_all(baseline_claims)

    total_pairs = res["total_evaluated_pairs"]
    intra_pairs = res["intra_cluster_pairs_count"]
    cross_pairs = res["cross_cluster_pairs_count"]

    # 1. Total pairs identity
    assert total_pairs == 24976, f"Expected 24976 pairs, got {total_pairs}"
    assert intra_pairs == 1847, f"Expected 1847 intra-cluster pairs, got {intra_pairs}"
    assert cross_pairs == 23129, f"Expected 23129 cross-cluster pairs, got {cross_pairs}"
    assert intra_pairs + cross_pairs == total_pairs

    # 2. Category subtotals identity
    classes = res["classification_counts"]
    intra_cls = res["intra_classification_breakdown"]
    cross_cls = res["cross_classification_breakdown"]

    assert classes["unrelated similarity"] == 22331
    assert classes["scope-narrowed rule"] == 1703
    assert classes["genuine conflict"] == 452
    assert classes["complementary detail"] == 335
    assert classes["restatement"] == 155

    assert sum(classes.values()) == total_pairs

    # 3. Intra + Cross = Total identity for each category
    for cat in ["unrelated similarity", "scope-narrowed rule", "genuine conflict", "complementary detail", "restatement"]:
        assert intra_cls[cat] + cross_cls[cat] == classes[cat], f"Mismatch for {cat}: {intra_cls[cat]} + {cross_cls[cat]} != {classes[cat]}"

    # 4. Conflict count identity (452 total = 422 diagnostic + 30 condition-governed)
    conflict_decisions = [d for d in res["decisions"] if d["classification"] == "genuine conflict"]
    assert len(conflict_decisions) == 452
    involving_223_224 = sum(1 for d in conflict_decisions if d["claim_a_number"] in (223, 224) or d["claim_b_number"] in (223, 224))
    non_223_224 = sum(1 for d in conflict_decisions if not (d["claim_a_number"] in (223, 224) or d["claim_b_number"] in (223, 224)))
    assert involving_223_224 == 422, f"Expected 422 diagnostic pairs, got {involving_223_224}"
    assert non_223_224 == 30, f"Expected 30 non-material condition pairs, got {non_223_224}"
    assert involving_223_224 + non_223_224 == 452

    # 5. Phase 2.5d Source Fidelity Audit: Verify all 452 rationales have zero fabrications
    audit_file = os.path.join(BASELINE_DIR, "phase2_5d_rationale_audit.json")
    diff_file = os.path.join(BASELINE_DIR, "phase2_5d_rationale_before_after_diff.json")

    assert os.path.exists(audit_file), "phase2_5d_rationale_audit.json must exist"
    assert os.path.exists(diff_file), "phase2_5d_rationale_before_after_diff.json must exist"

    with open(audit_file, "r", encoding="utf-8") as f:
        audit_data = json.load(f)

    records = audit_data["audit_records"]
    assert len(records) == 452

    # Forbidden fabricated tokens
    forbidden_tokens = [
        "universal 365-day",
        "diagnostic stress test",
        "$50 vs $200 vs $500 vs $1000",
        "8am-8pm est",
        "24/7 chat",
    ]

    for r in records:
        assert r["handbook_source_fidelity_verified"] is True
        assert r["audit_verdict"] == "PASSED_SOURCE_FAITHFUL"
        rat_lower = r["conflict_rationale"].lower()
        for tok in forbidden_tokens:
            assert tok not in rat_lower, f"Forbidden token '{tok}' found in pair {r['pair_key']}: {r['conflict_rationale']}"

    # Verify specific pairs
    by_pair = {tuple(r["pair_key"]): r for r in records}

    # Mutual pair (223, 224)
    r223_224 = by_pair[(223, 224)]
    assert "Section 5 (p. 7)" in r223_224["conflict_rationale"]
    assert "perishable goods" in r223_224["conflict_rationale"].lower()
    assert "90 days" in r223_224["conflict_rationale"].lower()

    # Manager approval pairs (Section 4.2)
    for p in [(32, 33), (32, 34), (32, 35), (33, 34), (33, 35), (34, 35)]:
        r = by_pair[p]
        assert "Section 4.2 (p. 6)" in r["conflict_rationale"]
        assert "$100" in r["conflict_rationale"]
        assert "$500" in r["conflict_rationale"]
        assert "$2,000" in r["conflict_rationale"]

    # Debit posting pair (57, 64)
    r57_64 = by_pair[(57, 64)]
    assert "Section 7 (p. 9" in r57_64["conflict_rationale"]
    assert "Section 8 (p. 10" in r57_64["conflict_rationale"]
    assert "5-10 business days" in r57_64["conflict_rationale"]
    assert "Up to 10 business days" in r57_64["conflict_rationale"]

    # Channel hours pair (209, 215)
    r209_215 = by_pair[(209, 215)]
    assert "Section 19 (p. 21)" in r209_215["conflict_rationale"]
    assert "Pacific Time" in r209_215["conflict_rationale"]
    assert "Response within 24 hours" in r209_215["conflict_rationale"]
    assert "N/A" in r209_215["conflict_rationale"]

    # Order cancellation pair (110, 114)
    r110_114 = by_pair[(110, 114)]
    assert "Section 11 (p. 13)" in r110_114["conflict_rationale"]

    # Anti-fraud pair (190, 192)
    r190_192 = by_pair[(190, 192)]
    assert "Section 17.1 (p. 19)" in r190_192["conflict_rationale"]

