import hashlib
import inspect
import json
import logging
import math
import re
from typing import Sequence
import httpx

from app.llm.base import BaseLLMProvider
from app.llm.schemas import ClaimExtractionResult, ContradictionResult, ExtractedClaim

logger = logging.getLogger(__name__)

CLAIM_EXTRACTION_SYSTEM_PROMPT = (
    "You are a strict enterprise document claim extractor. "
    "Extract ONLY explicit, verifiable claims stated in the supplied source text.\n\n"
    "Extraction Rules:\n"
    "1. ATOMIC CLAIMS: Extract atomic claims only. One claim must contain exactly one discrete factual statement.\n"
    "2. NO HALLUCINATIONS: Do not infer facts, policies, dates, numbers, permissions, or exceptions.\n"
    "3. PRESERVE MEANING: Preserve the document's meaning; do not rewrite a weaker statement as a stronger one.\n"
    "4. NAMED ENTITIES: Use complete named entities. Resolve pronouns only when the referent is explicit in the provided text.\n"
    "5. EXACT EVIDENCE: For every claim, include an exact verbatim evidence_text substring copied directly from the source.\n"
    "6. NUMERICAL EXTRACTION: If a number, amount, period, date, percentage, or limit exists, populate numeric_value and numeric_unit only when explicitly stated.\n"
    "7. EMPTY FALLBACK: If there are no clear policy, technical, or factual claims, return {\"claims\": []}.\n\n"
    "Modality Definitions:\n"
    "- MUST: Mandatory obligation or requirement\n"
    "- CANNOT: Prohibition or barred action\n"
    "- CAN or MAY: Permission or allowed action\n"
    "- SHOULD: Recommendation\n"
    "- IS: Factual definition, state, or relationship"
)

CONTRADICTION_SYSTEM_PROMPT = (
    "Determine if the two claims contradict each other based strictly on enterprise policy logic. "
    "Return valid JSON with: is_contradiction (bool), conflict_type ('direct_contradiction'|'numerical_discrepancy'|'temporal_outdated'|'complementary'), "
    "severity ('high'|'medium'|'low'), confidence (0.0-1.0), and reasoning."
)


def _hash_emb(text: str, dim: int = 1536) -> list[float]:
    vec = [0.0] * dim
    words = re.findall(r"\w+", text.lower())
    if not words:
        vec[0] = 1.0
        return vec
    for w in words:
        h = int(hashlib.md5(w.encode()).hexdigest(), 16)
        vec[h % dim] += 1.0
    norm = math.sqrt(sum(v * v for v in vec))
    return [v / norm for v in vec] if norm > 0 else vec


class OllamaProvider(BaseLLMProvider):
    """Local LLM provider using Ollama with JSON-Schema constrained structured extraction."""

    def __init__(self):
        import os
        from app.core.config import settings
        self.base_url = os.getenv("OLLAMA_BASE_URL", settings.ollama_base_url).rstrip("/")
        self.model = os.getenv("OLLAMA_MODEL", settings.ollama_model or "qwen2.5:7b")
        self.emb_model = os.getenv("OLLAMA_EMBEDDING_MODEL", getattr(settings, "ollama_embedding_model", self.model))
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", str(getattr(settings, "ollama_timeout", 120))))
        self.temperature = getattr(settings, "ollama_temperature", 0.0)
        self.num_ctx = getattr(settings, "ollama_num_ctx", 8192)
        self.embedding_dim = 1536
        logger.info("OllamaProvider initialized: model=%s base_url=%s num_ctx=%d", self.model, self.base_url, self.num_ctx)

    async def _chat(self, prompt: str, schema: dict | None = None) -> str:
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": CLAIM_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            "stream": False,
            "options": {
                "temperature": self.temperature,
                "num_ctx": self.num_ctx,
            },
        }
        if schema:
            payload["format"] = schema
        else:
            payload["format"] = "json"

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.base_url}/api/chat", json=payload)
            if hasattr(resp, "raise_for_status"):
                if inspect.iscoroutinefunction(resp.raise_for_status):
                    await resp.raise_for_status()
                else:
                    resp.raise_for_status()
            raw_data = resp.json() if callable(resp.json) else resp.json
            data = await raw_data if inspect.isawaitable(raw_data) else raw_data
            return data.get("message", {}).get("content", "").strip()

    @staticmethod
    def _clean(raw: str) -> str:
        raw = re.sub(r"<think>.*?</think>", "", raw, flags=re.DOTALL).strip()
        raw = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
        raw = re.sub(r"\s*```\s*$", "", raw, flags=re.MULTILINE)
        return raw.strip()

    async def extract_claims(
        self, document_title: str, section_title: str, section_content: str
    ) -> ClaimExtractionResult:
        empty = ClaimExtractionResult(
            claims=[], extraction_model=self.model, extraction_method="ollama_json_extraction"
        )
        if not (section_content or "").strip():
            return empty

        if getattr(self, "_model_unavailable", False):
            return empty

        user_prompt = (
            f"Document Title: {document_title}\n"
            f"Section Title: {section_title or 'General'}\n"
            f"Section Text:\n---\n{section_content}\n---"
        )

        claim_json_schema = {
            "type": "object",
            "properties": {
                "claims": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "claim_text": {"type": "string"},
                            "subject": {"type": "string"},
                            "predicate": {"type": "string"},
                            "object": {"type": "string"},
                            "modality": {"type": "string", "enum": ["MUST", "CANNOT", "CAN", "MAY", "SHOULD", "IS"]},
                            "claim_type": {"type": "string", "enum": ["policy", "security", "financial", "compliance", "operational", "technical", "general"]},
                            "evidence_text": {"type": "string"},
                            "evidence_text_span": {"type": "string"},
                            "confidence": {"type": "number"},
                            "numeric_value": {"type": ["number", "null"]},
                            "numeric_unit": {"type": ["string", "null"]}
                        },
                        "required": ["subject", "predicate", "object", "modality", "claim_type"]
                    }
                }
            },
            "required": ["claims"]
        }

        raw = ""
        try:
            raw = self._clean(await self._chat(user_prompt, schema=claim_json_schema))
            data = json.loads(raw)
            if isinstance(data, dict):
                rows = data.get("claims") or data.get("data") or [data]
            elif isinstance(data, list):
                rows = data
            else:
                rows = []
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            self._model_unavailable = True
            if not getattr(self, "_warned_missing_model", False):
                logger.warning("Ollama extract_claims network error (%s): %s. Falling back to deterministic extractors.", self.model, e)
                self._warned_missing_model = True
            return empty
        except json.JSONDecodeError:
            logger.warning("Ollama extract_claims non-JSON (%s): %s", self.model, raw[:400])
            return empty

        claims = []
        for item in rows:
            if not isinstance(item, dict):
                continue
            
            ct = str(item.get("claim_text") or item.get("claim") or item.get("statement") or "").strip()
            subj = str(item.get("subject") or "").strip()
            pred = str(item.get("predicate") or "").strip()
            obj = str(item.get("object") or "").strip()

            if not ct and subj and pred and obj:
                ct = f"{subj} {pred} {obj}."

            if not ct:
                continue

            ev = str(item.get("evidence_text_span") or item.get("evidence_text") or ct).strip()
            modality = str(item.get("modality") or "MUST").upper()
            claim_type = str(item.get("claim_type") or "policy")
            
            conf = 0.95
            try:
                if item.get("confidence") is not None:
                    conf = float(item["confidence"])
            except Exception:
                pass

            num_val = None
            if item.get("numeric_value") is not None:
                try:
                    num_val = float(item["numeric_value"])
                except Exception:
                    pass

            num_unit = str(item.get("numeric_unit")).strip() if item.get("numeric_unit") else None

            claims.append(
                ExtractedClaim(
                    claim_text=ct,
                    subject=subj or "Document Policy",
                    predicate=pred or "asserts",
                    object=obj or ct,
                    claim_type=claim_type,
                    modality=modality,
                    confidence=min(1.0, max(0.0, conf)),
                    evidence_text_span=ev,
                    numeric_value=num_val,
                    numeric_unit=num_unit,
                )
            )

        logger.info("OllamaProvider extracted %d candidate claims from '%s'", len(claims), section_title)
        return ClaimExtractionResult(
            claims=claims,
            extraction_model=self.model,
            extraction_method="ollama_json_extraction",
        )

    async def evaluate_contradiction(
        self, claim_a_text: str, claim_b_text: str
    ) -> ContradictionResult:
        if getattr(self, "_model_unavailable", False):
            from app.llm.mock_provider import MockLLMProvider
            return await MockLLMProvider().evaluate_contradiction(claim_a_text, claim_b_text)

        user_prompt = f"{CONTRADICTION_SYSTEM_PROMPT}\n\nClaim A: {claim_a_text}\nClaim B: {claim_b_text}"
        try:
            raw = self._clean(await self._chat(user_prompt))
            data = json.loads(raw)
            return ContradictionResult(
                is_contradiction=bool(data.get("is_contradiction", False)),
                conflict_type=str(data.get("conflict_type", "direct_contradiction")),
                severity=str(data.get("severity", "high")),
                confidence=float(data.get("confidence", 0.90)),
                reasoning=str(data.get("reasoning", "")),
            )
        except Exception as e:
            self._model_unavailable = True
            if not getattr(self, "_warned_missing_model", False):
                logger.warning(
                    "Ollama evaluate_contradiction failed (%s): %s. Falling back to deterministic contradiction evaluator.",
                    self.model,
                    e,
                )
                self._warned_missing_model = True
            from app.llm.mock_provider import MockLLMProvider
            return await MockLLMProvider().evaluate_contradiction(claim_a_text, claim_b_text)

    async def detect_contradiction(self, claim_a_text: str, claim_b_text: str) -> ContradictionResult:
        return await self.evaluate_contradiction(claim_a_text, claim_b_text)

    async def get_embedding(self, text: str) -> list[float]:
        if getattr(self, "_embeddings_unavailable", False):
            return _hash_emb(text, self.embedding_dim)

        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                resp = await client.post(
                    f"{self.base_url}/api/embeddings",
                    json={"model": self.emb_model, "prompt": text}
                )
                if resp.status_code == 200:
                    raw_data = resp.json() if callable(resp.json) else resp.json
                    data = await raw_data if inspect.isawaitable(raw_data) else raw_data
                    emb = data.get("embedding")
                    if emb and len(emb) > 0:
                        return emb
                elif resp.status_code in (404, 500):
                    self._embeddings_unavailable = True
        except Exception:
            self._embeddings_unavailable = True
        return _hash_emb(text, self.embedding_dim)

    async def generate_embedding(self, text: str) -> list[float]:
        return await self.get_embedding(text)

    async def get_embeddings(self, texts: Sequence[str]) -> list[list[float]]:
        if getattr(self, "_embeddings_unavailable", False):
            return [_hash_emb(t, self.embedding_dim) for t in texts]
        results = []
        for t in texts:
            results.append(await self.get_embedding(t))
        return results

    async def generate_embeddings_batch(self, texts: Sequence[str]) -> list[list[float]]:
        return await self.get_embeddings(texts)

    async def generate_grounded_answer(
        self,
        query: str,
        citations: list[dict],
        has_conflicts: bool = False,
        warnings: list[str] | None = None,
        history: list[dict] | None = None,
    ) -> str:
        """Synthesize a factual, grounded answer to query based strictly on verified context claims."""
        if not getattr(self, "_model_unavailable", False):
            context_items = []
            for idx, c in enumerate(citations, start=1):
                claim_txt = c.get("claim_text", "")
                source_doc = c.get("source_title") or c.get("source_document") or "Verified Knowledge"
                folder = c.get("folder_name") or "Enterprise Policies"
                context_items.append(f"[{idx}] {claim_txt} (Folder: {folder} | Source: {source_doc})")
            
            context_block = "\n".join(context_items) if context_items else "No verified claims found."
            
            system_prompt = (
                "You are the Trulin Context Trust Copilot—an enterprise decision governance assistant.\n"
                "Synthesize a fluent, polished, executive response that answers the user's question directly based STRICTLY on the verified context claims below.\n\n"
                "FORMATTING GUIDELINES:\n"
                "1. Start with a clear direct answer in the first 1-2 sentences answering the user's inquiry.\n"
                "2. Group specific criteria, conditions, or thresholds into a bulleted list with bold topic prefixes.\n"
                "3. Tag every statement with inline citations using [Source 1], [Source 2], etc.\n"
                "4. NEVER output raw unformatted dumps or copy-paste claims verbatim without explanatory framing.\n"
                "5. If the user's specific question (e.g. annual enterprise contract terms) is not addressed in the retrieved claims, explicitly disclose the information gap."
            )
            user_prompt = f"User Query: {query}\n\nVerified Organizational Context:\n{context_block}"
            
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.post(
                        f"{self.base_url}/api/chat",
                        json={
                            "model": self.model,
                            "messages": [
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt}
                            ],
                            "stream": False,
                            "options": {"temperature": 0.1, "num_ctx": self.num_ctx}
                        }
                    )
                    if resp.status_code == 200:
                        raw_data = resp.json() if callable(resp.json) else resp.json
                        data = await raw_data if inspect.isawaitable(raw_data) else raw_data
                        llm_text = data.get("message", {}).get("content", "").strip()
                        if llm_text:
                            return llm_text
                    elif resp.status_code == 404:
                        self._model_unavailable = True
            except Exception as e:
                logger.warning("Ollama generate_grounded_answer error: %s", e)
                self._model_unavailable = True
        
        # Intelligent Hybrid Synthesis Fallback
        from app.services.policy_answer_synthesizer import PolicyAnswerSynthesizer
        return PolicyAnswerSynthesizer.synthesize(
            query=query,
            citations=citations,
            has_conflicts=has_conflicts,
            warnings=warnings,
            history=history,
        )

