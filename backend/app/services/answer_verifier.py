"""
Answer Verifier Service for Copilot Grounding.

Inspects LLM outputs to guarantee evidence-first integrity:
1. Validates all inline [Source X] references against retrieved citations.
2. Cross-checks numerical, currency, duration, and policy entities against source evidence.
3. Identifies omitted conflict caveats when underlying claims are disputed.
4. Computes grounding confidence scores and returns actionable verification telemetry.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AnswerVerificationResult:
    is_verified: bool
    verification_status: str  # "VERIFIED", "PARTIALLY_GROUNDED", "CITATION_MISMATCH", "UNVERIFIED"
    grounding_score: float
    cited_source_indices: list[int] = field(default_factory=list)
    invalid_source_indices: list[int] = field(default_factory=list)
    unverified_numbers: list[str] = field(default_factory=list)
    hallucination_warnings: list[str] = field(default_factory=list)
    disputed_conflict_flagged: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "is_verified": self.is_verified,
            "verification_status": self.verification_status,
            "grounding_score": round(self.grounding_score, 2),
            "cited_source_indices": self.cited_source_indices,
            "invalid_source_indices": self.invalid_source_indices,
            "unverified_numbers": self.unverified_numbers,
            "hallucination_warnings": self.hallucination_warnings,
            "disputed_conflict_flagged": self.disputed_conflict_flagged,
        }


class AnswerVerifier:
    """Enterprise-grade groundedness validator for Copilot responses."""

    # Regex patterns for citations and numerical assertions
    SOURCE_PATTERN = re.compile(r"\[(?:Source\s*)?(\d+)\]", re.IGNORECASE)
    # Extracts amounts ($500, €100), percentages (99.9%), durations (30 days, 24 hours), port numbers
    NUMERIC_ENTITY_PATTERN = re.compile(
        r"(?:\$\s*\d+(?:,\d{3})*(?:\.\d+)?|\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:%|percent|days|hours|minutes|seconds|months|years|port|users|seats|retries|dollars|usd)\b)",
        re.IGNORECASE,
    )

    @classmethod
    def verify(
        cls,
        synthesized_answer: str,
        citations: list[dict[str, Any]],
        has_conflicts: bool = False,
        mode: str = "document_qa",
    ) -> AnswerVerificationResult:
        """
        Validates the synthesized answer against the provided citations.
        """
        if not synthesized_answer or not synthesized_answer.strip():
            return AnswerVerificationResult(
                is_verified=False,
                verification_status="UNVERIFIED",
                grounding_score=0.0,
                hallucination_warnings=["Synthesized answer is empty."],
            )

        lower_ans = synthesized_answer.lower()
        if "no verified rule found" in lower_ans or "no verified policy records" in lower_ans:
            return AnswerVerificationResult(
                is_verified=True,
                verification_status="NO_VERIFIED_RULE",
                grounding_score=1.0,
                cited_source_indices=[],
                invalid_source_indices=[],
                unverified_numbers=[],
                hallucination_warnings=[],
                disputed_conflict_flagged=False,
            )

        num_citations = len(citations)
        warnings: list[str] = []

        # 1. Parse all [Source X] references
        raw_matches = cls.SOURCE_PATTERN.findall(synthesized_answer)
        cited_indices = sorted(list({int(m) for m in raw_matches if m.isdigit()}))

        valid_indices = []
        invalid_indices = []
        for idx in cited_indices:
            if 1 <= idx <= num_citations:
                valid_indices.append(idx)
            else:
                invalid_indices.append(idx)

        if invalid_indices:
            warnings.append(
                f"Answer references non-existent sources: {invalid_indices} (only {num_citations} sources available)."
            )

        # 2. Check citation presence for Document Q&A
        if mode == "document_qa" and num_citations > 0 and not valid_indices:
            # Check if it was an explicit negative response (e.g., "no documentation found")
            lower_ans = synthesized_answer.lower()
            is_unanswerable_stated = any(
                phrase in lower_ans
                for phrase in [
                    "does not specify",
                    "not found",
                    "no policy",
                    "not mentioned",
                    "unclear",
                    "cannot determine",
                    "do not contain",
                ]
            )
            if not is_unanswerable_stated:
                warnings.append(
                    "Answer contains statements without inline citation markers [Source X]."
                )

        # 3. Compile aggregate text of all valid cited sources for entity matching
        cited_evidence_corpus = []
        for idx in valid_indices:
            c = citations[idx - 1]
            cited_evidence_corpus.append(str(c.get("claim_text", "")))
            cited_evidence_corpus.append(str(c.get("verbatim_evidence", "")))
            cited_evidence_corpus.append(str(c.get("evidence_span", "")))
            evidence = c.get("evidence")
            if isinstance(evidence, dict):
                cited_evidence_corpus.append(str(evidence.get("verbatim_quote", "")))
                cited_evidence_corpus.append(str(evidence.get("clause_text", "")))
            elif isinstance(evidence, str):
                cited_evidence_corpus.append(evidence)

        # Also compile all available citations as fallback
        all_evidence_corpus = []
        for c in citations:
            all_evidence_corpus.append(str(c.get("claim_text", "")))
            all_evidence_corpus.append(str(c.get("verbatim_evidence", "")))
            all_evidence_corpus.append(str(c.get("evidence_span", "")))
            evidence = c.get("evidence")
            if isinstance(evidence, dict):
                all_evidence_corpus.append(str(evidence.get("verbatim_quote", "")))
                all_evidence_corpus.append(str(evidence.get("clause_text", "")))
            elif isinstance(evidence, str):
                all_evidence_corpus.append(evidence)

        cited_text_block = " ".join(cited_evidence_corpus).lower()
        all_text_block = " ".join(all_evidence_corpus).lower()

        # 4. Numerical and Entity Groundedness Check
        answer_entities = cls.NUMERIC_ENTITY_PATTERN.findall(synthesized_answer)
        unverified_numbers = []

        for entity in answer_entities:
            clean_entity = entity.strip().lower()
            # Normalize whitespace
            clean_entity_norm = re.sub(r"\s+", " ", clean_entity)

            # Check if this exact entity appears in cited sources or any sources
            if clean_entity_norm not in all_text_block:
                # Also check pure numeric component (e.g. "30" from "30 days")
                numeric_only = re.sub(r"[^\d.]", "", clean_entity_norm)
                if numeric_only and numeric_only not in all_text_block:
                    unverified_numbers.append(entity)

        if unverified_numbers:
            warnings.append(
                f"Found unverified numerical/quantity assertions not present in evidence: {', '.join(unverified_numbers)}"
            )

        # 5. Conflict Acknowledgment Check
        disputed_conflict_flagged = False
        if has_conflicts:
            lower_ans = synthesized_answer.lower()
            dispute_keywords = ["conflict", "dispute", "contradict", "discrepancy", "diverg", "differ", "warning"]
            disputed_conflict_flagged = any(k in lower_ans for k in dispute_keywords)
            if not disputed_conflict_flagged:
                warnings.append(
                    "Retrieved evidence contains active policy conflicts, but the synthesized answer did not highlight this discrepancy."
                )

        # 6. Compute Grounding Score (0.0 to 1.0)
        score = 1.0

        # Penalize for invalid source references
        if invalid_indices:
            score -= 0.35 * min(len(invalid_indices), 2)

        # Penalize for missing citations when evidence exists
        if mode == "document_qa" and num_citations > 0 and not valid_indices:
            score -= 0.30

        # Penalize for unverified quantities
        if unverified_numbers:
            score -= 0.20 * min(len(unverified_numbers), 2)

        # Penalize if conflicts exist but weren't surfaced
        if has_conflicts and not disputed_conflict_flagged:
            score -= 0.25

        score = max(0.0, min(1.0, score))

        # 7. Determine Final Verification Status
        if invalid_indices:
            status = "CITATION_MISMATCH"
            is_verified = False
        elif unverified_numbers:
            status = "PARTIALLY_GROUNDED"
            is_verified = score >= 0.70
        elif not valid_indices and num_citations > 0 and mode == "document_qa":
            status = "PARTIALLY_GROUNDED"
            is_verified = False
        elif score >= 0.80:
            status = "VERIFIED"
            is_verified = True
        elif score >= 0.50:
            status = "PARTIALLY_GROUNDED"
            is_verified = True
        else:
            status = "UNVERIFIED"
            is_verified = False

        return AnswerVerificationResult(
            is_verified=is_verified,
            verification_status=status,
            grounding_score=score,
            cited_source_indices=valid_indices,
            invalid_source_indices=invalid_indices,
            unverified_numbers=unverified_numbers,
            hallucination_warnings=warnings,
            disputed_conflict_flagged=disputed_conflict_flagged,
        )
