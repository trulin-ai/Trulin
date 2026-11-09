"""
Canonical Predicate Registry (Sprint 2 / Layer 5-7).
Defines versioned, controlled enterprise policy predicates to prevent
unconstrained generic verbs ('specifies', 'be', 'defines', 'override')
from being approved as canonical policy assertions.
"""

from __future__ import annotations

import re
from enum import Enum
from typing import Optional, Set, Tuple


class CanonicalPredicate(str, Enum):
    """Controlled canonical predicate vocabulary for enterprise governance."""

    # Policy Entitlements & Windows
    HAS_RETURN_WINDOW = "has_return_window"
    HAS_RETURN_DEADLINE = "has_return_deadline"
    HAS_REFUND_PERCENTAGE = "has_refund_percentage"
    HAS_REFUND_ELIGIBILITY = "has_refund_eligibility"
    HAS_REFUND_METHOD = "has_refund_method"
    HAS_POSTING_DURATION = "has_posting_duration"
    HAS_STAGE_DURATION = "has_stage_duration"

    # Cancellation States & Post-Shipment Outcomes
    HAS_CANCELLATION_ELIGIBILITY = "has_cancellation_eligibility"
    HAS_CANCELLATION_RULE = "has_cancellation_rule"
    HAS_CANCELLATION_REFUND_OUTCOME = "has_cancellation_refund_outcome"
    HAS_CANCELLATION_REFUND_TIMING = "has_cancellation_refund_timing"
    HAS_POST_SHIPMENT_RESOLUTION_PATH = "has_post_shipment_resolution_path"
    HAS_POST_DELIVERY_RESOLUTION_PATH = "has_post_delivery_resolution_path"

    # Warranty Obligations
    HAS_WARRANTY_PERIOD = "has_warranty_period"
    HAS_WARRANTY_REMEDY = "has_warranty_remedy"

    # Authorizations & Risk Gates
    REQUIRES_APPROVAL_ROLE = "requires_approval_role"
    REQUIRES_FRAUD_REVIEW = "requires_fraud_review"

    # Contact Channels & Operational Service Levels
    HAS_CONTACT_CHANNEL = "has_contact_channel"
    HAS_CONTACT_HOURS = "has_contact_hours"
    HAS_CONTACT_PHONE = "has_contact_phone"
    HAS_CONTACT_EMAIL = "has_contact_email"
    HAS_CONTACT_ADDRESS = "has_contact_address"
    HAS_SERVICE_LEVEL_TARGET = "has_service_level_target"

    # Definitions, References & Structured Options
    HAS_INTERNAL_POLICY_REFERENCE = "has_internal_policy_reference"
    HAS_DEFINITION = "has_definition"
    HAS_VALIDITY_RULE = "has_validity_rule"
    HAS_RESOLUTION_OPTION_DETAILS = "has_resolution_option_details"
    HAS_RESOLUTION_PATH = "has_resolution_path"
    HAS_BILLING_SCHEDULE = "has_billing_schedule"
    HAS_RETURN_SHIPPING_RULE = "has_return_shipping_rule"
    HAS_RETURN_LABEL_COST = "has_return_label_cost"
    HAS_DUTIES_AND_TAXES_RULE = "has_duties_and_taxes_rule"
    HAS_REFUND_ALLOCATION_RULE = "has_refund_allocation_rule"
    HAS_DISPUTE_RESOLUTION_RULE = "has_dispute_resolution_rule"
    HAS_IDENTITY_VERIFICATION_REQUIREMENT = "has_identity_verification_requirement"
    HAS_PROVIDER_GOVERNED_TIMELINE = "has_provider_governed_timeline"
    HAS_EXAMPLE_VALUE = "has_example_value"

    # Normalized Domain Behaviors & Atomic Criteria
    RESPONSIBLE_FOR_SHIPPING_COSTS = "responsible_for_shipping_costs"
    COVERS_SHIPPING_COSTS = "covers_shipping_costs"
    MAY_OVERRIDE_STANDARD_TERMS = "may_override_standard_terms"
    CAN_INITIATE_RETURN = "can_initiate_return"
    CAN_CANCEL_BEFORE_SHIPMENT = "can_cancel_before_shipment"
    CAN_CANCEL_BEFORE_TRIAL_ENDS = "can_cancel_before_trial_ends"
    PROVIDES_DOCUMENTATION_UPON_REQUEST = "provides_documentation_upon_request"
    MUST_BE_HANDLED_AS_RETURN = "must_be_handled_as_return"
    MAY_RECEIVE_GOODWILL_DISCOUNT = "may_receive_goodwill_discount"
    MAY_APPLY_ADMINISTRATION_FEE = "may_apply_administration_fee"
    MAY_RECEIVE_STORE_CREDIT = "may_receive_store_credit"
    MUST_VERIFY_REFUND_CONDITIONS = "must_verify_refund_conditions"
    REQUIRES_RETURN_WITHIN_APPLICABLE_WINDOW = "requires_return_within_applicable_window"
    MUST_BE_IN_ORIGINAL_CONDITION = "must_be_in_original_condition"
    REQUIRES_VERIFIABLE_ORDER_OR_PURCHASE_PROOF = "requires_verifiable_order_or_purchase_proof"
    HAS_REPLACEMENT_ELIGIBILITY = "has_replacement_eligibility"
    HAS_DISPUTE_RESOLUTION_PREFERENCE = "has_dispute_resolution_preference"
    HAS_EVIDENCE_SUBMISSION_DEADLINE = "has_evidence_submission_deadline"
    HAS_DISPUTE_DECISION_TIMELINE = "has_dispute_decision_timeline"
    HAS_RMA_GENERATION_BEHAVIOR = "has_rma_generation_behavior"
    HAS_DEFAULT_REFUND_DESTINATION = "has_default_refund_destination"
    HAS_EXPIRATION_RULE = "has_expiration_rule"
    HAS_RETURN_CHANNEL_ELIGIBILITY = "has_return_channel_eligibility"
    HAS_PURCHASE_VERIFICATION_REQUIREMENT = "has_purchase_verification_requirement"
    HAS_EXPIRATION_AND_FEE_RULE = "has_expiration_and_fee_rule"
    HAS_REFUND_WINDOW = "has_refund_window"
    HAS_CURRENCY_CONVERSION_RULE = "has_currency_conversion_rule"
    HAS_USAGE_LIMIT = "has_usage_limit"
    HAS_IMPLEMENTATION_RATIONALE = "has_implementation_rationale"
    HAS_REPORTING_REQUIREMENT = "has_reporting_requirement"
    HAS_COURTESY_REPLACEMENT_RULE = "has_courtesy_replacement_rule"
    MAY_ISSUE_REFUND_WITHOUT_RETURN = "may_issue_refund_without_return"
    HAS_FUNDS_DEBIT_OUTCOME = "has_funds_debit_outcome"

    # Enterprise Workforce & Policy Governance
    HAS_CONFIRMED_NOTICE_DURATION = "has_confirmed_notice_duration"
    HAS_PROBATIONARY_NOTICE_DURATION = "has_probationary_notice_duration"
    MUST_RETURN_COMPANY_PROPERTY = "must_return_company_property"
    MAY_RECOVER_SHORT_NOTICE_AMOUNT = "may_recover_short_notice_amount"
    ISSUES_PAY_IN_LIEU_OF_NOTICE = "issues_pay_in_lieu_of_notice"
    PROHIBITS_PAY_IN_LIEU_OF_NOTICE = "prohibits_pay_in_lieu_of_notice"
    APPLIES_TO_EMPLOYMENT_TYPES = "applies_to_employment_types"
    REQUIRES_OFFBOARDING_HANDOVER_TASKS = "requires_offboarding_handover_tasks"
    REFERENCES_GOVERNING_POLICIES = "references_governing_policies"
    HAS_DOCUMENT_METADATA = "has_document_metadata"
    HAS_INTELLECTUAL_PROPERTY_OWNERSHIP = "has_intellectual_property_ownership"

    # Commercial & Policy Operations (Slice 3 Refinements)
    OFFERS_STORE_CREDIT_BONUS = "offers_store_credit_bonus"
    HAS_RETURN_FREIGHT_DEDUCTION = "has_return_freight_deduction"
    REQUIRES_RECEIPT_RETENTION = "requires_receipt_retention"
    USES_ORIGINAL_CHARGE_CURRENCY = "uses_original_charge_currency"
    IS_RESPONSIBLE_FOR_DUTY_DRAWBACK = "is_responsible_for_duty_drawback"
    IS_REQUIRED_FOR_REFUND_REQUEST = "is_required_for_refund_request"
    HAS_REFUND_RULE = "has_refund_rule"
    HAS_REVISION_HISTORY = "has_revision_history"


class PredicateRegistry:
    """
    Registry for validating, normalizing, and shielding enterprise policy predicates.
    """

    CANONICAL_PREDICATES: Set[str] = {p.value for p in CanonicalPredicate}

    DISALLOWED_GENERIC_VERBS: Set[str] = {
        "be", "is", "are", "defines", "specifies", "cover", "covers", "return", "returns",
        "issue", "start", "verify", "override", "has_refund", "have", "has",
        "must_satisfy_requirement", "apply", "offer", "specifies_governing_rule",
    }

    RAW_PHRASE_MAPPINGS = {
        "must verify each condition": CanonicalPredicate.MUST_VERIFY_REFUND_CONDITIONS.value,
        "must verify refund conditions": CanonicalPredicate.MUST_VERIFY_REFUND_CONDITIONS.value,
        "can start a return": CanonicalPredicate.CAN_INITIATE_RETURN.value,
        "can start their return": CanonicalPredicate.CAN_INITIATE_RETURN.value,
        "start return": CanonicalPredicate.CAN_INITIATE_RETURN.value,
        "may override these terms": CanonicalPredicate.MAY_OVERRIDE_STANDARD_TERMS.value,
        "may override standard terms": CanonicalPredicate.MAY_OVERRIDE_STANDARD_TERMS.value,
        "override standard terms": CanonicalPredicate.MAY_OVERRIDE_STANDARD_TERMS.value,
        "requires manager approval": CanonicalPredicate.REQUIRES_APPROVAL_ROLE.value,
        "team lead approval required": CanonicalPredicate.REQUIRES_APPROVAL_ROLE.value,
        "manager approval required": CanonicalPredicate.REQUIRES_APPROVAL_ROLE.value,
        "director approval required": CanonicalPredicate.REQUIRES_APPROVAL_ROLE.value,
        "fraud review required": CanonicalPredicate.REQUIRES_FRAUD_REVIEW.value,
        "secondary fraud review": CanonicalPredicate.REQUIRES_FRAUD_REVIEW.value,
        "can be cancelled": CanonicalPredicate.HAS_CANCELLATION_ELIGIBILITY.value,
        "can it be cancelled": CanonicalPredicate.HAS_CANCELLATION_ELIGIBILITY.value,
        "cancel before shipment": CanonicalPredicate.CAN_CANCEL_BEFORE_SHIPMENT.value,
        "can cancel before shipment": CanonicalPredicate.CAN_CANCEL_BEFORE_SHIPMENT.value,
        "cancel before trial ends": CanonicalPredicate.CAN_CANCEL_BEFORE_TRIAL_ENDS.value,
        "can cancel before trial ends": CanonicalPredicate.CAN_CANCEL_BEFORE_TRIAL_ENDS.value,
        "cancel before the trial ends": CanonicalPredicate.CAN_CANCEL_BEFORE_TRIAL_ENDS.value,
        "provides documentation upon request": CanonicalPredicate.PROVIDES_DOCUMENTATION_UPON_REQUEST.value,
        "provide documentation upon request": CanonicalPredicate.PROVIDES_DOCUMENTATION_UPON_REQUEST.value,
        "provides commercial invoice upon request": CanonicalPredicate.PROVIDES_DOCUMENTATION_UPON_REQUEST.value,
        "will provide commercial invoice": CanonicalPredicate.PROVIDES_DOCUMENTATION_UPON_REQUEST.value,
        "must be handled as return": CanonicalPredicate.MUST_BE_HANDLED_AS_RETURN.value,
        "shipped order must be handled as return": CanonicalPredicate.HAS_POST_SHIPMENT_RESOLUTION_PATH.value,
        "goodwill discount": CanonicalPredicate.MAY_RECEIVE_GOODWILL_DISCOUNT.value,
        "administration fee": CanonicalPredicate.MAY_APPLY_ADMINISTRATION_FEE.value,
        "apply administration fee": CanonicalPredicate.MAY_APPLY_ADMINISTRATION_FEE.value,
        "store credit": CanonicalPredicate.MAY_RECEIVE_STORE_CREDIT.value,
        "offer store credit": CanonicalPredicate.MAY_RECEIVE_STORE_CREDIT.value,
        "receive store credit": CanonicalPredicate.MAY_RECEIVE_STORE_CREDIT.value,
        "full refund within 3–5 days": CanonicalPredicate.HAS_CANCELLATION_REFUND_TIMING.value,
        "full refund within 3-5 days": CanonicalPredicate.HAS_CANCELLATION_REFUND_TIMING.value,
        "see section 9": CanonicalPredicate.HAS_INTERNAL_POLICY_REFERENCE.value,
        "see section 14": CanonicalPredicate.HAS_INTERNAL_POLICY_REFERENCE.value,
        "covered by warranty": CanonicalPredicate.HAS_RESOLUTION_PATH.value,
        "governing rule": CanonicalPredicate.HAS_VALIDITY_RULE.value,
        "specifies governing rule": CanonicalPredicate.HAS_VALIDITY_RULE.value,
        "lost or stolen gift cards": CanonicalPredicate.HAS_REPLACEMENT_ELIGIBILITY.value,
        "lost or stolen gift card": CanonicalPredicate.HAS_REPLACEMENT_ELIGIBILITY.value,
        "gift card replacement": CanonicalPredicate.HAS_REPLACEMENT_ELIGIBILITY.value,
        "resolve directly": CanonicalPredicate.HAS_DISPUTE_RESOLUTION_PREFERENCE.value,
        "contact us before filing a dispute": CanonicalPredicate.HAS_DISPUTE_RESOLUTION_PREFERENCE.value,
        "dispute resolution preference": CanonicalPredicate.HAS_DISPUTE_RESOLUTION_PREFERENCE.value,
        "submit evidence within 7 days": CanonicalPredicate.HAS_EVIDENCE_SUBMISSION_DEADLINE.value,
        "evidence submission within 7 days": CanonicalPredicate.HAS_EVIDENCE_SUBMISSION_DEADLINE.value,
        "evidence submission deadline": CanonicalPredicate.HAS_EVIDENCE_SUBMISSION_DEADLINE.value,
        "issuer decides within 30–90 days": CanonicalPredicate.HAS_DISPUTE_DECISION_TIMELINE.value,
        "issuer decides within 30-90 days": CanonicalPredicate.HAS_DISPUTE_DECISION_TIMELINE.value,
        "dispute decision timeline": CanonicalPredicate.HAS_DISPUTE_DECISION_TIMELINE.value,
        "portal returns generate rma": CanonicalPredicate.HAS_RMA_GENERATION_BEHAVIOR.value,
        "online requests generate rma": CanonicalPredicate.HAS_RMA_GENERATION_BEHAVIOR.value,
        "rma generation behavior": CanonicalPredicate.HAS_RMA_GENERATION_BEHAVIOR.value,
        "original payment method": CanonicalPredicate.HAS_DEFAULT_REFUND_DESTINATION.value,
        "refunded to original payment method": CanonicalPredicate.HAS_DEFAULT_REFUND_DESTINATION.value,
        "default refund destination": CanonicalPredicate.HAS_DEFAULT_REFUND_DESTINATION.value,
        "never expire": CanonicalPredicate.HAS_EXPIRATION_RULE.value,
        "no expiration": CanonicalPredicate.HAS_EXPIRATION_RULE.value,
        "carry no fees": CanonicalPredicate.HAS_EXPIRATION_RULE.value,
        "gift cards never expire": CanonicalPredicate.HAS_EXPIRATION_AND_FEE_RULE.value,
        "has expiration rule": CanonicalPredicate.HAS_EXPIRATION_RULE.value,
        "gift cards never expire and carry no fees": CanonicalPredicate.HAS_EXPIRATION_AND_FEE_RULE.value,
        "never expire and carry no fees": CanonicalPredicate.HAS_EXPIRATION_AND_FEE_RULE.value,
        "has expiration and fee rule": CanonicalPredicate.HAS_EXPIRATION_AND_FEE_RULE.value,
        "items bought in-store": CanonicalPredicate.HAS_RETURN_CHANNEL_ELIGIBILITY.value,
        "bought in-store": CanonicalPredicate.HAS_RETURN_CHANNEL_ELIGIBILITY.value,
        "return channel eligibility": CanonicalPredicate.HAS_RETURN_CHANNEL_ELIGIBILITY.value,
        "has return channel eligibility": CanonicalPredicate.HAS_RETURN_CHANNEL_ELIGIBILITY.value,
        "order number or proof of purchase": CanonicalPredicate.HAS_PURCHASE_VERIFICATION_REQUIREMENT.value,
        "proof of purchase can be verified": CanonicalPredicate.HAS_PURCHASE_VERIFICATION_REQUIREMENT.value,
        "purchase verification requirement": CanonicalPredicate.HAS_PURCHASE_VERIFICATION_REQUIREMENT.value,
        "has purchase verification requirement": CanonicalPredicate.HAS_PURCHASE_VERIFICATION_REQUIREMENT.value,
        "encourage customers to contact us": CanonicalPredicate.HAS_DISPUTE_RESOLUTION_PREFERENCE.value,
        "video course refund": CanonicalPredicate.HAS_REFUND_WINDOW.value,
        "currency conversion": CanonicalPredicate.HAS_CURRENCY_CONVERSION_RULE.value,
        "has currency conversion rule": CanonicalPredicate.HAS_CURRENCY_CONVERSION_RULE.value,
        "exchange differences are not compensated": CanonicalPredicate.HAS_CURRENCY_CONVERSION_RULE.value,
        "keep it limit": CanonicalPredicate.HAS_USAGE_LIMIT.value,
        "has usage limit": CanonicalPredicate.HAS_USAGE_LIMIT.value,
        "fraud-prevention rationale": CanonicalPredicate.HAS_IMPLEMENTATION_RATIONALE.value,
        "has implementation rationale": CanonicalPredicate.HAS_IMPLEMENTATION_RATIONALE.value,
        "stolen package reporting": CanonicalPredicate.HAS_REPORTING_REQUIREMENT.value,
        "has reporting requirement": CanonicalPredicate.HAS_REPORTING_REQUIREMENT.value,
        "courtesy replacement": CanonicalPredicate.HAS_COURTESY_REPLACEMENT_RULE.value,
        "has courtesy replacement rule": CanonicalPredicate.HAS_COURTESY_REPLACEMENT_RULE.value,
        "chargeback resolution preference": CanonicalPredicate.HAS_DISPUTE_RESOLUTION_PREFERENCE.value,
        "has dispute resolution preference": CanonicalPredicate.HAS_DISPUTE_RESOLUTION_PREFERENCE.value,
        "items returned after 90 days": CanonicalPredicate.HAS_REFUND_ELIGIBILITY.value,
        "returned after 90 days": CanonicalPredicate.HAS_REFUND_ELIGIBILITY.value,
        "after 90 days": CanonicalPredicate.HAS_REFUND_ELIGIBILITY.value,
        "perishable goods past 14 days": CanonicalPredicate.HAS_REFUND_ELIGIBILITY.value,
        "corrupt or inaccessible digital files": CanonicalPredicate.HAS_REFUND_WINDOW.value,
        "corrupt or inaccessible digital product": CanonicalPredicate.HAS_REFUND_WINDOW.value,
        "damaged items under $40": CanonicalPredicate.MAY_ISSUE_REFUND_WITHOUT_RETURN.value,
        "damaged item valued under $40": CanonicalPredicate.MAY_ISSUE_REFUND_WITHOUT_RETURN.value,
        "funds are debited": CanonicalPredicate.HAS_FUNDS_DEBIT_OUTCOME.value,
        "has funds debit outcome": CanonicalPredicate.HAS_FUNDS_DEBIT_OUTCOME.value,
    }

    @classmethod
    def is_canonical(cls, predicate: str) -> bool:
        """Checks if a predicate is a valid approved canonical predicate."""
        if not predicate:
            return False
        return predicate.strip().lower() in cls.CANONICAL_PREDICATES

    @classmethod
    def is_disallowed_generic(cls, predicate: str) -> bool:
        """Checks if a predicate is a prohibited bare verb or generic token."""
        if not predicate:
            return True
        p_clean = predicate.strip().lower()
        return (
            p_clean in cls.DISALLOWED_GENERIC_VERBS
            or p_clean.isdigit()
            or len(p_clean) <= 1
        )

    @classmethod
    def normalize_predicate(cls, raw_pred: str) -> Tuple[str, bool]:
        """
        Normalizes a raw predicate verb phrase into an approved canonical predicate.
        Returns:
            (canonical_predicate, is_canonical)
        """
        if not raw_pred:
            return "", False

        cleaned = raw_pred.strip().lower()

        # 1. Direct registry hit
        if cleaned in cls.CANONICAL_PREDICATES:
            return cleaned, True

        # 2. Known raw phrase mapping
        if cleaned in cls.RAW_PHRASE_MAPPINGS:
            return cls.RAW_PHRASE_MAPPINGS[cleaned], True

        for phrase, mapped in cls.RAW_PHRASE_MAPPINGS.items():
            if phrase in cleaned:
                return mapped, True

        # 3. Disallowed generic token
        if cls.is_disallowed_generic(cleaned):
            return cleaned, False

        # 4. Unknown but syntactically valid predicate
        return cleaned, False
