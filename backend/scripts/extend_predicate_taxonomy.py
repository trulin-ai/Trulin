import json
from pathlib import Path

path = Path(__file__).resolve().parent.parent / "app" / "taxonomy" / "predicates.v1.json"
with open(path, "r", encoding="utf-8") as f:
    data = json.load(f)

new_predicates = [
    # FAM-1: Commercial Contracts & MSAs
    {
        "predicate_id": "has_indemnification_obligation",
        "label": "Obligates indemnification for third-party claims and liabilities",
        "action_category": "INDEMNIFICATION",
        "allowed_subject_roles": ["VENDOR", "CUSTOMER", "CONTRACTING_PARTY", "ANY_PARTY"],
        "allowed_object_roles": ["LIABILITY", "LOSSES", "CLAIMS", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "HIGH"
    },
    {
        "predicate_id": "has_liability_cap",
        "label": "Defines maximum aggregate liability limitation dollar ceiling",
        "action_category": "LIABILITY",
        "allowed_subject_roles": ["VENDOR", "CUSTOMER", "CONTRACTING_PARTY", "ANY_PARTY"],
        "allowed_object_roles": ["FEES_PAID", "DOLLAR_AMOUNT", "DIRECT_DAMAGES", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "HIGH"
    },
    {
        "predicate_id": "has_governing_law",
        "label": "Specifies governing jurisdiction and applicable law",
        "action_category": "GOVERNANCE",
        "allowed_subject_roles": ["CONTRACTING_PARTY", "AGREEMENT", "ANY_PARTY"],
        "allowed_object_roles": ["JURISDICTION", "STATE_LAW", "LEGAL_FORUM", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "LOW"
    },
    {
        "predicate_id": "has_confidentiality_duration",
        "label": "Specifies confidentiality and non-disclosure survival term",
        "action_category": "CONFIDENTIALITY",
        "allowed_subject_roles": ["RECEIVING_PARTY", "DISCLOSING_PARTY", "ANY_PARTY"],
        "allowed_object_roles": ["DURATION_YEARS", "SURVIVAL_PERIOD", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "MEDIUM"
    },
    {
        "predicate_id": "has_ip_ownership_assignment",
        "label": "Assigns ownership of intellectual property or work product deliverables",
        "action_category": "IP_ASSIGNMENT",
        "allowed_subject_roles": ["VENDOR", "CUSTOMER", "DEVELOPER", "ANY_PARTY"],
        "allowed_object_roles": ["DELIVERABLES", "WORK_PRODUCT", "PATENTS", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "HIGH"
    },
    {
        "predicate_id": "has_termination_for_convenience",
        "label": "Permits agreement termination without cause upon written notice",
        "action_category": "TERMINATION",
        "allowed_subject_roles": ["CUSTOMER", "VENDOR", "EITHER_PARTY", "ANY_PARTY"],
        "allowed_object_roles": ["NOTICE_PERIOD", "CONVENIENCE_TERMS", "ANY_OBJECT"],
        "default_modality": "MAY",
        "requires_condition": True,
        "risk_level": "HIGH"
    },
    {
        "predicate_id": "has_warranty_disclaimer",
        "label": "Disclaims implied warranties of merchantability and fitness",
        "action_category": "WARRANTY",
        "allowed_subject_roles": ["VENDOR", "LICENSOR", "ANY_PARTY"],
        "allowed_object_roles": ["IMPLIED_WARRANTIES", "MERCHANTABILITY", "FITNESS", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "MEDIUM"
    },
    {
        "predicate_id": "has_dispute_resolution_forum",
        "label": "Mandates forum, venue, or binding arbitration for legal disputes",
        "action_category": "PROCEDURAL",
        "allowed_subject_roles": ["CONTRACTING_PARTY", "ANY_PARTY"],
        "allowed_object_roles": ["ARBITRATION", "VENUE", "COURT", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "MEDIUM"
    },

    # FAM-2: HR & Employment Policies
    {
        "predicate_id": "has_notice_period",
        "label": "Defines mandatory resignation or termination notice period duration",
        "action_category": "NOTICE",
        "allowed_subject_roles": ["EMPLOYEE", "EXECUTIVE", "STAFF", "MANAGEMENT", "ANY_PARTY"],
        "allowed_object_roles": ["DURATION_DAYS", "NOTICE_WINDOW", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "MEDIUM"
    },
    {
        "predicate_id": "has_notice_period_waiver_authority",
        "label": "Designates executive role authorized to waive notice period requirements",
        "action_category": "PROCEDURAL",
        "allowed_subject_roles": ["MANAGEMENT", "HR_OPERATIONS", "VICE_PRESIDENT", "ANY_PARTY"],
        "allowed_object_roles": ["WAIVER_APPROVAL", "CONDITIONS", "ANY_OBJECT"],
        "default_modality": "MAY",
        "requires_condition": True,
        "risk_level": "HIGH"
    },
    {
        "predicate_id": "has_severance_eligibility",
        "label": "Specifies severance pay entitlement upon termination without cause",
        "action_category": "POLICY_REMEDY",
        "allowed_subject_roles": ["EMPLOYEE", "TERMINATED_STAFF", "ANY_PARTY"],
        "allowed_object_roles": ["SEVERANCE_PAY", "WEEKS_SALARY", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": True,
        "risk_level": "MEDIUM"
    },
    {
        "predicate_id": "requires_written_resignation",
        "label": "Mandates resignation notice must be formally submitted in writing",
        "action_category": "PROCEDURAL",
        "allowed_subject_roles": ["EMPLOYEE", "RESIGNING_STAFF", "ANY_PARTY"],
        "allowed_object_roles": ["WRITTEN_NOTICE", "FORMAL_LETTER", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "LOW"
    },
    {
        "predicate_id": "has_pto_cashout_policy",
        "label": "Defines policy on accrued unused paid time off payout upon separation",
        "action_category": "FINANCIAL",
        "allowed_subject_roles": ["EMPLOYEE", "TERMINATED_STAFF", "ANY_PARTY"],
        "allowed_object_roles": ["ACCRUED_VACATION", "UNPAID_PTO", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "MEDIUM"
    },
    {
        "predicate_id": "requires_property_return_on_exit",
        "label": "Mandates immediate return of company property, equipment, and badges on exit",
        "action_category": "OPERATIONAL",
        "allowed_subject_roles": ["EMPLOYEE", "EXITING_STAFF", "ANY_PARTY"],
        "allowed_object_roles": ["COMPANY_PROPERTY", "EQUIPMENT", "KEYS_AND_BADGES", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "LOW"
    },
    {
        "predicate_id": "has_buyout_calculation_basis",
        "label": "Defines formula for notice period shortfall salary buyout calculation",
        "action_category": "FINANCIAL",
        "allowed_subject_roles": ["EMPLOYEE", "COMPANY", "ANY_PARTY"],
        "allowed_object_roles": ["BASIC_SALARY", "GROSS_PAY", "SHORTFALL_DAYS", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "MEDIUM"
    },
    {
        "predicate_id": "has_garden_leave_option",
        "label": "Permits company to place resigning employee on paid garden leave",
        "action_category": "OPERATIONAL",
        "allowed_subject_roles": ["COMPANY", "EMPLOYER", "ANY_PARTY"],
        "allowed_object_roles": ["GARDEN_LEAVE", "RESTRICTED_DUTIES", "ANY_OBJECT"],
        "default_modality": "MAY",
        "requires_condition": False,
        "risk_level": "LOW"
    },

    # FAM-3: Invoices & Commercial Billing
    {
        "predicate_id": "has_invoice_payment_terms",
        "label": "Specifies invoice payment due window net days from issuance",
        "action_category": "PAYMENT",
        "allowed_subject_roles": ["BUYER", "CUSTOMER", "BILLING_ACCOUNT", "ANY_PARTY"],
        "allowed_object_roles": ["PAYMENT_WINDOW", "DUE_DAYS", "NET_TERMS", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "LOW"
    },
    {
        "predicate_id": "has_late_payment_penalty_rate",
        "label": "Specifies late fee penalty interest rate charged on overdue invoice balances",
        "action_category": "FINANCIAL",
        "allowed_subject_roles": ["BUYER", "CUSTOMER", "ANY_PARTY"],
        "allowed_object_roles": ["PENALTY_RATE", "MONTHLY_PERCENT", "INTEREST", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": True,
        "risk_level": "MEDIUM"
    },
    {
        "predicate_id": "has_billing_currency",
        "label": "Specifies authorized settlement currency denomination for billing",
        "action_category": "FINANCIAL",
        "allowed_subject_roles": ["INVOICE", "BILLING_ACCOUNT", "ANY_PARTY"],
        "allowed_object_roles": ["CURRENCY_CODE", "USD", "EUR", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "LOW"
    },
    {
        "predicate_id": "has_tax_rate",
        "label": "Specifies applicable VAT, sales tax, or GST rate levied on line items",
        "action_category": "TAX",
        "allowed_subject_roles": ["INVOICE_LINE_ITEM", "TOTAL_DUE", "ANY_PARTY"],
        "allowed_object_roles": ["VAT_RATE", "SALES_TAX", "TAX_AMOUNT", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "LOW"
    },
    {
        "predicate_id": "has_billing_dispute_window",
        "label": "Defines time window within which invoice discrepancies must be submitted",
        "action_category": "PROCEDURAL",
        "allowed_subject_roles": ["CUSTOMER", "BUYER", "ANY_PARTY"],
        "allowed_object_roles": ["DISPUTE_DAYS", "AUDIT_WINDOW", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "MEDIUM"
    },
    {
        "predicate_id": "requires_purchase_order_reference",
        "label": "Mandates valid customer purchase order number on invoice for remittance",
        "action_category": "PROCEDURAL",
        "allowed_subject_roles": ["INVOICE", "VENDOR", "BUYER", "ANY_PARTY"],
        "allowed_object_roles": ["PO_NUMBER", "ORDER_IDENTIFIER", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "LOW"
    },
    {
        "predicate_id": "has_credit_memo_issuance_policy",
        "label": "Authorizes issuance of credit notes for billing adjustments or returns",
        "action_category": "FINANCIAL",
        "allowed_subject_roles": ["SELLER", "VENDOR", "ANY_PARTY"],
        "allowed_object_roles": ["CREDIT_MEMO", "ADJUSTED_AMOUNT", "ANY_OBJECT"],
        "default_modality": "MAY",
        "requires_condition": False,
        "risk_level": "LOW"
    },
    {
        "predicate_id": "has_remittance_bank_details",
        "label": "Specifies bank routing, account number, or IBAN/SWIFT instructions for payment",
        "action_category": "FINANCIAL",
        "allowed_subject_roles": ["SELLER", "VENDOR", "INVOICE", "ANY_PARTY"],
        "allowed_object_roles": ["BANK_ACCOUNT", "IBAN_SWIFT", "ROUTING", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "LOW"
    },

    # FAM-4: Statutory & Compliance Guidelines
    {
        "predicate_id": "cannot_claim_regularisation",
        "label": "Statutory bar prohibiting contract appointees from claiming absorption in government service",
        "action_category": "RESTRICTIONS",
        "allowed_subject_roles": ["CONTRACT_APPOINTEE", "TEMPORARY_STAFF", "ANY_PARTY"],
        "allowed_object_roles": ["REGULARISATION", "ABSORPTION", "PERMANENT_STATUS", "ANY_OBJECT"],
        "default_modality": "MUST_NOT",
        "requires_condition": False,
        "risk_level": "CRITICAL"
    },
    {
        "predicate_id": "has_maximum_contract_tenure",
        "label": "Defines statutory limitation on maximum duration of contractual engagement",
        "action_category": "PROCEDURAL",
        "allowed_subject_roles": ["CONTRACT_APPOINTEE", "GOVERNMENT_ENGAGEMENT", "ANY_PARTY"],
        "allowed_object_roles": ["DURATION_YEARS", "MAX_TERM", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "MEDIUM"
    },
    {
        "predicate_id": "has_statutory_remuneration_ceiling",
        "label": "Defines statutory monthly remuneration cap for contractual appointments",
        "action_category": "FINANCIAL",
        "allowed_subject_roles": ["GOVERNMENT_DEPARTMENT", "CONTRACT_APPOINTEE", "ANY_PARTY"],
        "allowed_object_roles": ["MONTHLY_CEILING", "REMUNERATION_CAP", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "MEDIUM"
    },
    {
        "predicate_id": "requires_mandatory_compliance_audit",
        "label": "Mandates independent annual compliance assessment or SSPA audit for suppliers",
        "action_category": "AUDIT",
        "allowed_subject_roles": ["SUPPLIER", "VENDOR", "DATA_PROCESSOR", "ANY_PARTY"],
        "allowed_object_roles": ["ANNUAL_AUDIT", "INDEPENDENT_ASSESSMENT", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "HIGH"
    },
    {
        "predicate_id": "has_breach_notification_deadline",
        "label": "Mandates maximum timeframe within which security or privacy incidents must be reported",
        "action_category": "COMPLIANCE",
        "allowed_subject_roles": ["DATA_PROCESSOR", "SUPPLIER", "ANY_PARTY"],
        "allowed_object_roles": ["NOTIFICATION_HOURS", "72_HOURS", "DEADLINE", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "HIGH"
    },
    {
        "predicate_id": "has_whistleblower_protection",
        "label": "Mandates non-retaliation protections for personnel reporting statutory non-compliance",
        "action_category": "COMPLIANCE",
        "allowed_subject_roles": ["REPORTING_PARTY", "EMPLOYEE", "ANY_PARTY"],
        "allowed_object_roles": ["NON_RETALIATION", "CONFIDENTIALITY", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "MEDIUM"
    },
    {
        "predicate_id": "is_subject_to_administrative_review",
        "label": "Subjects appointment or agreement to periodic administrative governance review",
        "action_category": "GOVERNANCE",
        "allowed_subject_roles": ["CONTRACTUAL_ENGAGEMENT", "APPOINTMENT", "ANY_PARTY"],
        "allowed_object_roles": ["GOVERNMENT_REVIEW", "ADMINISTRATIVE_EXIGENCY", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "LOW"
    },
    {
        "predicate_id": "requires_human_rights_due_diligence",
        "label": "Mandates annual due diligence assessment and disclosure on labor and human rights",
        "action_category": "COMPLIANCE",
        "allowed_subject_roles": ["SUPPLIER", "ENTERPRISE", "ANY_PARTY"],
        "allowed_object_roles": ["DUE_DILIGENCE_REPORT", "LABOR_ASSESSMENT", "ANY_OBJECT"],
        "default_modality": "MUST",
        "requires_condition": False,
        "risk_level": "MEDIUM"
    }
]

existing_pids = {p["predicate_id"].lower() for p in data["predicates"]}
added = 0
for np in new_predicates:
    if np["predicate_id"].lower() not in existing_pids:
        data["predicates"].append(np)
        added += 1

data["version"] = "2.0.0"
data["last_updated"] = "2026-11-10T15:20:00Z"

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2)

print(f"Added {added} new predicates. Total predicates now: {len(data['predicates'])}")

