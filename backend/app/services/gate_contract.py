"""
Universal Shared Governance Gate Contract (Phase 2.4).
Defines a shared, document-agnostic gate contract used by both ClaimGateEvaluator
and UniversalGateEvaluator:
- Evidence grounding & source-locator validity
- Predicate normativity & catch-all prevention
- Table-column binding integrity
- SPO compatibility & actor/instrument roles
- Polarity and modality consistency
- Condition, exception, and scope preservation
- Machine-readable reason codes for all failure modes (G8)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from app.extraction.predicate_registry import CanonicalPredicate, PredicateRegistry
from app.extraction.type_compatibility import EntityType, TypeCompatibilityMatrix


class GateFailureCode(str, Enum):
    """Machine-readable gate failure codes (Guardrail G8)."""
    # 1. Evidence Grounding & Locator Validity
    ERR_EVIDENCE_MISSING = "ERR_EVIDENCE_MISSING"
    ERR_EVIDENCE_FABRICATED = "ERR_EVIDENCE_FABRICATED"
    ERR_LOCATOR_INVALID = "ERR_LOCATOR_INVALID"

    # 2. Predicate Normativity & Taxonomy
    ERR_PREDICATE_CATCH_ALL = "ERR_PREDICATE_CATCH_ALL"
    ERR_PREDICATE_DEPRECATED = "ERR_PREDICATE_DEPRECATED"
    ERR_PREDICATE_INVALID = "ERR_PREDICATE_INVALID"

    # 3. Table Column Binding Integrity
    ERR_TABLE_BINDING_MISMATCH = "ERR_TABLE_BINDING_MISMATCH"

    # 4. SPO Compatibility & Semantic Typing
    ERR_SPO_INCOMPATIBLE = "ERR_SPO_INCOMPATIBLE"
    ERR_ACTOR_ROLE_INVERSION = "ERR_ACTOR_ROLE_INVERSION"
    ERR_INSTRUMENT_OBLIGATION = "ERR_INSTRUMENT_OBLIGATION"

    # 5. Polarity & Modality Consistency
    ERR_POLARITY_INVERSION = "ERR_POLARITY_INVERSION"
    ERR_MODALITY_MISMATCH = "ERR_MODALITY_MISMATCH"

    # 6. Condition, Exception & Scope Preservation
    ERR_CONDITION_LOST = "ERR_CONDITION_LOST"
    ERR_EXCEPTION_LOST = "ERR_EXCEPTION_LOST"
    ERR_SCOPE_LOST = "ERR_SCOPE_LOST"

    # 7. Value & Quantitative Fidelity (Phase 2.4b)
    ERR_VALUE_FIDELITY_MISMATCH = "ERR_VALUE_FIDELITY_MISMATCH"

    # 8. Structural Integrity, Deduplication & Status Invariants
    ERR_TEXT_INTEGRITY = "ERR_TEXT_INTEGRITY"
    ERR_NON_ATOMIC = "ERR_NON_ATOMIC"
    ERR_DUPLICATE_CLAIM = "ERR_DUPLICATE_CLAIM"
    ERR_CLAIM_TYPE_DISALLOWED = "ERR_CLAIM_TYPE_DISALLOWED"
    ERR_SUBJECT_INVALID = "ERR_SUBJECT_INVALID"
    ERR_COUNTERPARTY_UNRESOLVED = "ERR_COUNTERPARTY_UNRESOLVED"
    ERR_NO_SILENT_UPGRADE_VIOLATION = "ERR_NO_SILENT_UPGRADE_VIOLATION"


@dataclass
class SharedGateRequest:
    """Standardized input request for universal gate evaluation."""
    claim_text: str
    subject: Optional[str] = None
    predicate: Optional[str] = None
    object_val: Optional[str] = None
    evidence_quote: Optional[str] = None
    evidence_spans: Optional[List[Any]] = None
    locators: Optional[List[Dict[str, Any]]] = None
    conditions: Optional[List[str]] = None
    exceptions: Optional[List[str]] = None
    claim_type: str = "rule"
    status: str = "candidate"
    confidence: float = 0.95
    document_text: Optional[str] = None
    enclosing_clause: Optional[str] = None
    table_header: Optional[str] = None
    scope: Optional[str] = None
    target_status: Optional[str] = None
    is_upgrade_attempt: bool = False
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class SharedGateResult:
    """Standardized output result containing boolean flags, reason codes, and tier."""
    # Individual Gate Booleans
    evidence_grounding: bool = False
    source_locator_validity: bool = False
    predicate_normativity: bool = False
    table_column_binding: bool = True
    spo_compatibility: bool = False
    polarity_consistency: bool = False
    modality_consistency: bool = False
    condition_preservation: bool = True
    exception_preservation: bool = True
    scope_preservation: bool = True
    value_fidelity: bool = True

    # Structural Integrity & Invariants
    text_integrity: bool = True
    is_atomic: bool = True
    is_not_duplicate: bool = True
    claim_type_allowed: bool = True
    subject_valid: bool = True
    counterparty_resolved: bool = True
    no_silent_upgrade: bool = True

    # Aggregate Decisions
    all_gates_passed: bool = False
    certification_tier: str = "REVIEW_REQUIRED"
    rejection_reasons: List[str] = field(default_factory=list)
    reason_codes: List[str] = field(default_factory=list)
    gate_flags: Dict[str, bool] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "all_gates_passed": self.all_gates_passed,
            "certification_tier": self.certification_tier,
            "gate_flags": self.gate_flags,
            "rejection_reasons": self.rejection_reasons,
            "reason_codes": self.reason_codes,
        }


class SharedGovernanceGateEngine:
    """
    Unified gate evaluation engine powering both ClaimGateEvaluator
    and UniversalGateEvaluator.
    """

    OPERATIVE_MODAL_PATTERN = re.compile(
        r"\b("
        r"may|must|will|shall|can|cannot|should|"
        r"(?:is|are)\s+required(?:\s+to)?|approval\s+required|required|"
        r"(?:is|are)\s+accepted|accepted\s+in-store|"
        r"(?:is|are)\s+entitled\s+to|(?:is|are)\s+eligible\s+(?:for|to)|"
        r"agrees?\s+to|authorizes?|grants?|retains?|warrants?|reserves?|assigns?|requires?|"
        r"(?:is|are|remains)\s+responsible\s+for|has\s+a\b|has\s+the\s+right\s+to\b|"
        r"is\s+limited\s+to\b|is\s+capped\s+at\b|shall\s+be\s+limited\s+to\b|liability\s+is\s+the\b|"
        r"must\s+not|may\s+not|will\s+not|shall\s+not|neither\s+party\s+will|is\s+not\s+licensed\s+to|prohibited\s+from|"
        r"non-refundable|not\s+refundable|not\s+eligible|never\s+expire|applies|"
        r"(?:is|are)\s+issued|submits?|decides?|refunded|refunds?|receives?|bonus|deducted(?:\s+from)?|"
        r"due\s+within|payment\s+is\s+due|due\s+and\s+payable|subject\s+to\s+fees|expected\s+to|asked\s+to|"
        r"maximum\s+duration|notice\s+periods?\s+vary|notice\s+period\s+duration|has\s+defined|defined\s+a|"
        r"follows\s+the\s+doctrine|sub\s+total|total\b|designate|designated\s+by|administer"
        r")\b",
        re.IGNORECASE,
    )

    PROHIBITION_PREDICATES = {
        "cannot_be_cancelled",
        "cannot_be_refunded_for_cash",
        "cannot_be_returned_or_refunded",
        "cannot_be_applied_retroactively",
        "prohibits_pay_in_lieu_of_notice",
        "must_not_modify_agreement",
    }

    NEGATIVE_POLARITY_PATTERN = re.compile(
        r"\b(not|no|never|cannot|can't|won't|neither|nor|non-refundable|nonrefundable|prohibited|refuse|without)\b",
        re.IGNORECASE,
    )

    # Condition patterns in contract clauses
    CONDITION_CUE_PATTERN = re.compile(
        r"\b(if\s+|provided\s+(?:that\s+)?|when\s+|only\s+if\s+|subject\s+to\s+|where\s+|in\s+the\s+event\s+(?:that\s+)?)\b",
        re.IGNORECASE,
    )

    # Exception patterns in contract clauses
    EXCEPTION_CUE_PATTERN = re.compile(
        r"\b(except\s+(?:where\s+)?|unless\s+|with\s+(?:prior\s+)?(?:manager\s+)?approval|other\s+than\s+)\b",
        re.IGNORECASE,
    )

    NORMATIVE_TABLE_CUES = re.compile(
        r"\b(must|cannot|may|only|not\s+eligible|no|yes|required|free|deducted|refuse|never|covered|prohibited)\b",
        re.IGNORECASE,
    )

    TABLE_PROHIBITION_CUES = re.compile(
        r"\b(no|not\s+eligible|cannot|never|prohibited|refuse|non-refundable|not\s+permitted)\b",
        re.IGNORECASE,
    )

    AFFIRMATIVE_PERMISSION_PREDICATES = {
        "can_cancel_before_shipment",
        "can_cancel_before_trial_ends",
        "has_cancellation_eligibility",
        "has_refund_eligibility",
        "will_issue_refund",
        "can_initiate_return",
        "may_receive_store_credit",
    }

    NON_NORMATIVE_CONTENT_ROLES = {
        "definition",
        "example",
        "contact_information",
        "contact",
        "pure_metadata",
        "metadata",
        "revision_history",
    }

    @classmethod
    def _normalize_values(cls, text: str) -> str:
        word_to_num = {
            "one": "1", "two": "2", "three": "3", "four": "4", "five": "5",
            "six": "6", "seven": "7", "eight": "8", "nine": "9", "ten": "10",
            "fourteen": "14", "thirty": "30", "forty-five": "45", "sixty": "60", "ninety": "90"
        }
        res = (text or "").replace("–", "-").replace("—", "-")
        # Normalize cents: $25.00 -> $25
        res = re.sub(r"\$([0-9]+)\.00\b", r"$\1", res)
        for w, n in word_to_num.items():
            res = re.sub(r"\b" + w + r"\b", n, res, flags=re.IGNORECASE)
        return res

    @classmethod
    def _check_value_fidelity(
        cls,
        claim_text: str,
        object_val: str,
        conditions: List[str],
        exceptions: List[str],
        evidence_str: str,
        enclosing_clause: str,
    ) -> List[str]:
        mismatches: List[str] = []
        claim_combined = f"{object_val} {' '.join(conditions or [])} {' '.join(exceptions or [])} {claim_text}"
        ev_combined = f"{evidence_str} {enclosing_clause}"

        c_norm = cls._normalize_values(claim_combined)
        e_norm = cls._normalize_values(ev_combined)

        # 1. Currencies
        claim_currencies = set(re.findall(r"\$[0-9]+(?:,[0-9]{3})*(?:\.[0-9]{2})?", c_norm))
        ev_currencies = set(re.findall(r"\$[0-9]+(?:,[0-9]{3})*(?:\.[0-9]{2})?", e_norm))
        if ev_currencies and claim_currencies:
            for curr in claim_currencies:
                if curr not in ev_currencies and curr not in e_norm:
                    mismatches.append(f"Currency mismatch: claim asserts {curr}, but evidence contains {ev_currencies}")

        # 2. Percentages
        claim_percents = set(re.findall(r"[0-9]+(?:\.[0-9]+)?%", c_norm))
        ev_percents = set(re.findall(r"[0-9]+(?:\.[0-9]+)?%", e_norm))
        if ev_percents and claim_percents:
            for p in claim_percents:
                if p not in ev_percents and p not in e_norm:
                    mismatches.append(f"Percentage mismatch: claim asserts {p}, but evidence contains {ev_percents}")

        # 3. Durations (days, months, years, hours)
        duration_pat = re.compile(r"\b([0-9]+(?:-[0-9]+)?)\s*(?:calendar\s+|business\s+)?(days?|months?|years?|hours?)\b", re.IGNORECASE)
        claim_durations = {f"{m.group(1)} {m.group(2).lower()}" for m in duration_pat.finditer(c_norm)}
        ev_durations = {f"{m.group(1)} {m.group(2).lower()}" for m in duration_pat.finditer(e_norm)}
        if ev_durations and claim_durations:
            for d in claim_durations:
                d_base = d.rstrip("s")
                matched = any(d == ed or d_base in ed or ed.rstrip("s") == d_base for ed in ev_durations)
                if not matched:
                    mismatches.append(f"Duration mismatch: claim asserts '{d}', but evidence specifies {ev_durations}")

        # 4. Numerical counts and return limits
        count_pat = re.compile(r"\b([0-9]+)\s+(?:receipt-less\s+)?returns?\b|\b([0-9]+)\s+instances?\b", re.IGNORECASE)
        claim_counts = {m.group(1) or m.group(2) for m in count_pat.finditer(c_norm)}
        ev_counts = {m.group(1) or m.group(2) for m in count_pat.finditer(e_norm)}
        if ev_counts and claim_counts:
            for cnt in claim_counts:
                if cnt not in ev_counts:
                    mismatches.append(f"Numerical count limit mismatch: claim asserts {cnt}, but evidence specifies {ev_counts}")

        return mismatches

    @classmethod
    def evaluate(cls, req: SharedGateRequest) -> SharedGateResult:
        res = SharedGateResult()
        reasons: List[str] = []
        codes: List[str] = []

        # ---------------------------------------------------------------------
        # Gate Family 1: Evidence Grounding & Source-Locator Validity
        # ---------------------------------------------------------------------
        evidence_str = (req.evidence_quote or "").strip()
        if not evidence_str and req.evidence_spans:
            for sp in req.evidence_spans:
                txt = getattr(sp, "verbatim_quote", None) or (sp.get("verbatim_quote") if isinstance(sp, dict) else str(sp))
                if txt and txt.strip():
                    evidence_str = txt.strip()
                    break

        if not evidence_str:
            res.evidence_grounding = False
            reasons.append("Evidence grounding failure: Missing or empty evidence span.")
            codes.append(GateFailureCode.ERR_EVIDENCE_MISSING.value)
        else:
            # Check physical document presence if document_text is provided
            if req.document_text is not None:
                doc_clean = " ".join(req.document_text.split()).replace("|", " ")
                ev_clean = " ".join(evidence_str.split()).replace("|", " ").replace("\x7f", " ")
                ev_tokens = ev_clean.split()
                if not ev_tokens:
                    res.evidence_grounding = False
                    reasons.append("Evidence grounding failure: Evidence span contains no lexical tokens.")
                    codes.append(GateFailureCode.ERR_EVIDENCE_MISSING.value)
                else:
                    pat = r"\s+".join([re.escape(t) for t in ev_tokens])
                    if not re.search(pat, req.document_text, re.IGNORECASE) and not re.search(pat, doc_clean, re.IGNORECASE):
                        res.evidence_grounding = False
                        reasons.append(f"Evidence grounding failure: Asserted span '{evidence_str[:60]}' not found in source document text.")
                        codes.append(GateFailureCode.ERR_EVIDENCE_FABRICATED.value)
                    else:
                        res.evidence_grounding = True
            else:
                res.evidence_grounding = True

        # Locator Validity
        if req.locators:
            valid_loc = True
            for loc in req.locators:
                # Must be a valid dict or object with non-negative offsets
                start = loc.get("start") if isinstance(loc, dict) else getattr(loc, "start", None)
                end = loc.get("end") if isinstance(loc, dict) else getattr(loc, "end", None)
                if start is not None and end is not None:
                    if start < 0 or end < start:
                        valid_loc = False
                        break
            if not valid_loc:
                res.source_locator_validity = False
                reasons.append("Source locator failure: Invalid character offsets [start > end or start < 0].")
                codes.append(GateFailureCode.ERR_LOCATOR_INVALID.value)
            else:
                res.source_locator_validity = True
        else:
            # If no locators provided, but evidence exists, locator validity is neutral/true
            res.source_locator_validity = res.evidence_grounding

        # ---------------------------------------------------------------------
        # Gate Family 2: Predicate Normativity & Taxonomy
        # ---------------------------------------------------------------------
        pred_clean = (req.predicate or "").strip().lower()
        pred_class = PredicateRegistry.get_predicate_class(pred_clean)

        if pred_class == "catch_all":
            res.predicate_normativity = False
            reasons.append(f"Predicate normativity failure: Predicate '{req.predicate}' is an unconstrained catch-all.")
            codes.append(GateFailureCode.ERR_PREDICATE_CATCH_ALL.value)
        elif pred_class == "deprecated":
            res.predicate_normativity = False
            reasons.append(f"Predicate normativity failure: Predicate '{req.predicate}' is a deprecated verb.")
            codes.append(GateFailureCode.ERR_PREDICATE_DEPRECATED.value)
        elif pred_class != "canonical":
            res.predicate_normativity = False
            reasons.append(f"Predicate normativity failure: Predicate '{req.predicate}' is not a canonical registered predicate.")
            codes.append(GateFailureCode.ERR_PREDICATE_INVALID.value)
        else:
            res.predicate_normativity = True

        # ---------------------------------------------------------------------
        # Gate Family 3: Table-Column Binding Integrity
        # ---------------------------------------------------------------------
        if req.table_header:
            match = PredicateRegistry.validate_table_header_predicate_match(req.table_header, pred_clean)
            if not match:
                res.table_column_binding = False
                reasons.append(
                    f"Table column binding failure: Table header '{req.table_header}' does not match predicate '{req.predicate}'."
                )
                codes.append(GateFailureCode.ERR_TABLE_BINDING_MISMATCH.value)
            else:
                res.table_column_binding = True
        else:
            res.table_column_binding = True

        # ---------------------------------------------------------------------
        # Gate Family 4: SPO Compatibility & Semantic Typing
        # ---------------------------------------------------------------------
        spo_res = TypeCompatibilityMatrix.evaluate_compatibility(
            subject=req.subject or "",
            predicate=req.predicate or "",
            object_text=req.object_val or "",
            clause_text=req.enclosing_clause or req.claim_text or "",
        )
        if not spo_res.is_compatible:
            res.spo_compatibility = False
            reasons.append(f"SPO compatibility failure: {spo_res.reason}")
            if spo_res.blocked_rule in ("BLOCK-ACTOR-001", "BLOCK-CUSTOMER-ROLE"):
                codes.append(GateFailureCode.ERR_ACTOR_ROLE_INVERSION.value)
            elif spo_res.blocked_rule == "BLOCK-INSTRUMENT-ROLE":
                codes.append(GateFailureCode.ERR_INSTRUMENT_OBLIGATION.value)
            else:
                codes.append(GateFailureCode.ERR_SPO_INCOMPATIBLE.value)
        else:
            res.spo_compatibility = True

        # ---------------------------------------------------------------------
        # Gate Family 5: Polarity & Modality Consistency (Hardened Phase 2.4b)
        # ---------------------------------------------------------------------
        # Polarity check
        combined_text = f"{req.claim_text} {evidence_str}".strip()
        has_negative_polarity = bool(cls.NEGATIVE_POLARITY_PATTERN.search(combined_text))

        if pred_clean in cls.PROHIBITION_PREDICATES and not has_negative_polarity:
            res.polarity_consistency = False
            reasons.append(
                f"Polarity inversion failure: Prohibition predicate '{req.predicate}' contradicts affirmative phrasing lacking negation."
            )
            codes.append(GateFailureCode.ERR_POLARITY_INVERSION.value)
        else:
            res.polarity_consistency = True

        # Table-Derived Prohibition Conversion Check:
        # Prevent table-derived prohibitions ("No", "Not eligible", "Refuse") from being converted into permissions
        if "|" in evidence_str or (req.metadata and (req.metadata.get("table_grid") or req.metadata.get("is_table"))):
            has_table_prohibition = bool(cls.TABLE_PROHIBITION_CUES.search(evidence_str))
            if has_table_prohibition and pred_clean in cls.AFFIRMATIVE_PERMISSION_PREDICATES:
                res.polarity_consistency = False
                reasons.append(
                    f"Table-derived prohibition violation: Table evidence specifies prohibition ('no'/'not eligible'/'refuse'), "
                    f"but claim asserts affirmative permission predicate '{req.predicate}'."
                )
                if GateFailureCode.ERR_POLARITY_INVERSION.value not in codes:
                    codes.append(GateFailureCode.ERR_POLARITY_INVERSION.value)

        # Modality check:
        # Table rows are NOT given a blanket exemption merely for containing "|".
        # Exempt ONLY rows classified as definition, example, contact_info, or pure metadata.
        content_role = str((req.metadata.get("content_role") if req.metadata else None) or "").lower()
        is_exempt_non_normative = (
            content_role in cls.NON_NORMATIVE_CONTENT_ROLES
            or (req.claim_type or "").lower() in ("definition", "reference", "description", "contact_info")
        )

        if (req.claim_type or "").lower() in ("rule", "policy_rule", "policy"):
            if not is_exempt_non_normative:
                has_operative_modal = bool(cls.OPERATIVE_MODAL_PATTERN.search(combined_text))
                has_normative_table_cue = bool(cls.NORMATIVE_TABLE_CUES.search(combined_text))
                if not (has_operative_modal or has_normative_table_cue):
                    res.modality_consistency = False
                    reasons.append(
                        "Modality mismatch failure: Rule assertion lacks operative deontic modal verb (must, may, shall, cannot) "
                        "or normative table indicator (required, free, deducted, not eligible, no, yes)."
                    )
                    codes.append(GateFailureCode.ERR_MODALITY_MISMATCH.value)
                else:
                    res.modality_consistency = True
            else:
                res.modality_consistency = True
        else:
            res.modality_consistency = True

        # ---------------------------------------------------------------------
        # Gate Family 6: Condition, Exception & Scope Preservation
        # ---------------------------------------------------------------------
        # Condition check
        evidence_lower = evidence_str.lower()
        has_condition_cue = bool(cls.CONDITION_CUE_PATTERN.search(evidence_lower))
        if has_condition_cue:
            # Ensure conditions are captured in req.conditions, object, or claim_text
            condition_captured = bool(req.conditions) or any(
                cue in (req.object_val or "").lower() for cue in ("if", "when", "provided", "under")
            ) or any(
                cue in (req.claim_text or "").lower() for cue in ("if", "when", "provided", "under")
            )
            if not condition_captured:
                res.condition_preservation = False
                reasons.append("Condition lost: Source evidence contains operative condition ('if/when/provided') that was omitted from structured claim.")
                codes.append(GateFailureCode.ERR_CONDITION_LOST.value)
            else:
                res.condition_preservation = True
        else:
            res.condition_preservation = True

        # Exception check
        has_exception_cue = bool(cls.EXCEPTION_CUE_PATTERN.search(evidence_lower))
        if has_exception_cue:
            exception_captured = bool(req.exceptions) or any(
                cue in (req.object_val or "").lower() for cue in ("except", "unless", "approval")
            ) or any(
                cue in (req.claim_text or "").lower() for cue in ("except", "unless", "approval")
            )
            if not exception_captured:
                res.exception_preservation = False
                reasons.append("Exception lost: Source evidence contains operative exception ('except/unless/approval') that was omitted from structured claim.")
                codes.append(GateFailureCode.ERR_EXCEPTION_LOST.value)
            else:
                res.exception_preservation = True
        else:
            res.exception_preservation = True

        # Scope check
        if req.scope:
            scope_captured = (
                req.scope.lower() in (req.subject or "").lower() or
                req.scope.lower() in (req.object_val or "").lower() or
                req.scope.lower() in (req.claim_text or "").lower()
            )
            if not scope_captured:
                res.scope_preservation = False
                reasons.append(f"Scope lost: Context scope '{req.scope}' is missing from subject, object, and claim text.")
                codes.append(GateFailureCode.ERR_SCOPE_LOST.value)
            else:
                res.scope_preservation = True
        else:
            res.scope_preservation = True

        # ---------------------------------------------------------------------
        # Gate Family 7: Value & Quantitative Fidelity (Phase 2.4b)
        # ---------------------------------------------------------------------
        val_mismatches = cls._check_value_fidelity(
            claim_text=req.claim_text,
            object_val=req.object_val or "",
            conditions=req.conditions or [],
            exceptions=req.exceptions or [],
            evidence_str=evidence_str,
            enclosing_clause=req.enclosing_clause or "",
        )
        if val_mismatches:
            res.value_fidelity = False
            for vm in val_mismatches:
                reasons.append(f"Value fidelity failure: {vm}")
            codes.append(GateFailureCode.ERR_VALUE_FIDELITY_MISMATCH.value)
        else:
            res.value_fidelity = True

        # ---------------------------------------------------------------------
        # Gate Family 8: Status & Silent Upgrade Invariants
        # ---------------------------------------------------------------------
        if req.is_upgrade_attempt or (req.target_status == "verified" and req.status in ("rejected", "candidate", "conflicted")):
            res.no_silent_upgrade = False
            reasons.append(
                f"Silent upgrade violation: Claim with baseline status '{req.status}' cannot be promoted to 'verified' without satisfying promotion gate."
            )
            codes.append(GateFailureCode.ERR_NO_SILENT_UPGRADE_VIOLATION.value)
        else:
            res.no_silent_upgrade = True

        # ---------------------------------------------------------------------
        # Aggregate Decisions
        # ---------------------------------------------------------------------
        gate_flags = {
            "evidence_grounding": res.evidence_grounding,
            "source_locator_validity": res.source_locator_validity,
            "predicate_normativity": res.predicate_normativity,
            "table_column_binding": res.table_column_binding,
            "spo_compatibility": res.spo_compatibility,
            "polarity_consistency": res.polarity_consistency,
            "modality_consistency": res.modality_consistency,
            "condition_preservation": res.condition_preservation,
            "exception_preservation": res.exception_preservation,
            "scope_preservation": res.scope_preservation,
            "value_fidelity": res.value_fidelity,
            "text_integrity": res.text_integrity,
            "is_atomic": res.is_atomic,
            "is_not_duplicate": res.is_not_duplicate,
            "claim_type_allowed": res.claim_type_allowed,
            "no_silent_upgrade": res.no_silent_upgrade,
        }

        all_passed = all(gate_flags.values())
        res.all_gates_passed = all_passed
        res.gate_flags = gate_flags
        res.rejection_reasons = reasons
        res.reason_codes = codes

        if all_passed:
            res.certification_tier = "AUTOMATED_CERTIFIED"
        else:
            res.certification_tier = "REVIEW_REQUIRED"

        return res
