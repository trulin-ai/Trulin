"""
Phase 3: Universal Type-Compatibility Matrix.

Enforces strict, document-agnostic semantic typing between entities, predicates, and objects.
Prevents structurally valid but semantically impossible claims:
- Customer cannot offer store credit bonuses (Customer receives, Merchant provides).
- Price adjustment windows cannot be labeled as return windows.
- Bank posting duration cannot be labeled as return windows.
- Subscription pause privileges cannot be labeled as refund rules.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple


class EntityType(str, Enum):
    ACTOR_CUSTOMER = "customer"
    ACTOR_PROVIDER = "provider"
    ACTOR_AGENT = "agent"
    PAYMENT_METHOD = "payment_method"
    SUBSCRIPTION = "subscription"
    POLICY_WINDOW = "policy_window"
    POSTING_DURATION = "posting_duration"
    PRODUCT = "product"
    DOCUMENT = "document"
    UNKNOWN = "unknown"


@dataclass
class TypeCompatibilityResult:
    is_compatible: bool
    requires_review: bool
    blocked_rule: Optional[str] = None
    reason: Optional[str] = None
    subject_category: EntityType = EntityType.UNKNOWN
    predicate_family: str = "generic"


class TypeCompatibilityMatrix:
    """Universal semantic matrix enforcing subject-action-object compatibility."""

    # Explicitly blocked anti-patterns
    BLOCKED_COMBINATIONS = [
        # 1. Customer offering merchant benefits
        {
            "subject_pattern": r"\b(customers?|clients?|buyers?|subscribers?|users?)\b",
            "predicate_pattern": r"\b(offers?_store_credit_bonus|grants?_store_credit_bonus|provides?_store_credit_bonus|issues?_bonus)\b",
            "rule_id": "BLOCK-ACTOR-001",
            "reason": "Actor inversion: Customer cannot offer or issue store credit bonuses; customers receive store credit incentives from the provider.",
        },
        # 2. Price adjustment conflated with return window
        {
            "subject_pattern": r"\b(price\s+adjustments?|price\s+match(?:ing)?|price\s+drops?)\b",
            "predicate_pattern": r"\b(has_return_window|specifies_return_window|requires_return_window)\b",
            "rule_id": "BLOCK-TEMPORAL-001",
            "reason": "Temporal conflation: Price adjustments govern refund of price differences, not physical item return windows.",
        },
        # 3. Bank posting duration conflated with return window
        {
            "subject_pattern": r"\b(posting|posted\s+by\s+bank|bank\s+posting|credit\s+card\s+refund|debit\s+card\s+refund|paypal\s+refund|wire\s+transfer)\b",
            "predicate_pattern": r"\b(has_return_window|specifies_return_window|requires_return_window)\b",
            "rule_id": "BLOCK-TEMPORAL-002",
            "reason": "Temporal conflation: Bank or payment gateway posting timelines cannot be classified as customer product return windows.",
        },
        # 4. Subscription pause conflated with refund rule
        {
            "subject_pattern": r"\b(subscriptions?|pause|pausing|trailhead\s+box)\b",
            "predicate_pattern": r"\b(has_refund_rule|specifies_refund_rule)\b",
            "object_pattern": r"\b(pause|pausing|months?\s+pause|hold)\b",
            "rule_id": "BLOCK-CONCEPT-001",
            "reason": "Concept cross-wiring: Subscription pause is an account service privilege, not a monetary refund rule.",
        },
        # 5. Non-refundable item unconditional prohibition without exceptions
        {
            "subject_pattern": r"\b(non-refundable|final\s+sale|clearance)\b",
            "predicate_pattern": r"\b(cannot_be_refunded|prohibited_from_refund)\b",
            "object_pattern": r"\b(under\s+any\s+circumstances|unconditionally|absolute)\b",
            "rule_id": "BLOCK-EXCEPTION-001",
            "reason": "Exception dropped: Non-refundable declarations cannot be absolute when parent clauses provide statutory/defect exceptions.",
        },
    ]

    @classmethod
    def classify_subject(cls, subject: str) -> EntityType:
        s_lower = (subject or "").lower().strip()
        if any(w in s_lower for w in ("customer", "buyer", "client", "subscriber", "consumer", "employee", "recipient")):
            return EntityType.ACTOR_CUSTOMER
        if any(w in s_lower for w in ("northwind", "provider", "vendor", "merchant", "company", "we", "us", "seller")):
            return EntityType.ACTOR_PROVIDER
        if any(w in s_lower for w in ("agent", "support agent", "manager", "director", "approver")):
            return EntityType.ACTOR_AGENT
        if any(w in s_lower for w in ("apple pay", "google pay", "card", "paypal", "visa", "mastercard", "klarna", "payment method")):
            return EntityType.PAYMENT_METHOD
        if any(w in s_lower for w in ("subscription", "trailhead box", "rewards plus", "care plan")):
            return EntityType.SUBSCRIPTION
        if any(w in s_lower for w in ("posting", "posted by bank", "processing timeline")):
            return EntityType.POSTING_DURATION
        if any(w in s_lower for w in ("return window", "reporting window", "trial window", "price adjustment")):
            return EntityType.POLICY_WINDOW
        return EntityType.UNKNOWN

    @classmethod
    def evaluate_compatibility(
        cls,
        subject: str,
        predicate: str,
        object_text: str = "",
        clause_text: str = "",
    ) -> TypeCompatibilityResult:
        s_clean = (subject or "").strip()
        p_clean = (predicate or "").strip()
        o_clean = (object_text or "").strip()
        c_clean = (clause_text or "").strip()

        # 1. Check explicitly blocked anti-patterns
        for blocked in cls.BLOCKED_COMBINATIONS:
            s_match = bool(re.search(blocked["subject_pattern"], s_clean, re.IGNORECASE))
            p_match = bool(re.search(blocked["predicate_pattern"], p_clean, re.IGNORECASE))
            o_match = True
            if "object_pattern" in blocked:
                o_match = bool(re.search(blocked["object_pattern"], o_clean, re.IGNORECASE) or re.search(blocked["object_pattern"], c_clean, re.IGNORECASE))

            if s_match and p_match and o_match:
                return TypeCompatibilityResult(
                    is_compatible=False,
                    requires_review=True,
                    blocked_rule=blocked["rule_id"],
                    reason=blocked["reason"],
                    subject_category=cls.classify_subject(s_clean),
                    predicate_family=p_clean,
                )

        # 2. Check Allowed Predicate Family by Subject Category
        subj_type = cls.classify_subject(s_clean)
        p_lower = p_clean.lower()

        # Customer: receives / requests / must_provide
        if subj_type == EntityType.ACTOR_CUSTOMER:
            if p_lower.startswith(("offers_", "grants_", "issues_refund", "authorizes_refund")):
                return TypeCompatibilityResult(
                    is_compatible=False,
                    requires_review=True,
                    blocked_rule="BLOCK-CUSTOMER-ROLE",
                    reason=f"Customer cannot perform provider action '{p_clean}'. Customers receive, request, or comply.",
                    subject_category=subj_type,
                    predicate_family=p_clean,
                )

        # Payment Method: specifies / references
        if subj_type == EntityType.PAYMENT_METHOD:
            if any(w in p_lower for w in ("must_comply", "agrees_to", "is_responsible_for")):
                return TypeCompatibilityResult(
                    is_compatible=False,
                    requires_review=True,
                    blocked_rule="BLOCK-INSTRUMENT-ROLE",
                    reason=f"Payment instrument cannot bear behavioral legal obligations '{p_clean}'.",
                    subject_category=subj_type,
                    predicate_family=p_clean,
                )

        return TypeCompatibilityResult(
            is_compatible=True,
            requires_review=False,
            subject_category=subj_type,
            predicate_family=p_clean,
        )

