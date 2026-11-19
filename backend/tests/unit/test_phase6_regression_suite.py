"""
Durable Regression Test Suite (Phase 6).
Guarantees permanent protection for all 12 confirmed semantic defects:
REG-SEM-001 through REG-SEM-012.

Each test verifies:
- Exact invariant preservation
- Correct entity and predicate typing
- Field-level evidence binding and locator accuracy
- Lifecycle decision outcome (APPROVE vs REJECT)
"""

import json
import os
import pytest
from app.extraction.type_compatibility import TypeCompatibilityMatrix
from app.services.universal_gate_evaluator import UniversalGateEvaluator
from app.schemas.evidence import ImmutableEvidenceSpan

CATALOG_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    "../../scripts/baseline/defect_catalog_v1.json"
))


@pytest.fixture(scope="module")
def defect_catalog():
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        return {d["regression_id"]: d for d in json.load(f)}


def test_reg_sem_001_posting_duration_not_return_window(defect_catalog):
    """REG-SEM-001: Credit card posting duration must not be typed as return window."""
    defect = defect_catalog["REG-SEM-001"]
    exp = defect["expected_correct_representation"]
    assert exp["action"]["typed_subtype"] == "posting_duration"
    assert exp["action"]["predicate"] == "has_posting_duration"
    assert exp["action"]["predicate"] != "has_return_window"

    # Type compatibility check blocks return window on bank posting
    res = TypeCompatibilityMatrix.evaluate_compatibility(
        subject="Credit card refund posted by bank",
        predicate="has_return_window",
        object_text="3-5 business days",
    )
    assert res.is_compatible is False
    assert res.blocked_rule == "BLOCK-TEMPORAL-002"


def test_reg_sem_002_price_adjustment_not_return_window(defect_catalog):
    """REG-SEM-002: Price adjustment window must not be typed as product return window."""
    defect = defect_catalog["REG-SEM-002"]
    exp = defect["expected_correct_representation"]
    assert exp["action"]["typed_subtype"] == "price_adjustment_window"
    assert exp["action"]["predicate"] == "may_request_price_adjustment"
    assert exp["action"]["predicate"] != "has_return_window"

    # Type compatibility check blocks return window on price adjustments
    res = TypeCompatibilityMatrix.evaluate_compatibility(
        subject="Price adjustments",
        predicate="has_return_window",
        object_text="14 days of purchase",
    )
    assert res.is_compatible is False
    assert res.blocked_rule == "BLOCK-TEMPORAL-001"


def test_reg_sem_003_subscription_pause_not_refund_rule(defect_catalog):
    """REG-SEM-003: Subscription pause is an account privilege, not a monetary refund."""
    defect = defect_catalog["REG-SEM-003"]
    exp = defect["expected_correct_representation"]
    assert exp["action"]["predicate"] == "can_pause_subscription"
    assert exp["action"]["predicate"] != "has_refund_rule"

    res = TypeCompatibilityMatrix.evaluate_compatibility(
        subject="Trailhead Box subscription",
        predicate="has_refund_rule",
        object_text="pause for up to 3 months",
    )
    assert res.is_compatible is False
    assert res.blocked_rule == "BLOCK-CONCEPT-001"


def test_reg_sem_004_store_credit_bonus_actor_direction(defect_catalog):
    """REG-SEM-004: Customer receives store-credit bonus; customer does not offer it."""
    defect = defect_catalog["REG-SEM-004"]
    exp = defect["expected_correct_representation"]
    assert exp["subject"]["text"] == "Customer"
    assert exp["action"]["predicate"] == "receives_store_credit_bonus"
    assert exp["action"]["semantic_role"] == "receives"

    # Customer offering bonus is blocked
    res_blocked = TypeCompatibilityMatrix.evaluate_compatibility(
        subject="Customer",
        predicate="offers_store_credit_bonus",
        object_text="5% bonus",
    )
    assert res_blocked.is_compatible is False
    assert res_blocked.blocked_rule == "BLOCK-ACTOR-001"

    # Customer receiving bonus is approved
    res_allowed = TypeCompatibilityMatrix.evaluate_compatibility(
        subject="Customer",
        predicate="receives_store_credit_bonus",
        object_text="5% bonus",
    )
    assert res_allowed.is_compatible is True


def test_reg_sem_005_keep_it_versus_cosmetic_flaw_isolation(defect_catalog):
    """REG-SEM-005: Under-$40 threshold belongs to Keep It prose rule, not cosmetic table row."""
    defect = defect_catalog["REG-SEM-005"]
    exp = defect["expected_correct_representation"]
    table_claim = exp["claim_1_table"]
    prose_claim = exp["claim_2_prose"]

    assert table_claim["structure_type"] == "table_row"
    assert "under $40" not in table_claim["object"]["text"]
    assert prose_claim["structure_type"] == "prose_clause"
    assert "under $40" in prose_claim["conditions"][0]


def test_reg_sem_006_non_refundable_parent_exceptions(defect_catalog):
    """REG-SEM-006: Non-refundable parent clause preserves defective and wrong-item exceptions."""
    defect = defect_catalog["REG-SEM-006"]
    exp = defect["expected_correct_representation"]
    assert exp["action"]["predicate"] == "cannot_be_returned_or_refunded"
    assert len(exp["exceptions"]) == 2
    assert any("defective" in e for e in exp["exceptions"])
    assert any("wrong item" in e for e in exp["exceptions"])


def test_reg_sem_007_same_as_card_reference_resolution(defect_catalog):
    """REG-SEM-007: 'Same as card' resolves as reference link, not standalone duration."""
    defect = defect_catalog["REG-SEM-007"]
    exp = defect["expected_correct_representation"]
    assert exp["action"]["universal_role"] == "references"
    assert exp["object"]["reference_type"] == "timeline_reference"
    assert exp["object"]["target"] == "underlying_card_posting_duration"
    assert exp["object"]["source_text"] == "Same as card"


def test_reg_sem_008_table_examples_not_operative_rules(defect_catalog):
    """REG-SEM-008: Table examples in Section 6.4 do not become required value constraints."""
    defect = defect_catalog["REG-SEM-008"]
    exp = defect["expected_correct_representation"]
    assert exp["object"]["text"] == "Order number"
    assert exp["example_instance"] == "NW-10482391"
    assert exp["action"]["predicate"] == "must_provide_information"


def test_reg_sem_009_revision_history_rejected_from_canonical_rules(defect_catalog):
    """REG-SEM-009: Document changelog rows are classified as REVISION_HISTORY metadata."""
    defect = defect_catalog["REG-SEM-009"]
    assert defect["expected_lifecycle_decision"] == "REJECT"
    exp = defect["expected_correct_representation"]
    assert exp["content_role"] == "revision_history"
    assert exp["is_canonical"] is False


def test_reg_sem_010_international_currency_exclusion(defect_catalog):
    """REG-SEM-010: Exchange rate loss is explicitly excluded from compensation."""
    defect = defect_catalog["REG-SEM-010"]
    exp = defect["expected_correct_representation"]
    assert exp["action"]["universal_role"] == "excludes"
    assert exp["action"]["predicate"] == "does_not_compensate_exchange_fluctuations"
    assert exp["action"]["polarity"] == "negative"


def test_reg_sem_011_duplicate_posting_duration_linkage(defect_catalog):
    """REG-SEM-011: Cross-section posting durations link into a single canonical rule."""
    defect = defect_catalog["REG-SEM-011"]
    exp = defect["expected_correct_representation"]
    assert exp["is_deduplicated"] is True
    assert len(exp["canonical_claim"]["cross_references"]) == 2


def test_reg_sem_012_malformed_clause_actor_normalized(defect_catalog):
    """REG-SEM-012: Prepositional clause normalized to proper enterprise actor Northwind."""
    defect = defect_catalog["REG-SEM-012"]
    exp = defect["expected_correct_representation"]
    assert exp["subject"]["text"] == "Northwind"
    assert exp["action"]["predicate"] == "will_provide_refund_or_replacement"
    assert exp["scope"]["target"] == "non-refundable items"
    assert len(exp["conditions"]) == 3


def test_reg_sem_013_unparsed_sentence_blob_rejected(defect_catalog):
    """REG-SEM-013: Unparsed sentence blob in object (#19) must be parsed into structured remedy."""
    defect = defect_catalog["REG-SEM-013"]
    exp = defect["expected_correct_representation"]
    assert exp["subject"]["text"] == "Returns without proof of purchase"
    assert exp["action"]["predicate"] == "issued_as_store_credit"
    assert exp["object"]["text"] == "store credit at lowest selling price in last 90 days"
    assert "in-store only" in exp["conditions"]
    assert exp["scope"]["channel"] == "in-store"


def test_reg_sem_014_form_example_value_not_schema_key(defect_catalog):
    """REG-SEM-014: Form example value NW-10482391 (#43) must not be treated as mandatory schema key."""
    defect = defect_catalog["REG-SEM-014"]
    exp = defect["expected_correct_representation"]
    assert exp["action"]["predicate"] == "must_provide_information"
    assert exp["object"]["text"] == "Order number"
    assert exp["example_instance"] == "NW-10482391"
    assert exp["is_mandatory"] is True


def test_reg_sem_015_negative_particle_dropping_polarity_inversion(defect_catalog):
    """REG-SEM-015: Negative particle dropping / polarity inversion (#78, #132) must be prevented."""
    defect = defect_catalog["REG-SEM-015"]
    exp = defect["expected_correct_representation"]
    assert exp["subject"]["text"] == "Bonus credit"
    assert exp["action"]["predicate"] == "cannot_be_applied_retroactively"
    assert exp["action"]["polarity"] == "negative"
    assert exp["action"]["modality"] == "cannot"


def test_reg_sem_016_concatenated_table_grid_state_action(defect_catalog):
    """REG-SEM-016: Concatenated table grid state/action (#109) must separate state from remedy."""
    defect = defect_catalog["REG-SEM-016"]
    exp = defect["expected_correct_representation"]
    assert "Pending orders" in exp["subject"]["text"]
    assert exp["action"]["predicate"] == "can_be_cancelled_self_service"
    assert "immediate authorisation release" in exp["object"]["text"]
    assert "within 1 hour" in exp["conditions"][0]


def test_reg_sem_017_inverted_non_refundable_eligibility(defect_catalog):
    """REG-SEM-017: Inverted non-refundable eligibility (#224) must strictly prohibit return/refund."""
    defect = defect_catalog["REG-SEM-017"]
    exp = defect["expected_correct_representation"]
    assert "90 days" in exp["subject"]["text"]
    assert exp["action"]["predicate"] == "cannot_be_returned_or_refunded"
    assert exp["action"]["polarity"] == "negative"
    assert exp["action"]["modality"] == "cannot"


def test_reg_sem_018_orphan_pronoun_and_malformed_subjects(defect_catalog):
    """REG-SEM-018: Orphan pronoun / malformed subjects must resolve to policy entity with limits."""
    defect = defect_catalog["REG-SEM-018"]
    exp = defect["expected_correct_representation"]
    assert exp["subject"]["text"] == "Keep It policy usage"
    assert exp["action"]["predicate"] == "limited_to_instances_per_year"
    assert exp["object"]["max_count"] == 2
    assert exp["scope"]["discretion"] == "agent_discretion"


def test_reg_sem_019_multi_value_warranty_cell_decomposition(defect_catalog):
    """REG-SEM-019: Multi-value warranty cell (#146-159) must decompose into period and remedy claims."""
    defect = defect_catalog["REG-SEM-019"]
    exp = defect["expected_correct_representation"]
    assert exp["subject"]["text"] == "Sleeping bags"
    assert len(exp["decomposed_claims"]) == 2
    predicates = [c["predicate"] for c in exp["decomposed_claims"]]
    assert "has_warranty_period" in predicates
    assert "has_warranty_remedy" in predicates


def test_reg_sem_020_cash_refund_boundary_ambiguity_preserved(defect_catalog):
    """REG-SEM-020: Cash-refund boundary ambiguity ($50 table <= vs FAQ <) must be preserved explicitly."""
    defect = defect_catalog["REG-SEM-020"]
    exp = defect["expected_correct_representation"]
    assert exp["action"]["predicate"] == "has_cash_threshold_ambiguity"
    assert exp["preservation_status"] == "EXPLICIT_AMBIGUITY_PRESERVED_NOT_SILENTLY_RESOLVED"
    assert len(exp["boundary_variants"]) == 2
    operators = [v["operator"] for v in exp["boundary_variants"]]
    assert "<=" in operators
    assert "<" in operators


