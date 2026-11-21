import pytest
from unittest.mock import patch

from app.core.config import settings
from app.llm.mock_provider import MockLLMProvider
from app.schemas.chat import (
    PolicyAnswerContract,
    GroundedClaimItem,
    ResponsePlan,
    QuestionType,
    DisplayDepth,
)
from app.services.feedback_telemetry_service import (
    FeedbackTelemetryService,
    PilotChecklist,
    PilotFeedbackRequest,
    PilotIssueCategory,
    PilotVerdict,
)
from app.services.policy_answer_synthesizer import PolicyAnswerSynthesizer
from app.services.policy_wording_refiner import PolicyWordingRefiner


@pytest.fixture
def sample_citations():
    return [
        {
            "source_index": 1,
            "claim_id": "clm-1",
            "document_id": "doc-msa",
            "source_title": "Commercial Licensing Agreement",
            "section": "7.1",
            "page": 5,
            "trust_score": 1.0,
            "certification_tier": "AUTOMATED_CERTIFIED",
            "claim_text": "License transfer requires 30 days prior written notice and written consent.",
            "evidence": "License transfer requires 30 days prior written notice and written consent.",
            "subject": "Licensee",
            "predicate": "requires",
            "object": "30 days prior written notice",
            "modality": "MUST",
        }
    ]


# ----------------------------------------------------------------------
# 1. Configuration 1: adaptive=False, wording=False
# Deterministic legacy baseline: No explanation blocks, no LLM call
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_feature_flag_config_1_deterministic_legacy(sample_citations):
    with patch.object(settings, "enable_adaptive_composition", False):
        contract = PolicyAnswerSynthesizer.synthesize_structured(
            query="What must a customer do before transferring a license?",
            citations=sample_citations,
            requested_depth="standard",
        )

        assert contract.schema_version == "2"
        # When adaptive composition is disabled, explanation_blocks must be empty
        assert contract.explanation_blocks == []
        assert "No license transfer is valid" in contract.bottom_line_answer

    mock_llm = MockLLMProvider()
    mock_llm.mock_completion_text = '{"statements": []}'

    with patch.object(settings, "enable_llm_wording_refinement", False):
        final_contract, markdown = await PolicyWordingRefiner.refine_contract(
            contract=contract,
            citations=sample_citations,
            llm_provider=mock_llm,
            enabled=False,
        )

        assert final_contract.wording_metadata is None
        # Markdown must use deterministic legacy section headers
        assert "### 🛡️ Bottom-Line Answer" in markdown
        assert "### 📜 Verified Operative Claims" in markdown
        assert "[Source 1]" in markdown


# ----------------------------------------------------------------------
# 2. Configuration 2: adaptive=True, wording=False
# Adaptive composition active, deterministic wording preserved
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_feature_flag_config_2_adaptive_deterministic(sample_citations):
    with patch.object(settings, "enable_adaptive_composition", True):
        contract = PolicyAnswerSynthesizer.synthesize_structured(
            query="What must a customer do before transferring a license?",
            citations=sample_citations,
            requested_depth="standard",
        )

        # Adaptive composition active: explanation blocks created
        assert len(contract.explanation_blocks) >= 1
        block_types = [b.block_type for b in contract.explanation_blocks]
        assert "paragraph" in block_types or "checklist" in block_types

    mock_llm = MockLLMProvider()
    mock_llm.mock_completion_text = '{"statements": []}'

    with patch.object(settings, "enable_llm_wording_refinement", False):
        final_contract, markdown = await PolicyWordingRefiner.refine_contract(
            contract=contract,
            citations=sample_citations,
            llm_provider=mock_llm,
            enabled=False,
        )

        assert final_contract.wording_metadata is None
        # Markdown contains explanation block statements
        assert len(final_contract.explanation_blocks) >= 1
        assert "30 days" in markdown


# ----------------------------------------------------------------------
# 3. Configuration 3: adaptive=True, wording=True
# Adaptive composition + Structured statement rewriting with verifier
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_feature_flag_config_3_adaptive_wording_success(sample_citations):
    with patch.object(settings, "enable_adaptive_composition", True):
        contract = PolicyAnswerSynthesizer.synthesize_structured(
            query="What must a customer do before transferring a license?",
            citations=sample_citations,
            requested_depth="standard",
        )

    # LLM returns polished wording preserving all facts, numbers (30 days), and source tags
    mock_llm = MockLLMProvider()
    mock_llm.mock_completion_text = (
        '{\n'
        '  "statements": [\n'
        '    {\n'
        '      "id": "stmt-1",\n'
        '      "text": "No license transfer is valid unless the licensee provides 30 days prior written notice and written consent [Source 1]."\n'
        '    }\n'
        '  ]\n'
        '}'
    )

    with patch.object(settings, "enable_llm_wording_refinement", True):
        final_contract, markdown = await PolicyWordingRefiner.refine_contract(
            contract=contract,
            citations=sample_citations,
            llm_provider=mock_llm,
            enabled=True,
        )

        assert final_contract.wording_metadata is not None
        assert final_contract.wording_metadata["applied"] is True
        assert final_contract.wording_metadata["statements_polished"] >= 1
        assert "No license transfer is valid unless the licensee" in markdown


@pytest.mark.asyncio
async def test_feature_flag_config_3_adaptive_wording_adversarial_rejected(sample_citations):
    with patch.object(settings, "enable_adaptive_composition", True):
        contract = PolicyAnswerSynthesizer.synthesize_structured(
            query="What must a customer do before transferring a license?",
            citations=sample_citations,
            requested_depth="standard",
        )

    # Adversarial LLM drops the "30 days" number
    mock_llm = MockLLMProvider()
    mock_llm.mock_completion_text = (
        '{\n'
        '  "statements": [\n'
        '    {\n'
        '      "id": "stmt-1",\n'
        '      "text": "The licensee may provide written notice whenever convenient [Source 1]."\n'
        '    }\n'
        '  ]\n'
        '}'
    )

    with patch.object(settings, "enable_llm_wording_refinement", True):
        final_contract, markdown = await PolicyWordingRefiner.refine_contract(
            contract=contract,
            citations=sample_citations,
            llm_provider=mock_llm,
            enabled=True,
        )

        assert final_contract.wording_metadata is not None
        assert final_contract.wording_metadata["applied"] is False
        assert final_contract.wording_metadata["fallback_reason"] == "all_statements_failed_mutation_verification"
        # Deterministic text preserved: 30 days must be in markdown
        assert "30 days" in markdown


# ----------------------------------------------------------------------
# 4. Configuration 4: adaptive=False, wording=True
# Legacy contract structure + Single-answer wording polish
# ----------------------------------------------------------------------
@pytest.mark.asyncio
async def test_feature_flag_config_4_legacy_contract_wording_polish(sample_citations):
    with patch.object(settings, "enable_adaptive_composition", False):
        contract = PolicyAnswerSynthesizer.synthesize_structured(
            query="What must a customer do before transferring a license?",
            citations=sample_citations,
            requested_depth="standard",
        )
        assert contract.explanation_blocks == []

    # Polished single-answer text preserving negative restriction, facts, 30 days and [Source 1]
    safe_polish = "Under the Commercial Licensing Agreement, no license transfer is valid unless the customer provides documented notice and 30 days prior written consent [Source 1]."
    mock_llm = MockLLMProvider()
    mock_llm.mock_completion_text = safe_polish

    with patch.object(settings, "enable_llm_wording_refinement", True):
        final_contract, markdown = await PolicyWordingRefiner.refine_contract(
            contract=contract,
            citations=sample_citations,
            llm_provider=mock_llm,
            enabled=True,
        )

        assert final_contract.wording_metadata is not None
        assert final_contract.wording_metadata["applied"] is True
        assert final_contract.bottom_line_answer == safe_polish


# ----------------------------------------------------------------------
# 5. Pilot Feedback Telemetry & Compliance Aggregation
# ----------------------------------------------------------------------
def test_pilot_feedback_lifecycle_and_summary():
    FeedbackTelemetryService.clear_pilot_feedback()

    # 1. Reviewer A evaluates Message 1 -> PASS
    req1 = PilotFeedbackRequest(
        message_id="msg-101",
        session_id="sess-pilot-1",
        reviewer_name="Sarah (Legal)",
        reviewer_role="Counsel",
        verdict=PilotVerdict.PASS,
        checklist=PilotChecklist(
            scope_identified=True,
            answers_inquiry=True,
            grounded_evidence=True,
            conditions_surfaced=True,
            conflicts_flagged=True,
            depth_appropriate=True,
            navigation_works=True,
            tone_and_safety=True,
        ),
        notes="Completely accurate notice period. Conditions clearly visible.",
        latency_ms=124.5,
        feature_flags={"enable_adaptive_composition": True, "enable_llm_wording_refinement": True},
        wording_outcome={"requested": True, "applied": True},
        question_type="lookup",
        depth="standard",
    )
    rec1 = FeedbackTelemetryService.record_pilot_feedback(req1)
    assert rec1["verdict"] == "PASS"

    # 2. Reviewer B evaluates Message 2 -> NEEDS_IMPROVEMENT (MISSING_CONDITION)
    req2 = PilotFeedbackRequest(
        message_id="msg-102",
        session_id="sess-pilot-1",
        reviewer_name="Marcus (Procurement)",
        reviewer_role="Procurement Specialist",
        verdict=PilotVerdict.NEEDS_IMPROVEMENT,
        issue_category=PilotIssueCategory.MISSING_CONDITION,
        checklist=PilotChecklist(
            scope_identified=True,
            answers_inquiry=True,
            grounded_evidence=True,
            conditions_surfaced=False,  # Flagged
            conflicts_flagged=True,
            depth_appropriate=True,
            navigation_works=True,
            tone_and_safety=True,
        ),
        notes="Answer covers base rule but Brief view omitted written notice prerequisite.",
        latency_ms=98.2,
        feature_flags={"enable_adaptive_composition": True, "enable_llm_wording_refinement": False},
        wording_outcome=None,
        question_type="procedure",
        depth="brief",
    )
    rec2 = FeedbackTelemetryService.record_pilot_feedback(req2)
    assert rec2["verdict"] == "NEEDS_IMPROVEMENT"

    # Check summary aggregation
    summary = FeedbackTelemetryService.get_pilot_summary()
    assert summary["total_evaluations"] == 2
    assert summary["verdict_distribution"]["PASS"] == 1
    assert summary["verdict_distribution"]["NEEDS_IMPROVEMENT"] == 1
    assert summary["verdict_distribution"]["UNSAFE"] == 0
    assert summary["unsafe_count"] == 0
    assert summary["pass_rate"] == 0.5
    assert summary["issue_category_distribution"]["MISSING_CONDITION"] == 1
    assert summary["checklist_compliance_rates"]["conditions_surfaced"] == 0.5
    assert summary["checklist_compliance_rates"]["scope_identified"] == 1.0
    assert summary["avg_latency_ms"] == round((124.5 + 98.2) / 2, 2)
    assert summary["wording_success_rate"] == 1.0
