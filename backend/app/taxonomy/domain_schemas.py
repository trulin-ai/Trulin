"""
Phase 5 Domain Schema Definitions per Document Family.

Provides:
1. Per-family domain specifications (FAM-1, FAM-2, FAM-3, FAM-4).
2. Allowed subject roles, object roles, and semantic constraints.
3. Family-aware SPO validation logic for Universal Gate Contract compliance.
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Set
from pydantic import BaseModel, Field


class DocumentFamily(str, Enum):
    CONTRACTS = "FAM-1"
    HR_POLICIES = "FAM-2"
    INVOICES = "FAM-3"
    STATUTORY = "FAM-4"


class ObjectType(str, Enum):
    CURRENCY = "CURRENCY"
    DURATION_DAYS = "DURATION_DAYS"
    DURATION_YEARS = "DURATION_YEARS"
    PERCENTAGE = "PERCENTAGE"
    LEGAL_FORUM = "LEGAL_FORUM"
    ROLE_SPECIFICATION = "ROLE_SPECIFICATION"
    DOCUMENT_REQUIREMENT = "DOCUMENT_REQUIREMENT"
    TEXT_SPECIFICATION = "TEXT_SPECIFICATION"


class FamilyDomainSchema(BaseModel):
    family_id: str
    family_name: str
    target_recall: float
    target_lifecycle: float
    allowed_subject_roles: List[str]
    allowed_object_roles: List[str]
    core_predicates: List[str]
    prohibited_generic_predicates: List[str] = Field(
        default_factory=lambda: [
            "has_summary",
            "has_clause",
            "is_clause",
            "complies_with",
            "governs_contract_validity",
            "has_rule",
        ]
    )


DOMAIN_SCHEMAS: Dict[str, FamilyDomainSchema] = {
    "FAM-1": FamilyDomainSchema(
        family_id="FAM-1",
        family_name="Commercial Contracts & MSAs",
        target_recall=0.90,
        target_lifecycle=0.95,
        allowed_subject_roles=[
            "VENDOR", "CUSTOMER", "CONTRACTING_PARTY", "LICENSOR", "LICENSEE",
            "AFFILIATE", "DEVELOPER", "EITHER_PARTY", "RECIPIENT", "DISCLOSING_PARTY", "ANY_PARTY"
        ],
        allowed_object_roles=[
            "LIABILITY", "LOSSES", "CLAIMS", "FEES_PAID", "DOLLAR_AMOUNT",
            "DIRECT_DAMAGES", "JURISDICTION", "STATE_LAW", "LEGAL_FORUM",
            "DURATION_YEARS", "SURVIVAL_PERIOD", "DELIVERABLES", "WORK_PRODUCT",
            "PATENTS", "NOTICE_PERIOD", "CONVENIENCE_TERMS", "IMPLIED_WARRANTIES",
            "MERCHANTABILITY", "FITNESS", "ARBITRATION", "VENUE", "COURT", "ANY_OBJECT"
        ],
        core_predicates=[
            "has_indemnification_obligation",
            "has_liability_cap",
            "has_governing_law",
            "has_confidentiality_duration",
            "has_ip_ownership_assignment",
            "has_termination_for_convenience",
            "has_warranty_disclaimer",
            "has_dispute_resolution_forum",
            "grants_product_license",
            "must_not_reverse_engineer",
        ],
    ),
    "FAM-2": FamilyDomainSchema(
        family_id="FAM-2",
        family_name="HR & Employment Policies",
        target_recall=0.95,
        target_lifecycle=0.98,
        allowed_subject_roles=[
            "EMPLOYEE", "EXECUTIVE", "STAFF", "MANAGEMENT", "HR_OPERATIONS",
            "VICE_PRESIDENT", "TERMINATED_STAFF", "RESIGNING_STAFF", "EXITING_STAFF",
            "COMPANY", "EMPLOYER", "CXO", "SENIOR_MANAGEMENT", "ANY_PARTY"
        ],
        allowed_object_roles=[
            "DURATION_DAYS", "NOTICE_WINDOW", "WAIVER_APPROVAL", "CONDITIONS",
            "SEVERANCE_PAY", "WEEKS_SALARY", "WRITTEN_NOTICE", "FORMAL_LETTER",
            "ACCRUED_VACATION", "UNPAID_PTO", "COMPANY_PROPERTY", "EQUIPMENT",
            "KEYS_AND_BADGES", "BASIC_SALARY", "GROSS_PAY", "SHORTFALL_DAYS",
            "GARDEN_LEAVE", "RESTRICTED_DUTIES", "ANY_OBJECT"
        ],
        core_predicates=[
            "has_notice_period",
            "has_notice_period_waiver_authority",
            "has_severance_eligibility",
            "requires_written_resignation",
            "has_pto_cashout_policy",
            "requires_property_return_on_exit",
            "has_buyout_calculation_basis",
            "has_garden_leave_option",
        ],
    ),
    "FAM-3": FamilyDomainSchema(
        family_id="FAM-3",
        family_name="Invoices & Commercial Billing",
        target_recall=0.95,
        target_lifecycle=0.98,
        allowed_subject_roles=[
            "BUYER", "CUSTOMER", "BILLING_ACCOUNT", "INVOICE", "INVOICE_LINE_ITEM",
            "TOTAL_DUE", "SELLER", "VENDOR", "PAYMENT_GATEWAY", "ANY_PARTY"
        ],
        allowed_object_roles=[
            "PAYMENT_WINDOW", "DUE_DAYS", "NET_TERMS", "PENALTY_RATE",
            "MONTHLY_PERCENT", "INTEREST", "CURRENCY_CODE", "USD", "EUR",
            "VAT_RATE", "SALES_TAX", "TAX_AMOUNT", "DISPUTE_DAYS", "AUDIT_WINDOW",
            "PO_NUMBER", "ORDER_IDENTIFIER", "CREDIT_MEMO", "ADJUSTED_AMOUNT",
            "BANK_ACCOUNT", "IBAN_SWIFT", "ROUTING", "ANY_OBJECT"
        ],
        core_predicates=[
            "has_invoice_payment_terms",
            "has_late_payment_penalty_rate",
            "has_billing_currency",
            "has_tax_rate",
            "has_billing_dispute_window",
            "requires_purchase_order_reference",
            "has_credit_memo_issuance_policy",
            "has_remittance_bank_details",
        ],
    ),
    "FAM-4": FamilyDomainSchema(
        family_id="FAM-4",
        family_name="Statutory & Compliance Guidelines",
        target_recall=0.90,
        target_lifecycle=0.95,
        allowed_subject_roles=[
            "CONTRACT_APPOINTEE", "TEMPORARY_STAFF", "GOVERNMENT_ENGAGEMENT",
            "GOVERNMENT_DEPARTMENT", "SUPPLIER", "VENDOR", "DATA_PROCESSOR",
            "REPORTING_PARTY", "EMPLOYEE", "CONTRACTUAL_ENGAGEMENT", "APPOINTMENT",
            "ENTERPRISE", "ANY_PARTY"
        ],
        allowed_object_roles=[
            "REGULARISATION", "ABSORPTION", "PERMANENT_STATUS", "DURATION_YEARS",
            "MAX_TERM", "MONTHLY_CEILING", "REMUNERATION_CAP", "ANNUAL_AUDIT",
            "INDEPENDENT_ASSESSMENT", "NOTIFICATION_HOURS", "72_HOURS", "DEADLINE",
            "NON_RETALIATION", "CONFIDENTIALITY", "GOVERNMENT_REVIEW",
            "ADMINISTRATIVE_EXIGENCY", "DUE_DILIGENCE_REPORT", "LABOR_ASSESSMENT", "ANY_OBJECT"
        ],
        core_predicates=[
            "cannot_claim_regularisation",
            "has_maximum_contract_tenure",
            "has_statutory_remuneration_ceiling",
            "requires_mandatory_compliance_audit",
            "has_breach_notification_deadline",
            "has_whistleblower_protection",
            "is_subject_to_administrative_review",
            "requires_human_rights_due_diligence",
        ],
    ),
}


class DomainSchemaValidator:
    """Validates claims against family-specific domain schemas."""

    @classmethod
    def get_schema(cls, family_id: str) -> Optional[FamilyDomainSchema]:
        return DOMAIN_SCHEMAS.get(family_id)

    @classmethod
    def validate_spo(
        cls,
        family_id: str,
        subject_role: str,
        predicate_id: str,
        object_role: str,
    ) -> Dict[str, Any]:
        schema = cls.get_schema(family_id)
        if not schema:
            return {"is_valid": False, "reason": f"Unknown document family: {family_id}"}

        pid = (predicate_id or "").strip().lower()

        # Check banned generic predicates
        if pid in schema.prohibited_generic_predicates:
            return {
                "is_valid": False,
                "reason": f"Predicate '{predicate_id}' is banned generic predicate in family {family_id}",
            }

        # Check subject role
        s_upper = (subject_role or "").strip().upper()
        if "ANY_PARTY" not in schema.allowed_subject_roles and s_upper not in schema.allowed_subject_roles:
            return {
                "is_valid": False,
                "reason": f"Subject role '{subject_role}' not permitted in family {family_id}",
            }

        # Check object role
        o_upper = (object_role or "").strip().upper()
        if "ANY_OBJECT" not in schema.allowed_object_roles and o_upper not in schema.allowed_object_roles:
            return {
                "is_valid": False,
                "reason": f"Object role '{object_role}' not permitted in family {family_id}",
            }

        return {"is_valid": True, "reason": None}
