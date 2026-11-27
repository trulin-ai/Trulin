import json
import logging
from typing import Sequence

from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import settings
from app.llm.base import BaseLLMProvider
from app.llm.schemas import (
    ClaimExtractionResult,
    ContradictionResult,
    ExtractedClaim,
)

logger = logging.getLogger(__name__)


class LLMClaimExtractionOutput(BaseModel):
    claims: list[ExtractedClaim]


class LLMContradictionOutput(BaseModel):
    is_contradiction: bool
    conflict_type: str
    severity: str
    confidence: float
    reasoning: str


class OpenAIProvider(BaseLLMProvider):
    """OpenAI API & OpenAI-Compatible Gateway Provider (OpenRouter, Ox Alpha, Groq, etc.)."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str = "gpt-4o-mini",
        embedding_model: str = "text-embedding-3-small",
        default_headers: dict[str, str] | None = None,
    ):
        self.api_key = api_key or settings.openai_api_key or settings.openrouter_api_key or "sk-dummy"
        self.base_url = base_url or settings.openai_base_url
        self.model = model or settings.openai_model
        self.embedding_model = embedding_model or settings.openai_embedding_model
        
        client_kwargs: dict = {"api_key": self.api_key}
        if self.base_url:
            client_kwargs["base_url"] = self.base_url
        if default_headers:
            client_kwargs["default_headers"] = default_headers

        self.client = AsyncOpenAI(**client_kwargs)

    async def extract_claims(
        self,
        document_title: str,
        section_title: str,
        section_content: str,
    ) -> ClaimExtractionResult:
        system_prompt = (
            "You are an enterprise knowledge provenance and atomic claim extraction specialist.\n\n"
            "CRITICAL EXTRACTION DIRECTIVES:\n"
            "1. ATOMIC DECOMPOSITION: Split compound sentences into discrete, independent atomic facts. Never lump multiple distinct rules or conditions into one claim.\n"
            "2. ENTITY ANCHORING: Resolve all dangling pronouns ('they', 'it', 'the user', 'employees') using the Document Title and Section Header to ensure the Subject is fully qualified.\n"
            "3. STRUCTURED TRIPLET: Output Subject (entity/policy scope), Predicate (action/relation), Object (bound/value/target).\n"
            "4. MODALITY & TYPE: Set modality to 'MUST' (obligation), 'CAN' (permission), 'CANNOT' (prohibition), or 'IS' (definition). Set claim_type to 'policy', 'technical', 'financial', 'metric', or 'compliance'.\n"
            "5. NUMERIC EXTRACTION: If the claim contains a numerical threshold, duration, or percentage, set numeric_value (e.g. 14.0, 99.9) and numeric_unit ('days', 'percent', 'USD', etc.). Every number must exist verbatim in the text.\n"
            "6. EXACT CITATION: 'evidence_text_span' MUST be an exact verbatim substring from the Content.\n"
            "7. PROPOSITIONAL RIGOR & NOISE FILTER: Extract ONLY substantive, operative claims (rules, requirements, conditions, entitlements, liabilities). NEVER extract Table of Contents entries, page references, section headers, or metadata boilerplate (e.g. 'Points to Remember 5 3.3.', 'Purpose 4 2.', 'Internal Wingify 1').\n"
            "8. TABLE EXTRACTION: If tabular matrix data is present (such as Grade levels vs notice durations), linearize each row into a distinct, complete declarative policy rule."
        )

        user_prompt = (
            f"Document Hierarchy: {document_title} > {section_title}\n\n"
            f"Content to Extract From:\n{section_content}"
        )

        # 1. Attempt OpenAI structured output parsing
        try:
            response = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=LLMClaimExtractionOutput,
                temperature=0.0,
            )
            parsed = response.choices[0].message.parsed
            claims = parsed.claims if parsed else []
            return ClaimExtractionResult(
                claims=claims,
                extraction_model=self.model,
                extraction_method="openai_structured_outputs",
            )
        except Exception as parse_err:
            logger.debug("Structured parse unsupported or failed (%s); trying standard JSON mode", parse_err)

        # 2. Fallback to standard chat completion with JSON mode (compatible with OpenRouter / Ox Alpha)
        try:
            json_system_prompt = (
                f"{system_prompt}\n\n"
                "Return ONLY a valid JSON object with key 'claims':\n"
                '{"claims": [{"claim_text": "...", "subject": "...", "predicate": "...", "object": "...", '
                '"claim_type": "policy|technical|financial|metric|compliance", "modality": "MUST|CAN|CANNOT|IS", '
                '"numeric_value": 14.0, "numeric_unit": "days", "scope": "...", "confidence": 0.95, '
                '"evidence_text_span": "exact verbatim substring"}]}'
            )
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": json_system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            raw_claims = data.get("claims", [])
            claims = []
            for c in raw_claims:
                # Handle possible field variations from diverse LLMs
                if "exact_span" in c and "evidence_text_span" not in c:
                    c["evidence_text_span"] = c["exact_span"]
                claims.append(ExtractedClaim(**c))
            return ClaimExtractionResult(
                claims=claims,
                extraction_model=self.model,
                extraction_method="openai_json_mode",
            )
        except Exception as json_err:
            logger.warning("JSON mode extraction failed (%s); falling back to rule extractor", json_err)
            from app.llm.mock_provider import MockLLMProvider
            return await MockLLMProvider().extract_claims(document_title, section_title, section_content)

    async def get_embedding(self, text: str) -> list[float]:
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text,
            )
            return response.data[0].embedding
        except Exception as emb_err:
            logger.debug("Embedding endpoint unavailable (%s); using deterministic vector", emb_err)
            from app.llm.mock_provider import MockLLMProvider
            return await MockLLMProvider().get_embedding(text)

    async def get_embeddings(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=list(texts),
            )
            return [item.embedding for item in response.data]
        except Exception as emb_err:
            logger.debug("Embeddings batch endpoint unavailable (%s); using deterministic vectors", emb_err)
            from app.llm.mock_provider import MockLLMProvider
            return await MockLLMProvider().get_embeddings(texts)

    async def evaluate_contradiction(
        self,
        claim_a_text: str,
        claim_b_text: str,
    ) -> ContradictionResult:
        # Fast local evaluation for illustrative examples, metadata headers, and temporal updates
        from app.llm.mock_provider import MockLLMProvider
        mock_eval = await MockLLMProvider().evaluate_contradiction(claim_a_text, claim_b_text)
        if not mock_eval.is_contradiction or mock_eval.conflict_type in ("illustrative_example", "temporal_outdated"):
            return mock_eval

        system_prompt = (
            "You are a logic and contradiction analysis engine. "
            "Evaluate whether Claim A and Claim B contradict each other, state conflicting requirements, "
            "or represent numerical discrepancies on the same topic."
        )

        user_prompt = (
            f"Claim A: {claim_a_text}\n"
            f"Claim B: {claim_b_text}\n\n"
            "Analyze if they contradict or disagree."
        )

        # 1. Attempt OpenAI structured output parsing
        try:
            response = await self.client.beta.chat.completions.parse(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=LLMContradictionOutput,
                temperature=0.0,
            )
            parsed = response.choices[0].message.parsed
            if parsed:
                return ContradictionResult(
                    is_contradiction=parsed.is_contradiction,
                    conflict_type=parsed.conflict_type,
                    severity=parsed.severity,
                    confidence=parsed.confidence,
                    reasoning=parsed.reasoning,
                )
        except Exception as parse_err:
            logger.debug("Contradiction structured parse failed (%s); trying standard JSON mode", parse_err)

        # 2. Fallback to standard chat completion with JSON mode
        try:
            json_system_prompt = (
                f"{system_prompt}\n\n"
                "Return ONLY a valid JSON object matching: "
                '{"is_contradiction": bool, "conflict_type": "direct_contradiction|numerical_discrepancy|temporal_outdated|compatible", '
                '"severity": "high|medium|low", "confidence": 0.90, "reasoning": "one sentence explanation"}'
            )
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": json_system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            content = response.choices[0].message.content or "{}"
            data = json.loads(content)
            return ContradictionResult(
                is_contradiction=bool(data.get("is_contradiction", False)),
                conflict_type=str(data.get("conflict_type", "compatible")),
                severity=str(data.get("severity", "low")),
                confidence=float(data.get("confidence", 0.85)),
                reasoning=str(data.get("reasoning", "Evaluated via JSON mode.")),
            )
        except Exception as json_err:
            logger.debug("JSON mode contradiction eval failed (%s); using rule evaluator", json_err)
            from app.llm.mock_provider import MockLLMProvider
            return await MockLLMProvider().evaluate_contradiction(claim_a_text, claim_b_text)

    async def generate_grounded_answer(
        self,
        query: str,
        citations: list[dict],
        has_conflicts: bool = False,
        warnings: list[str] | None = None,
        history: list[dict] | None = None,
    ) -> str:
        """Synthesize a natural language, factual answer using the model."""
        if not citations:
            return (
                f'No verified claims or policies matching "{query}" were found in the current organization knowledge base. '
                "Please ingest the relevant documentation or connect enterprise data sources."
            )

        # Sanitize and format verified citations
        sanitized_citations = []
        for idx, c in enumerate(citations[:10]):
            text = c.get('claim_text', '').strip()
            if text.startswith("{") or '"connectors":' in text or "synthetic" in text.lower():
                continue
            if len(text) > 300:
                text = text[:300].rsplit(" ", 1)[0] + "..."
            sanitized_citations.append(
                f"[Source {idx + 1}] {text} (Document: {c.get('source_title', 'Knowledge Base')} > {c.get('section', 'General')}, Trust Score: {int(float(c.get('trust_score', 0.8))*100)}%)"
            )

        citations_context = "\n".join(sanitized_citations) if sanitized_citations else "No specific text excerpts available."

        warning_context = ""
        if warnings:
            warning_context = "\n⚠️ Potential Policy Discrepancies / Conflicts:\n" + "\n".join(f"- {w}" for w in warnings)

        system_prompt = (
            "You are Context Trust Layer Copilot, an enterprise governance intelligence assistant. "
            "Formulate an attractive, crisp, and well-structured answer directly answering the user's inquiry based strictly on the verified context.\n"
            "Structure the response clearly using Markdown:\n"
            "- Start with a clear 1-sentence **Bottom Line / Direct Answer**.\n"
            "- Use clean bullet points (`- `) with **bold keywords** for specific rules, numbers, dollar thresholds, durations, windows, eligible roles, or exceptions.\n"
            "- Attach citation markers like [Source 1], [Source 2] to material assertions.\n"
            "- If there are specific policies, section references, or caveats, state them in a bullet point or a brief note.\n"
            "- If there is a contradiction or gap in the verified knowledge base, explicitly mention it.\n"
            "DO NOT invent facts or override limitations. DO NOT write a single dense wall-of-text paragraph. Keep it visually engaging, scannable, and professional."
        )

        user_prompt = (
            f"User Question: {query}\n\n"
            f"Verified Enterprise Claims:\n{citations_context}\n"
            f"{warning_context}\n\n"
            "Please provide a structured, attractive, and authoritative answer for the user."
        )

        messages = [{"role": "system", "content": system_prompt}]
        if history:
            for turn in history[-4:]:
                r = turn.get("role")
                c = turn.get("content", "")
                if r in ("user", "assistant") and c:
                    messages.append({"role": r, "content": c[:300]})
        messages.append({"role": "user", "content": user_prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=500,
            )
            content = response.choices[0].message.content
            if content and len(content.strip()) > 10:
                return content.strip()
        except Exception as chat_err:
            logger.warning("LLM answer synthesis failed (%s); using template synthesis", chat_err)

        from app.llm.mock_provider import MockLLMProvider
        return await MockLLMProvider().generate_grounded_answer(query, citations, has_conflicts, warnings, history=history)

    async def generate_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 300,
        temperature: float = 0.0,
    ) -> str:
        """Generate text completion via OpenAI or OpenAI-compatible gateway (OpenRouter)."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

