from abc import ABC, abstractmethod
from typing import Sequence

from app.llm.schemas import ClaimExtractionResult, ContradictionResult


class BaseLLMProvider(ABC):
    """Abstract Base Class for LLM and Embedding services."""

    @abstractmethod
    async def extract_claims(
        self,
        document_title: str,
        section_title: str,
        section_content: str,
    ) -> ClaimExtractionResult:
        """Extract atomic claims from a document section."""
        pass

    @abstractmethod
    async def get_embedding(self, text: str) -> list[float]:
        """Generate a dense vector embedding for the given text."""
        pass

    @abstractmethod
    async def get_embeddings(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate vector embeddings for a list of texts."""
        pass

    @abstractmethod
    async def evaluate_contradiction(
        self,
        claim_a_text: str,
        claim_b_text: str,
    ) -> ContradictionResult:
        """Analyze whether two claims contradict, disagree, or complement each other."""
        pass

    @abstractmethod
    async def generate_grounded_answer(
        self,
        query: str,
        citations: list[dict],
        has_conflicts: bool = False,
        warnings: list[str] | None = None,
        history: list[dict] | None = None,
    ) -> str:
        """Synthesize a factual, grounded answer to query based strictly on verified context claims."""
        pass

    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        system_prompt: str | None = None,
        max_tokens: int = 300,
        temperature: float = 0.0,
    ) -> str:
        """Generate a raw text completion from the provider."""
        pass
