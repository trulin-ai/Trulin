"""
Policy Wording Refiner Service.

A strictly constrained, optional wording layer that polishes deterministic policy answers:
1. Operates only on already-synthesized PolicyAnswerContract instances.
2. Structured statement-level rewriting: provides statement IDs and demands JSON output.
3. Zero new facts: prompt strictly prohibits inventing claims, numbers, dates, or exceptions.
4. Citation preservation: requires preserving all [Source X] references verbatim.
5. Fail-closed abstentions: completely bypasses LLM for NO_VERIFIED_RULE and UNVERIFIED states.
6. Strict post-verification: validates each statement through AnswerVerifier.verify_statement_mutation()
   to prevent negation flips, modality changes, or dropped numbers.
7. Fail-safe: if LLM fails, times out, or fails verification, immediately returns deterministic Markdown.
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.core.config import settings
from app.llm.base import BaseLLMProvider
from app.llm.mock_provider import MockLLMProvider
from app.schemas.chat import PolicyAnswerContract
from app.services.answer_verifier import AnswerVerifier
from app.services.policy_answer_synthesizer import PolicyAnswerSynthesizer

logger = logging.getLogger(__name__)

WORDING_REFINER_SYSTEM_PROMPT = (
    "You are an executive wording assistant for an enterprise governance copilot.\n"
    "Your ONLY job is to improve the readability, polish, and professional tone of the provided policy statements.\n\n"
    "CRITICAL CONSTRAINTS (ZERO-MUTATION CONTRACT):\n"
    "1. FACTUAL BOUNDARY: Use ONLY the exact facts, numbers, windows, and entities present in the input.\n"
    "2. NO INVENTED ENTITIES: Never introduce new dates, dollar amounts, percentages, timelines, or obligations.\n"
    "3. CITATION PRESERVATION: Preserve every citation tag like [Source 1], [Source 2] verbatim.\n"
    "4. MODALITY PRESERVATION: Never change permission ('may') to obligation ('must'), or vice-versa.\n"
    "5. NEGATION PRESERVATION: Never remove or introduce negations ('not', 'cannot', 'prohibited', 'unless').\n"
    "6. STRUCTURED OUTPUT: Return ONLY a valid JSON object matching this schema:\n"
    "   {\"statements\": [{\"id\": \"stmt-1\", \"text\": \"Polished statement [Source 1]\"}]}\n"
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

        # 3. Handle Structured Statement Rewriting if explanation_blocks exist
        if contract.explanation_blocks:
            normative_statements = [
                s for b in contract.explanation_blocks
                for s in b.statements
                if s.is_normative
            ]

            if normative_statements:
                statements_payload = [
                    {"id": s.id, "text": s.text, "modality": s.modality}
                    for s in normative_statements
                ]

                user_prompt = (
                    f"Scope: {contract.scope_summary.label if contract.scope_summary else 'Governing Policy'}\n"
                    f"Input Statements:\n{json.dumps(statements_payload, indent=2)}\n\n"
                    "Rewrite each statement for executive readability while strictly preserving all facts, numbers, modality, conditions, and [Source X] tags.\n"
                    "Return ONLY valid JSON matching: {\"statements\": [{\"id\": \"stmt-id\", \"text\": \"...\"}]}"
                )

                try:
                    if hasattr(llm_provider, "generate_completion"):
                        raw_completion = await llm_provider.generate_completion(
                            prompt=user_prompt,
                            system_prompt=WORDING_REFINER_SYSTEM_PROMPT,
                            max_tokens=400,
                            temperature=0.0,
                        )
                    elif hasattr(llm_provider, "mock_completion_text"):
                        raw_completion = getattr(llm_provider, "mock_completion_text")
                    else:
                        return contract, deterministic_markdown

                    # Parse JSON from completion
                    cleaned_completion = raw_completion.strip()
                    # Extract json block if wrapped in markdown code fence
                    json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned_completion)
                    if json_match:
                        cleaned_completion = json_match.group(1).strip()

                    parsed_data = None
                    try:
                        parsed_data = json.loads(cleaned_completion)
                    except Exception:
                        # Fallback heuristic: search for {"statements": ...}
                        dict_match = re.search(r"(\{[\s\S]*\"statements\"[\s\S]*\})", cleaned_completion)
                        if dict_match:
                            try:
                                parsed_data = json.loads(dict_match.group(1))
                            except Exception:
                                pass

                    if not parsed_data or not isinstance(parsed_data, dict) or "statements" not in parsed_data:
                        logger.warning("LLM wording refinement produced non-JSON output; safely using deterministic contract.")
                        contract.wording_metadata = {"requested": True, "applied": False, "fallback_reason": "invalid_json_format"}
                        return contract, deterministic_markdown

                    rewritten_list = parsed_data.get("statements", [])
                    rewritten_map = {item.get("id"): item.get("text") for item in rewritten_list if isinstance(item, dict) and item.get("id") and item.get("text")}

                    applied_count = 0
                    fallback_reasons = []

                    # Verify and apply rewrites statement by statement
                    for stmt in normative_statements:
                        new_text = rewritten_map.get(stmt.id)
                        if not new_text:
                            continue

                        is_safe, reason = AnswerVerifier.verify_statement_mutation(
                            original_text=stmt.text,
                            rewritten_text=new_text,
                            required_modality=stmt.modality,
                        )

                        if is_safe:
                            stmt.text = new_text
                            applied_count += 1
                            # If stmt-1 was bottom-line, update bottom-line too
                            if stmt.id == "stmt-1":
                                contract.bottom_line_answer = new_text
                        else:
                            fallback_reasons.append(f"{stmt.id}: {reason}")
                            logger.warning("Statement %s rejected: %s", stmt.id, reason)

                    if applied_count > 0:
                        contract.wording_metadata = {
                            "requested": True,
                            "applied": True,
                            "statements_polished": applied_count,
                            "rejected_mutations": fallback_reasons,
                        }
                        refined_markdown = PolicyAnswerSynthesizer.render_markdown(contract)
                        logger.info("Successfully polished %d statements in answer contract.", applied_count)
                        return contract, refined_markdown
                    else:
                        contract.wording_metadata = {
                            "requested": True,
                            "applied": False,
                            "fallback_reason": "all_statements_failed_mutation_verification",
                            "details": fallback_reasons,
                        }
                        return contract, deterministic_markdown

                except Exception as e:
                    logger.warning("LLM structured wording refinement failed (%s); returning deterministic contract.", e)
                    contract.wording_metadata = {"requested": True, "applied": False, "fallback_reason": str(e)}
                    return contract, deterministic_markdown

        # 4. Fallback for contracts without explanation_blocks (legacy V1 path)
        user_prompt = (
            f"Draft Answer: {contract.bottom_line_answer}\n\n"
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

            rewritten = re.sub(
                r"^(?:Here is (?:the|a) (?:rewritten|clarified|polished|revised) (?:answer|response):?\s*)",
                "",
                rewritten.strip(),
                flags=re.IGNORECASE,
            ).strip('"` \n')

            if not rewritten or len(rewritten) < 15:
                return contract, deterministic_markdown

            is_safe, reason = AnswerVerifier.verify_statement_mutation(
                original_text=contract.bottom_line_answer,
                rewritten_text=rewritten,
            )
            if not is_safe:
                logger.warning("LLM wording rejected by mutation verifier (%s); falling back to deterministic answer.", reason)
                contract.wording_metadata = {"requested": True, "applied": False, "fallback_reason": reason}
                return contract, deterministic_markdown

            contract.bottom_line_answer = rewritten
            contract.wording_metadata = {"requested": True, "applied": True}
            refined_markdown = PolicyAnswerSynthesizer.render_markdown(contract)
            return contract, refined_markdown

        except Exception as e:
            logger.warning("LLM wording refinement call raised exception (%s); safely falling back to deterministic answer.", e)
            contract.wording_metadata = {"requested": True, "applied": False, "fallback_reason": str(e)}
            return contract, deterministic_markdown
