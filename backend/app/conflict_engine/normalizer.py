"""
Claim Decision Key Normalizer.

Transforms raw text, subjects, predicates, objects, and conditions
into a normalized canonical decision key for deterministic conflict evaluation.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, Optional, Tuple


@dataclass(frozen=True)
class NormalizedClaimKey:
    """Canonical, normalized comparison key for an enterprise claim."""
    subject_key: str
    predicate_key: str
    scope_key: Dict[str, str] = field(default_factory=dict)
    condition_key: Dict[str, str] = field(default_factory=dict)
    value_scalar: Optional[float] = None
    value_unit: Optional[str] = None
    modality: str = "POLICY_FACT"
    temporal_window: Tuple[Optional[datetime], Optional[datetime]] = (None, None)
    process_stage: Optional[str] = None
    payment_method: Optional[str] = None
    item_condition: Optional[str] = None
    approval_band: Optional[str] = None
    risk_band: Optional[str] = None
    channel: Optional[str] = None
    policy_domain: Optional[str] = None
    has_exception: bool = False
    exception_text: Optional[str] = None
    audience: Optional[str] = None
    department: Optional[str] = None


class ClaimNormalizer:
    """Normalizes claims into structured decision keys."""

    STOPWORDS = {
        "the", "a", "an", "and", "or", "of", "in", "at", "per", "upon", "under", "for",
        "employees", "employee", "wingify", "staff"
    }

    # Predicate canonicalization mapping
    PREDICATE_CANONICAL_MAP = {
        "has_probationary_notice_duration": "notice_period.probationary_duration",
        "has_confirmed_notice_duration": "notice_period.confirmed_duration",
        "has_notice_duration": "notice_period.duration",
        "request_leave_during_notice_period": "leave.notice_period_request",
        "return": "asset.return_property",
        "cover": "expense.shipping_coverage",
        "deducted_per_asset_management_policy": "deduction.asset_retention",
        "adjusted_from_full_and_final_salary": "deduction.loan_advance",
        "recovered_upon_early_exit": "deduction.wfh_allowance",
        "holds_right_to_recover_short_notice": "discretionary.short_notice_recovery",
        "may_recover_short_notice_amount": "discretionary.short_notice_recovery",
        "must_return_company_property": "asset.return_property",
        "covers_shipping_costs": "expense.shipping_coverage",
        "issues_pay_in_lieu_of_notice": "severance.pay_in_lieu",
        "prohibits_pay_in_lieu_of_notice": "severance.pay_in_lieu_prohibition",
        "applies_to_employment_types": "policy.applicability_scope",
        "governs_employment_categories": "policy.applicability_scope",
        "requires_offboarding_handover_tasks": "offboarding.handover_tasks",
        "prohibited_in_any_media": "confidentiality.public_disclosure",
        "prohibited_except_internal_confidential_use": "confidentiality.reproduction",
    }

    @classmethod
    def normalize_entity_tokens(cls, text: str) -> str:
        """Strips punctuation and noise words to create a stable entity key."""
        if not text or not isinstance(text, str):
            return ""
        clean = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
        tokens = [t for t in clean.split() if t not in cls.STOPWORDS and len(t) >= 2]
        return "_".join(tokens)

    @classmethod
    def extract_scalar_and_unit(cls, object_text: str, claim_text: str) -> Tuple[Optional[float], Optional[str]]:
        """Extracts numerical scalar and normalized measurement unit, masking statutory citations."""
        search_corpus = f"{object_text} {claim_text}".lower()

        # Mask statutory citations, standard identifiers, and years to prevent false numeric conflicts
        masked_corpus = re.sub(r"\btitle\s+\d+\b", " ", search_corpus)
        masked_corpus = re.sub(r"\b(?:nist\s+)?sp\s+\d+(?:-\d+[a-z]?)?\b", " ", masked_corpus)
        masked_corpus = re.sub(r"\bfips\s+\d+(?:-\d+)?\b", " ", masked_corpus)
        masked_corpus = re.sub(r"\bpart\s+\d+(?:\.\d+)?\b", " ", masked_corpus)
        masked_corpus = re.sub(r"\bsection\s+\d+(?:\.\d+)?\b", " ", masked_corpus)
        masked_corpus = re.sub(r"\b(?:security\s+)?level\s+[1234]\b", " ", masked_corpus)
        masked_corpus = re.sub(r"\baal[123]\b", " ", masked_corpus)
        masked_corpus = re.sub(r"\b(?:19|20)\d\d\b", " ", masked_corpus)  # Years like 2010

        # Match numbers with explicit units or currency
        currency_match = re.search(r"\$\s*(\d+(?:\.\d+)?)", masked_corpus)
        if currency_match:
            try:
                return float(currency_match.group(1)), "USD"
            except ValueError:
                pass

        unit_match = re.search(r"\b(\d+(?:\.\d+)?)\s*(calendar\s+days?|calendar_days?|business\s+days?|business_days?|days?|months?|years?|hours?|weeks?|%|percent)\b", masked_corpus)
        if unit_match:
            try:
                num = float(unit_match.group(1))
            except ValueError:
                num = None
            raw_unit = unit_match.group(2).lower().strip()
            if "business" in raw_unit:
                unit = "business_days"
            elif "calendar" in raw_unit:
                unit = "calendar_days"
            elif raw_unit in ("day", "days"):
                unit = "days"
            elif raw_unit in ("month", "months"):
                unit = "months"
            elif raw_unit in ("year", "years"):
                unit = "years"
            elif raw_unit in ("hour", "hours"):
                unit = "hours"
            elif raw_unit in ("week", "weeks"):
                unit = "weeks"
            elif raw_unit in ("%", "percent"):
                unit = "%"
            else:
                unit = raw_unit
            return num, unit

        return None, None

    @classmethod
    def normalize_conditions(cls, conditions: list[str], claim_text: str) -> Dict[str, str]:
        """Normalizes free-text conditions into canonical dimension key-value pairs."""
        cond_dict: Dict[str, str] = {}
        combined_text = ((" ".join(conditions) + " " + claim_text)).lower()

        # 1. Employment Status Dimension
        probation_keywords = ("probation", "probationary", "during probation", "probationers")
        confirmed_keywords = ("confirmed", "upon confirmation", "post-confirmation", "confirmed employees")

        is_prob = any(k in combined_text for k in probation_keywords)
        is_conf = any(k in combined_text for k in confirmed_keywords)

        if is_prob and not is_conf:
            cond_dict["employment_status"] = "probationary"
        elif is_conf and not is_prob:
            cond_dict["employment_status"] = "confirmed"

        # 2. Separation Condition
        if "offboarding" in combined_text or "separation" in combined_text or "exit" in combined_text:
            cond_dict["lifecycle_phase"] = "offboarding"

        # 3. Manager Approval Requirement
        if "prior written approval" in combined_text or "manager approval" in combined_text:
            cond_dict["approval_required"] = "manager_written"

        return cond_dict

    @classmethod
    def normalize_scope(cls, subject_text: str, claim_text: str) -> Dict[str, str]:
        """Extracts grade, tier, or role scope dimensions."""
        scope_dict: Dict[str, str] = {}
        combined = f"{subject_text} {claim_text}".lower()

        # Match Grade (e.g. Grade A, Grade B, Grade C, Grade D, Grade E)
        grade_match = re.search(r"\bgrade\s+([a-e])\b", combined)
        if grade_match:
            scope_dict["grade"] = grade_match.group(1).upper()

        # Match Role Category
        if "cxo" in combined:
            scope_dict["category"] = "cxo"
        elif "senior management" in combined:
            scope_dict["category"] = "senior_management"
        elif "middle management" in combined:
            scope_dict["category"] = "middle_management"
        elif "junior management" in combined:
            scope_dict["category"] = "junior_management"
        elif "fellow" in combined:
            scope_dict["category"] = "fellow"

        # Match Tier (e.g. Standard, Gold, Silver, Bronze, VIP)
        tier_match = re.search(r"\b(gold|silver|bronze|platinum|standard|vip)\b", combined)
        if tier_match:
            scope_dict["tier"] = tier_match.group(1).lower()

        return scope_dict

    @classmethod
    def normalize_process_stage(cls, text: str) -> Optional[str]:
        t = text.lower()
        if any(k in t for k in ("rma review", "rma request", "rma issuance", "issuance of rma")):
            return "rma_issuance"
        elif any(k in t for k in ("transit", "return transit", "shipping return", "in transit")):
            return "return_transit"
        elif any(k in t for k in ("warehouse inspection", "receipt and inspection", "receipt/inspection", "inspect", "within 1 business day of inspection", "approved and issued")):
            return "inspection_approval_issuance"
        elif any(k in t for k in ("resolution option", "resolution timeline", "full refund timeline", "full refund")):
            return "resolution_option_timeline"
        elif any(k in t for k in ("refund issuance", "issuance of refund", "issuing refund")):
            return "refund_issuance"
        elif any(k in t for k in ("evidence submission", "submitting evidence")):
            return "evidence_submission"
        elif any(k in t for k in ("issuer decision", "bank decision")):
            return "issuer_decision"
        elif "bank transfer" in t or "stage: debit card" in t:
            return "bank_transfer_processing"
        elif any(k in t for k in ("posting", "post by bank", "posted by bank", "days to post")):
            return "bank_posting_duration"
        return None

    @classmethod
    def normalize_payment_method(cls, text: str) -> Optional[str]:
        t = text.lower()
        if any(k in t for k in ("credit card", "visa", "mastercard", "amex", "credit_card")):
            return "credit_card"
        elif "debit card" in t or "debit_card" in t:
            return "debit_card"
        elif "paypal" in t:
            return "paypal"
        elif "store credit" in t:
            return "store_credit"
        elif any(k in t for k in ("check", "cheque")):
            return "check"
        elif "cash" in t:
            return "cash"
        elif any(k in t for k in ("bnpl", "buy now pay later", "klarna", "afterpay")):
            return "bnpl"
        elif "gift card" in t:
            return "gift_card"
        elif "split payment" in t or "split" in t:
            return "split_payment"
        return None

    @classmethod
    def normalize_item_condition(cls, text: str) -> Optional[str]:
        t = text.lower()
        if "unopened" in t or "factory sealed" in t:
            return "unopened"
        elif "opened" in t and ("intact" in t or "packaging intact" in t):
            return "opened_intact"
        elif "light wear" in t or "signs of use" in t:
            return "light_wear"
        elif "heavy use" in t or "significant wear" in t or "heavily used" in t:
            return "heavy_use"
        elif "missing original box" in t or "missing box" in t:
            return "missing_box"
        elif "damaged by customer" in t or "customer damaged" in t:
            return "customer_damaged"
        elif "defective" in t:
            return "defective"
        return None

    @classmethod
    def normalize_approval_band(cls, text: str) -> Optional[str]:
        t = text.lower()
        if re.search(r"\bup\s+to\s+\$?50\b", t):
            return "up_to_50"
        elif re.search(r"\b(?:under|less\s+than)\s+\$?50\b", t):
            return "under_50"
        elif re.search(r"\b(?:over|more\s+than)\s+\$?50\b", t):
            return "over_50"
        elif re.search(r"\b(?:up\s+to|under|<=)\s*\$?100\b", t):
            return "up_to_100"
        elif re.search(r"(?:between\s+)?\$?100(?:\.01)?\s*(?:-|to)\s*\$?500", t):
            return "100_500"
        elif re.search(r"(?:>|\bover|\bmore\s+than|exceeding)\s*\$?2,?000\b", t):
            return "over_2000"
        elif re.search(r"(?:>|\bover|\bmore\s+than|exceeding)\s*\$?500", t):
            return "over_500"
        return None

    @classmethod
    def normalize_risk_band(cls, text: str) -> Optional[str]:
        t = text.lower()
        if re.search(r"30\s*(?:-|to)\s*40%", t):
            return "rate_30_40"
        elif re.search(r"(?:>|\bover|\bmore\s+than)\s*40%", t):
            return "rate_over_40"
        return None

    @classmethod
    def normalize_channel(cls, text: str) -> Optional[str]:
        t = text.lower()
        if "escalated" in t or "escalation" in t or "complaint" in t:
            return "escalated_complaint"
        elif "standard refund query" in t or "standard query" in t:
            return "standard_refund_query"
        elif "email" in t:
            return "email"
        elif "chat" in t:
            return "chat"
        elif "phone" in t and any(c in t for c in ("us", "canada", "north america")):
            return "phone_us_canada"
        elif "phone" in t and any(c in t for c in ("uk", "united kingdom", "europe")):
            return "phone_uk"
        elif "phone" in t:
            return "phone"
        elif "in-store" in t or "in store" in t:
            return "in_store"
        return None

    @classmethod
    def normalize_policy_domain(cls, text: str) -> Optional[str]:
        t = text.lower()
        if "subscription" in t or "trailhead box" in t or "membership" in t or "rewards plus" in t:
            return "subscription"
        elif "warranty" in t:
            return "warranty"
        return None

    @classmethod
    def build_key(cls, claim: Any) -> NormalizedClaimKey:
        """Constructs a NormalizedClaimKey from a Claim, CandidateClaim, or NormalizedClaimKey object."""
        if isinstance(claim, NormalizedClaimKey):
            return claim
        raw_subj = getattr(claim, "subject", "") or ""
        raw_pred = getattr(claim, "predicate", "") or ""
        raw_obj = getattr(claim, "object", "") or getattr(claim, "object_value", "") or ""
        raw_text = getattr(claim, "claim_text", "") or ""
        raw_conds = getattr(claim, "conditions", []) or []

        # Canonical subject key
        subj_key = cls.normalize_entity_tokens(raw_subj) or cls.normalize_entity_tokens(raw_text[:40])

        # Canonical predicate key
        pred_key = cls.PREDICATE_CANONICAL_MAP.get(raw_pred, raw_pred)

        # Conditions and Scope
        cond_dict = cls.normalize_conditions(raw_conds, raw_text)
        if getattr(claim, "condition", None):
            cond_dict["condition"] = str(getattr(claim, "condition"))

        scope_dict = cls.normalize_scope(raw_subj, raw_text)
        if getattr(claim, "grade", None):
            scope_dict["grade"] = str(getattr(claim, "grade")).upper()
        if getattr(claim, "tier", None):
            scope_dict["tier"] = str(getattr(claim, "tier")).lower()

        # Scalar and Unit
        scalar_val, unit_val = cls.extract_scalar_and_unit(raw_obj, raw_text)
        if scalar_val is None:
            raw_s = getattr(claim, "value", None) or getattr(claim, "scalar", None)
            if raw_s is not None:
                try:
                    scalar_val = float(raw_s)
                except (ValueError, TypeError):
                    pass
        if unit_val is None and getattr(claim, "unit", None):
            unit_val = str(getattr(claim, "unit"))

        # Modality
        modality = getattr(claim, "modality", "POLICY_FACT") or "POLICY_FACT"

        # Multi-dimensional Applicability Dimensions
        raw_span = getattr(claim, "evidence_text_span", "") or ""
        cond_strings = [str(c.get("field", "") if isinstance(c, dict) else c) + " " + str(c.get("value", "") if isinstance(c, dict) else "") for c in raw_conds]
        search_corpus = f"{raw_subj} {raw_pred} {raw_obj} {raw_text} {raw_span} {' '.join(cond_strings)}"
        p_stage = getattr(claim, "process_stage", None) or cls.normalize_process_stage(search_corpus)
        p_method = getattr(claim, "payment_method", None) or cls.normalize_payment_method(search_corpus)
        i_cond = getattr(claim, "item_condition", None) or cls.normalize_item_condition(search_corpus)
        a_band = getattr(claim, "approval_band", None) or cls.normalize_approval_band(search_corpus)
        r_band = getattr(claim, "risk_band", None) or cls.normalize_risk_band(search_corpus)
        chan = getattr(claim, "channel", None) or cls.normalize_channel(search_corpus)
        p_domain = getattr(claim, "policy_domain", None) or cls.normalize_policy_domain(search_corpus)

        # Explicit Exceptions & Scope/Audience extraction
        corpus_lower = search_corpus.lower()
        exception_indicators = (
            "except", "unless", "excluding", "annual plan", "annual subscription",
            "enterprise tier", "upon approval", "with prior approval", "vp approval",
            "special exception", "carveout", "custom contract", "vip", "rewards gold",
            "cooling-off", "statutory", "receipt-less"
        )
        has_exc = any(indicator in corpus_lower for indicator in exception_indicators) or bool(getattr(claim, "exceptions", None))
        exc_match = None
        for ind in exception_indicators:
            if ind in corpus_lower:
                exc_match = ind
                break

        # Audience
        audience = getattr(claim, "audience", None)
        if not audience:
            if "contractor" in corpus_lower or "contract" in corpus_lower or "intern" in corpus_lower:
                audience = "contractors_interns"
            elif "full-time" in corpus_lower or "full time" in corpus_lower or "regular employee" in corpus_lower:
                audience = "full_time"
            elif "all employee" in corpus_lower:
                audience = "all_employees"

        # Department / Organizational Scope
        dept = getattr(claim, "department", None)
        if not dept:
            for d in ("finance", "engineering", "legal", "hr", "sales", "operations", "security", "procurement"):
                if d in corpus_lower:
                    dept = d
                    break

        return NormalizedClaimKey(
            subject_key=subj_key,
            predicate_key=pred_key,
            scope_key=scope_dict,
            condition_key=cond_dict,
            value_scalar=scalar_val,
            value_unit=unit_val,
            modality=modality,
            process_stage=p_stage,
            payment_method=p_method,
            item_condition=i_cond,
            approval_band=a_band,
            risk_band=r_band,
            channel=chan,
            policy_domain=p_domain,
            has_exception=has_exc,
            exception_text=exc_match,
            audience=audience,
            department=dept,
        )
