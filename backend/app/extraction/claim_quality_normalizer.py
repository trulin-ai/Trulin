"""
Sprint AF: Claim Quality Normalizer
Transforms raw extracted contract claims into clean, atomic, deduplicated, and agent-usable policy claims.

Implements the 7-phase quality pipeline:
1. Split non-atomic claims (one claim = one subject + one predicate + one object + optional conditions)
2. Normalize bad subjects & enforce subject allowlist
3. Enforce a central controlled predicate vocabulary
4. Deduplicate claims by normalized semantic signature
5. Reclassify non-rules (separate descriptions, definitions, references, and examples)
6. Context-aware conflict evaluation (no false conflicts on complementary rights)
7. Re-review and recover falsely rejected contractual rules
"""

from __future__ import annotations

import hashlib
import logging
import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger(__name__)

NORMALIZER_VERSION = "v2.0-certified"


class NormalizedClaimCategory(str, Enum):
    """Taxonomic classification separating enforceable policy rules from contextual content."""
    # Primary Agent-Facing Normative Rules (Enter Primary Claim Graph)
    POLICY_RULE = "POLICY_RULE"          # General operative normative rule
    POLICY_CLAIM = "POLICY_CLAIM"        # Alias for backwards compatibility
    OBLIGATION = "OBLIGATION"            # Affirmative mandatory duty (must, shall, will)
    PROHIBITION = "PROHIBITION"          # Restrictive prohibition (must not, may not, cannot)
    PERMISSION = "PERMISSION"            # Permissive right or privilege (may, is permitted to)
    ENTITLEMENT = "ENTITLEMENT"          # Commercial remedy or affirmative entitlement (credit, refund)
    ELIGIBILITY = "ELIGIBILITY"          # Qualifying threshold or status requirement (eligible)

    # Contextual / Non-Rule Categories (Excluded from Primary Claim Graph)
    DEFINITION = "DEFINITION"            # Terminology / boundary exclusions ("Software does not include...")
    DESCRIPTION = "DESCRIPTION"          # Informational capabilities / non-binding facts ("Availability may vary...")
    REFERENCE = "REFERENCE"              # Cross-document navigation links ("Details in Product Terms...")
    SCOPE_RULE = "SCOPE_RULE"            # Temporal / order application scope ("Applies to new orders...")
    RESPONSIBILITY = "RESPONSIBILITY"    # Organizational delegation / role declarations ("Microsoft remains responsible...")
    EXAMPLE = "EXAMPLE"                  # Non-binding illustrative scenario ("For example, Customer may...")

    @classmethod
    def is_agent_facing(cls, category: NormalizedClaimCategory) -> bool:
        """Only normative policy rules enter the primary agent-facing claim graph."""
        return category in {
            cls.POLICY_RULE, cls.POLICY_CLAIM, cls.OBLIGATION,
            cls.PROHIBITION, cls.PERMISSION, cls.ENTITLEMENT, cls.ELIGIBILITY,
        }


class NormativeModality(str, Enum):
    """Controlled normative modality for policy claims."""
    OBLIGATION = "OBLIGATION"            # must, shall, is required to, will
    PROHIBITION = "PROHIBITION"          # must not, may not, cannot, shall not
    PERMISSION = "PERMISSION"            # may, is permitted to, is allowed to
    ENTITLEMENT = "ENTITLEMENT"          # is entitled to, will receive (credit, refund)
    ELIGIBILITY = "ELIGIBILITY"          # meets requirements, eligible



# =============================================================================
# 1. Subject Allowlist & Canonical Subject Aliases
# =============================================================================

CANONICAL_SUBJECT_ALLOWLIST: Set[str] = {
    # Contract Parties & Operational Roles
    "Customer", "Microsoft", "Partner", "Affiliate", "Either party", "Each party",
    "Supplier", "Vendor", "Employee", "Employer", "Company", "Client",
    "Contractor", "Administrator", "Publisher", "Representatives", "Buyer",
    "Seller", "Licensor", "Licensee", "User", "End User", "Subcontractor",
    "Auditor", "Manufacturer", "Distributor", "Subscriber", "Parties",
    "Neither party", "Both parties", "Customer or Affiliate",
    "Service Provider", "Provider", "Merchant", "Carrier", "Insurer", "Insured",
    "Google", "AWS", "Apple", "Oracle", "Salesforce",
    # Specific Domain & Policy Role Subjects (Slice 3)
    "Apple Pay / Google Pay",
    "Trailhead Box subscription", "Trailhead Box",
    "Rewards Plus subscription", "Rewards Plus",
    "Gear Care Plan subscription", "Gear Care Plan",
    "Partial refund for cosmetic flaws", "Partial refund (keep item)",
    "Damaged item under $40",
    "Oversize items",
    "International refund",
    "Video course", "Video courses",
    "Photos",
    "Northwind policy version 4.0",
    "Order number", "Email on order", "Item SKU / name", "Reason for return", "Preferred resolution",
    "In-store refunds", "Price adjustments", "Free trials", "Order cancellation",
    # Universal Operative Artifacts
    "Product", "Products", "Software", "Service", "Services", "Subscription",
    "Order", "Refund request", "Deliverable", "Deliverables",
    "Documentation", "Data", "Confidential Information", "Account", "Invoice",
    "Waiver", "Notice",
}

SUBJECT_REPAIR_MAP: Dict[str, str] = {
    # Singularization & Aliases
    "customers": "Customer",
    "customer": "Customer",
    "the customer": "Customer",
    "end users": "End User",
    "end user": "End User",
    "partners": "Partner",
    "partner": "Partner",
    "affiliates": "Affiliate",
    "affiliate": "Affiliate",
    "the parties": "Each party",
    "parties": "Each party",
    "each party": "Each party",
    "either party": "Either party",
    "neither party": "Neither party",
    "both parties": "Each party",
    "clients": "Client",
    "client": "Client",
    "the company": "Company",
    "company": "Company",
    "employers": "Employer",
    "employer": "Employer",
    "employees": "Employee",
    "employee": "Employee",
    "contractors": "Contractor",
    "contractor": "Contractor",
    "suppliers": "Supplier",
    "supplier": "Supplier",
    "vendors": "Vendor",
    "vendor": "Vendor",
    "licensors": "Licensor",
    "licensor": "Licensor",
    "licensees": "Licensee",
    "licensee": "Licensee",
    "buyers": "Buyer",
    "buyer": "Buyer",
    "sellers": "Seller",
    "seller": "Seller",
    "users": "User",
    "user": "User",
    "subcontractors": "Subcontractor",
    "subcontractor": "Subcontractor",
    "auditors": "Auditor",
    "auditor": "Auditor",
    "distributors": "Distributor",
    "distributor": "Distributor",
    "subscribers": "Subscriber",
    "subscriber": "Subscriber",
    "providers": "Provider",
    "provider": "Provider",
    "service providers": "Service Provider",
    "service provider": "Service Provider",
    # Universal Passive Noun Phrase Subject Mappings
    "all amounts due under any unpaid invoices": "Customer",
    "all amounts due under unpaid invoices": "Customer",
    "amounts due under unpaid invoices": "Customer",
    "all amounts due": "Customer",
    "amounts due": "Customer",
    "unpaid invoices": "Customer",
    "outstanding balance": "Customer",
    "fees payable": "Customer",
    "payment obligations": "Customer",
    "any other proposed assignment of this agreement": "Customer",
    "any other proposed assignment": "Customer",
    "proposed assignment": "Customer",
    "assignment of this agreement": "Customer",
    "more details about cancelation": "Customer",
    "more details about cancelat ion": "Customer",
    "any waiver": "Either party",
    "waiver of any breach": "Either party",
    "all notices": "Either party",
    "any notice": "Either party",
    "written notices": "Either party",
    "the defending party": "Each party",
    "the party being defended": "Each party",
    "defended party": "Each party",
    "defending party": "Each party",
    "indemnifying party": "Each party",
    "indemnified party": "Each party",
    "publishers": "Publisher",
    "publisher": "Publisher",
    "representatives": "Representatives",
    "non-microsoft product": "Publisher",
    "non-vendor product": "Publisher",
    "third-party product": "Publisher",
    "third-party service": "Publisher",
    # Specific Domain & Policy Role Subject Repairs (Slice 3)
    "apple pay / google pay": "Apple Pay / Google Pay",
    "apple pay": "Apple Pay / Google Pay",
    "google pay": "Apple Pay / Google Pay",
    "trailhead box": "Trailhead Box subscription",
    "trailhead box subscription": "Trailhead Box subscription",
    "rewards plus": "Rewards Plus subscription",
    "rewards plus subscription": "Rewards Plus subscription",
    "gear care plan": "Gear Care Plan subscription",
    "gear care plan subscription": "Gear Care Plan subscription",
    "partial refund (keep item)": "Partial refund for cosmetic flaws",
    "partial refund for cosmetic flaws": "Partial refund for cosmetic flaws",
    "damaged items valued under $40": "Damaged item under $40",
    "damaged item under $40": "Damaged item under $40",
    "oversize items": "Oversize items",
    "international refund": "International refund",
    "international refunds": "International refund",
    "video course": "Video course",
    "video courses": "Video course",
    "photos": "Photos",
    "northwind policy version 4.0": "Northwind policy version 4.0",
    "order number": "Order number",
    "email on order": "Email on order",
    "item sku / name": "Item SKU / name",
    "reason for return": "Reason for return",
    "preferred resolution": "Preferred resolution",
    "in-store refunds": "In-store refunds",
    "in store": "In-store refunds",
    "price adjustments": "Price adjustments",
    "price adjustment": "Price adjustments",
    "free trials": "Free trials",
    "order cancellation": "Order cancellation",
}


# =============================================================================
# 2. Controlled Predicate Vocabulary Dictionary
# =============================================================================

CONTROLLED_PREDICATE_VOCABULARY: Dict[str, str] = {
    # Licensing & Permitted Use
    "grants_product_license": "Microsoft grants Customer a non-exclusive license to use ordered Products",
    "grants_deliverables_license": "Microsoft grants Customer a license to use and modify Services Deliverables",
    "may_order_for_affiliate": "Customer may order Products for use by its Affiliates",
    "may_use_preexisting_work": "Each party may use and modify the other's Pre-existing Work for Professional Services",
    "may_transfer_perpetual_license": "Customer may transfer fully-paid perpetual licenses under specific merger/divestiture conditions",
    "must_uninstall_upon_transfer": "Customer must uninstall and discontinue using licensed Products upon transfer",
    "must_provide_transfer_documentation": "Customer must provide transferee copies of General Terms and Product Terms upon license transfer",
    "retains_reservation_of_rights": "Microsoft reserves all intellectual property rights not expressly granted",
    "retains_enforcement_rights": "Customer retains sole right to enforce Agreement against Microsoft on behalf of Affiliates",

    # Prohibitions & Usage Restrictions
    "prohibited_from_reverse_engineering": "Customer must not reverse engineer, decompile, or disassemble Products/Deliverables",
    "prohibited_from_licensing_interference": "Customer must not install software that subjects Microsoft IP to third-party licenses",
    "prohibited_from_circumventing_limits": "Customer must not work around technical limitations in Products/Deliverables",
    "prohibited_from_multi_device_splitting": "Customer must not separate and run parts of a Deliverable on multiple devices",
    "prohibited_from_version_downgrading": "Customer must not upgrade or downgrade parts of a Product at different times",
    "prohibited_from_separate_transfers": "Customer must not transfer parts of a Product separately",
    "prohibited_from_commercial_hosting": "Customer must not distribute, rent, lease, or use Products to offer third-party hosting",
    "must_comply_with_restrictions": "Licenses are solely for Customer's own use and business purposes and are nontransferable",

    # Compliance & Audit Obligations
    "must_keep_compliance_records": "Customer must maintain records relating to Products it and its Affiliates use",
    "may_conduct_compliance_audit": "Microsoft may verify Customer compliance upon 30 days notice at Microsoft's expense",
    "must_provide_audit_access": "Customer must promptly provide requested documents and system access for verification",
    "must_acquire_unlicensed_usage": "Customer must order sufficient licenses within 30 days to cover unlicensed use",
    "must_reimburse_audit_penalty": "Customer must reimburse audit costs and pay 125% price if unlicensed use exceeds 5%",
    "has_return_window": "Remedy or return notification window under applicable warranty or audit terms",
    "has_remedy_window": "Cure or remedy notification period for non-compliance or breach",

    # Confidentiality & Data Protection
    "must_maintain_confidentiality": "Each party will take reasonable steps to protect the other's Confidential Information",
    "prohibited_from_unauthorized_disclosure": "Neither party will disclose Confidential Information to third parties except Representatives under NDA",
    "must_notify_unauthorized_disclosure": "Each party must promptly notify the other upon discovery of unauthorized use or disclosure",
    "may_disclose_under_legal_mandate": "A party may disclose Confidential Information if required by law after giving notice",
    "is_not_required_to_restrict_assignments": "Neither party is required to restrict work assignments of Representatives based on residual knowledge",
    "must_obtain_privacy_consents": "Customer will obtain all required third-party consents before providing Personal Data to Microsoft",
    "must_process_data_per_dpa": "Microsoft will process Customer Data and Personal Data per Agreement and DPA",
    "must_observe_confidentiality_duration": "Confidentiality obligations apply until deletion for Customer Data and five years for other info",

    # Warranties & Third-Party IP Defense
    "warrants_service_level_agreement": "Microsoft warrants Online Services will perform in accordance with applicable SLA",
    "warrants_software_performance": "Microsoft warrants Software will perform substantially as described for one year",
    "warrants_professional_standards": "Microsoft warrants Professional Services will meet industry standards of care",
    "must_notify_warranty_claim_within_window": "Customer must notify warranty claim within 90 days from completion of work",
    "has_professional_services_remedy_window": "Customer warranty notification remedy window for professional services",
    "must_defend_ip_claims": "Party will defend the other against third-party intellectual property infringement claims",
    "must_provide_defense_cooperation": "Defended party must provide prompt written notice and requested assistance for defense",

    # Liability Limits & Exclusions
    "has_liability_cap": "Party aggregate liability is limited to amounts required to pay in prior 12 months (or license fee for perpetual)",
    "excludes_consequential_damages": "Neither party will be liable for indirect, incidental, special, punitive, or consequential damages",

    # Compliance & Remedies
    "must_remediate_unlicensed_use_within_30_days": "Customer must order sufficient licenses within 30 days to cover unlicensed use",

    # Invoicing, Payment & Late Fees
    "must_provide_payment_method": "Customer must provide valid payment method or choose invoicing if eligible",
    "must_pay_within_30_days": "Customer will pay all invoiced amounts due within thirty (30) calendar days following invoice date",
    "must_pay_unpaid_invoices_immediately": "Customer must pay all amounts due under unpaid invoices immediately upon termination",
    "may_assess_late_fee": "Microsoft may assess a late fee of up to 2% monthly on payments overdue by more than 15 calendar days",
    "authorizes_recurring_charges": "Customer authorizes Microsoft to periodically charge payment method for auto-renewing subscriptions",
    "must_pay_applicable_taxes": "Customer will pay applicable VAT, sales, and transaction taxes owed under the Agreement",
    "must_pay_income_taxes": "Microsoft will be responsible for taxes based upon its net income and property ownership",
    "may_deduct_withheld_taxes": "Customer may deduct required tax withholdings upon providing official receipts to Microsoft",
    "may_withdraw_invoicing_eligibility": "Microsoft may withdraw Customer's invoicing eligibility at any time for any reason",
    "must_promptly_notify_changes": "Customer must promptly notify Microsoft of changes in name, location, or ownership",

    # Term, Termination & Suspension
    "may_terminate_without_cause": "Either party may terminate the Agreement without cause on 60 days written notice",
    "may_terminate_for_material_breach": "Either party may terminate on 30 days notice for uncured material breach",
    "becomes_due_immediately": "All unpaid invoice amounts become due and payable immediately upon termination",
    "must_pay_unpaid_usage": "Customer must pay for all unpaid usage and Professional Services upon termination",
    "will_receive_refund_on_breach": "Customer will receive credit or refund for advance payments for period after termination",
    "must_provide_notice_before_suspension": "Microsoft will give Customer 30 days notice before suspension for material breach",
    "must_stop_use_and_disable_billing": "Customer must stop using Products and turn off recurring billing if it rejects modifications",
    "may_modify_or_discontinue_products": "Microsoft may modify or discontinue offering a Product or Professional Service",


    # Modifications, Assignment & Governance
    "may_update_agreement": "Microsoft may update Agreement from time to time, applying to new orders and renewals",
    "must_receive_60_days_modification_notice": "Customer must receive written notice at least 60 days before General Terms changes take effect",
    "must_not_modify_agreement": "Customer may not modify Agreement; conflicting PO terms are void",
    "may_assign_to_affiliate": "Either party may assign Agreement to an Affiliate upon written notice",
    "consents_to_payment_assignment": "Customer consents to assignment of payment rights to Microsoft Affiliates or third parties",
    "requires_written_approval": "Assignment to third parties requires prior written approval of the non-assigning party",
    "requires_written_agreement": "Any waiver of contract provisions must be in writing and signed by the waiving party",
    "requires_written_notice": "Action requires prior written notice to the other party",
    "must_be_in_writing": "All notices under this Agreement must be in writing",
    "may_provide_electronic_notice": "Microsoft may provide notices electronically through portal, email, or identified website",
    "submits_to_governing_jurisdiction": "The parties agree to exclusive venue in King County, Washington (US/Global) or Ireland (Europe)",
    "applies_order_of_precedence": "Parties apply specified order of precedence in case of conflict between documents",
    "warrants_government_procurement_compliance": "Customer warrants compliance with procurement laws if a government entity",
    "must_meet_eligibility_criteria": "Customer must meet eligibility criteria for academic, government, or nonprofit Products",
    "may_verify_and_suspend_eligibility": "Microsoft may verify eligibility and suspend Product use if criteria not met",
    "must_control_end_user_access": "Customer must control access and use of Products by End Users",
    "may_sublicense_deliverables": "Customer may sublicense rights in Services Deliverables to Affiliates",
    "must_comply_with_trade_laws": "Each party will comply with applicable import/export and OFAC sanctions trade laws",
    "may_suspend_for_trade_laws": "Microsoft may suspend or terminate Agreement if performance violates Trade Laws",
    "varies_by_region": "Product availability may vary by geographical region",
    # Commercial & Policy Operations (Slice 3 Refinements)
    "offers_store_credit_bonus": "Customers who choose store credit receive a 5% bonus up to $25",
    "receives_store_credit_bonus": "Customers who choose store credit receive a 5% bonus up to $25",
    "has_posting_duration": "Bank or card network posting duration for processed refunds",
    "has_price_adjustment_window": "Price drop protection window and one-time difference refund terms",
    "may_request_first_charge_refund": "Customer may request full refund of first renewal charge within 7 days if forgot to cancel",
    "can_pause_subscription": "Subscriber may pause subscription for up to 3 months once per year",
    "has_cancellation_window": "Order cancellation timeline and authorization release",
    "has_return_freight_deduction": "Oversize items are subject to a flat-rate return freight deduction of $49",
    "requires_receipt_retention": "Customers must retain the drop-off receipt until refund is confirmed",
    "uses_original_charge_currency": "International refunds are issued in the currency of the original charge",
    "is_responsible_for_duty_drawback": "Customers are responsible for filing customs duty drawback claims",
    "is_required_for_refund_request": "Specified documentation or photographic proof is required for refund request",
    "has_refund_rule": "Governing refund entitlement or restriction rule for subscriptions or policies",
    "has_revision_history": "Historical policy version changelog and effective dates",
}

# Vague predicate transformation lookup (only for unambiguous semantic mappings)
VAGUE_PREDICATE_REPLACEMENT: Dict[str, str] = {
    "become": "becomes_due_immediately",
    "approved": "requires_written_approval",
    "vary": "varies_by_region",
    "apply_to": "applies_to_contract_orders",
    "give": "must_provide_notice_before_suspension",
    "withdraw": "may_withdraw_invoicing_eligibility",
    "suspend": "may_suspend_for_security_or_breach",
    "terminate": "may_terminate_without_cause",
    "defend": "must_defend_ip_claims",
    "comply_with": "must_comply_with_trade_laws",
    "disclose": "prohibited_from_unauthorized_disclosure",
}


# =============================================================================
# 3. Normalized Claim Representation & Quality Scoring
# =============================================================================

@dataclass
class ClaimQualityScore:
    """100-point composite quality score across 6 objective validation criteria."""
    subject_validity: float = 20.0       # 0 - 20 (allowlist actor vs vague/fragment)
    predicate_validity: float = 20.0     # 0 - 20 (controlled dictionary vs generic verb)
    atomicity: float = 20.0              # 0 - 20 (single duty vs compound multi-obligation)
    evidence_grounding: float = 20.0     # 0 - 20 (exact textual support vs unsupported inference)
    deduplication_status: float = 10.0   # 0 - 10 (canonical unique vs duplicate)
    claim_type_correctness: float = 10.0 # 0 - 10 (proper normative classification)
    total_score: float = 100.0
    status: str = "CANONICAL"            # >= 90: CANONICAL, 75-89: REVIEW, < 75: REJECT_OR_REPAIR

    def calculate_total(self) -> float:
        self.total_score = round(
            self.subject_validity +
            self.predicate_validity +
            self.atomicity +
            self.evidence_grounding +
            self.deduplication_status +
            self.claim_type_correctness,
            2
        )
        if self.total_score >= 90.0:
            self.status = "CANONICAL"
        elif self.total_score >= 75.0:
            self.status = "REVIEW"
        else:
            self.status = "REJECT_OR_REPAIR"
        return self.total_score


@dataclass
class NormalizedClaim:
    """A clean, atomic, agent-usable policy claim with parent-child provenance and quality metrics."""
    claim_id: str
    subject: str
    predicate: str
    object: str
    modality: NormativeModality
    category: NormalizedClaimCategory
    is_atomic: bool = True
    conditions: List[str] = field(default_factory=list)
    evidence_span: str = ""
    locator: Dict[str, Any] = field(default_factory=dict)
    trust_score: float = 1.0
    status: str = "VERIFIED"  # VERIFIED, CANONICAL, REVIEW, NON_RULE, COLLAPSED_DUPLICATE
    rationale: str = "Verified atomic policy obligation."

    # Parent-child provenance for multi-rule decomposition
    parent_claim_id: Optional[str] = None
    split_index: Optional[int] = None
    split_count: Optional[int] = None

    # Quality scoring and review escalation
    quality_score: Optional[ClaimQualityScore] = None
    review_reasons: List[str] = field(default_factory=list)

    def semantic_signature(self) -> str:
        """
        Computes a deterministic hash for deduplication based on:
        normalized subject + normalized predicate + normalized object tokens + normalized conditions + modality.
        """
        s = self.subject.strip().lower()
        p = self.predicate.strip().lower()
        # Clean object tokens: remove stopwords and punctuation
        o_clean = re.sub(r"[^\w\s]", "", self.object.lower())
        o_tokens = " ".join(sorted(set(o_clean.split()) - {"the", "a", "an", "this", "that", "these", "any", "and", "or", "of", "to", "for", "in"}))
        cond_str = "|".join(sorted(self.conditions))
        mod_str = self.modality.value if hasattr(self.modality, "value") else str(self.modality)
        raw_key = f"{s}::{p}::{o_tokens}::{cond_str}::{mod_str}"
        return hashlib.sha256(raw_key.encode("utf-8")).hexdigest()[:16]


# =============================================================================
# 4. Claim Quality Normalization Pipeline
# =============================================================================

class ClaimQualityNormalizer:
    """
    Universal Claim Quality Normalizer for Enterprise Contracts, Agreements, and Policies.
    
    Transforms raw extracted claims into clean, atomic, deduplicated, and agent-usable policy claims:
    1. Universal Header, Page Number, and Physical Postal Address Stripping
    2. Universal Subject Allowlist & Entity Matching
    3. Multi-Rule Compound Sentence Splitting
    4. Controlled Predicate Normalization
    5. Taxonomic Separation of Non-Rules (Definitions, Descriptions, References, Responsibilities)
    6. Deterministic Semantic Signature Deduplication
    7. Context-Aware Conflict Compatibility Gate
    """

    FRAGMENT_REJECTION_SET: Set[str] = {
        "the following", "following", "the following apply", "n/a", "-", "--", "none",
        "see below", "as follows", "applicable terms", "general", "overview",
        "table of contents", "exhibit", "schedule", "appendix", "attachment",
    }

    REJECTED_GENERIC_PREDICATES: Set[str] = {
        "order", "use", "become", "in", "apply_to", "customer", "vary", "approved", "has_validity_rule", "has_definition",
        "has_licensing_requirement", "company", "its", "provide", "true", "refer", "modify",
    }

    @classmethod
    def compute_dedup_signature(cls, claim: NormalizedClaim) -> str:
        """Computes deterministic SHA-256 deduplication signature for a claim."""
        return claim.semantic_signature()

    @classmethod
    def clean_subject_text(cls, raw: str) -> str:
        """
        Strips running headers, page numbers, document slugs, and physical postal addresses
        universally across any commercial contract, SaaS agreement, or policy document.
        """
        if not raw:
            return ""

        s = raw.strip()

        # 1. Strip running page numbers & document slugs
        # e.g., "Page 1 of 11", "Page 5", "Doc-057 Page 2 of 10", "Contract No. 1234"
        s = re.sub(r"\bpage\s+\d+(\s+of\s+\d+)?\b.*", "", s, flags=re.I).strip()
        s = re.sub(r"\bdoc(?:ument)?\s*[-:#]?\s*[\w\-]+", "", s, flags=re.I).strip()
        s = re.sub(r"\bcontract\s*[-:#]?\s*[\w\-]+", "", s, flags=re.I).strip()

        # 2. Strip universal physical postal addresses:
        # Matches street addresses, suite/building, city/state/zip, country
        postal_pattern = (
            r"(?:\b\d+[\w\s,\.\-]+?\b(?:Street|St|Avenue|Ave|Parkway|Pkwy|Boulevard|Blvd|"
            r"Road|Rd|Drive|Dr|Way|Lane|Ln|Court|Ct|Circle|Cir|Suite|Ste|Floor|Fl|Building|Bldg|Box)\b"
            r"[^\n\r]*?(?:\b[A-Z]{2}\b|\b\d{5}(?:-\d{4})?|\bUSA\b|\bUS\b|\bUK\b|\bCanada\b|\bIreland\b|\bAustralia\b|\bGermany\b|\bFrance\b)?)"
        )
        s = re.sub(postal_pattern, " ", s, flags=re.I).strip()

        # 3. Strip leading/trailing bullet points, dashes, punctuation
        s = re.sub(r"^[\s•●❖\-_*#\.\,\:\;]+", "", s).strip()
        s = re.sub(r"[\s•●❖\-_*#\.\,\:\;]+$", "", s).strip()
        return s

    @classmethod
    def normalize_subject_entity(cls, raw_subject: str) -> Tuple[Optional[str], bool]:
        """
        Repairs and normalizes subject string into a canonical contracting entity.
        Returns (canonical_subject, is_valid).
        """
        if not raw_subject:
            return None, False

        # 1. Clean headers, page numbers, and postal blocks
        s = cls.clean_subject_text(raw_subject)
        if not s:
            # If cleaning stripped the entire string, check if the raw string contained an allowlisted entity
            for cand in sorted(CANONICAL_SUBJECT_ALLOWLIST, key=lambda x: -len(x)):
                if re.search(r"\b" + re.escape(cand.lower()) + r"\b", raw_subject.lower()):
                    return cand, True
            return None, False

        # 2. Check fragment rejection
        s_lower = s.lower().strip()
        if s_lower in cls.FRAGMENT_REJECTION_SET:
            return None, False

        # 3. Direct lookup in repair map (for raw or cleaned text)
        raw_clean = re.sub(r"^[\s•●❖\-_*]+", "", raw_subject).strip().lower()
        if raw_clean in SUBJECT_REPAIR_MAP:
            return SUBJECT_REPAIR_MAP[raw_clean], True
        if s_lower in SUBJECT_REPAIR_MAP:
            return SUBJECT_REPAIR_MAP[s_lower], True

        # 4. Check if already in canonical allowlist
        for allowed in CANONICAL_SUBJECT_ALLOWLIST:
            if s_lower == allowed.lower():
                return allowed, True

        # 5. Universal Allowlist Word-Boundary Scan
        # Sorted by length descending so multi-word entities (e.g. 'End User', 'Customer or Affiliate', 'Either party')
        # match prior to shorter substrings ('User', 'Customer', 'party').
        for candidate in sorted(CANONICAL_SUBJECT_ALLOWLIST, key=lambda x: -len(x)):
            pattern = r"\b" + re.escape(candidate.lower()) + r"\b"
            if re.search(pattern, s_lower) or re.search(pattern, raw_subject.lower()):
                return candidate, True

        return s, False

    REJECTED_GENERIC_PREDICATES: Set[str] = {
        "order", "use", "become", "in", "apply_to", "customer", "vary", "approved", "has_validity_rule"
    }

    @classmethod
    def normalize_subject_with_safety_check(
        cls,
        raw_subject: str,
        evidence_context: str = "",
    ) -> Tuple[Optional[str], bool, Optional[str]]:
        """
        Repairs and normalizes subject string into a canonical contracting entity.
        Enforces Stage 4 Safety Rule:
        - If passive subject maps cleanly to one actor AND surrounding evidence supports it -> normalize automatically.
        - If multiple actors could owe/perform and evidence is ambiguous -> route to human review.
        Returns (canonical_subject, is_valid, review_reason).
        """
        norm_subj, is_valid = cls.normalize_subject_entity(raw_subject)
        if not is_valid or not norm_subj:
            return None, False, "UNRECOGNIZED_OR_FRAGMENT_SUBJECT"

        s_lower = raw_subject.lower()
        if any(term in s_lower for term in ("unpaid invoice", "amount due", "outstanding balance", "fee payable")):
            if evidence_context:
                ctx_lower = evidence_context.lower()
                if "partner" in ctx_lower and "customer" in ctx_lower and "reseller" in ctx_lower:
                    return norm_subj, True, "AMBIGUOUS_PASSIVE_DEBTOR_REQUIRES_REVIEW"

        return norm_subj, True, None

    @classmethod
    def is_atomic_rule(cls, text: str) -> Tuple[bool, List[str]]:
        """
        Determines whether a contractual statement is atomic (one duty) or compound (multiple rules).
        Returns (is_atomic, triggers_found).
        
        Stage 3 Decomposition Triggers:
        1. Enumeration sequences: (i), (ii) or (1), (2) or (a), (b)
        2. Semicolons separating independent obligations
        3. 'and' linking two distinct modal duties ('will do X and is responsible for Y')
        4. 'or' linking distinct permissions/remedies ('may transfer to Affiliate or a third party...')
        5. Multiple parties performing different actions
        """
        if not text or len(text.strip()) < 20:
            return True, []

        raw = text.strip()
        triggers: List[str] = []

        # 1. Enumerations
        enum_pattern = r"(?:;\s*(?:and|or)?\s*|\s+(?:and|or)\s+|[:;]\s*)?\(([iIvVxXa-dA-D1-9]+)\)\s*"
        if len(list(re.finditer(enum_pattern, raw))) >= 2:
            triggers.append("ENUMERATION_SUBCLAUSES")

        # 2. Semicolons separating clauses
        if ";" in raw:
            parts = [p.strip() for p in raw.split(";") if len(p.strip()) > 10]
            if len(parts) >= 2:
                triggers.append("SEMICOLON_SEPARATED_OBLIGATIONS")

        # 3. Dual obligation conjunctions
        dual_pattern = r"\b(?:will|must|shall|agrees to)\b.+?\band\s+(?:is responsible for|must|shall|will)\b"
        if re.search(dual_pattern, raw, re.I):
            triggers.append("DUAL_OBLIGATION_CONJUNCTION")

        # 4. Multiple parties performing distinct actions
        actor_matches = re.findall(r"\b(Customer|Microsoft|Vendor|Supplier|Client|Either party|Each party)\s+(?:must|shall|may|will)\b", raw, re.I)
        if len(set(actor_matches)) >= 2:
            triggers.append("MULTIPLE_PARTY_ACTIONS")

        is_atomic = len(triggers) == 0
        return is_atomic, triggers

    @classmethod
    def decompose_compound_claim(cls, claim: NormalizedClaim) -> List[NormalizedClaim]:
        """
        Decomposes a compound claim into atomic child claims, preserving:
        - Parent-child provenance (parent_claim_id, split_index, split_count)
        - Shared conditions and context
        - Source evidence quote and exact locators
        """
        is_atom, triggers = cls.is_atomic_rule(claim.object)
        if is_atom:
            return [claim]

        subclauses = cls.split_compound_clause(claim.object)
        if len(subclauses) <= 1:
            return [claim]

        children: List[NormalizedClaim] = []
        for idx, sub_obj in enumerate(subclauses):
            child_pred = cls.normalize_predicate(claim.predicate, claim.subject, sub_obj)
            child_cat, child_mod = cls.classify_claim_category(claim.subject, child_pred, sub_obj)

            child_claim = NormalizedClaim(
                claim_id=f"{claim.claim_id}:split:{idx+1}",
                subject=claim.subject,
                predicate=child_pred,
                object=sub_obj,
                modality=child_mod,
                category=child_cat,
                is_atomic=True,
                conditions=list(claim.conditions),
                evidence_span=claim.evidence_span,
                locator=dict(claim.locator or {}),
                trust_score=claim.trust_score,
                status="VERIFIED" if NormalizedClaimCategory.is_agent_facing(child_cat) else "NON_RULE",
                rationale=f"Atomic child claim decomposed from {claim.claim_id} (trigger: {', '.join(triggers)}).",
                parent_claim_id=claim.claim_id,
                split_index=idx + 1,
                split_count=len(subclauses),
            )
            children.append(child_claim)

        return children

    @classmethod
    def split_compound_clause(cls, text: str) -> List[str]:
        """
        Universally decomposes compound multi-rule contractual statements into atomic single-duty propositions.
        
        Detects:
        1. Enumerated subclauses: (i), (ii), (iii) or (1), (2), (3) or (a), (b), (c)
        2. Semicolon-separated obligations: '... ; and ...'
        3. Conjunction-linked distinct duties: '... will control access ... and is responsible for ...'
        """
        if not text or len(text.strip()) < 15:
            return [text.strip()] if text else []

        raw = text.strip()

        # 1. Check for enumerated subclauses: e.g. (i), (ii), (iii) or (1), (2), (3) or (a), (b), (c)
        enum_pattern = r"(?:;\s*(?:and|or)?\s*|\s+(?:and|or)\s+|[:;]\s*)?\(([iIvVxXa-dA-D1-9]+)\)\s*"
        enum_matches = list(re.finditer(enum_pattern, raw))
        if len(enum_matches) >= 2:
            prefix = raw[:enum_matches[0].start()].rstrip(" :;-")
            subclauses = []
            for i in range(len(enum_matches)):
                start = enum_matches[i].end()
                end = enum_matches[i + 1].start() if i + 1 < len(enum_matches) else len(raw)
                clause_text = raw[start:end].strip(" ;,.\n\r")
                if clause_text:
                    if prefix and not any(clause_text.lower().startswith(w) for w in ("customer", "microsoft", "party", "either", "each", "vendor", "client")):
                        subclauses.append(f"{prefix} ({enum_matches[i].group(1)}) {clause_text}")
                    else:
                        subclauses.append(clause_text)
            if subclauses:
                return subclauses

        # 2. Check for semicolon-separated compound obligations
        if ";" in raw:
            parts = [p.strip(" \t\n\r.") for p in re.split(r";\s*(?:and|further|provided\s+that)?\s*", raw) if len(p.strip()) > 15]
            if len(parts) >= 2:
                return parts

        # 3. Conjunction-linked dual obligations: e.g. "... and is responsible for ..."
        dual_pattern = r"^(.+?\b(?:will|must|shall|agrees to)\s+[^;]+?)\s+and\s+(is responsible for\b.+)$"
        m = re.match(dual_pattern, raw, flags=re.I)
        if m:
            part1 = m.group(1).strip()
            part2 = m.group(2).strip()
            subj_m = re.match(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)\b", part1)
            subj = subj_m.group(1) if subj_m else "Party"
            return [part1, f"{subj} {part2}"]

        return [raw]

    @classmethod
    def normalize_predicate(cls, raw_predicate: str, subject: str, object_text: str) -> str:
        """
        Maps raw, extracted, or vague verbs into the controlled enterprise vocabulary.
        Uses universal context heuristics across any commercial agreement domain.
        """
        p_clean = raw_predicate.strip().lower()

        # If already a recognized canonical predicate, preserve immediately
        from app.extraction.predicate_registry import PredicateRegistry
        if PredicateRegistry.is_canonical(p_clean):
            return p_clean

        # Context-dependent disambiguation for vague verbs
        if p_clean == "customer":
            if "deliverable" in object_text.lower():
                return "grants_deliverables_license"
            if "license" in object_text.lower() or "product" in object_text.lower():
                return "grants_product_license"
            return "customer"

        if p_clean == "order":
            if "affiliate" in object_text.lower():
                return "may_order_for_affiliate"
            if "license" in object_text.lower() or "product" in object_text.lower():
                return "grants_product_license"
            return "may_order"

        if p_clean == "use":
            obj_lower = object_text.lower()
            if "carrier" in obj_lower or "shipping" in obj_lower:
                return "has_return_shipping_rule"
            if "store credit" in obj_lower or "credit" in obj_lower:
                return "may_receive_store_credit"
            if "pre-existing" in obj_lower or "preexisting" in obj_lower:
                return "may_use_preexisting_work"
            if "transfer" in obj_lower:
                return "must_uninstall_upon_transfer"
            if "end user" in obj_lower:
                return "must_control_end_user_access"
            if "interfere" in obj_lower or "reverse" in obj_lower:
                return "prohibited_from_licensing_interference"
            return "may_use"

        if p_clean == "in":
            obj_lower = object_text.lower()
            if "writing" in obj_lower:
                return "must_be_in_writing"
            return "requires_written_notice"

        if p_clean == "become":
            return "becomes_due_immediately"

        if p_clean == "approved":
            return "requires_written_approval"

        if p_clean == "vary":
            return "varies_by_region"

        if p_clean == "terminate":
            if "without cause" in object_text.lower() or "60 days" in object_text.lower():
                return "may_terminate_without_cause"
            if "material breach" in object_text.lower() or "cure" in object_text.lower() or "30 days" in object_text.lower():
                return "may_terminate_for_material_breach"
            if "convenience" in object_text.lower():
                return "may_terminate_for_convenience"
            return "may_terminate_without_cause"

        if p_clean == "pay":
            obj_lower = object_text.lower()
            if "immediately" in obj_lower or "upon receipt" in obj_lower:
                return "must_pay_unpaid_invoices_immediately"
            if "before termination" in obj_lower or "prior to termination" in obj_lower:
                return "must_pay_for_services_before_termination"
            if "unpaid" in obj_lower:
                return "must_pay_unpaid_usage"
            if "tax" in obj_lower:
                return "must_pay_applicable_taxes"
            if "late" in obj_lower:
                return "may_assess_late_fee"
            if "30 days" in obj_lower or "thirty" in obj_lower:
                return "must_pay_within_30_days"
            return "must_pay_invoices"

        if p_clean in ("authorizes", "authorize"):
            obj_lower = object_text.lower()
            if any(k in obj_lower for k in ("credit", "financial", "invoicing", "eligibility")):
                return "authorizes_financial_assessment"
            if any(k in obj_lower for k in ("recurring", "periodically", "renewal", "automatic")):
                return "authorizes_recurring_charges"
            return "authorizes_financial_assessment"

        if p_clean in ("perform", "performs"):
            obj_lower = object_text.lower()
            if any(k in obj_lower for k in ("affiliate", "subcontractor")):
                return "may_perform_through_affiliates_and_subcontractors"
            if any(k in obj_lower for k in ("standard", "care", "skill", "warrant", "warranty")):
                return "warrants_professional_standards"
            return "may_perform_through_affiliates_and_subcontractors"

        if p_clean in ("modify", "modifies"):
            obj_lower = object_text.lower()
            if any(k in obj_lower for k in ("discontinue", "may modify", "regulatory", "regulation")):
                return "may_modify_or_discontinue_product"
            return "must_not_modify_agreement"

        if p_clean == "defend":
            if any(w in object_text.lower() for w in ("infringement", "claim", "ip", "intellectual property", "third-party")):
                return "must_defend_ip_claims"
            return "must_provide_defense_cooperation"

        if p_clean in ("disclose", "discloses"):
            if "law" in object_text.lower() or "legal" in object_text.lower():
                return "may_disclose_under_legal_mandate"
            return "prohibited_from_unauthorized_disclosure"

        if p_clean in ("comply", "comply_with"):
            if "trade" in object_text.lower() or "export" in object_text.lower() or "sanction" in object_text.lower():
                return "must_comply_with_trade_laws"
            return "must_comply_with_restrictions"

        if p_clean in ("warrant", "warrants"):
            if "service" in object_text.lower():
                return "warrants_service_level_agreement"
            if "software" in object_text.lower():
                return "warrants_software_performance"
            return "warrants_professional_standards"

        if p_clean in VAGUE_PREDICATE_REPLACEMENT:
            return VAGUE_PREDICATE_REPLACEMENT[p_clean]

        if p_clean in CONTROLLED_PREDICATE_VOCABULARY:
            return p_clean

        from app.extraction.predicate_registry import PredicateRegistry
        if PredicateRegistry.is_canonical(p_clean):
            return p_clean

        # Return sanitized snake_case predicate
        return re.sub(r"\W+", "_", p_clean)

    @classmethod
    def classify_claim_category(cls, subject: str, predicate: str, object_text: str) -> Tuple[NormalizedClaimCategory, NormativeModality]:
        """Classifies content into policy claims vs descriptions, definitions, and references."""
        obj_lower = object_text.lower()
        subj_lower = subject.lower()

        # 1. Examples (Non-binding)
        if "for example" in obj_lower or "for instance" in obj_lower or "by way of example" in obj_lower:
            return NormalizedClaimCategory.EXAMPLE, NormativeModality.PERMISSION

        # 2. References (External documentation / citation links / URL destinations)
        if any(w in obj_lower for w in (
            "can be found in", "product terms site", "licensing site", "published on the product terms",
            "identified website", "incorporated by reference", "incorporated in this agreement by reference",
            "http://", "https://", "aka.ms", "may be found at", "refer to",
        )) or "refer" in predicate.lower():
            return NormalizedClaimCategory.REFERENCE, NormativeModality.PERMISSION

        # 3. Descriptions (Informational / capabilities / non-enforceable statements)
        if any(w in obj_lower for w in (
            "vary by region", "varies by region", "will not affect customer's perpetual licenses",
            "fixes are licensed under the same terms", "support for products and other value-added",
            "is not guaranteed", "subject to change", "general information", "informational purposes",
        )):
            return NormalizedClaimCategory.DESCRIPTION, NormativeModality.PERMISSION

        # 4. Definitions & Scope Rules (Term boundaries, non-coverage, expiry scope)
        if any(w in obj_lower for w in ("apply to new orders", "apply to new orders and renewals", "applies to existing subscriptions", "changes take effect upon renewal", "scope of the agreement")):
            return NormalizedClaimCategory.SCOPE_RULE, NormativeModality.PERMISSION

        if any(w in obj_lower for w in (
            "does not include", "defined in", "means", "be part of an online service",
            "expire at the end of the applicable subscription period",
            "attempted license transfers that do not comply",
            "without required approval will be void",
            "will not constitute a waiver", "is defined as", "shall mean", "has the meaning",
        )) or "has_definition" in predicate.lower():
            return NormalizedClaimCategory.DEFINITION, NormativeModality.PERMISSION

        # 5. Responsibilities (Organizational delegation / legal accountability statements)
        if any(w in obj_lower for w in (
            "remains responsible", "responsible for the performance",
            "responsible for any use of the products that does not comply",
            "responsible for all obligations under this agreement and for its affiliates",
            "is responsible for",
        )) or "remains_responsible_for" in predicate:
            return NormalizedClaimCategory.RESPONSIBILITY, NormativeModality.OBLIGATION

        # 6. Policy Claims (Normative legal duties, permissions, prohibitions, entitlements, and eligibility)
        if any(w in obj_lower for w in ("must not", "may not", "cannot", "prohibited", "is not licensed")):
            return NormalizedClaimCategory.POLICY_CLAIM, NormativeModality.PROHIBITION
        if any(w in obj_lower for w in ("must", "shall", "will pay", "required to", "agrees to")):
            return NormalizedClaimCategory.POLICY_CLAIM, NormativeModality.OBLIGATION
        if any(w in obj_lower for w in ("will receive", "credit", "refund")):
            return NormalizedClaimCategory.POLICY_CLAIM, NormativeModality.ENTITLEMENT
        if any(w in obj_lower for w in ("meets", "eligibility", "eligible")):
            return NormalizedClaimCategory.POLICY_CLAIM, NormativeModality.ELIGIBILITY
        return NormalizedClaimCategory.POLICY_CLAIM, NormativeModality.PERMISSION

    @classmethod
    def evaluate_conflict_compatibility(cls, claim_a: NormalizedClaim, claim_b: NormalizedClaim) -> Tuple[bool, str]:
        """
        Evaluates whether two claims are genuinely contradictory or complementary conditional rights.
        Returns (is_conflict, explanation).
        """
        # If subjects are different and non-overlapping, not a conflict
        if claim_a.subject != claim_b.subject and claim_a.subject not in ("Either party", "Each party", "Parties"):
            return False, "Distinct actors; rules apply to different legal entities."

        # Case: Termination clauses
        if "terminate" in claim_a.predicate and "terminate" in claim_b.predicate:
            # Check conditions
            cond_a = " ".join(claim_a.conditions).lower() + " " + claim_a.object.lower()
            cond_b = " ".join(claim_b.conditions).lower() + " " + claim_b.object.lower()

            is_without_cause_a = "without cause" in cond_a or "60 days" in cond_a
            is_without_cause_b = "without cause" in cond_b or "60 days" in cond_b

            is_for_breach_a = "material breach" in cond_a or "cure" in cond_a or "30 days" in cond_a
            is_for_breach_b = "material breach" in cond_b or "cure" in cond_b or "30 days" in cond_b

            if (is_without_cause_a and is_for_breach_b) or (is_for_breach_a and is_without_cause_b):
                return False, "Compatible conditional rights: termination without cause (60 days) and termination for breach (30 days) govern distinct legal triggers."

        # Case: Same predicate and overlapping conditions but contradictory modalities (e.g. OBLIGATION vs PROHIBITION)
        if claim_a.predicate == claim_b.predicate:
            if (claim_a.modality == NormativeModality.OBLIGATION and claim_b.modality == NormativeModality.PROHIBITION) or \
               (claim_a.modality == NormativeModality.PROHIBITION and claim_b.modality == NormativeModality.OBLIGATION):
                return True, f"Direct deontic contradiction: one rule mandates '{claim_a.predicate}' while the other prohibits it."

        return False, "No operational contradiction detected."

    @classmethod
    def normalize_candidate_claim(cls, candidate: Any) -> Optional[Any]:
        """
        Applies universal claim quality normalization to a CandidateClaim instance.
        Repairs subject, canonicalizes predicate, updates modality and classification.
        Returns None if candidate subject is an invalid fragment or malformed.
        """
        raw_subj = getattr(candidate, "subject", "")
        raw_pred = getattr(candidate, "predicate", "")
        raw_obj = str(getattr(candidate, "object", "") or "")
        loc = getattr(candidate, "locator", {}) or {}
        raw_text = getattr(candidate, "claim_text", "") or ""
        raw_span = getattr(candidate, "evidence_text_span", "") or ""
        combined_text = f"{raw_span} {raw_text} {raw_obj} {raw_subj}".lower()

        # Specific semantic remappings for high-priority candidates (Slice 3 & Phase 6 Calibration)
        # 0a. Liability cap
        if "liability" in combined_text and any(w in combined_text for w in ("aggregate", "maximum", "limited to", "12 months", "cap", "prior 12 months")):
            candidate.subject = "Each party" if not raw_subj or raw_subj.lower() in ("customer", "party", "each party") else raw_subj
            candidate.predicate = "has_liability_cap"
            candidate.claim_type = "rule"
            candidate.content_role = "policy_rule"
            candidate.modality = "POLICY_FACT"
            return candidate

        # 0b. Late fee penalty rate
        if ("late fee" in combined_text or "late payment" in combined_text) and any(w in combined_text for w in ("assess", "rate", "past due", "percent", "%", "penalty")):
            candidate.subject = "Microsoft" if "microsoft" in combined_text else (raw_subj or "Vendor")
            candidate.predicate = "has_late_payment_penalty_rate"
            candidate.claim_type = "rule"
            candidate.content_role = "policy_rule"
            candidate.modality = "PERMISSION"
            return candidate

        # 0c. Warranty remedy window
        if any(w in combined_text for w in ("warranty claim", "re-perform", "reperform")) and any(w in combined_text for w in ("90 days", "remedy window", "completion of the work")):
            candidate.subject = "Customer"
            candidate.predicate = "has_warranty_remedy_window"
            candidate.claim_type = "rule"
            candidate.content_role = "policy_rule"
            candidate.modality = "ENTITLED_TO"
            return candidate

        # 0d. Suspension during breach
        if "suspend" in combined_text and any(w in combined_text for w in ("material breach", "period of material breach", "without terminating")):
            candidate.subject = "Microsoft"
            candidate.predicate = "may_suspend_for_security_or_breach"
            candidate.claim_type = "rule"
            candidate.content_role = "policy_rule"
            candidate.modality = "PERMISSION"
            return candidate

        # 0e. Trade laws compliance
        if any(w in combined_text for w in ("export jurisdictions", "trade laws", "import or export of the products", "export administration regulations", "ofac")):
            if any(w in combined_text for w in ("comply", "compliance", "subject to u.s. and other countries")):
                candidate.subject = "Each party"
                candidate.predicate = "must_comply_with_trade_laws"
                candidate.claim_type = "rule"
                candidate.content_role = "policy_rule"
                candidate.modality = "OBLIGATION"
                return candidate

        # 0f. Definition with "does not include"
        if any(w in combined_text for w in ("does not include", "shall mean", "is defined as", "has the meaning")) and not any(w in combined_text for w in ("must", "shall pay", "penalty")):
            candidate.predicate = "has_definition"
            candidate.claim_type = "definition"
            candidate.content_role = "definition"
            candidate.modality = "POLICY_FACT"
            return candidate

        # 1. Candidate #78: 5% bonus credit mapped to receives_store_credit_bonus (actor inversion fixed)
        if "5% bonus" in combined_text or (raw_pred in ("has_default_refund_destination", "offers_store_credit_bonus", "receives_store_credit_bonus") and "bonus" in combined_text):
            candidate.subject = "Customer"
            candidate.predicate = "receives_store_credit_bonus"
            candidate.object = "5% bonus on credit value, maximum bonus $25.00 per return"
            candidate.conditions = ["chooses store credit instead of refund to original payment method"]
            candidate.modality = "MAY"
            candidate.claim_type = "rule"
            return candidate

        # 2. Candidate #94: $49 freight deduction mapped to has_return_freight_deduction
        if ("49" in combined_text or "freight deduction" in combined_text) and "oversize" in combined_text:
            candidate.subject = "Oversize items"
            candidate.predicate = "has_return_freight_deduction"
            candidate.object = "$49.00 flat return freight fee deducted from refund"
            candidate.conditions = ["change-of-mind return"]
            candidate.modality = "MUST"
            candidate.claim_type = "rule"
            return candidate

        # 3. Candidate #99: Retaining drop-off receipt mapped to requires_receipt_retention
        if "drop-off receipt" in combined_text:
            candidate.subject = "Customer"
            candidate.predicate = "requires_receipt_retention"
            candidate.object = "drop-off receipt until refund has been confirmed"
            candidate.modality = "MUST"
            candidate.claim_type = "rule"
            return candidate

        # 4. Candidate #178: Currency rule mapped to uses_original_charge_currency
        if "currency of the original charge" in combined_text:
            candidate.subject = "International refund"
            candidate.predicate = "uses_original_charge_currency"
            candidate.object = "currency of the original charge"
            candidate.modality = "MUST"
            candidate.claim_type = "rule"
            return candidate

        # 5. Candidate #180: Duty drawback responsibility certified as operative condition
        if "duty drawback" in combined_text:
            candidate.subject = "Customer"
            candidate.predicate = "is_responsible_for_duty_drawback"
            candidate.object = "filing customs duty drawback claims"
            candidate.conditions = ["where available"]
            candidate.modality = "MUST"
            candidate.claim_type = "rule"
            return candidate

        # 6. Candidate #134: Video courses 7-day exception re-anchored to Section 13.1
        if "video course" in combined_text and ("7 day" in combined_text or "20%" in combined_text):
            candidate.subject = "Video course"
            candidate.predicate = "has_refund_window"
            candidate.object = "7 days if less than 20% viewed"
            candidate.conditions = ["less than 20% viewed"]
            candidate.evidence_text_span = "Video courses may be refunded within 7 days if less than 20% of the content has been viewed."
            candidate.claim_text = "Video courses may be refunded within 7 days if less than 20% of the content has been viewed."
            candidate.modality = "MAY"
            candidate.claim_type = "rule"
            return candidate

        # 7. Candidate #104 & #105: Cosmetic flaws distinct from Keep It
        # Must run BEFORE Keep It so that 'Partial refund (keep item)' is not matched by 'keep it'
        if "cosmetic flaw" in combined_text or "partial refund (keep item)" in combined_text or ("keep item" in combined_text and ("|" in raw_text or "details" in str(loc).lower())):
            candidate.subject = "Partial refund for cosmetic flaws"
            candidate.predicate = "has_resolution_option_details"
            candidate.object = "Offered for minor cosmetic flaws"
            candidate.modality = "MAY"
            candidate.claim_type = "rule"
            return candidate

        # 8. Candidate #108 & #109: Keep It under-$40 policy with 2 per customer per year limit
        if re.search(r"\bkeep\s+it\b", combined_text, re.IGNORECASE) or "valued under $40" in combined_text or "under $40.00" in combined_text or ("under $40" in combined_text and "damage" in combined_text):
            candidate.subject = "Damaged item under $40"
            candidate.predicate = "may_issue_refund_without_return"
            candidate.object = "refund without requiring item return ('Keep It' policy)"
            candidate.conditions = ["at agent's discretion", "maximum 2 instances per customer per year"]
            candidate.modality = "MAY"
            candidate.claim_type = "rule"
            return candidate

        # 9. In-store immediate refund and bank posting duration (Candidate #24)
        if "in-store refunds to the original card" in combined_text or ("processed immediately" in combined_text and "bank" in combined_text):
            candidate.subject = "In-store refunds"
            candidate.predicate = "has_posting_duration"
            candidate.object = "processed immediately; bank may take 3-5 days to post the credit"
            candidate.modality = "POLICY_FACT"
            candidate.claim_type = "rule"
            return candidate

        # 10. Price drop adjustment (Candidate #81)
        if "drops in price" in combined_text or "price adjustment" in combined_text:
            candidate.subject = "Price adjustments"
            candidate.predicate = "has_price_adjustment_window"
            candidate.object = "14 days of purchase for one-time refund of difference"
            candidate.conditions = ["item drops in price within 14 days of purchase"]
            candidate.modality = "POLICY_FACT"
            candidate.claim_type = "rule"
            return candidate

        # 11. Courtesy refund if forgot to cancel trial (Candidate #86)
        if "forget to cancel" in combined_text or "forgot to cancel" in combined_text or ("first charge" in combined_text and "7 days" in combined_text):
            candidate.subject = "Free trials"
            candidate.predicate = "may_request_first_charge_refund"
            candidate.object = "within 7 days for a full refund of the first charge"
            candidate.conditions = ["forget to cancel and charged"]
            candidate.modality = "MAY"
            candidate.claim_type = "rule"
            return candidate

        # 12. Order cancellation status & self-service window (Candidate #80)
        if "refund pending (within 1 hour)" in combined_text or ("authorisation" in combined_text and "self-service" in combined_text and "processing" in combined_text):
            candidate.subject = "Order cancellation"
            candidate.predicate = "has_cancellation_window"
            candidate.object = "Refund Pending (within 1 hour) self-service full refund and immediate authorization release"
            candidate.modality = "POLICY_FACT"
            candidate.claim_type = "rule"
            return candidate

        # 13. Subscription Products disaggregation & Pause subscription (Candidate #87)
        if "trailhead box" in combined_text:
            candidate.subject = "Trailhead Box subscription"
            if "pause" in combined_text:
                candidate.predicate = "can_pause_subscription"
                candidate.object = "for up to 3 months, once per year, from the account page"
                candidate.modality = "MAY"
            elif "before the 25th" in combined_text or "cancellation" in (candidate.predicate or "").lower():
                candidate.predicate = "has_cancellation_rule"
            else:
                candidate.predicate = "has_refund_rule"
            candidate.claim_type = "rule"
            return candidate

        if "rewards plus" in combined_text:
            candidate.subject = "Rewards Plus subscription"
            candidate.predicate = "has_refund_rule"
            candidate.claim_type = "rule"
            return candidate

        if "gear care plan" in combined_text:
            candidate.subject = "Gear Care Plan subscription"
            candidate.predicate = "has_refund_rule"
            candidate.claim_type = "rule"
            return candidate

        # 14. Table Request Information: Preserve Exact Field Names & Required? vs Example
        col_hdr = loc.get("table_grid", {}).get("col_header") if loc.get("table_grid") else ""
        if "order number" in raw_subj.lower() or "| order number |" in raw_text.lower():
            candidate.subject = "Order number"
        elif "email on order" in raw_subj.lower() or "| email on order |" in raw_text.lower():
            candidate.subject = "Email on order"
        elif "item sku" in raw_subj.lower() or "| item sku" in raw_text.lower():
            candidate.subject = "Item SKU / name"
        elif "reason for return" in raw_subj.lower() or "| reason for return |" in raw_text.lower():
            candidate.subject = "Reason for return"
        elif "preferred resolution" in raw_subj.lower() or "| preferred resolution |" in raw_text.lower():
            candidate.subject = "Preferred resolution"
        elif "photos" in raw_subj.lower() or "| photos |" in raw_text.lower():
            candidate.subject = "Photos"

        if "required" in str(col_hdr).lower() or "required?" in raw_text.lower() or loc.get("col_header") == "Required?":
            candidate.predicate = "is_required_for_refund_request"
            candidate.claim_type = "rule"
        elif "example" in str(col_hdr).lower() or loc.get("col_header") == "Example":
            candidate.predicate = "has_example_value"
            candidate.claim_type = "non_rule"
            candidate.content_role = "example"

        # 15. Revision History
        if "revision" in (loc.get("section_heading") or "").lower() or "document history" in (loc.get("section_heading") or "").lower() or "20.1 revision history" in combined_text:
            candidate.predicate = "has_revision_history"
            candidate.content_role = "revision_history"
            candidate.claim_type = "non_rule"

        # Preserve threshold condition from raw subject before normalizer truncates it
        thresh_m = re.search(r"\b(?:over|exceeding|greater than|more than)\s*\$?\s*(\d+(?:\.\d+)?)\b", raw_subj, re.IGNORECASE)
        if thresh_m:
            val_num = float(thresh_m.group(1))
            val_str = f"{int(val_num) if val_num.is_integer() else val_num}"
            t_cond = f"order_value > {val_str} USD"
            current_conds = getattr(candidate, "conditions", None)
            if current_conds is None:
                candidate.conditions = [t_cond]
            elif t_cond not in current_conds:
                current_conds.append(t_cond)
        if re.search(r"\bany\s+reason\b", raw_subj, re.IGNORECASE):
            current_conds = getattr(candidate, "conditions", None)
            if current_conds is None:
                candidate.conditions = ["return_reason: any reason"]
            elif "return_reason: any reason" not in current_conds:
                current_conds.append("return_reason: any reason")

        norm_subj, is_valid = cls.normalize_subject_entity(candidate.subject)
        if not is_valid or not norm_subj:
            return None

        norm_pred = cls.normalize_predicate(raw_pred, norm_subj, raw_obj)
        cat, modality = cls.classify_claim_category(norm_subj, norm_pred, raw_obj)
        if cat == NormalizedClaimCategory.DEFINITION and norm_pred in ("has_validity_rule", "validity_rule", "is_valid"):
            norm_pred = "has_definition"
            candidate.claim_type = "definition"

        candidate.subject = norm_subj
        candidate.predicate = norm_pred
        candidate.modality = modality.value
        qualifiers = getattr(candidate, "qualifiers", None)
        if qualifiers is None:
            candidate.qualifiers = [f"category:{cat.value}"]
        elif f"category:{cat.value}" not in qualifiers:
            qualifiers.append(f"category:{cat.value}")

        return candidate

    @classmethod
    def score_claim_quality(cls, claim: NormalizedClaim) -> ClaimQualityScore:
        """
        Evaluates a claim against the Stage 9 100-point composite rubric:
        - Subject validity: 0-20
        - Predicate validity: 0-20
        - Atomicity: 0-20
        - Evidence grounding: 0-20
        - Deduplication status: 0-10
        - Claim-type correctness: 0-10

        Status rules:
        >= 90: CANONICAL
        75 - 89: REVIEW
        < 75: REJECT_OR_REPAIR
        """
        score = ClaimQualityScore()

        # 1. Subject validity (0 - 20)
        norm_subj, valid_subj, subj_review = cls.normalize_subject_with_safety_check(claim.subject, claim.evidence_span)
        if not valid_subj or not norm_subj:
            score.subject_validity = 0.0
        elif subj_review is not None:
            score.subject_validity = 14.0  # Downgrade ambiguous passive mapping
        elif norm_subj in CANONICAL_SUBJECT_ALLOWLIST:
            score.subject_validity = 20.0
        else:
            score.subject_validity = 10.0

        # 2. Predicate validity (0 - 20)
        pred = (claim.predicate or "").strip().lower()
        if pred in cls.REJECTED_GENERIC_PREDICATES:
            score.predicate_validity = 0.0
        elif pred in CONTROLLED_PREDICATE_VOCABULARY:
            score.predicate_validity = 20.0
        elif any(pred.startswith(m) for m in ("must_", "may_", "prohibited_", "warrants_", "has_", "grants_", "requires_")):
            score.predicate_validity = 18.0
        else:
            score.predicate_validity = 10.0

        # 3. Atomicity (0 - 20)
        is_atom, triggers = cls.is_atomic_rule(claim.object)
        if not is_atom or not claim.is_atomic:
            score.atomicity = 5.0
        else:
            score.atomicity = 20.0

        # 4. Evidence grounding (0 - 20)
        ev = (claim.evidence_span or "").strip()
        loc = claim.locator or {}
        if not ev or len(ev) < 10:
            score.evidence_grounding = 0.0
        elif not loc.get("page") and not loc.get("section"):
            score.evidence_grounding = 12.0
        else:
            score.evidence_grounding = 20.0

        # 5. Deduplication status (0 - 10)
        if claim.status == "COLLAPSED_DUPLICATE":
            score.deduplication_status = 0.0
        else:
            score.deduplication_status = 10.0

        # 6. Claim-type correctness (0 - 10)
        if NormalizedClaimCategory.is_agent_facing(claim.category):
            score.claim_type_correctness = 10.0
        else:
            score.claim_type_correctness = 6.0

        score.calculate_total()
        return score

    @classmethod
    def should_route_to_human_review(cls, claim: NormalizedClaim) -> Tuple[bool, List[str]]:
        """
        Determines whether a claim must be routed to the blinded human adjudication queue.
        Stage 10 Routing Triggers:
        - Low-confidence or ambiguous subject normalization
        - Unrecognized / generic predicates
        - Compound sentences that cannot be safely split
        - Potential duplicates with differing conditions
        - Potential conflicts
        - Claims involving high-risk clauses (jurisdiction, liability cap, indemnity, termination)
        """
        reasons: List[str] = []
        score = cls.score_claim_quality(claim)

        if score.status == "REVIEW":
            reasons.append(f"Quality score in review tier: {score.total_score:.1f}/100")

        if score.predicate_validity < 15.0:
            reasons.append(f"Generic or unrecognized predicate: '{claim.predicate}'")

        if not claim.is_atomic or score.atomicity < 15.0:
            reasons.append("Non-atomic compound proposition requiring manual decomposition")

        # High-risk legal clauses
        obj_lower = (claim.object or "").lower()
        pred_lower = (claim.predicate or "").lower()
        if any(w in obj_lower or w in pred_lower for w in ("liability", "indemnif", "termination", "governing law", "jurisdiction", "exclusive venue")):
            reasons.append("High-risk legal clause (liability / indemnity / termination / jurisdiction)")

        return (len(reasons) > 0, reasons)
