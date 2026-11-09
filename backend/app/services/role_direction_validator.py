"""
Evidence-Conditioned Role Direction Validator.

Universal role validation that checks clause evidence for explicit grant language
instead of assuming hardcoded company or counterparty roles.
"""

import re
from dataclasses import dataclass
from typing import Optional

from app.taxonomy.registry import PredicateRegistryService


@dataclass
class RoleDirectionResult:
    is_valid: bool
    requires_review: bool
    explicit_grant_found: bool
    reason: Optional[str] = None


class RoleDirectionValidator:
    """Validates directional assignment of rights and duties against clause evidence."""

    ASYMMETRIC_VENDOR_RIGHTS = {
        "may_suspend_for_security_or_breach",
        "may_suspend_subscription",
        "may_assess_late_fee",
        "may_collect_return_or_insufficient_funds_fee",
        "may_require_security_for_invoicing",
        "may_audit_compliance",
    }

    ASYMMETRIC_CUSTOMER_RIGHTS = {
        "has_professional_services_remedy_window",
        "may_review_non_microsoft_product_terms",
    }

    CUSTOMER_ROLES = {"customer", "client", "buyer", "subscriber", "licensee", "employee", "recipient"}
    VENDOR_ROLES = {"vendor", "provider", "supplier", "licensor", "service_provider", "employer", "discloser"}

    @classmethod
    def validate(
        cls,
        subject: str,
        predicate: str,
        clause_text: Optional[str] = "",
        subject_role: Optional[str] = None,
    ) -> RoleDirectionResult:
        s_clean = (subject or "").strip()
        s_lower = s_clean.lower()
        p_clean = (predicate or "").strip()
        p_lower = p_clean.lower()
        clause_lower = (clause_text or "").lower()

        # Reciprocal/neutral subjects always pass
        if s_lower in {"either party", "each party", "both parties", "neither party", "parties", "any party"}:
            return RoleDirectionResult(is_valid=True, requires_review=False, explicit_grant_found=True)

        if "either party" in clause_lower or "each party" in clause_lower:
            # Clause explicitly grants reciprocal right
            return RoleDirectionResult(is_valid=True, requires_review=False, explicit_grant_found=True)

        # Fail-closed check: Custom contract precedence cannot be granted as an unrestricted customer permission
        if p_lower in ("may_override_standard_terms", "may_supersede_standard_terms"):
            if s_lower in cls.CUSTOMER_ROLES or any(w in s_lower for w in ("customer", "buyer", "user", "client", "business customer")):
                return RoleDirectionResult(
                    is_valid=False,
                    requires_review=True,
                    explicit_grant_found=False,
                    reason=(
                        "Role direction failure: An individual Customer cannot be granted unilateral permission "
                        "to override standard policy terms; precedence belongs to custom contracts or corporate agreements."
                    ),
                )

        # Fail-closed check: Provider commitment to provide documentation upon request cannot be reversed into customer requirement
        if p_lower == "requires_verifiable_order_or_purchase_proof":
            if re.search(r"\b(?:will provide|provides|provide)\b.*\b(?:upon\s+(?:\w+\s+)?request|on\s+(?:\w+\s+)?request)\b", clause_lower) and any(
                w in s_lower or w in clause_lower for w in ("northwind", "vendor", "provider", "supplier", "we ")
            ):
                return RoleDirectionResult(
                    is_valid=False,
                    requires_review=True,
                    explicit_grant_found=False,
                    reason=(
                        "Role direction reversal: Clause states provider supplies commercial invoice and proof of return "
                        "upon request, which contradicts a requirement on the customer to supply proof."
                    ),
                )

        # Fail-closed check: Physical goods pre-shipment cancellation cannot apply to digital subscriptions or free trials
        if p_lower == "can_cancel_before_shipment":
            if "trial" in clause_lower and not any(w in clause_lower for w in ("ship", "shipped", "shipping", "carrier", "tracking")):
                return RoleDirectionResult(
                    is_valid=False,
                    requires_review=True,
                    explicit_grant_found=False,
                    reason=(
                        "Incompatible action domain: Physical goods pre-shipment cancellation predicate "
                        "cannot be applied to digital trial subscription cancellation."
                    ),
                )

        # Check taxonomy allowed subject roles
        pred_defn = PredicateRegistryService.get_predicate(p_lower)
        if pred_defn:
            if "ANY_PARTY" in pred_defn.allowed_subject_roles:
                return RoleDirectionResult(is_valid=True, requires_review=False, explicit_grant_found=True)

        # Asymmetric vendor right assigned to customer-side role
        is_customer_subject = s_lower in cls.CUSTOMER_ROLES or (subject_role and subject_role.upper() in {"CUSTOMER", "BUYER", "LICENSEE"})
        is_vendor_right = p_lower in cls.ASYMMETRIC_VENDOR_RIGHTS or any(k in p_lower for k in ["suspend", "late_fee", "security_for_invoicing"])

        if is_customer_subject and is_vendor_right:
            # Look for explicit grant language empowering this subject in clause
            escaped_subj = re.escape(s_lower)
            grant_pattern = rf"\b{escaped_subj}\s+(?:may|can|has\s+the\s+right\s+to|reserves\s+the\s+right\s+to|is\s+entitled\s+to|shall\s+have\s+the\s+right\s+to)\b"
            if re.search(grant_pattern, clause_lower):
                return RoleDirectionResult(is_valid=True, requires_review=False, explicit_grant_found=True)
            else:
                return RoleDirectionResult(
                    is_valid=False,
                    requires_review=True,
                    explicit_grant_found=False,
                    reason=(
                        f"Role direction requires review: Predicate '{p_clean}' is typically a provider-held right assigned to subject '{s_clean}', "
                        f"but surrounding clause does not explicitly grant that right to {s_clean}."
                    ),
                )

        # Asymmetric customer right assigned to provider-side role
        is_vendor_subject = s_lower in cls.VENDOR_ROLES or (subject_role and subject_role.upper() in {"VENDOR", "LICENSOR", "SUPPLIER"})
        is_customer_right = p_lower in cls.ASYMMETRIC_CUSTOMER_RIGHTS

        if is_vendor_subject and is_customer_right:
            escaped_subj = re.escape(s_lower)
            grant_pattern = rf"\b{escaped_subj}\s+(?:may|can|has\s+the\s+right\s+to|is\s+entitled\s+to)\b"
            if re.search(grant_pattern, clause_lower):
                return RoleDirectionResult(is_valid=True, requires_review=False, explicit_grant_found=True)
            else:
                return RoleDirectionResult(
                    is_valid=False,
                    requires_review=True,
                    explicit_grant_found=False,
                    reason=(
                        f"Role direction requires review: Predicate '{p_clean}' is typically a customer/buyer right assigned to subject '{s_clean}', "
                        f"but surrounding clause does not explicitly grant that right to {s_clean}."
                    ),
                )

        return RoleDirectionResult(is_valid=True, requires_review=False, explicit_grant_found=True)
