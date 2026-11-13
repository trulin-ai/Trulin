"""
Layer 6: Claim Lifecycle Decision Engine.
Synthesizes 6-dimensional validation results into an authoritative lifecycle decision:
- [APPROVE] Automated activation for trusted, authoritative, and fully grounded claims.
- [REVIEW]  Human-in-the-Loop escalation for ambiguous, partial, or non-authoritative items.
- [REJECT]  Hard rejection for ungrounded claims or unauthorized scope violations.
"""

from __future__ import annotations

import re

import logging
from app.extraction.models import CandidateClaim
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.validation_gate.evaluators import (
    AuthorityEvaluator,
    CompletenessEvaluator,
    MeaningEvaluator,
    ScopeEvaluator,
    SourceMatchEvaluator,
    TemporalValidityEvaluator,
)
from app.validation_gate.models import (
    CandidateGateEvaluation,
    ClaimLifecycleDecision,
    DecisionCode,
    DimensionEvaluation,
    ReviewStatus,
)

logger = logging.getLogger(__name__)


class ClaimLifecycleDecisionEngine:
    """Evaluates candidate claims across 6 dimensions and determines lifecycle actions."""

    AUTO_APPROVE_THRESHOLD: float = 0.88

    # Dimension weightings for composite trust score
    WEIGHTS = {
        "source_match": 0.30,
        "meaning": 0.25,
        "authority": 0.20,
        "completeness": 0.15,
        "time": 0.10,
    }

    @classmethod
    def evaluate_candidate(
        cls,
        candidate: CandidateClaim,
        envelope: CanonicalSourceEnvelope,
    ) -> CandidateGateEvaluation:
        # 1. Evaluate 6 Core Dimensions
        source_match = SourceMatchEvaluator.evaluate(candidate, envelope)
        completeness = CompletenessEvaluator.evaluate(candidate)
        meaning = MeaningEvaluator.evaluate(candidate)
        scope = ScopeEvaluator.evaluate(candidate, envelope)
        time_eval = TemporalValidityEvaluator.evaluate(candidate, envelope)
        authority = AuthorityEvaluator.evaluate(envelope)

        # 2. Determine Human Review Trigger
        needs_review = (
            not meaning.passed
            or not completeness.passed
            or not authority.passed
            or not time_eval.passed
        )

        review_trigger = DimensionEvaluation(
            dimension_name="review",
            status=ReviewStatus.REVIEW_REQUIRED.value if needs_review else ReviewStatus.NO_REVIEW_NEEDED.value,
            score=0.5 if needs_review else 1.0,
            passed=not needs_review,
            reason="Human review recommended due to uncertainty or partial evidence." if needs_review else "All dimensions verified automatically without human review required.",
            details={"needs_human_review": needs_review},
        )

        # 3. Calculate Composite Trust Score
        composite_score = (
            source_match.score * cls.WEIGHTS["source_match"]
            + meaning.score * cls.WEIGHTS["meaning"]
            + authority.score * cls.WEIGHTS["authority"]
            + completeness.score * cls.WEIGHTS["completeness"]
            + time_eval.score * cls.WEIGHTS["time"]
        )
        composite_score = round(min(max(composite_score, 0.0), 1.0), 4)

        # 4. Synthesize Claim Lifecycle Decision & Machine-Readable Cause Code
        claim_type = getattr(candidate, "claim_type", "policy")

        # Invariant Knockouts (Fail-Closed Gates)
        # Invariant Knockout 0: Malformed Fragment / Broken Token Quarantine
        full_cand_text = (getattr(candidate, "claim_text", "") or "") + " " + (getattr(candidate, "subject", "") or "")
        malformed_markers = [
            r"\breleased immediately wit\b",
            r"\bhout serving\b",
            r"\binsubordinat ion\b",
            r"\bseve re\b",
            r"\bwarran ting\b",
            r"\bO Responsibilities\b",
            r"\bRespons ibilities\b"
        ]
        if any(re.search(p, full_cand_text, re.IGNORECASE) for p in malformed_markers):
            return cls._create_evaluation(
                candidate=candidate,
                envelope=envelope,
                claim_type=claim_type,
                source_match=source_match,
                completeness=completeness,
                meaning=DimensionEvaluation(
                    dimension_name="meaning",
                    status="fail",
                    score=0.0,
                    passed=False,
                    reason="Malformed layout fragment or broken word boundary detected.",
                ),
                scope=scope,
                time_eval=time_eval,
                authority=authority,
                review_trigger=review_trigger,
                composite_score=0.0,
                decision=ClaimLifecycleDecision.REJECT,
                decision_code=DecisionCode.FRAGMENT_ASSERTION_DISCARDED,
                reason="REJECTED: Malformed layout fragment or broken word boundary quarantined.",
            )

        # Invariant Knockout 0B: Generic Page Number Subject
        if (getattr(candidate, "subject", "") or "").strip().lower().startswith("page "):
            return cls._create_evaluation(
                candidate=candidate,
                envelope=envelope,
                claim_type=claim_type,
                source_match=source_match,
                completeness=completeness,
                meaning=DimensionEvaluation(
                    dimension_name="meaning",
                    status="fail",
                    score=0.0,
                    passed=False,
                    reason="Generic page number header is not a valid enterprise subject entity.",
                ),
                scope=scope,
                time_eval=time_eval,
                authority=authority,
                review_trigger=review_trigger,
                composite_score=0.0,
                decision=ClaimLifecycleDecision.REJECT,
                decision_code=DecisionCode.FRAGMENT_ASSERTION_DISCARDED,
                reason="REJECTED: Generic page header subject is not canonical.",
            )

        # Invariant Knockout 0C: Non-canonical Prepositional / Document Title Subject
        cand_subj = (getattr(candidate, "subject", "") or "").strip()
        cand_subj_lower = cand_subj.lower()
        if (
            cand_subj_lower in (
                "in no event", "under no circumstances", "for the avoidance of doubt",
                "in the event", "to the extent", "in addition", "document header",
                "neither party", "either party", "as a result", "furthermore"
            )
            or re.search(r"(?:mcaps|commercial-supplier|-agreement-terms|agreement_for_leasing|\.pdf$|\.docx$|\.md$|terms-and-conditions)", cand_subj_lower)
        ):
            return cls._create_evaluation(
                candidate=candidate,
                envelope=envelope,
                claim_type=claim_type,
                source_match=source_match,
                completeness=completeness,
                meaning=DimensionEvaluation(
                    dimension_name="meaning",
                    status="fail",
                    score=0.0,
                    passed=False,
                    reason=f"Non-canonical subject entity '{cand_subj}' rejected.",
                ),
                scope=scope,
                time_eval=time_eval,
                authority=authority,
                review_trigger=review_trigger,
                composite_score=0.0,
                decision=ClaimLifecycleDecision.REJECT,
                decision_code=DecisionCode.FRAGMENT_ASSERTION_DISCARDED,
                reason=f"REJECTED: Non-canonical subject entity '{cand_subj}'.",
            )

        # Invariant Knockout 0D: Non-semantic Bullet Glyph / Symbol Object or Subject
        cand_obj_str = str(getattr(candidate, "object", "") or "").strip()
        if (
            any(b in cand_subj or b in cand_obj_str for b in ("●", "❖", "✔", "✓", "•"))
            or (cand_obj_str and not re.sub(r"[\s•●❖\-_|*✓✔✗✘\.]+", "", cand_obj_str))
            or (cand_subj and not re.sub(r"[\s•●❖\-_|*✓✔✗✘\.]+", "", cand_subj))
            or cand_subj in ("N/A", "n/a", "NA", "-")
            or cand_obj_str in ("N/A", "n/a", "NA", "-")
        ):
            return cls._create_evaluation(
                candidate=candidate,
                envelope=envelope,
                claim_type=claim_type,
                source_match=source_match,
                completeness=completeness,
                meaning=DimensionEvaluation(
                    dimension_name="meaning",
                    status="fail",
                    score=0.0,
                    passed=False,
                    reason="Matrix bullet/glyph symbol object has no textual semantic content.",
                ),
                scope=scope,
                time_eval=time_eval,
                authority=authority,
                review_trigger=review_trigger,
                composite_score=0.0,
                decision=ClaimLifecycleDecision.REJECT,
                decision_code=DecisionCode.FRAGMENT_ASSERTION_DISCARDED,
                reason="REJECTED: Non-semantic matrix bullet symbol object.",
            )
        # Invariant Knockout 1: Evidence-Candidate Association Mismatch
        source_uid = getattr(candidate, "source_unit_id", None) or getattr(candidate, "unit_id", None)
        ev_id = getattr(candidate, "evidence_id", None)
        if source_uid and ev_id:
            clean_ev_id = ev_id.removeprefix("ev:")
            if clean_ev_id != source_uid and not clean_ev_id.startswith(f"{source_uid}:"):
                decision = ClaimLifecycleDecision.REJECT
                decision_code = DecisionCode.EVIDENCE_CANDIDATE_MISMATCH
                reason = f"REJECTED: Evidence pointer mismatch. Candidate source unit '{source_uid}' does not match evidence unit '{ev_id}'."
                return cls._create_evaluation(
                    candidate=candidate,
                    envelope=envelope,
                    claim_type=claim_type,
                    source_match=DimensionEvaluation(
                        dimension_name="source_match",
                        status="fail",
                        score=0.0,
                        passed=False,
                        reason=f"Evidence pointer mismatch: {source_uid} != {ev_id}",
                    ),
                    completeness=completeness,
                    meaning=meaning,
                    scope=scope,
                    time_eval=time_eval,
                    authority=authority,
                    review_trigger=review_trigger,
                    composite_score=0.0,
                    decision=decision,
                    decision_code=decision_code,
                    reason=reason,
                )

        # Invariant Knockout 2: Table Grid Binding Row Value Mismatch
        tb = getattr(candidate, "table_binding", None)
        if tb:
            val = getattr(candidate, "value", None)
            val_mismatch = False
            if val is not None and tb.normalized_value is not None:
                if str(val).strip().lower() != str(tb.normalized_value).strip().lower():
                    val_mismatch = True
            elif val is not None and tb.cell_value:
                val_str = str(val).strip().lower()
                cell_str = tb.cell_value.strip().lower()
                norm_str = str(tb.normalized_value).strip().lower() if tb.normalized_value is not None else ""
                if val_str not in cell_str and val_str != norm_str:
                    val_mismatch = True

            if val_mismatch:
                decision = ClaimLifecycleDecision.REJECT
                decision_code = DecisionCode.ROW_VALUE_MISMATCH
                reason = (
                    f"REJECTED: Table row value mismatch. Candidate extracted value '{val}' "
                    f"contradicts table grid cell '{tb.cell_value}' (normalized: '{tb.normalized_value}') "
                    f"for row '{tb.row_key}' column '{tb.column_header}'."
                )
                return cls._create_evaluation(
                    candidate=candidate,
                    envelope=envelope,
                    claim_type=claim_type,
                    source_match=source_match,
                    completeness=completeness,
                    meaning=meaning,
                    scope=scope,
                    time_eval=time_eval,
                    authority=authority,
                    review_trigger=review_trigger,
                    composite_score=0.0,
                    decision=decision,
                    decision_code=decision_code,
                    reason=reason,
                )

        # 5. Synthesize Claim Lifecycle Decision & Machine-Readable Cause Code
        if claim_type == "descriptive_purpose":
            decision = ClaimLifecycleDecision.REJECT
            decision_code = DecisionCode.REJECT_DESCRIPTIVE_PURPOSE
            reason = "REJECTED: Descriptive purpose/preamble statement; non-normative context cannot be enforced as an operative constraint."
        # Fatal rules -> Hard REJECT
        elif not completeness.passed and completeness.details.get("decision_code") == "QUESTION_NOT_ASSERTION":
            decision = ClaimLifecycleDecision.REJECT
            decision_code = DecisionCode.QUESTION_NOT_ASSERTION
            reason = f"REJECTED: {completeness.reason}"
        elif not completeness.passed and completeness.details.get("decision_code") == "EXAMPLE_NON_CANONICAL":
            decision = ClaimLifecycleDecision.REJECT
            decision_code = DecisionCode.EXAMPLE_NON_CANONICAL
            reason = f"REJECTED: {completeness.reason}"
        elif not completeness.passed and completeness.details.get("decision_code") == "DEFINITION_FRAGMENT":
            decision = ClaimLifecycleDecision.REJECT
            decision_code = DecisionCode.DEFINITION_FRAGMENT
            reason = f"REJECTED: {completeness.reason}"
        elif not completeness.passed and completeness.details.get("decision_code") == "HEADING_NON_CANONICAL":
            decision = ClaimLifecycleDecision.REJECT
            decision_code = DecisionCode.HEADING_NON_CANONICAL
            reason = f"REJECTED: {completeness.reason}"
        elif not completeness.passed and completeness.details.get("decision_code") == "SUBJECT_CONTAMINATION":
            decision = ClaimLifecycleDecision.REJECT
            decision_code = DecisionCode.SUBJECT_CONTAMINATION
            reason = f"REJECTED: {completeness.reason}"
        elif not completeness.passed and completeness.details.get("decision_code") == "INCOMPLETE_ASSERTION":
            decision = ClaimLifecycleDecision.REJECT
            decision_code = DecisionCode.INCOMPLETE_ASSERTION
            reason = f"REJECTED: {completeness.reason}"
        elif not completeness.passed and completeness.details.get("decision_code") == "SUBJECT_NORMALIZATION_FAILED":
            decision = ClaimLifecycleDecision.REVIEW
            decision_code = DecisionCode.SUBJECT_NORMALIZATION_FAILED
            reason = f"REVIEW: {completeness.reason}"
        elif not completeness.passed and completeness.details.get("decision_code") == "CONTACT_INFO_NON_CANONICAL":
            decision = ClaimLifecycleDecision.REVIEW
            decision_code = DecisionCode.CONTACT_INFO_NON_CANONICAL
            reason = f"REVIEW: {completeness.reason}"
        elif not completeness.passed and "fragment detected" in str(completeness.reason).lower():
            decision = ClaimLifecycleDecision.REJECT
            decision_code = DecisionCode.FRAGMENT_ASSERTION_DISCARDED
            reason = f"REJECTED: Fragment discarded. {completeness.reason}"
        elif claim_type in ("derived_summary", "SUMMARY_NON_CANONICAL", "EXAMPLE", "example", "CONTACT_INFORMATION", "contact_info") or not getattr(candidate, "is_canonical", True):
            decision = ClaimLifecycleDecision.REVIEW
            decision_code = DecisionCode.SUMMARY_NON_CANONICAL if (claim_type in ("SUMMARY_NON_CANONICAL", "derived_summary") or not getattr(candidate, "is_canonical", True)) else DecisionCode.REVIEW_DERIVED_SUMMARY
            reason = "NON-CANONICAL CONTEXT: Retained for overview display; excluded from active decision gate to prevent duplicate evaluation against atomic row claims."
        elif not source_match.passed:
            decision = ClaimLifecycleDecision.REJECT
            decision_code = DecisionCode.REJECT_GROUNDING_FAILED
            reason = f"REJECTED: Grounding failure. {source_match.reason}"
        elif not scope.passed:
            decision = ClaimLifecycleDecision.REJECT
            decision_code = DecisionCode.REJECT_SCOPE_VIOLATION
            reason = f"REJECTED: Scope violation. {scope.reason}"
        elif not meaning.passed and ("Subject-Evidence mismatch" in meaning.reason or meaning.status == "unsupported"):
            decision = ClaimLifecycleDecision.REJECT
            decision_code = DecisionCode.REJECT_SEMANTIC_MISMATCH
            reason = f"REJECTED: Semantic grounding failure. {meaning.reason}"
        # HITL rules -> REVIEW
        elif needs_review or composite_score < cls.AUTO_APPROVE_THRESHOLD:
            decision = ClaimLifecycleDecision.REVIEW
            if completeness.details.get("decision_code") == "WEAK_PREDICATE":
                decision_code = DecisionCode.WEAK_PREDICATE
            elif completeness.details.get("decision_code") == "META_RULE_NOT_ATOMIC":
                decision_code = DecisionCode.META_RULE_NOT_ATOMIC
            elif completeness.details.get("unsupported_conditions"):
                decision_code = DecisionCode.UNSUPPORTED_CONDITION
            elif getattr(candidate, "is_ambiguous", False) or (tb and tb.is_merged_cell):
                decision_code = DecisionCode.TABLE_CELL_AMBIGUITY if (tb and tb.is_merged_cell) else DecisionCode.REVIEW_AMBIGUITY_FLAGGED
            elif not meaning.passed:
                decision_code = DecisionCode.REVIEW_UNCERTAIN_MEANING
            elif not completeness.passed:
                decision_code = DecisionCode.REVIEW_PARTIAL_COMPLETENESS
            elif not authority.passed:
                decision_code = DecisionCode.REVIEW_NON_AUTHORITATIVE
            elif not time_eval.passed:
                decision_code = DecisionCode.REVIEW_STALE_EVIDENCE
            else:
                decision_code = DecisionCode.REVIEW_SCORE_BELOW_THRESHOLD

            reasons = []
            if completeness.details.get("unsupported_conditions"): reasons.append(completeness.reason)
            elif not meaning.passed: reasons.append(meaning.reason)
            elif not completeness.passed: reasons.append(completeness.reason)
            if not authority.passed: reasons.append(authority.reason)
            if not time_eval.passed: reasons.append(time_eval.reason)
            if composite_score < cls.AUTO_APPROVE_THRESHOLD: reasons.append(f"Trust score {composite_score:.2f} is below {cls.AUTO_APPROVE_THRESHOLD} auto-approval threshold")
            reason = f"REVIEW: Human review recommended. {'; '.join(reasons)}"
        # All passed -> APPROVE
        else:
            decision = ClaimLifecycleDecision.APPROVE
            decision_code = DecisionCode.APPROVE_ALL_PASSED
            reason = f"APPROVED: All 6 dimensions verified. Trust score: {composite_score * 100:.1f}%."

        return cls._create_evaluation(
            candidate=candidate,
            envelope=envelope,
            claim_type=claim_type,
            source_match=source_match,
            completeness=completeness,
            meaning=meaning,
            scope=scope,
            time_eval=time_eval,
            authority=authority,
            review_trigger=review_trigger,
            composite_score=composite_score,
            decision=decision,
            decision_code=decision_code,
            reason=reason,
        )

    @classmethod
    def _create_evaluation(
        cls,
        candidate: CandidateClaim,
        envelope: CanonicalSourceEnvelope,
        claim_type: str,
        source_match: DimensionEvaluation,
        completeness: DimensionEvaluation,
        meaning: DimensionEvaluation,
        scope: DimensionEvaluation,
        time_eval: DimensionEvaluation,
        authority: DimensionEvaluation,
        review_trigger: DimensionEvaluation,
        composite_score: float,
        decision: ClaimLifecycleDecision,
        decision_code: DecisionCode,
        reason: str,
    ) -> CandidateGateEvaluation:
        return CandidateGateEvaluation(
            candidate_id=candidate.candidate_id,
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            claim_text=candidate.claim_text,
            subject=candidate.subject,
            predicate=candidate.predicate,
            object_=candidate.object or "",
            object=candidate.object or "",
            evidence_text_span=candidate.evidence_text_span,
            claim_type=claim_type,
            modality=getattr(candidate, "modality", "POLICY_FACT"),
            conditions=getattr(candidate, "conditions", []),
            value=getattr(candidate, "value", None),
            unit=getattr(candidate, "unit", None),
            scope=getattr(candidate, "scope", {}),
            locator=getattr(candidate, "locator", {}),
            is_ambiguous=getattr(candidate, "is_ambiguous", False),
            ambiguity_reason=getattr(candidate, "ambiguity_reason", None),
            source_match=source_match,
            completeness=completeness,
            meaning=meaning,
            scope_eval=scope,
            time=time_eval,
            authority=authority,
            review_trigger=review_trigger,
            composite_trust_score=composite_score,
            lifecycle_decision=decision,
            decision_code=decision_code,
            decision_reason=reason,
        )
