"""
Phase 5 Step 5.2 Unit Tests: Extended Predicate Registry, Domain Schemas, and Modality Calibration.

Tests:
1. Registration of all 32 extended domain predicates across FAM-1, FAM-2, FAM-3, FAM-4.
2. Domain schema role constraints and SPO validation for each family.
3. Banned generic predicate rejection (Gate Family 2).
4. Dynamic modality extractor calibration for legal, billing, and administrative vernacular.
5. Absolute non-regression of baseline Northwind predicates.
"""

import pytest
from app.taxonomy.registry import PredicateRegistryService
from app.taxonomy.domain_schemas import DomainSchemaValidator, DOMAIN_SCHEMAS
from app.services.dynamic_modality_extractor import DynamicModalityExtractor
from app.schemas.universal_claim import ModalityType


def test_extended_predicates_registered_all_families():
    service = PredicateRegistryService()

    # Sample predicates from each family
    fam1_preds = [
        "has_indemnification_obligation",
        "has_liability_cap",
        "has_governing_law",
        "has_confidentiality_duration",
        "has_ip_ownership_assignment",
        "has_termination_for_convenience",
        "has_warranty_disclaimer",
        "has_dispute_resolution_forum",
    ]
    fam2_preds = [
        "has_notice_period",
        "has_notice_period_waiver_authority",
        "has_severance_eligibility",
        "requires_written_resignation",
        "has_pto_cashout_policy",
        "requires_property_return_on_exit",
        "has_buyout_calculation_basis",
        "has_garden_leave_option",
    ]
    fam3_preds = [
        "has_invoice_payment_terms",
        "has_late_payment_penalty_rate",
        "has_billing_currency",
        "has_tax_rate",
        "has_billing_dispute_window",
        "requires_purchase_order_reference",
        "has_credit_memo_issuance_policy",
        "has_remittance_bank_details",
    ]
    fam4_preds = [
        "cannot_claim_regularisation",
        "has_maximum_contract_tenure",
        "has_statutory_remuneration_ceiling",
        "requires_mandatory_compliance_audit",
        "has_breach_notification_deadline",
        "has_whistleblower_protection",
        "is_subject_to_administrative_review",
        "requires_human_rights_due_diligence",
    ]

    all_preds = fam1_preds + fam2_preds + fam3_preds + fam4_preds
    for p in all_preds:
        defn = service.get_predicate(p)
        assert defn is not None, f"Predicate '{p}' not registered in taxonomy"
        assert defn.action_category in [
            "INDEMNIFICATION", "LIABILITY", "GOVERNANCE", "CONFIDENTIALITY",
            "IP_ASSIGNMENT", "TERMINATION", "WARRANTY", "PROCEDURAL",
            "NOTICE", "POLICY_REMEDY", "FINANCIAL", "OPERATIONAL",
            "PAYMENT", "TAX", "RESTRICTIONS", "AUDIT", "COMPLIANCE"
        ]


def test_domain_schema_role_validation():
    # FAM-1 Contract validation
    res1 = DomainSchemaValidator.validate_spo(
        family_id="FAM-1",
        subject_role="VENDOR",
        predicate_id="has_indemnification_obligation",
        object_role="LIABILITY",
    )
    assert res1["is_valid"] is True

    # FAM-2 HR Policy validation
    res2 = DomainSchemaValidator.validate_spo(
        family_id="FAM-2",
        subject_role="EMPLOYEE",
        predicate_id="has_notice_period",
        object_role="DURATION_DAYS",
    )
    assert res2["is_valid"] is True

    # FAM-3 Invoice validation
    res3 = DomainSchemaValidator.validate_spo(
        family_id="FAM-3",
        subject_role="BILLING_ACCOUNT",
        predicate_id="has_invoice_payment_terms",
        object_role="DUE_DAYS",
    )
    assert res3["is_valid"] is True

    # FAM-4 Statutory validation
    res4 = DomainSchemaValidator.validate_spo(
        family_id="FAM-4",
        subject_role="CONTRACT_APPOINTEE",
        predicate_id="cannot_claim_regularisation",
        object_role="REGULARISATION",
    )
    assert res4["is_valid"] is True


def test_banned_generic_predicates_rejected():
    for fam_id in ["FAM-1", "FAM-2", "FAM-3", "FAM-4"]:
        for banned in ["has_summary", "has_clause", "complies_with"]:
            res = DomainSchemaValidator.validate_spo(
                family_id=fam_id,
                subject_role="ANY_PARTY",
                predicate_id=banned,
                object_role="ANY_OBJECT",
            )
            assert res["is_valid"] is False
            assert "banned generic predicate" in res["reason"]


def test_modality_extractor_calibration_legal_administrative():
    # Legal prohibition
    mod1 = DynamicModalityExtractor.extract_modality(
        "Contract appointees shall not be entitled to claim regularisation or absorption in government service."
    )
    assert mod1 == ModalityType.MUST_NOT

    # Billing obligation
    mod2 = DynamicModalityExtractor.extract_modality(
        "Payment is due within 30 days from date of invoice."
    )
    assert mod2 == ModalityType.MUST

    # Contractual indemnification obligation
    mod3 = DynamicModalityExtractor.extract_modality(
        "Vendor shall indemnify and hold harmless customer from any third party claims."
    )
    assert mod3 == ModalityType.MUST

    # Discretionary waiver permission
    mod4 = DynamicModalityExtractor.extract_modality(
        "The Vice President shall have discretion to waive the notice period under business exigencies."
    )
    assert mod4 == ModalityType.MAY

    # Entitlement
    mod5 = DynamicModalityExtractor.extract_modality(
        "Terminated employees shall be entitled to receive severance pay based on tenure."
    )
    assert mod5 == ModalityType.ENTITLED_TO


def test_northwind_predicate_non_regression():
    service = PredicateRegistryService()
    northwind_preds = [
        "has_return_window",
        "has_refund_method",
        "has_fee_rule",
        "has_cancellation_window",
        "has_content_view_refund_window",
        "has_warranty_period",
    ]
    for p in northwind_preds:
        assert PredicateRegistryService.exists(p) is True, f"Northwind predicate '{p}' was unexpectedly removed"
