import decimal
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.db.enums import ClaimStatus, ConflictStatus, ConflictType
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.llm.schemas import ContradictionResult


def _safe_get_rel(obj, attr_name):
    """Safely gets a relationship or attribute without triggering SQLAlchemy async MissingGreenlet."""
    if obj is None:
        return None
    state = getattr(obj, "_sa_instance_state", None)
    if state and attr_name in state.unloaded:
        return None
    try:
        return getattr(obj, attr_name, None)
    except Exception:
        return None


@dataclass
class PrecedenceScoreBreakdown:
    """Explainable scoring factors for enterprise precedence decision."""
    explicit_supersession: float = 0.0
    authority_delta: float = 0.0
    scope_specificity: float = 0.0
    temporal_validity: float = 0.0
    certification_status: float = 0.0
    total_score: float = 0.0
    rationale: str = ""


@dataclass
class PrecedenceDecision:
    """Outcome of evaluating deterministic enterprise precedence rules between two contradictory claims."""
    is_auto_resolved: bool
    winner_claim_id: Optional[uuid.UUID] = None
    loser_claim_id: Optional[uuid.UUID] = None
    precedence_rule: Optional[str] = None
    reasoning: Optional[str] = None
    is_compatible_exception: bool = False
    conflict_type: ConflictType = ConflictType.DIRECT_CONTRADICTION
    score_breakdown: Optional[PrecedenceScoreBreakdown] = None
    scoring_factors: Dict[str, Any] = field(default_factory=dict)
    requires_human_review: bool = False
    review_reason: Optional[str] = None
    conflicting_fields: list[str] = field(default_factory=list)
    applicable_scope: Dict[str, Any] = field(default_factory=dict)
    effective_dates: Dict[str, Any] = field(default_factory=dict)
    source_authority: Dict[str, Any] = field(default_factory=dict)
    supporting_evidence: Dict[str, Any] = field(default_factory=dict)


class PrecedenceEngine:
    """
    Deterministic Enterprise Precedence Engine.
    
    Evaluates policy hierarchy, temporal document versioning, source authority,
    and exception specificity using explainable multi-factor scoring:
    precedence_score = explicit_supersession + authority_delta + scope_specificity + temporal_validity + certification_status
    """

    AUTHORITY_DIFFERENCE_THRESHOLD = 15  # Authority gap required to deterministically override

    @classmethod
    def evaluate_precedence(
        cls,
        claim_a: Claim,
        claim_b: Claim,
        eval_result: Optional[ContradictionResult] = None,
    ) -> PrecedenceDecision:
        """
        Evaluate deterministic rules via explainable multi-factor scoring.
        """
        from app.conflict_engine.normalizer import ClaimNormalizer
        from app.conflict_engine.compatibility_gate import CompatibilityGate

        key_a = ClaimNormalizer.build_key(claim_a)
        key_b = ClaimNormalizer.build_key(claim_b)

        text_a_clean = re.sub(r"\s+", " ", claim_a.claim_text.lower().strip())
        text_b_clean = re.sub(r"\s+", " ", claim_b.claim_text.lower().strip())

        # Build contract structured metadata
        ver_a = _safe_get_rel(claim_a, "document_version")
        ver_b = _safe_get_rel(claim_b, "document_version")
        doc_a = _safe_get_rel(ver_a, "document") if ver_a else None
        doc_b = _safe_get_rel(ver_b, "document") if ver_b else None
        src_a = _safe_get_rel(doc_a, "source") if doc_a else None
        src_b = _safe_get_rel(doc_b, "source") if doc_b else None

        raw_auth_a = getattr(src_a, "authority_level", None) if src_a is not None else getattr(claim_a, "authority_level", None)
        try:
            auth_a = int(raw_auth_a) if raw_auth_a is not None else 75
        except (ValueError, TypeError):
            auth_a = 75

        raw_auth_b = getattr(src_b, "authority_level", None) if src_b is not None else getattr(claim_b, "authority_level", None)
        try:
            auth_b = int(raw_auth_b) if raw_auth_b is not None else 75
        except (ValueError, TypeError):
            auth_b = 75
        auth_delta = auth_b - auth_a

        val_records_a = _safe_get_rel(claim_a, "validity_records")
        val_records_b = _safe_get_rel(claim_b, "validity_records")
        val_a = val_records_a[0] if val_records_a else None
        val_b = val_records_b[0] if val_records_b else None

        contract_scope = {
            "claim_a_scope": key_a.scope_key,
            "claim_b_scope": key_b.scope_key,
            "claim_a_audience": key_a.audience,
            "claim_b_audience": key_b.audience,
        }
        contract_dates = {
            "claim_a_valid_from": str(getattr(val_a, "valid_from", None)) if val_a else None,
            "claim_a_valid_until": str(getattr(val_a, "valid_until", None)) if val_a else None,
            "claim_b_valid_from": str(getattr(val_b, "valid_from", None)) if val_b else None,
            "claim_b_valid_until": str(getattr(val_b, "valid_until", None)) if val_b else None,
        }
        contract_authority = {
            "claim_a_authority": auth_a,
            "claim_b_authority": auth_b,
            "authority_delta": auth_delta,
        }
        ev_a = _safe_get_rel(claim_a, "evidence")
        ev_b = _safe_get_rel(claim_b, "evidence")
        contract_evidence = {
            "claim_a_citations": [getattr(e, "section", "") for e in (ev_a or []) if getattr(e, "section", None)],
            "claim_b_citations": [getattr(e, "section", "") for e in (ev_b or []) if getattr(e, "section", None)],
        }

        # Identify conflicting fields
        conflicting_fields = []
        if key_a.value_scalar != key_b.value_scalar and (key_a.value_scalar is not None or key_b.value_scalar is not None):
            conflicting_fields.append("value_scalar")
        if key_a.value_unit != key_b.value_unit and (key_a.value_unit is not None or key_b.value_unit is not None):
            conflicting_fields.append("value_unit")
        if key_a.modality != key_b.modality:
            conflicting_fields.append("modality")
        if not conflicting_fields:
            conflicting_fields.append("claim_text")

        # --- Rule 1: Exact / Near-Exact Semantic Duplicate ---
        if text_a_clean == text_b_clean:
            scores_a = _safe_get_rel(claim_a, "trust_scores")
            scores_b = _safe_get_rel(claim_b, "trust_scores")
            score_a = float(scores_a[0].overall_score) if scores_a else 0.8
            score_b = float(scores_b[0].overall_score) if scores_b else 0.8
            winner = claim_a if score_a >= score_b else claim_b
            loser = claim_b if winner == claim_a else claim_a
            breakdown = PrecedenceScoreBreakdown(
                certification_status=50.0,
                total_score=50.0 if winner == claim_b else -50.0,
                rationale="Identical semantic policy statement deduplicated; canonical master claim retained.",
            )
            return PrecedenceDecision(
                is_auto_resolved=True,
                winner_claim_id=winner.id,
                loser_claim_id=loser.id,
                precedence_rule="CANONICAL_DEDUPLICATION",
                reasoning="Identical semantic policy statement deduplicated; canonical master claim retained.",
                conflict_type=ConflictType.DIRECT_CONTRADICTION,
                score_breakdown=breakdown,
                conflicting_fields=conflicting_fields,
                applicable_scope=contract_scope,
                effective_dates=contract_dates,
                source_authority=contract_authority,
                supporting_evidence=contract_evidence,
            )

        # --- Rule 2: Specificity & Exception Mapping (Lex Specialis) ---
        tier_exception_keywords = [
            "enterprise", "exception", "upon vp approval", "enterprise tier",
            "gold", "rewards gold", "footwear", "holiday", "tents", "camping",
            "sleeping bags", "cooling-off", "statutory", "receipt-less", "keep it",
            "vip", "platinum", "custom contract", "case studies", "revision history",
            "summary at a glance", "policy summary", "written approval", "prior approval",
            "annual plan", "annual subscription", "eligible for pro-rated refunds"
        ]
        baseline_keywords = [
            "standard", "standard automated", "general tier", "baseline",
            "standard merchandise", "most items", "standard return policy", "no refunds",
            "all sales are final", "non-refundable", "strictly non-refundable"
        ]

        is_exception_a = any(k in text_a_clean for k in tier_exception_keywords) or key_a.has_exception or (claim_a.subject and any(k in claim_a.subject.lower() for k in tier_exception_keywords))
        is_exception_b = any(k in text_b_clean for k in tier_exception_keywords) or key_b.has_exception or (claim_b.subject and any(k in claim_b.subject.lower() for k in tier_exception_keywords))
        is_standard_a = any(k in text_a_clean for k in baseline_keywords) or (claim_a.subject and any(k in claim_a.subject.lower() for k in baseline_keywords))
        is_standard_b = any(k in text_b_clean for k in baseline_keywords) or (claim_b.subject and any(k in claim_b.subject.lower() for k in baseline_keywords))

        has_cond_a = bool(key_a.condition_key)
        has_cond_b = bool(key_b.condition_key)

        # If one is specific exception/condition and the other is general baseline policy (Lex Specialis)
        if (is_exception_a and is_standard_b) or (is_exception_b and is_standard_a) or ((has_cond_a != has_cond_b) and (is_standard_a or is_standard_b)):
            exc_claim = claim_a if is_exception_a or has_cond_a else claim_b
            base_claim = claim_b if exc_claim == claim_a else claim_a
            breakdown = PrecedenceScoreBreakdown(
                scope_specificity=50.0,
                total_score=0.0,
                rationale="Lex Specialis: Specific conditional exception co-exists with general baseline policy.",
            )
            return PrecedenceDecision(
                is_auto_resolved=True,
                is_compatible_exception=True,
                precedence_rule="LEX_SPECIALIS_EXCEPTION",
                reasoning="Rules govern distinct tiers: specific conditional exception or qualified policy co-exists with general baseline policy (Lex Specialis).",
                conflict_type=ConflictType.EXCEPTION_CONFLICT if (is_exception_a or is_exception_b) else ConflictType.CONDITIONAL_CONFLICT,
                score_breakdown=breakdown,
                conflicting_fields=conflicting_fields,
                applicable_scope=contract_scope,
                effective_dates=contract_dates,
                source_authority=contract_authority,
                supporting_evidence=contract_evidence,
            )

        # If both have different exceptions on the same topic -> Conflict requiring human review
        if is_exception_a and is_exception_b and key_a.exception_text != key_b.exception_text:
            breakdown = PrecedenceScoreBreakdown(
                scope_specificity=-50.0,
                total_score=0.0,
                rationale="Conflicting exceptions require human auditor review.",
            )
            return PrecedenceDecision(
                is_auto_resolved=False,
                requires_human_review=True,
                review_reason="Conflicting conditional exceptions cannot be auto-superseded.",
                conflict_type=ConflictType.EXCEPTION_CONFLICT,
                score_breakdown=breakdown,
                reasoning="Divergent conditional exceptions require human auditor adjudication.",
                conflicting_fields=conflicting_fields,
                applicable_scope=contract_scope,
                effective_dates=contract_dates,
                source_authority=contract_authority,
                supporting_evidence=contract_evidence,
            )

        # --- Rule 3: Multi-Factor Precedence Scoring ---
        # Factor 1: Explicit Supersession Reference (Dominates)
        supersedes_patterns = (
            "supersedes", "superseded", "superseding", "supersession",
            "replaces", "replacing", "prior terms are hereby superseded",
            "those terms control in the case of conflict", "control in the case of conflict",
            "overrides", "overriding", "prevails over"
        )
        has_super_a = any(p in text_a_clean for p in supersedes_patterns)
        has_super_b = any(p in text_b_clean for p in supersedes_patterns)
        s_explicit = 0.0
        if has_super_b and not has_super_a:
            s_explicit = 100.0
        elif has_super_a and not has_super_b:
            s_explicit = -100.0

        # Factor 2: Authority Delta (Must meet 15% threshold to contribute)
        s_auth = 0.0
        if abs(auth_delta) >= cls.AUTHORITY_DIFFERENCE_THRESHOLD:
            s_auth = 35.0 if auth_delta > 0 else -35.0

        # Factor 3: Scope Specificity & Scope Mismatch Check
        s_scope = 0.0
        if key_a.scope_key and key_b.scope_key and key_a.scope_key != key_b.scope_key:
            # Scope mismatch prevents resolution entirely
            s_scope = -999.0

        # Factor 4: Temporal Validity & Version Lineage
        now = datetime.now(timezone.utc)
        s_temp = 0.0
        if val_a and val_b:
            a_exp = (val_a.valid_until and val_a.valid_until < now) or not val_a.is_current
            b_exp = (val_b.valid_until and val_b.valid_until < now) or not val_b.is_current
            if a_exp and not b_exp:
                s_temp += 40.0
            elif b_exp and not a_exp:
                s_temp -= 40.0

        has_legacy_a = "legacy" in text_a_clean or "archived" in text_a_clean or "deprecated" in text_a_clean
        has_legacy_b = "legacy" in text_b_clean or "archived" in text_b_clean or "deprecated" in text_b_clean
        has_curr_a = "current" in text_a_clean or "effective 2026" in text_a_clean or "active policy" in text_a_clean
        has_curr_b = "current" in text_b_clean or "effective 2026" in text_b_clean or "active policy" in text_b_clean
        is_temp_eval = bool(eval_result and eval_result.conflict_type in ("temporal_outdated", "temporal_conflict"))

        if (has_legacy_a and not has_legacy_b) or (has_curr_b and has_legacy_a) or (is_temp_eval and has_legacy_a):
            s_temp += 30.0
        elif (has_legacy_b and not has_legacy_a) or (has_curr_a and has_legacy_b) or (is_temp_eval and has_legacy_b):
            s_temp -= 30.0

        # Document Version Lineage:
        # Same document version lineage is strong (+30.0)
        # Different documents recency is weak (+5.0) to prevent recency-only override
        is_same_doc = ver_a and ver_b and getattr(ver_a, "document_id", None) == getattr(ver_b, "document_id", None)
        num_a = getattr(ver_a, "version_number", 1) if ver_a else 1
        num_b = getattr(ver_b, "version_number", 1) if ver_b else 1

        if is_same_doc and num_a != num_b:
            s_temp += 30.0 if num_b > num_a else -30.0
        elif not is_same_doc and num_a != num_b:
            s_temp += 5.0 if num_b > num_a else -5.0

        # Factor 5: Certification Status
        st_a = getattr(claim_a, "status", ClaimStatus.CANDIDATE)
        st_b = getattr(claim_b, "status", ClaimStatus.CANDIDATE)
        s_cert = 0.0
        if st_b == ClaimStatus.VERIFIED and st_a != ClaimStatus.VERIFIED:
            s_cert += 20.0
        elif st_a == ClaimStatus.VERIFIED and st_b != ClaimStatus.VERIFIED:
            s_cert -= 20.0

        total_score = s_explicit + s_auth + s_scope + s_temp + s_cert

        breakdown = PrecedenceScoreBreakdown(
            explicit_supersession=s_explicit,
            authority_delta=s_auth,
            scope_specificity=s_scope,
            temporal_validity=s_temp,
            certification_status=s_cert,
            total_score=total_score,
            rationale=f"Score {total_score:+.1f} (Supersession={s_explicit}, Auth={s_auth}, Scope={s_scope}, Temp={s_temp}, Cert={s_cert})",
        )

        # Check for scope mismatch halt
        if s_scope == -999.0:
            return PrecedenceDecision(
                is_auto_resolved=False,
                requires_human_review=True,
                review_reason="Scope mismatch between claims prevents automatic resolution.",
                conflict_type=ConflictType.SCOPE_CONFLICT,
                score_breakdown=breakdown,
                reasoning="Claims govern distinct applicability scopes and cannot supersede each other.",
                conflicting_fields=conflicting_fields,
                applicable_scope=contract_scope,
                effective_dates=contract_dates,
                source_authority=contract_authority,
                supporting_evidence=contract_evidence,
            )

        # Infer granular conflict type from conflicting fields and metadata
        val_from_a = getattr(val_a, "valid_from", None) if val_a else None
        val_from_b = getattr(val_b, "valid_from", None) if val_b else None

        if s_explicit != 0 or (is_same_doc and num_a != num_b):
            inferred_c_type = ConflictType.VERSION_CONFLICT
        elif abs(auth_delta) >= cls.AUTHORITY_DIFFERENCE_THRESHOLD:
            inferred_c_type = ConflictType.AUTHORITY_CONFLICT
        elif val_from_a and val_from_b:
            inferred_c_type = ConflictType.TEMPORAL_CONFLICT
        elif "value_scalar" in conflicting_fields or "value_unit" in conflicting_fields:
            inferred_c_type = ConflictType.NUMERIC_CONFLICT
        elif "modality" in conflicting_fields:
            # Distinguish direct contradiction (MUST vs MUST_NOT) from modality nuance (MUST vs MAY)
            m_a = key_a.modality.upper()
            m_b = key_b.modality.upper()
            if (m_a == "MUST" and m_b == "MUST_NOT") or (m_a == "MUST_NOT" and m_b == "MUST"):
                inferred_c_type = ConflictType.DIRECT_CONTRADICTION
            else:
                inferred_c_type = ConflictType.MODALITY_CONFLICT
        elif has_cond_a != has_cond_b or (has_cond_a and has_cond_b and key_a.condition_key != key_b.condition_key):
            inferred_c_type = ConflictType.CONDITIONAL_CONFLICT
        elif is_exception_a or is_exception_b:
            inferred_c_type = ConflictType.EXCEPTION_CONFLICT
        else:
            inferred_c_type = ConflictType.DIRECT_CONTRADICTION

        # Check temporal expiration flags
        a_is_expired = bool(val_a and ((val_a.valid_until and val_a.valid_until < now) or not val_a.is_current))
        b_is_expired = bool(val_b and ((val_b.valid_until and val_b.valid_until < now) or not val_b.is_current))

        # Check if authority delta is the sole factor but below threshold
        if abs(auth_delta) < cls.AUTHORITY_DIFFERENCE_THRESHOLD and s_explicit == 0.0 and s_temp == 0.0:
            return PrecedenceDecision(
                is_auto_resolved=False,
                requires_human_review=True,
                review_reason=f"Authority delta ({abs(auth_delta)}%) is below the {cls.AUTHORITY_DIFFERENCE_THRESHOLD}% threshold.",
                conflict_type=inferred_c_type,
                score_breakdown=breakdown,
                reasoning=f"Conflict cannot be auto-resolved deterministically; human auditor review required.",
                conflicting_fields=conflicting_fields,
                applicable_scope=contract_scope,
                effective_dates=contract_dates,
                source_authority=contract_authority,
                supporting_evidence=contract_evidence,
            )

        # Auto-Resolution Decision
        if s_explicit >= 100.0 or total_score >= 25.0:
            rule = "EXPLICIT_SUPERSESSION" if s_explicit >= 100.0 else (
                "TEMPORAL_EXPIRATION_PRECEDENCE" if a_is_expired else (
                    "TEMPORAL_VERSION_PRECEDENCE" if (is_same_doc and num_b > num_a) else (
                        "AUTHORITY_HIERARCHY_PRECEDENCE" if s_auth >= 35.0 else (
                            "TEMPORAL_OBSOLESCENCE" if s_temp >= 30.0 else "DETERMINISTIC_PRECEDENCE"
                        )
                    )
                )
            )
            c_type = inferred_c_type
            reason = f"Active document version v{num_b}.0 supersedes legacy version v{num_a}.0." if (is_same_doc and num_b > num_a) else (
                "Claim A has passed its valid_until date or is marked inactive." if a_is_expired else (
                    f"Governing source authority ({auth_b}%) supersedes departmental policy ({auth_a}%)." if s_auth >= 35.0 else (
                        f"Claim B established decisive precedence score ({total_score:+.1f})."
                    )
                )
            )
            return PrecedenceDecision(
                is_auto_resolved=True,
                winner_claim_id=claim_b.id,
                loser_claim_id=claim_a.id,
                precedence_rule=rule,
                reasoning=reason,
                conflict_type=c_type,
                score_breakdown=breakdown,
                conflicting_fields=conflicting_fields,
                applicable_scope=contract_scope,
                effective_dates=contract_dates,
                source_authority=contract_authority,
                supporting_evidence=contract_evidence,
            )

        elif s_explicit <= -100.0 or total_score <= -25.0:
            rule = "EXPLICIT_SUPERSESSION" if s_explicit <= -100.0 else (
                "TEMPORAL_EXPIRATION_PRECEDENCE" if b_is_expired else (
                    "TEMPORAL_VERSION_PRECEDENCE" if (is_same_doc and num_a > num_b) else (
                        "AUTHORITY_HIERARCHY_PRECEDENCE" if s_auth <= -35.0 else (
                            "TEMPORAL_OBSOLESCENCE" if s_temp <= -30.0 else "DETERMINISTIC_PRECEDENCE"
                        )
                    )
                )
            )
            c_type = inferred_c_type
            reason = f"Active document version v{num_a}.0 supersedes legacy version v{num_b}.0." if (is_same_doc and num_a > num_b) else (
                "Claim B has passed its valid_until date or is marked inactive." if b_is_expired else (
                    f"Governing source authority ({auth_a}%) supersedes departmental policy ({auth_b}%)." if s_auth <= -35.0 else (
                        f"Claim A established decisive precedence score ({total_score:+.1f})."
                    )
                )
            )
            return PrecedenceDecision(
                is_auto_resolved=True,
                winner_claim_id=claim_a.id,
                loser_claim_id=claim_b.id,
                precedence_rule=rule,
                reasoning=reason,
                conflict_type=c_type,
                score_breakdown=breakdown,
                conflicting_fields=conflicting_fields,
                applicable_scope=contract_scope,
                effective_dates=contract_dates,
                source_authority=contract_authority,
                supporting_evidence=contract_evidence,
            )

        # Ambiguous band (-25 < total_score < 25) -> Human review required
        return PrecedenceDecision(
            is_auto_resolved=False,
            requires_human_review=True,
            review_reason="Score in ambiguous range (-25 to +25); requires human auditor adjudication.",
            conflict_type=inferred_c_type,
            score_breakdown=breakdown,
            reasoning="Genuinely conflicting corporate policies without deterministic hierarchy winner.",
            conflicting_fields=conflicting_fields,
            applicable_scope=contract_scope,
            effective_dates=contract_dates,
            source_authority=contract_authority,
            supporting_evidence=contract_evidence,
        )
