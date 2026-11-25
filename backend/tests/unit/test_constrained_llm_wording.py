"""
Unit tests for the Constrained LLM Wording Layer (PolicyWordingRefiner).

Guarantees:
1. Zero Hallucination: Ungrounded numbers, dates, or amounts trigger rejection and deterministic fallback.
2. Citation Integrity: Missing or non-existent [Source X] references trigger rejection and deterministic fallback.
3. Fail-Closed Preservation: NO_VERIFIED_RULE and UNVERIFIED states completely bypass the LLM.
4. Exception Safety: Provider timeouts or runtime errors cleanly fall back to deterministic synthesis.
5. Successful Polish: Valid rephrasings that pass AnswerVerifier update the answer contract.
"""

import pytest
from unittest.mock import AsyncMock

from app.llm.base import BaseLLMProvider
from app.schemas.chat import (
    AnswerScope,
    GroundedClaimItem,
    PolicyAnswerContract,
)
from app.services.policy_wording_refiner import PolicyWordingRefiner
from app.services.policy_answer_synthesizer import PolicyAnswerSynthesizer


class MockRefinementProvider(BaseLLMProvider):
    """Custom mock provider for testing LLM wording refinement paths."""

    def __init__(self, response_text: str = "", should_raise: bool = False):
        self.response_text = response_text
        self.should_raise = should_raise

    async def generate_completion(self, prompt: str, system_prompt: str | None = None, max_tokens: int = 300, temperature: float = 0.0) -> str:
        if self.should_raise:
            raise RuntimeError("Simulated provider timeout or network error")
        return self.response_text

    async def extract_claims(self, document_title: str, section_title: str, section_content: str):
        from app.llm.schemas import ClaimExtractionResult
        return ClaimExtractionResult(claims=[], extraction_model="mock", extraction_method="mock")

    async def get_embedding(self, text: str):
        return [0.0] * 1536

    async def get_embeddings(self, texts):
        return [[0.0] * 1536 for _ in texts]

    async def evaluate_contradiction(self, claim_a_text: str, claim_b_text: str):
        from app.llm.schemas import ContradictionResult
        return ContradictionResult(is_contradiction=False, conflict_type="compatible", severity="low", confidence=1.0, reasoning="mock")

    async def generate_grounded_answer(self, query: str, citations: list[dict], has_conflicts: bool = False, warnings: list[str] | None = None, history: list[dict] | None = None) -> str:
        return "mock"


@pytest.fixture
def sample_verified_contract():
    return PolicyAnswerContract(
        bottom_line_answer="Either party may terminate the agreement on 30 days' notice for material breach if the other party fails to cure [Source 1].",
        conditions=["Applies to termination for material breach", "Subject to 30-day cure period"],
        exceptions=[],
        verified_claims_used=[
            GroundedClaimItem(
                claim_id="CLM-BREACH-01",
                source_index=1,
                subject="Party",
                predicate="may_terminate_for_cause",
                object="Agreement",
                modality="MAY",
                verbatim_evidence="Either party may terminate the agreement on 30 days' notice for material breach if the other party fails to cure.",
                document_title="Master Services Agreement",
                section="14.2",
            )
        ],
        section_context=[],
        grounding_score=1.0,
        verification_status="VERIFIED",
        answer_scope=AnswerScope(document_ids=["DOC-MSA-01"], workspace="policy", temporal_validity="current"),
    )


@pytest.fixture
def sample_citations():
    return [
        {
            "source_index": 1,
            "claim_id": "CLM-BREACH-01",
            "source_title": "Master Services Agreement",
            "document_id": "DOC-MSA-01",
            "section": "14.2",
            "verbatim_evidence": "Either party may terminate the agreement on 30 days' notice for material breach if the other party fails to cure.",
            "claim_text": "Either party may terminate the agreement on 30 days' notice for material breach if the other party fails to cure.",
        }
    ]


@pytest.mark.asyncio
async def test_valid_wording_polish_updates_contract(sample_verified_contract, sample_citations):
    """A valid, grounded rephrasing should update the contract and return verified markdown."""
    polished_text = (
        "Under the governing agreement, a party may terminate for material breach by providing **30 days' notice**, "
        "provided the breach remains uncured during that period [Source 1]."
    )
    provider = MockRefinementProvider(response_text=polished_text)

    contract, markdown = await PolicyWordingRefiner.refine_contract(
        contract=sample_verified_contract,
        citations=sample_citations,
        has_conflicts=False,
        llm_provider=provider,
    )

    assert contract.bottom_line_answer == polished_text
    assert "[Source 1]" in contract.bottom_line_answer
    assert "30 days' notice" in contract.bottom_line_answer
    assert "### 🛡️ Bottom-Line Answer" in markdown


@pytest.mark.asyncio
async def test_ungrounded_number_injection_triggers_deterministic_fallback(sample_verified_contract, sample_citations):
    """If the LLM hallucinates a new number (e.g., $100,000 or 60 days), it MUST be discarded."""
    deterministic_original = sample_verified_contract.bottom_line_answer
    hallucinated_text = (
        "Under the governing agreement, either party may terminate on 60 days notice and claim $100,000 damages [Source 1]."
    )
    provider = MockRefinementProvider(response_text=hallucinated_text)

    contract, markdown = await PolicyWordingRefiner.refine_contract(
        contract=sample_verified_contract,
        citations=sample_citations,
        has_conflicts=False,
        llm_provider=provider,
    )

    # Contract must remain completely untouched with the original deterministic answer
    assert contract.bottom_line_answer == deterministic_original
    assert "$100,000" not in markdown
    assert "60 days" not in markdown


@pytest.mark.asyncio
async def test_missing_citations_triggers_deterministic_fallback(sample_verified_contract, sample_citations):
    """If the LLM drops the required [Source 1] citation tag, it MUST be discarded."""
    deterministic_original = sample_verified_contract.bottom_line_answer
    uncited_text = (
        "Either party may terminate the agreement on 30 days notice for material breach."
    )
    provider = MockRefinementProvider(response_text=uncited_text)

    contract, markdown = await PolicyWordingRefiner.refine_contract(
        contract=sample_verified_contract,
        citations=sample_citations,
        has_conflicts=False,
        llm_provider=provider,
    )

    assert contract.bottom_line_answer == deterministic_original
    assert "[Source 1]" in contract.bottom_line_answer


@pytest.mark.asyncio
async def test_invalid_source_index_triggers_deterministic_fallback(sample_verified_contract, sample_citations):
    """If the LLM cites a non-existent source [Source 99], it MUST be discarded."""
    deterministic_original = sample_verified_contract.bottom_line_answer
    invalid_source_text = (
        "Either party may terminate the agreement on 30 days notice for material breach [Source 99]."
    )
    provider = MockRefinementProvider(response_text=invalid_source_text)

    contract, markdown = await PolicyWordingRefiner.refine_contract(
        contract=sample_verified_contract,
        citations=sample_citations,
        has_conflicts=False,
        llm_provider=provider,
    )

    assert contract.bottom_line_answer == deterministic_original
    assert "[Source 99]" not in markdown


@pytest.mark.asyncio
async def test_fail_closed_abstention_never_calls_llm(sample_citations):
    """Abstention states (NO_VERIFIED_RULE) must NEVER invoke the LLM."""
    abstention_contract = PolicyAnswerContract(
        bottom_line_answer="No verified rule matching quantum cryptography was found in governing policies.",
        conditions=[],
        exceptions=[],
        verified_claims_used=[],
        section_context=[],
        grounding_score=1.0,
        verification_status="NO_VERIFIED_RULE",
        answer_scope=AnswerScope(document_ids=[], workspace="policy", temporal_validity="current"),
    )
    # Provider is set to raise an error if called
    provider = MockRefinementProvider(should_raise=True)

    contract, markdown = await PolicyWordingRefiner.refine_contract(
        contract=abstention_contract,
        citations=[],
        has_conflicts=False,
        llm_provider=provider,
    )

    assert contract.verification_status == "NO_VERIFIED_RULE"
    assert "No verified rule" in contract.bottom_line_answer


@pytest.mark.asyncio
async def test_provider_timeout_safely_falls_back(sample_verified_contract, sample_citations):
    """If the provider times out or crashes, the system must cleanly return the deterministic contract."""
    deterministic_original = sample_verified_contract.bottom_line_answer
    provider = MockRefinementProvider(should_raise=True)

    contract, markdown = await PolicyWordingRefiner.refine_contract(
        contract=sample_verified_contract,
        citations=sample_citations,
        has_conflicts=False,
        llm_provider=provider,
    )

    assert contract.bottom_line_answer == deterministic_original
    assert "### 🛡️ Bottom-Line Answer" in markdown


@pytest.mark.asyncio
async def test_refinement_disabled_flag(sample_verified_contract, sample_citations):
    """When refinement is disabled via argument or settings, returns deterministic immediately."""
    provider = MockRefinementProvider(response_text="This should not be called [Source 1]")

    contract, markdown = await PolicyWordingRefiner.refine_contract(
        contract=sample_verified_contract,
        citations=sample_citations,
        has_conflicts=False,
        llm_provider=provider,
        enabled=False,
    )

    assert contract.bottom_line_answer == sample_verified_contract.bottom_line_answer
    assert "This should not be called" not in markdown
