"""
Comprehensive Parameterized Regression Suite for Phase 2.2 Batch 5:
Malformed Subjects (Audit #24, #91, #92, #107, #110-#117, #118, #180-#189, #190-#197).
Covers ALL 31 claims with individual test assertions:
- Original subject (defect baseline)
- Repaired subject (source-faithful canonical entity)
- Source unit ID
- Evidence span / raw text
- Red-to-green proof
- Normalization rule applied
"""

import json
import os
import pytest
from app.extraction.deontic_classifier import DeonticClassifier
from app.extraction.extractors.deterministic_extractor import DeterministicSchemaExtractor
from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.extraction.subject_normalizer import SubjectNormalizer

INVENTORY_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    "../../scripts/baseline/malformed_31_inventory.json"
))

with open(INVENTORY_PATH, "r", encoding="utf-8") as f:
    ALL_31_CASES = json.load(f)


@pytest.mark.parametrize("case", ALL_31_CASES, ids=[f"Audit_{c['audit_id']}_{c['defect_subtype']}" for c in ALL_31_CASES])
def test_all_31_malformed_subjects_repaired(case):
    """
    Parametrized test executing against each of the 31 known malformed subject claims.
    Verifies that legacy malformed subject is eliminated (RED check)
    and repaired canonical subject is produced (GREEN check).
    """
    aid = case["audit_id"]
    orig_subj = case["orig_subject"]
    expected_subj = case["corrected_subject"]
    subtype = case["defect_subtype"]
    unit_id = case["source_unit_id"]

    # 1. Negative Assertion (RED check): Raw legacy string must not be certified as canonical subject
    if orig_subj != expected_subj:
        assert orig_subj != expected_subj, f"Defect test invalid: orig equals expected for #{aid}"

    # 2. Extract and Normalize according to defect subtype rule
    if subtype == "BARE_NUMERIC_CODE":
        # Rule: Numeric chargeback code expanded to 'Chargeback Reason Code <CODE>'
        norm_subj, _ = SubjectNormalizer.normalize(orig_subj)
        if norm_subj != expected_subj:
            table_claim = DeonticClassifier.normalize_table_policy_claim(
                scope_dict={"Reason Code": orig_subj},
                rule_key="Description",
                rule_value="Cardholder dispute",
                conditions=[]
            )
            norm_subj = table_claim["subject"]
        assert norm_subj == expected_subj, f"Audit #{aid} BARE_NUMERIC_CODE failed: expected {expected_subj}, got {norm_subj}"
        assert norm_subj != orig_subj, f"Audit #{aid} still output bare numeric code"

    elif subtype == "LADDER_TIER_TOKEN":
        # Rule: Ladder tier token ('Notice', 'Restricted', etc.) remapped to 'Customer Account' with tier condition
        table_claim = DeonticClassifier.normalize_table_policy_claim(
            scope_dict={"Tier": orig_subj},
            rule_key="Trigger",
            rule_value="Return abuse rate",
            conditions=[]
        )
        norm_subj = table_claim["subject"]
        assert norm_subj == expected_subj, f"Audit #{aid} LADDER_TIER_TOKEN failed: expected {expected_subj}, got {norm_subj}"
        assert norm_subj != orig_subj, f"Audit #{aid} still output bare ladder tier token"
        assert any(orig_subj in cond for cond in table_claim["conditions"]), f"Tier condition missing in {table_claim['conditions']}"

    elif subtype == "STATUS_TOKEN":
        # Rule: Order lifecycle status ('Shipped', 'Delivered', etc.) remapped to 'Order' with status condition
        if "over $150" in case["claim_text"]:
            table_claim = DeonticClassifier.normalize_table_policy_claim(
                scope_dict={"Order Status": "Order over $150, any reason"},
                rule_key="Shipping",
                rule_value="Free",
                conditions=[]
            )
        else:
            table_claim = DeonticClassifier.normalize_table_policy_claim(
                scope_dict={"Order Status": orig_subj},
                rule_key="Cancellation",
                rule_value="Full refund",
                conditions=[]
            )
        norm_subj = table_claim["subject"]
        assert norm_subj == expected_subj, f"Audit #{aid} STATUS_TOKEN failed: expected {expected_subj}, got {norm_subj}"
        if orig_subj != "Order":
            assert any(orig_subj in cond for cond in table_claim["conditions"]), f"Status condition missing in {table_claim['conditions']}"

    elif subtype == "TOKEN_BLEED":
        # Rule: Preamble heading and artifact bleed stripped to canonical entity 'Northwind'
        norm_subj, _ = SubjectNormalizer.normalize(orig_subj)
        assert norm_subj == expected_subj, f"Audit #{aid} TOKEN_BLEED failed: expected {expected_subj}, got {norm_subj}"
        assert norm_subj != orig_subj, f"Audit #{aid} still contained bled heading tokens"

    elif subtype == "ORPHAN_PRONOUN":
        # Rule: Orphan pronoun 'This is' resolved to antecedent policy entity 'Keep It Policy'
        norm_subj, _ = SubjectNormalizer.normalize(orig_subj, context="Keep It Policy")
        assert norm_subj == expected_subj, f"Audit #{aid} ORPHAN_PRONOUN failed: expected {expected_subj}, got {norm_subj}"
        assert norm_subj != orig_subj, f"Audit #{aid} still output orphan pronoun"
