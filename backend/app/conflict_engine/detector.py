import decimal
import re
import uuid
import asyncio
from typing import Sequence

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.conflict_engine.compatibility_gate import CompatibilityGate
from app.conflict_engine.facet_sharder import FacetSharder
from app.conflict_engine.multi_agent_arbiter import MultiAgentArbiter
from app.conflict_engine.precedence_engine import PrecedenceEngine
from app.db.enums import ClaimStatus, ConflictStatus, ConflictType
from app.db.models.claim import Claim
from app.db.models.claim_conflict import ClaimConflict
from app.ingestion.parsers.evidence_model import ContentRole
from app.llm.base import BaseLLMProvider
from app.llm.factory import get_llm_provider
from app.llm.schemas import ContradictionResult


STOPWORDS = {
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "aren't", "as", "at", "be", "because", "been", "before", "being",
    "below", "between", "both", "but", "by", "can", "can't", "cannot", "could",
    "couldn't", "did", "didn't", "do", "does", "doesn't", "doing", "don't", "down",
    "during", "each", "few", "for", "from", "further", "had", "hadn't", "has",
    "hasn't", "have", "haven't", "having", "he", "he'd", "he'll", "he's", "her",
    "here", "here's", "hers", "herself", "him", "himself", "his", "how", "how's",
    "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", "isn't", "it",
    "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my",
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other",
    "ought", "our", "ours", "ourselves", "out", "over", "own", "same", "shan't",
    "she", "she'd", "she'll", "she's", "should", "shouldn't", "so", "some", "such",
    "than", "that", "that's", "the", "their", "theirs", "them", "themselves",
    "then", "there", "there's", "these", "they", "they'd", "they'll", "they're",
    "they've", "this", "those", "through", "to", "too", "under", "until", "up",
    "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were",
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which",
    "while", "who", "who's", "whom", "why", "why's", "with", "won't", "would",
    "wouldn't", "you", "you'd", "you'll", "you're", "you've", "your", "yours",
    "page", "section", "document", "policy", "requirement", "standard", "rule",
    "item", "clause", "specified", "specifies", "accordance", "following", "general",
    "total", "part", "details", "described", "provides", "including", "also", "per",
    "one", "two", "three", "four", "five", "first", "second", "third", "must", "may"
}


def _extract_content_tokens(text: str) -> set[str]:
    tokens = re.findall(r"[a-z]{3,}", text.lower())
    return {re.sub(r"s$", "", t) for t in tokens} - STOPWORDS


def are_claims_topically_related(claim_a: Claim, claim_b: Claim) -> bool:
    """Pre-filter to determine if two claims share sufficient topical alignment to warrant contradiction checks."""
    # Check subject overlap if both present
    if claim_a.subject and claim_b.subject:
        subj_a = _extract_content_tokens(claim_a.subject)
        subj_b = _extract_content_tokens(claim_b.subject)
        if subj_a and subj_b and subj_a.intersection(subj_b):
            return True

    # Check claim text token overlap
    tokens_a = _extract_content_tokens(claim_a.claim_text)
    tokens_b = _extract_content_tokens(claim_b.claim_text)
    common = tokens_a.intersection(tokens_b)

    # Require at least 2 distinct domain terms in common, or 1 if claims are short (<= 5 tokens)
    min_overlap = 1 if (len(tokens_a) <= 5 or len(tokens_b) <= 5) else 2
    return len(common) >= min_overlap


def is_illustrative_claim(claim: Claim) -> bool:
    """Pillar 2: Classify whether a claim is an illustrative example or hypothetical scenario rather than a normative policy rule."""
    if claim.claim_type and any(k in claim.claim_type.lower() for k in ("illustrative", "example", "sample")):
        return True
    text_lower = (claim.claim_text or "").lower()
    illustrative_patterns = [
        r"\bexample\s*:\s*transaction\b",
        r"\bfor\s+example\b",
        r"\bhypothetical\b",
        r"\bsample\s+transaction\b",
        r"\billustrative\s+only\b",
        r"\brf-\d+-\d+\b",
        r"\bscenario\s+[0-9a-z]+\b",
        r"\bcase\s+[a-z]\b",
        r"\bcase\s+study\b",
    ]
    return any(re.search(p, text_lower) for p in illustrative_patterns)


class ConflictDetector:
    """Detects semantic and logical contradictions between claims across documents."""

    def __init__(
        self,
        session: AsyncSession,
        llm_provider: BaseLLMProvider | None = None,
    ):
        self.session = session
        self.llm = llm_provider or get_llm_provider()

    async def detect_conflicts_for_claim(
        self,
        target_claim: Claim,
    ) -> Sequence[ClaimConflict]:
        """Compare target_claim against all topically related active claims in the same organization."""
        detected_conflicts: list[ClaimConflict] = []

        # Policy-Eligible Filtering: Only active, canonical POLICY_RULE claims can enter governing conflict detection
        target_role = getattr(target_claim, "content_role", ContentRole.POLICY_RULE)
        if target_role not in (ContentRole.POLICY_RULE, "policy_rule", "policy"):
            return detected_conflicts

        if not getattr(target_claim, "is_canonical", True):
            return detected_conflicts

        # Stage 10: Lifecycle & Status Check - Exclude rejected, superseded, and outdated claims
        if getattr(target_claim, "status", None) in (ClaimStatus.REJECTED, ClaimStatus.SUPERSEDED, ClaimStatus.OUTDATED):
            return detected_conflicts

        val_recs = getattr(target_claim, "__dict__", {}).get("validity_records")
        if val_recs is not None and len(val_recs) > 0:
            if not any(getattr(v, "is_current", True) for v in val_recs):
                return detected_conflicts

        # Pillar 2: Illustrative sample & non-canonical summary pre-filter
        # Concrete transaction examples and derived summaries never contradict operative canonical policies
        non_canonical_types = (
            "derived_summary", "summary_non_canonical", "summary", "example", "revision_history",
            "definition", "form_field_specification", "non_canonical", "faq", "faq_question", "faq_answer", "heading",
            "contact_information", "contact_info", "contact_channel",
        )
        target_type = (getattr(target_claim, "claim_type", "") or "").lower()
        if is_illustrative_claim(target_claim) or target_type in non_canonical_types or any(t in target_type for t in ("contact", "summary", "example")):
            return detected_conflicts

        # Tier 1: Candidate Ingestion Pruning via FacetSharder (O(N^2) -> O(K))
        stmt, target_facet = FacetSharder.build_candidate_query(target_claim, limit=100)
        res = await self.session.execute(stmt)
        candidates = res.scalars().all()

        unprocessed_candidates = []
        for cand in candidates:
            # Policy-Eligible Filtering on Candidate
            cand_role = getattr(cand, "content_role", ContentRole.POLICY_RULE)
            if cand_role != ContentRole.POLICY_RULE:
                continue

            if not getattr(cand, "is_canonical", True):
                continue

            # Stage 10: Lifecycle & Status Check on Candidate
            if getattr(cand, "status", None) in (ClaimStatus.REJECTED, ClaimStatus.SUPERSEDED, ClaimStatus.OUTDATED):
                continue

            cand_val_recs = getattr(cand, "__dict__", {}).get("validity_records")
            if cand_val_recs is not None and len(cand_val_recs) > 0:
                if not any(getattr(v, "is_current", True) for v in cand_val_recs):
                    continue

            # Pillar 2: Skip illustrative candidates and non-canonical summaries
            cand_type = (getattr(cand, "claim_type", "") or "").lower()
            if is_illustrative_claim(cand) or cand_type in non_canonical_types or any(t in cand_type for t in ("contact", "summary", "example")):
                continue

            # Facet compatibility pruning
            cand_facet = FacetSharder.detect_facet(cand.claim_text)
            if not FacetSharder.are_facets_compatible(target_facet, cand_facet):
                continue

            # Pre-filter out claims that have no topical connection
            if not are_claims_topically_related(target_claim, cand):
                continue

            # Deterministic Pre-LLM Compatibility Gate:
            # Check if decision keys actively compete (predicates, conditions, scopes)
            compat = CompatibilityGate.evaluate_compatibility(target_claim, cand)
            if not compat.is_comparable:
                # Complementary rules, orthogonal predicates, or non-overlapping conditional scopes do NOT contradict
                continue

            # Check if conflict already logged for this pair
            pair_stmt = select(ClaimConflict).where(
                or_(
                    (ClaimConflict.claim_a_id == target_claim.id) & (ClaimConflict.claim_b_id == cand.id),
                    (ClaimConflict.claim_a_id == cand.id) & (ClaimConflict.claim_b_id == target_claim.id),
                )
            )
            pair_res = await self.session.execute(pair_stmt)
            if not pair_res.scalar_one_or_none():
                unprocessed_candidates.append(cand)

        if not unprocessed_candidates:
            return detected_conflicts

        # Evaluate candidate pairs in PARALLEL via asyncio.gather
        async def _eval_pair(cand):
            # Fast-path: Check deterministic scalar/unit contradiction before calling LLM
            is_val_conflict, val_conflict_type = CompatibilityGate.evaluate_value_conflict(target_claim, cand)
            if is_val_conflict:
                eval_res = ContradictionResult(
                    is_contradiction=True,
                    conflict_type=val_conflict_type,
                    severity="high",
                    confidence=0.98,
                    reasoning="Deterministic numeric or deontic contradiction on competing decision keys.",
                )
                return cand, eval_res
            elif val_conflict_type == "MATCHING_VALUES":
                eval_res = ContradictionResult(
                    is_contradiction=False,
                    conflict_type="compatible_values",
                    severity="low",
                    confidence=0.99,
                    reasoning="Identical scalar values and units on competing decision keys.",
                )
                return cand, eval_res

            # Ambiguous or natural-language conditions: Delegate to LLM
            eval_res = await self.llm.evaluate_contradiction(
                claim_a_text=target_claim.claim_text,
                claim_b_text=cand.claim_text,
            )
            return cand, eval_res

        eval_results = await asyncio.gather(
            *[_eval_pair(cand) for cand in unprocessed_candidates],
            return_exceptions=False,
        )

        for cand, eval_res in eval_results:
            if eval_res.is_contradiction:
                # 1. Deterministic Enterprise Precedence Engine
                precedence = PrecedenceEngine.evaluate_precedence(target_claim, cand, eval_res)

                if precedence.is_auto_resolved:
                    if precedence.is_compatible_exception:
                        # Specialized tier exception co-exists with baseline standard
                        continue

                    # Winner / Loser determined deterministically
                    winner_id = precedence.winner_claim_id
                    winner_claim = target_claim if winner_id == target_claim.id else cand
                    loser_claim = cand if winner_id == target_claim.id else target_claim

                    # State machine: Never promote candidate or OCR claim to verified automatically
                    if winner_claim.status == ClaimStatus.CANDIDATE or getattr(winner_claim, "claim_type", "").lower() in ("ocr", "candidate", "provisional"):
                        winner_claim.status = ClaimStatus.CANDIDATE
                    else:
                        winner_claim.status = ClaimStatus.VERIFIED

                    is_super = precedence.precedence_rule in ("EXPLICIT_SUPERSESSION", "TEMPORAL_VERSION_PRECEDENCE")
                    loser_claim.status = ClaimStatus.SUPERSEDED if is_super else ClaimStatus.OUTDATED

                    c_type = ConflictType.normalize(precedence.conflict_type or eval_res.conflict_type).value
                    # Record conflict as auto-resolved with full audit provenance
                    conflict = ClaimConflict(
                        claim_a_id=target_claim.id,
                        claim_b_id=cand.id,
                        conflict_type=c_type,
                        severity=eval_res.severity,
                        confidence=decimal.Decimal(f"{eval_res.confidence:.4f}"),
                        resolution_status=ConflictStatus.RESOLVED,
                        resolved_claim_id=winner_id,
                        conflicting_fields=precedence.conflicting_fields,
                        supporting_evidence=precedence.supporting_evidence,
                        source_authority=precedence.source_authority,
                        applicable_scope=precedence.applicable_scope,
                        effective_dates=precedence.effective_dates,
                        resolution_rationale=precedence.reasoning,
                    )
                    self.session.add(conflict)
                    detected_conflicts.append(conflict)
                    continue

                # 2. Tier 4: Multi-Agent Consensus Arbiter (Prosecutor, Defender, Supreme Judge)
                sev_weights = {"CRITICAL": 80, "HIGH": 50, "MEDIUM": 25, "LOW": 10}
                base_w = sev_weights.get(str(eval_res.severity).upper(), 25)
                impact_est = base_w * float(eval_res.confidence)

                dummy_conf = ClaimConflict(
                    claim_a_id=target_claim.id,
                    claim_b_id=cand.id,
                    conflict_type=ConflictType.normalize(eval_res.conflict_type).value,
                    severity=eval_res.severity,
                    confidence=decimal.Decimal(f"{eval_res.confidence:.4f}"),
                )
                arb_verdict = MultiAgentArbiter.evaluate_arbitration(
                    conflict=dummy_conf,
                    claim_a=target_claim,
                    claim_b=cand,
                    impact_score=impact_est,
                )

                if arb_verdict.is_auto_arbitrated:
                    winner_id = arb_verdict.winner_claim_id
                    winner_claim = target_claim if winner_id == target_claim.id else cand
                    loser_claim = cand if winner_id == target_claim.id else target_claim

                    if winner_claim.status == ClaimStatus.VERIFIED or (getattr(winner_claim, "is_canonical", False) and winner_claim.status not in (ClaimStatus.CANDIDATE, ClaimStatus.REJECTED)):
                        winner_claim.status = ClaimStatus.VERIFIED
                    else:
                        winner_claim.status = ClaimStatus.CANDIDATE

                    loser_claim.status = ClaimStatus.OUTDATED

                    conflict = ClaimConflict(
                        claim_a_id=target_claim.id,
                        claim_b_id=cand.id,
                        conflict_type=ConflictType.normalize(eval_res.conflict_type).value,
                        severity=eval_res.severity,
                        confidence=decimal.Decimal(f"{arb_verdict.confidence:.4f}"),
                        resolution_status=ConflictStatus.RESOLVED,
                        resolved_claim_id=winner_id,
                        conflicting_fields=precedence.conflicting_fields,
                        supporting_evidence=precedence.supporting_evidence,
                        source_authority=precedence.source_authority,
                        applicable_scope=precedence.applicable_scope,
                        effective_dates=precedence.effective_dates,
                        resolution_rationale=arb_verdict.judge_verdict or arb_verdict.rationale,
                    )
                    self.session.add(conflict)
                    detected_conflicts.append(conflict)
                    continue

                # 3. Truly Ambiguous, Exception, or Critical Blast Contradictions -> Queued for Human Review
                if eval_res and eval_res.conflict_type in ("INCOMPATIBLE_NUMERIC_VALUE", "CONTRADICTORY_POLICY_RULES"):
                    c_type = eval_res.conflict_type
                else:
                    c_type = ConflictType.normalize(precedence.conflict_type or eval_res.conflict_type).value
                conflict = ClaimConflict(
                    claim_a_id=target_claim.id,
                    claim_b_id=cand.id,
                    conflict_type=c_type,
                    severity=eval_res.severity,
                    confidence=decimal.Decimal(f"{eval_res.confidence:.4f}"),
                    resolution_status=ConflictStatus.HUMAN_REVIEW_REQUIRED,
                    conflicting_fields=precedence.conflicting_fields,
                    supporting_evidence=precedence.supporting_evidence,
                    source_authority=precedence.source_authority,
                    applicable_scope=precedence.applicable_scope,
                    effective_dates=precedence.effective_dates,
                    resolution_rationale=precedence.reasoning,
                )
                self.session.add(conflict)

                target_claim.status = ClaimStatus.CONFLICTED
                cand.status = ClaimStatus.CONFLICTED

                detected_conflicts.append(conflict)

        if detected_conflicts:
            await self.session.flush()

        return detected_conflicts

    async def detect_all_organization_conflicts(
        self,
        organization_id: uuid.UUID,
    ) -> Sequence[ClaimConflict]:
        stmt = select(Claim).where(Claim.organization_id == organization_id)
        res = await self.session.execute(stmt)
        claims = res.scalars().all()

        all_conflicts: list[ClaimConflict] = []
        for claim in claims:
            conflicts = await self.detect_conflicts_for_claim(claim)
            all_conflicts.extend(conflicts)

        return all_conflicts
