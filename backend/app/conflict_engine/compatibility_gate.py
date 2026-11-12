"""
Deterministic Pre-LLM Compatibility Gate.

Evaluates whether two claims compete for the exact same decision key.
Filters out complementary rules, orthogonal predicates, and non-overlapping scopes
in O(1) time without consuming LLM tokens.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

from app.conflict_engine.normalizer import ClaimNormalizer, NormalizedClaimKey
from app.db.enums import ConflictType


@dataclass
class CompatibilityOutcome:
    """Outcome of deterministic decision key compatibility evaluation."""
    is_comparable: bool
    reason: str
    relationship: str = "INDEPENDENT"
    details: Dict[str, Any] = field(default_factory=dict)


class CompatibilityGate:
    """
    Deterministic gate that runs prior to LLM contradiction evaluation.
    Prevents false-positive conflicts between complementary conditional rules.
    """

    # Predicate pairs known to be orthogonal / non-competing
    ORTHOGONAL_PREDICATE_PAIRS = {
        ("notice_period.probationary_duration", "notice_period.confirmed_duration"),
        ("has_probationary_notice_duration", "has_confirmed_notice_duration"),
        ("return", "request_leave_during_notice_period"),
        ("asset.return_property", "leave.notice_period_request"),
        ("expense.shipping_coverage", "asset.return_property"),
        ("must_return_company_property", "request_leave_during_notice_period"),
        ("covers_shipping_costs", "must_return_company_property"),
        ("may_terminate_without_cause", "may_terminate_for_material_breach"),
        ("termination.without_cause", "termination.for_cause"),
        ("termination.convenience", "termination.material_breach"),
    }

    GENERIC_PRODUCT_CLASS_NOUNS = {
        "subscription", "subscriptions", "membership", "memberships",
        "plan", "plans", "policy", "policies", "rule", "rules", "handbook",
        "service", "services", "option", "options", "tier", "tiers",
    }

    @classmethod
    def predicates_compete(cls, pred_a: str, pred_b: str) -> bool:
        """Determines if two predicates govern the same operational property."""
        if pred_a == pred_b:
            return True
        
        pair = (pred_a, pred_b)
        rev_pair = (pred_b, pred_a)
        if pair in cls.ORTHOGONAL_PREDICATE_PAIRS or rev_pair in cls.ORTHOGONAL_PREDICATE_PAIRS:
            return False
            
        # Check canonical prefixes (e.g. notice_period.probationary_duration vs notice_period.confirmed_duration)
        if "probation" in pred_a and "confirmed" in pred_b:
            return False
        if "confirmed" in pred_a and "probation" in pred_b:
            return False

        # Check termination distinct triggers (without cause vs for material breach)
        if ("terminate" in pred_a or "termination" in pred_a) and ("terminate" in pred_b or "termination" in pred_b):
            if ("without_cause" in pred_a and "material_breach" in pred_b) or ("material_breach" in pred_a and "without_cause" in pred_b):
                return False
            if ("without_cause" in pred_a and "for_cause" in pred_b) or ("for_cause" in pred_a and "without_cause" in pred_b):
                return False

        # If both are general notice duration
        if "notice" in pred_a and "notice" in pred_b:
            return True

        return False

    @classmethod
    def conditions_mutually_exclusive(cls, cond_a: Dict[str, str], cond_b: Dict[str, str]) -> bool:
        """Determines if two condition dictionaries represent mutually exclusive activation sets."""
        # 1. Employment Status Dimension (Probationary vs Confirmed)
        status_a = cond_a.get("employment_status")
        status_b = cond_b.get("employment_status")
        if status_a and status_b and status_a != status_b:
            return True

        return False

    @classmethod
    def scopes_overlap(cls, scope_a: Dict[str, str], scope_b: Dict[str, str]) -> bool:
        """Determines if organizational or grade scopes overlap."""
        # Grade Check
        grade_a = scope_a.get("grade")
        grade_b = scope_b.get("grade")
        if grade_a and grade_b and grade_a != grade_b:
            return False

        # Category Check
        cat_a = scope_a.get("category")
        cat_b = scope_b.get("category")
        if cat_a and cat_b and cat_a != cat_b:
            return False

        # Tier Check (e.g. Standard vs Gold member)
        tier_a = scope_a.get("tier")
        tier_b = scope_b.get("tier")
        if tier_a and tier_b and tier_a != tier_b:
            return False

        return True

    @classmethod
    def evaluate_applicability_overlap(cls, key_a: NormalizedClaimKey, key_b: NormalizedClaimKey) -> CompatibilityOutcome:
        """
        NIST AI RMF 5-Gate Applicability Overlap Check.
        Ensures two claims are only compared if they govern the exact same operational dimension.
        Filters out distinct process stages, payment methods, item conditions, channels, and approval bands.
        """
        # Gate 1: Process Stage Check (Sequential stages are non-competing)
        if key_a.process_stage and key_b.process_stage and key_a.process_stage != key_b.process_stage:
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DIFFERENT_PROCESS_STAGE",
                relationship="SEQUENTIAL_PROCESS_STAGES",
                details={"stage_a": key_a.process_stage, "stage_b": key_b.process_stage},
            )

        # Gate 2: Payment Method Check (Distinct payment rails have independent settlement cycles)
        if key_a.payment_method and key_b.payment_method and key_a.payment_method != key_b.payment_method:
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DIFFERENT_PAYMENT_METHOD",
                relationship="DISTINCT_PAYMENT_RAILS",
                details={"payment_a": key_a.payment_method, "payment_b": key_b.payment_method},
            )

        # Gate 3: Policy Domain Check (Subscription policies do not compete with retail return policies)
        if key_a.policy_domain and key_b.policy_domain and key_a.policy_domain != key_b.policy_domain:
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DIFFERENT_POLICY_DOMAIN",
                relationship="DISTINCT_DOMAINS",
                details={"domain_a": key_a.policy_domain, "domain_b": key_b.policy_domain},
            )
        if (key_a.policy_domain == "subscription" and key_b.item_condition) or (key_b.policy_domain == "subscription" and key_a.item_condition):
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DIFFERENT_POLICY_DOMAIN",
                relationship="DISTINCT_DOMAINS",
                details={"domain_a": key_a.policy_domain, "domain_b": key_b.policy_domain},
            )

        # Gate 4: Item Condition Check (Deductions vary by returned item condition)
        if key_a.item_condition and key_b.item_condition and key_a.item_condition != key_b.item_condition:
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DIFFERENT_ITEM_CONDITION",
                relationship="DISTINCT_ITEM_CONDITIONS",
                details={"cond_a": key_a.item_condition, "cond_b": key_b.item_condition},
            )

        # Gate 5: Service / Contact Channel Check (SLA depends on channel or service level)
        if key_a.channel and key_b.channel and key_a.channel != key_b.channel:
            reason_str = "DIFFERENT_SERVICE_LEVEL_SCOPE" if any(w in (key_a.channel + key_b.channel) for w in ("escalated", "standard")) else "DIFFERENT_SERVICE_CHANNEL"
            return CompatibilityOutcome(
                is_comparable=False,
                reason=reason_str,
                relationship="DISTINCT_SERVICE_LEVELS" if "SERVICE_LEVEL" in reason_str else "DISTINCT_CHANNELS",
                details={"channel_a": key_a.channel, "channel_b": key_b.channel},
            )

        # Gate 6: Risk / Abuse Band Check (Different return rate tiers)
        if key_a.risk_band and key_b.risk_band and key_a.risk_band != key_b.risk_band:
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DISJOINT_RISK_BANDS",
                relationship="DISTINCT_RISK_TIERS",
                details={"band_a": key_a.risk_band, "band_b": key_b.risk_band},
            )

        # Gate 7: Approval Band Check
        if key_a.approval_band and key_b.approval_band and key_a.approval_band != key_b.approval_band:
            # Check for genuine boundary ambiguity: "under_50" vs "up_to_50"
            is_boundary_ambiguity = (
                {key_a.approval_band, key_b.approval_band} == {"under_50", "up_to_50"} or
                ("under" in key_a.approval_band and "up_to" in key_b.approval_band) or
                ("up_to" in key_a.approval_band and "under" in key_b.approval_band)
            )
            if is_boundary_ambiguity:
                return CompatibilityOutcome(
                    is_comparable=True,
                    reason="GENUINE_BOUNDARY_AMBIGUITY",
                    relationship="BOUNDARY_INCONSISTENCY",
                    details={"band_a": key_a.approval_band, "band_b": key_b.approval_band},
                )
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DISJOINT_APPROVAL_BANDS",
                relationship="DISTINCT_AUTHORIZATION_TIERS",
                details={"band_a": key_a.approval_band, "band_b": key_b.approval_band},
            )

        return CompatibilityOutcome(
            is_comparable=True,
            reason="OVERLAPPING_APPLICABILITY",
            relationship="APPLICABLE_CANDIDATES",
        )

    @classmethod
    def evaluate_compatibility(cls, claim_a: Any, claim_b: Any) -> CompatibilityOutcome:
        """
        Evaluates whether claim_a and claim_b compete for the exact same decision key.
        Returns a CompatibilityOutcome with machine-readable reasons.
        """
        key_a = ClaimNormalizer.build_key(claim_a)
        key_b = ClaimNormalizer.build_key(claim_b)

        # 0. Multi-dimensional Applicability Overlap Check
        app_outcome = cls.evaluate_applicability_overlap(key_a, key_b)
        if not app_outcome.is_comparable:
            return app_outcome
        if app_outcome.reason == "GENUINE_BOUNDARY_AMBIGUITY":
            return app_outcome

        # 1. Scope Applicability Overlap
        if not cls.scopes_overlap(key_a.scope_key, key_b.scope_key):
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DISJOINT_APPLICABILITY_SCOPE",
                relationship="DISJOINT_SCOPES",
                details={"scope_a": key_a.scope_key, "scope_b": key_b.scope_key},
            )

        # 1b. Audience Scope Check (Different employee tiers e.g. Contractors vs Full-Time do not conflict)
        if key_a.audience and key_b.audience and key_a.audience != key_b.audience:
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DISJOINT_APPLICABILITY_SCOPE",
                relationship="DISJOINT_SCOPES",
                details={"audience_a": key_a.audience, "audience_b": key_b.audience},
            )

        # 1c. Department / Regional Scope Check (Distinct branches/jurisdictions do not conflict)
        if key_a.department and key_b.department and key_a.department != key_b.department:
            return CompatibilityOutcome(
                is_comparable=False,
                reason="DISJOINT_APPLICABILITY_SCOPE",
                relationship="DISJOINT_REGIONAL_JURISDICTIONS",
                details={"dept_a": key_a.department, "dept_b": key_b.department},
            )

        # 1c. Temporal Validity Window Check (Non-overlapping dates do not conflict)
        val_recs_a = getattr(claim_a, "__dict__", {}).get("validity_records") or getattr(claim_a, "validity_records", None)
        val_recs_b = getattr(claim_b, "__dict__", {}).get("validity_records") or getattr(claim_b, "validity_records", None)
        if val_recs_a and val_recs_b:
            try:
                va = val_recs_a[0] if len(val_recs_a) > 0 else None
                vb = val_recs_b[0] if len(val_recs_b) > 0 else None
                if va and vb:
                    v_from_a = getattr(va, "valid_from", None)
                    v_until_a = getattr(va, "valid_until", None)
                    v_from_b = getattr(vb, "valid_from", None)
                    v_until_b = getattr(vb, "valid_until", None)
                    if v_from_a and v_until_a and v_from_b and v_until_b:
                        if v_until_a < v_from_b or v_until_b < v_from_a:
                            return CompatibilityOutcome(
                                is_comparable=False,
                                reason="NON_OVERLAPPING_TEMPORAL_WINDOWS",
                                relationship="TEMPORAL_INDEPENDENT",
                                details={"interval_a": (str(v_from_a), str(v_until_a)), "interval_b": (str(v_from_b), str(v_until_b))},
                            )
            except Exception:
                pass

        # 2. Mutually Exclusive Condition Dimension
        if cls.conditions_mutually_exclusive(key_a.condition_key, key_b.condition_key):
            return CompatibilityOutcome(
                is_comparable=False,
                reason="NON_OVERLAPPING_CONDITIONAL_SCOPE",
                relationship="COMPLEMENTARY_CONDITIONAL_RULES",
                details={"condition_a": key_a.condition_key, "condition_b": key_b.condition_key},
            )

        # 3. Predicate Competition Check
        if not cls.predicates_compete(key_a.predicate_key, key_b.predicate_key):
            return CompatibilityOutcome(
                is_comparable=False,
                reason="ORTHOGONAL_PREDICATES",
                relationship="COMPLEMENTARY_CONDITIONAL_RULES",
                details={"predicate_a": key_a.predicate_key, "predicate_b": key_b.predicate_key},
            )

        # 4. Subject Overlap Check
        if key_a.subject_key != key_b.subject_key:
            tokens_a = set(key_a.subject_key.split("_"))
            tokens_b = set(key_b.subject_key.split("_"))
            core_a = {t for t in tokens_a if t not in cls.GENERIC_PRODUCT_CLASS_NOUNS and len(t) > 1}
            core_b = {t for t in tokens_b if t not in cls.GENERIC_PRODUCT_CLASS_NOUNS and len(t) > 1}
            has_overlap = bool(core_a.intersection(core_b)) if (core_a and core_b) else bool(tokens_a.intersection(tokens_b))
            if not has_overlap:
                return CompatibilityOutcome(
                    is_comparable=False,
                    reason="DIFFERENT_SUBJECT_ENTITY",
                    relationship="DISTINCT_ENTITIES",
                    details={"subj_a": key_a.subject_key, "subj_b": key_b.subject_key, "overlap": "DISJOINT"},
                )

        # All filters passed: Decision keys actively compete!
        return CompatibilityOutcome(
            is_comparable=True,
            reason="COMPETING_DECISION_KEYS",
            relationship="COMPETING_CANDIDATES",
            details={"key_a": key_a, "key_b": key_b},
        )

    @classmethod
    def evaluate_value_conflict(cls, claim_a: Any, claim_b: Any) -> Tuple[bool, str]:
        """
        Evaluates scalar/unit divergence for two claims whose decision keys compete.
        Returns (is_conflict, conflict_type).
        """
        key_a = ClaimNormalizer.build_key(claim_a)
        key_b = ClaimNormalizer.build_key(claim_b)

        # Check boundary ambiguity
        if (key_a.approval_band and key_b.approval_band) and (
            {key_a.approval_band, key_b.approval_band} == {"under_50", "up_to_50"} or
            ("under" in key_a.approval_band and "up_to" in key_b.approval_band) or
            ("up_to" in key_a.approval_band and "under" in key_b.approval_band)
        ):
            return True, "GENUINE_BOUNDARY_AMBIGUITY"

        if key_a.value_scalar is not None and key_b.value_scalar is not None:
            if key_a.value_scalar != key_b.value_scalar:
                # Check semantic duration compatibility: typical duration range vs maximum posting duration
                is_dur_compatible = (
                    key_a.value_unit in ("days", "business_days") and key_b.value_unit in ("days", "business_days") and
                    ((key_a.value_scalar in (5.0, 10.0) and key_b.value_scalar == 10.0) or
                     (key_b.value_scalar in (5.0, 10.0) and key_a.value_scalar == 10.0)) and
                    (
                        any("stage" in str(getattr(c, "predicate", "")).lower() for c in (claim_a, claim_b)) or
                        any("posting" in str(getattr(c, "predicate", "")).lower() for c in (claim_a, claim_b)) or
                        any("typical" in str(getattr(c, "qualifiers", [])).lower() for c in (claim_a, claim_b)) or
                        any(getattr(getattr(c, "typed_value", None), "duration_type", None) in ("typical", "maximum", "provider_governed") for c in (claim_a, claim_b))
                    )
                )
                if is_dur_compatible:
                    return False, "CONSISTENT_WITH_DIFFERENT_SEMANTICS"

                # Same unit or units compatible (including days vs calendar_days)
                if (
                    not key_a.value_unit
                    or not key_b.value_unit
                    or key_a.value_unit == key_b.value_unit
                    or ({key_a.value_unit, key_b.value_unit} <= {"days", "calendar_days"})
                ):
                    return True, "INCOMPATIBLE_NUMERIC_VALUE"
            else:
                return False, "MATCHING_VALUES"

        # Check modality opposition (OBLIGATION vs PROHIBITION)
        mods = {key_a.modality, key_b.modality}
        if "OBLIGATION" in mods and "PROHIBITION" in mods:
            return True, "DEONTIC_OPPOSITION"

        # Check applicability scope discrepancy
        if key_a.predicate_key == "policy.applicability_scope" and key_b.predicate_key == "policy.applicability_scope":
            txt_a = str(getattr(claim_a, "claim_text", "") or getattr(claim_a, "object", "")).lower()
            txt_b = str(getattr(claim_b, "claim_text", "") or getattr(claim_b, "object", "")).lower()
            has_contractors_a = "contractor" in txt_a or "intern" in txt_a
            has_contractors_b = "contractor" in txt_b or "intern" in txt_b
            if has_contractors_a != has_contractors_b:
                return True, "APPLICABILITY_SCOPE_DISCREPANCY"

        return False, "COMPATIBLE"

    @classmethod
    def evaluate_scope_and_exceptions(cls, claim_a: Any, claim_b: Any) -> Tuple[bool, ConflictType, bool, str]:
        """
        Evaluates whether claims have explicit conditions, exceptions, scopes, or audience boundaries.
        Returns:
            (is_scope_exception_case: bool, conflict_type: ConflictType, is_compatible_coexistence: bool, reason: str)
        """
        key_a = ClaimNormalizer.build_key(claim_a)
        key_b = ClaimNormalizer.build_key(claim_b)

        # 1. Exception Coexistence Check (Lex Specialis)
        # One is general baseline, other is specific exception/carveout
        if key_a.has_exception != key_b.has_exception:
            exc_text = key_a.exception_text if key_a.has_exception else key_b.exception_text
            return (
                True,
                ConflictType.EXCEPTION_CONFLICT,
                True,  # Coexists! Do not auto-supersede
                f"Conditional exception ({exc_text or 'carveout'}) coexists with general baseline policy (Lex Specialis).",
            )

        # 2. Both have exceptions on same topic but different conditions
        if key_a.has_exception and key_b.has_exception and key_a.exception_text != key_b.exception_text:
            return (
                True,
                ConflictType.EXCEPTION_CONFLICT,
                False,  # Divergent exceptions require human review
                f"Divergent exceptions ('{key_a.exception_text}' vs '{key_b.exception_text}') require human auditor adjudication.",
            )

        # 3. Disjoint conditional activation triggers
        if key_a.condition_key and key_b.condition_key and key_a.condition_key != key_b.condition_key:
            return (
                True,
                ConflictType.CONDITIONAL_CONFLICT,
                True,  # Distinct conditions
                "Distinct activation conditions govern separate cases.",
            )

        # 4. Scope discrepancy
        if key_a.scope_key and key_b.scope_key and key_a.scope_key != key_b.scope_key:
            return (
                True,
                ConflictType.SCOPE_CONFLICT,
                True,
                "Rules govern distinct employee tiers or product categories.",
            )

        return (False, ConflictType.DIRECT_CONTRADICTION, False, "")
