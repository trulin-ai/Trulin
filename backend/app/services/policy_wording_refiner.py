"""
Policy Wording Refiner Service.

A strictly constrained, optional wording layer that polishes deterministic policy answers:
1. Operates only on already-synthesized PolicyAnswerContract instances.
2. Zero new facts: prompt strictly prohibits inventing claims, numbers, dates, or exceptions.
3. Citation preservation: requires preserving all [Source X] references verbatim.
4. Fail-closed abstentions: completely bypasses LLM for NO_VERIFIED_RULE and UNVERIFIED states.
5. Strict post-verification: validates output through AnswerVerifier.verify().
6. Fail-safe: if LLM fails, times out, or fails verification, immediately returns deterministic Markdown.
"""

import logging
import re
from typing import Any, Optional, Tuple

from app.core.config import settings
from app.llm.base import BaseLLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.schemas.chat import PolicyAnswerContract
from app.services.answer_verifier import AnswerVerifier
from app.services.policy_answer_synthesizer import PolicyAnswerSynthesizer

logger = logging.getLogger(__name__)

WORDING_REFINER_SYSTEM_PROMPT = (
    "You are an executive wording assistant for an enterprise governance copilot.\n"
    "Your ONLY job is to improve the readability, polish, and professional tone of the provided policy answer.\n\n"
    "CRITICAL CONSTRAINTS (ZERO-HALLUCINATION CONTRACT):\n"
    "1. FACTUAL BOUNDARY: Use ONLY the exact facts, numbers, windows, and entities present in the input text.\n"
    "2. NO INVENTED ENTITIES: Never introduce new dates, dollar amounts, percentages, timelines, or obligations.\n"
    "3. CITATION PRESERVATION: Preserve every citation tag like [Source 1], [Source 2] verbatim in the output.\n"
    "4. NO SPECULATION: Do not infer, generalize, or extrapolate beyond what is explicitly stated.\n"
    "5. PRESERVE CONFLICTS: If multiple policy pathways or conflicting terms are mentioned, you must preserve the distinction and NEVER choose one side over another.\n"
    "6. CONCISE & EXECUTIVE: Deliver a clear, direct bottom-line response in 1-3 sentences.\n"
)


class PolicyWordingRefiner:
    """Constrained post-synthesis wording refiner with automated fail-safe fallbacks."""

    @classmethod
    async def refine_contract(
        cls,
        contract: PolicyAnswerContract,
        citations: list[dict[str, Any]],
        has_conflicts: bool = False,
        llm_provider: Optional[BaseLLMProvider] = None,
        enabled: Optional[bool] = None,
    ) -> Tuple[PolicyAnswerContract, str]:
        """
        Refines the wording of a PolicyAnswerContract.
        Returns a tuple of:
          - (updated_contract, final_markdown_answer)
        If refinement is disabled, bypassed, fails, or fails verification, returns the original
        contract and PolicyAnswerSynthesizer.render_markdown(contract).
        """
        deterministic_markdown = PolicyAnswerSynthesizer.render_markdown(contract)

        is_enabled = enabled if enabled is not None else getattr(settings, "enable_llm_wording_refinement", True)
        if not is_enabled:
            return contract, deterministic_markdown

        # 1. Fail-closed: Never run LLM on abstention or unverified states
        if contract.verification_status in ("NO_VERIFIED_RULE", "UNVERIFIED"):
            return contract, deterministic_markdown

        # 2. Check provider availability
        if llm_provider is None or getattr(llm_provider, "_model_unavailable", False):
            return contract, deterministic_markdown

        # If MockLLMProvider is in use without custom mock completion, use deterministic answer
        if isinstance(llm_provider, MockLLMProvider) and not hasattr(llm_provider, "mock_completion_text"):
            return contract, deterministic_markdown

        # 3. Construct zero-hallucination prompt
        conditions_str = ""
        if contract.conditions:
            conditions_str += "\nConditions:\n" + "\n".join(f"- {c}" for c in contract.conditions)
        if contract.exceptions:
            conditions_str += "\nExceptions:\n" + "\n".join(f"- {e}" for e in contract.exceptions)

        user_prompt = (
            f"Draft Answer: {contract.bottom_line_answer}"
            f"{conditions_str}\n\n"
            "Rewrite the draft answer for executive clarity while strictly preserving all facts, numbers, and [Source X] tags exactly."
        )

        try:
            if hasattr(llm_provider, "generate_completion"):
                rewritten = await llm_provider.generate_completion(
                    prompt=user_prompt,
                    system_prompt=WORDING_REFINER_SYSTEM_PROMPT,
                    max_tokens=250,
                    temperature=0.0,
                )
            elif hasattr(llm_provider, "mock_completion_text"):
                rewritten = getattr(llm_provider, "mock_completion_text")
            else:
                return contract, deterministic_markdown

            # Clean output preamble if any
            rewritten = re.sub(
                r"^(?:Here is (?:the|a) (?:rewritten|clarified|polished|revised) (?:answer|response):?\s*)",
                "",
                rewritten.strip(),
                flags=re.IGNORECASE,
            ).strip('"` \n')

            if not rewritten or len(rewritten) < 15:
                logger.warning("LLM wording refinement produced empty or trivial response; using deterministic contract.")
                return contract, deterministic_markdown

            # 4. Strict Post-Verification Gate
            verification = AnswerVerifier.verify(
                synthesized_answer=rewritten,
                citations=citations,
                has_conflicts=has_conflicts,
                mode="document_qa",
            )

            # Check 1: Verification status
            if not verification.is_verified:
                logger.warning(
                    "LLM wording failed verification (status=%s, warnings=%s); falling back to deterministic answer.",
                    verification.verification_status,
                    verification.hallucination_warnings,
                )
                return contract, deterministic_markdown

            # Check 2: Ungrounded numbers, percentages, durations
            if verification.unverified_numbers:
                logger.warning(
                    "LLM wording introduced ungrounded numbers (%s); falling back to deterministic answer.",
                    verification.unverified_numbers,
                )
                return contract, deterministic_markdown

            # Check 3: Invalid source indices
            if verification.invalid_source_indices:
                logger.warning(
                    "LLM wording referenced non-existent sources (%s); falling back to deterministic answer.",
                    verification.invalid_source_indices,
                )
                return contract, deterministic_markdown

            # Check 4: Citation dropping - if input answer had citations, output must cite at least one valid source
            if citations and not verification.cited_source_indices:
                logger.warning(
                    "LLM wording omitted all citations; falling back to deterministic answer."
                )
                return contract, deterministic_markdown

            # 5. Success: update contract with polished wording and re-render
            contract.bottom_line_answer = rewritten
            refined_markdown = PolicyAnswerSynthesizer.render_markdown(contract)
            logger.info("Successfully refined answer wording with verified LLM output.")
            return contract, refined_markdown

        except Exception as e:
            logger.warning("LLM wording refinement call raised exception (%s); safely falling back to deterministic answer.", e)
            return contract, deterministic_markdown
