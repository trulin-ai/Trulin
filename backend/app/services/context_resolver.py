import logging
import re
from typing import Sequence
from app.llm.base import BaseLLMProvider

logger = logging.getLogger(__name__)

FOLLOW_UP_INDICATORS = [
    r"\bthat\b",
    r"\bthis\b",
    r"\bit\b",
    r"\bthese\b",
    r"\bthose\b",
    r"\bthe same\b",
    r"\bwhat about\b",
    r"\bhow about\b",
    r"\band for\b",
    r"\bdoes it\b",
    r"\bdoes that\b",
    r"\bcan it\b",
    r"\bcan that\b",
    r"\bwhy\b",
    r"\bexceptions?\b",
    r"\bfirst one\b",
    r"\bsecond one\b",
    r"\blatter\b",
    r"\bformer\b",
]

FOLLOW_UP_REGEX = re.compile("|".join(FOLLOW_UP_INDICATORS), re.IGNORECASE)


class ConversationContextResolver:
    """Resolves follow-up queries in multi-turn conversations into standalone, search-ready queries."""

    def __init__(self, llm_provider: BaseLLMProvider):
        self.llm = llm_provider

    def is_follow_up_query(self, query: str) -> bool:
        """Determines whether a query likely relies on antecedent conversation context."""
        q_clean = query.strip()
        words = q_clean.split()
        if len(words) <= 3:
            return True
        # If the query is already a long, complete self-contained sentence (>= 7 words)
        # starting with complete interrogatives ("What is the...", "Can I approve...", "Am I allowed to..."),
        # do not treat it as a follow-up query just because it contains relative pronouns ("that", "it")
        if len(words) >= 7 and re.match(r"^(?:what\s+(?:is|are|happens|does)|can\s+(?:i|we|an\s+agent)|am\s+i\s+allowed|how\s+(?:do|does|can))\b", q_clean, re.I):
            explicit_anaphora = [r"\bthat\s+(?:one|item|rule|clause|policy)\b", r"\bthe\s+same\b", r"\blatter\b", r"\bformer\b", r"\bas\s+mentioned\b", r"\babove\b"]
            return any(re.search(pat, q_clean, re.I) for pat in explicit_anaphora)
        return bool(FOLLOW_UP_REGEX.search(q_clean))

    async def resolve_query(
        self,
        current_query: str,
        history: Sequence[dict[str, str]] | None = None,
    ) -> str:
        """Reformulates user query into a standalone search query if conversational context is needed."""
        clean_query = current_query.strip()
        if not history or not self.is_follow_up_query(clean_query):
            return clean_query

        # Filter last 4 turns (user and assistant)
        filtered_history = [
            h for h in history[-4:]
            if h.get("role") in ("user", "assistant") and h.get("content")
        ]
        if not filtered_history:
            return clean_query

        history_lines = []
        for h in filtered_history:
            role = "User" if h["role"] == "user" else "Assistant"
            content = h["content"].split("\n")[0][:180]
            history_lines.append(f"{role}: {content}")
        history_text = "\n".join(history_lines)

        # Attempt LLM reformulation if provider is OpenAI / OpenRouter
        if hasattr(self.llm, "client") and hasattr(self.llm, "model"):
            try:
                system_prompt = (
                    "You are a conversational query context resolver. "
                    "Given the recent conversation history and a user follow-up question, "
                    "rewrite the follow-up question into a single, complete, standalone search query. "
                    "Preserve all specific entities, policy names, contract types, numerical limits, and topics from earlier turns. "
                    "DO NOT answer the question. DO NOT include quotes or explanations. Output ONLY the standalone query."
                )
                user_prompt = (
                    f"Conversation History:\n{history_text}\n\n"
                    f"User Follow-up: {clean_query}\n\n"
                    "Standalone Query:"
                )
                response = await self.llm.client.chat.completions.create(
                    model=self.llm.model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    temperature=0.0,
                    max_tokens=60,
                )
                rewritten = response.choices[0].message.content.strip().strip('"\'')
                if rewritten and len(rewritten) >= 5:
                    logger.debug("Rewrote follow-up query: '%s' -> '%s'", clean_query, rewritten)
                    return rewritten
            except Exception as e:
                logger.warning("Query rewrite LLM call failed (%s); using deterministic resolution", e)

        # Deterministic Fallback: Extract key context terms from the last user message
        last_user_turns = [h["content"] for h in filtered_history if h.get("role") == "user"]
        if last_user_turns:
            prev_turn = last_user_turns[-1].strip()
            # Remove punctuation and common stop words to get topic core
            prev_tokens = [w for w in prev_turn.split() if len(w) > 3 and w.lower() not in (
                "what", "when", "where", "which", "does", "have", "with", "from", "about", "your", "this", "that"
            )]
            context_anchor = " ".join(prev_tokens[:5])
            if context_anchor and context_anchor.lower() not in clean_query.lower():
                resolved = f"{context_anchor} {clean_query}"
                logger.debug("Deterministic query expansion: '%s' -> '%s'", clean_query, resolved)
                return resolved

        return clean_query
