"""
Unit Test Suite for Adaptive, Evidence-Grounded Response System (Phases A - E).

Validates:
1. PolicyAnswerContract Schema Version 2 backward compatibility and extensions.
2. ResponsePlanner heuristics across all 8 QuestionTypes and depth resolutions.
3. Depth-scope decoupling invariant.
4. Semantic mutation verifier (negation flips, modality changes, numeric drift, dropped citations).
5. Statement-level claim mapping in explanation blocks.
6. Dual-envelope synchronization between structured contract and Markdown.
"""

import pytest

from app.schemas.chat import (
    DisplayDepth,
    ExplanationBlock,
    ExplanationStatement,
    GroundedClaimItem,
    PolicyAnswerContract,
    QuestionType,
    ResponsePlan,
    ScopeSummary,
)
from app.services.answer_verifier import AnswerVerifier
from app.services.policy_answer_synthesizer import PolicyAnswerSynthesizer
from app.services.response_planner import ResponsePlanner


# ==============================================================================
# Group 1: Schema Version 2 & Backward Compatibility
# ==============================================================================

def test_contract_schema_v2_backward_compatibility():
    """V1 legacy instantiation without new fields continues to work seamlessly."""
    v1_contract = PolicyAnswerContract(
        bottom_line_answer="Notice must be provided within 30 days [Source 1].",
        conditions=["Must be in writing."],
        exceptions=["Does not apply to emergency maintenance."],
        verified_claims_used=[],
    )
    assert v1_contract.schema_version == "2"
    assert v1_contract.bottom_line_answer.startswith("Notice must be provided")
    assert len(v1_contract.conditions) == 1
    assert v1_contract.response_plan is None
    assert v1_contract.explanation_blocks == []


def test_contract_schema_v2_with_statement_level_mapping():
    """Schema v2 supports explanation blocks with statement-level claim mapping."""
    stmt1 = ExplanationStatement(
        id="stmt-1",
        text="Either party may terminate the contract upon 30 days' notice [Source 1].",
        claim_ids=["clm-101"],
        source_indices=[1],
        is_normative=True,
        modality="MAY",
    )
    stmt2 = ExplanationStatement(
        id="stmt-2",
        text="The terminating party must provide written notice of material breach [Source 1].",
        claim_ids=["clm-101"],
        source_indices=[1],
        is_normative=True,
        modality="MUST",
    )
    block = ExplanationBlock(
        id="block-1",
        heading="Termination Requirements",
        block_type="checklist",
        statements=[stmt1, stmt2],
    )
    contract = PolicyAnswerContract(
        bottom_line_answer=stmt1.text,
        explanation_blocks=[block],
        scope_summary=ScopeSummary(
            label="Master Services Agreement · v1.0",
            document_ids=["doc-1"],
            resolution_status="resolved",
        ),
    )
    assert len(contract.explanation_blocks) == 1
    assert len(contract.explanation_blocks[0].statements) == 2
    assert contract.explanation_blocks[0].statements[0].claim_ids == ["clm-101"]
    assert contract.scope_summary.label == "Master Services Agreement · v1.0"


# ==============================================================================
# Group 2: Response Planner Question Type Classification
# ==============================================================================

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


def test_planner_lookup_classification(sample_citations):
    plan = ResponsePlanner.plan_response(
        query="What is the refund window for physical hardware?",
        citations=sample_citations,
    )
    assert plan.question_type == QuestionType.LOOKUP
    assert plan.resolved_depth == DisplayDepth.BRIEF
    assert "summary" in plan.required_sections


def test_planner_procedure_classification(sample_citations):
    plan = ResponsePlanner.plan_response(
        query="What must a customer do before transferring a license?",
        citations=sample_citations,
    )
    assert plan.question_type == QuestionType.PROCEDURE
    assert plan.resolved_depth == DisplayDepth.STANDARD
    assert plan.group_by == "step"
    assert "prerequisites" in plan.required_sections


def test_planner_comparison_classification(sample_citations):
    multi_citations = sample_citations + [
        {
            "source_index": 2,
            "claim_id": "clm-2",
            "document_id": "doc-std",
            "source_title": "Standard Terms",
            "claim_text": "Refund within 14 days.",
            "evidence": "Refund within 14 days.",
        }
    ]
    plan = ResponsePlanner.plan_response(
        query="What is the difference between Enterprise and Standard terms?",
        citations=multi_citations,
    )
    assert plan.question_type == QuestionType.COMPARISON
    assert plan.group_by == "criterion"
    assert "comparison" in plan.required_sections


def test_planner_overview_classification(sample_citations):
    plan = ResponsePlanner.plan_response(
        query="Summarize the key provisions of our data protection policy",
        citations=sample_citations,
    )
    assert plan.question_type == QuestionType.OVERVIEW
    assert plan.resolved_depth == DisplayDepth.DETAILED


def test_planner_conflict_classification(sample_citations):
    plan = ResponsePlanner.plan_response(
        query="How long is data retained after cancellation?",
        citations=sample_citations,
        has_conflicts=True,
    )
    assert plan.question_type == QuestionType.CONFLICT
    assert plan.group_by == "pathway"
    assert "pathways" in plan.required_sections


def test_planner_unsupported_classification():
    plan = ResponsePlanner.plan_response(
        query="What is the policy on quantum teleportation?",
        citations=[],
    )
    assert plan.question_type == QuestionType.UNSUPPORTED
    assert plan.resolved_depth == DisplayDepth.BRIEF
    assert "abstention" in plan.required_sections


# ==============================================================================
# Group 3: Depth-Scope Decoupling Invariant
# ==============================================================================

def test_depth_scope_decoupling(sample_citations):
    """Changing requested depth adjusts resolved depth without altering citation scope."""
    plan_brief = ResponsePlanner.plan_response(
        query="Explain the license transfer rules",
        citations=sample_citations,
        requested_depth="brief",
    )
    plan_detailed = ResponsePlanner.plan_response(
        query="Explain the license transfer rules",
        citations=sample_citations,
        requested_depth="detailed",
    )
    assert plan_brief.resolved_depth == DisplayDepth.BRIEF
    assert plan_detailed.resolved_depth == DisplayDepth.DETAILED
    assert plan_brief.scope_status == plan_detailed.scope_status == "resolved"


# ==============================================================================
# Group 4: Semantic Mutation Verifier Invariants
# ==============================================================================

def test_mutation_verifier_rejects_negation_introduction():
    """Reject rewrites that flip positive statements into negatives ('is required' -> 'is not required')."""
    original = "Written approval is required prior to license transfer [Source 1]."
    mutated = "Written approval is not required prior to license transfer [Source 1]."
    is_safe, reason = AnswerVerifier.verify_statement_mutation(original, mutated, required_modality="MUST")
    assert is_safe is False
    assert "polarity_flip_negation_introduced" in reason


def test_mutation_verifier_rejects_negation_dropping():
    """Reject rewrites that drop negative prohibitions ('in no event' -> 'either party will')."""
    original = "In no event will either party be liable for indirect damages [Source 1]."
    mutated = "Either party will be liable for indirect damages [Source 1]."
    is_safe, reason = AnswerVerifier.verify_statement_mutation(original, mutated)
    assert is_safe is False
    assert "polarity_flip_negation_dropped" in reason


def test_mutation_verifier_rejects_modality_escalation():
    """Reject rewrites that escalate permission ('may') to mandatory obligation ('must')."""
    original = "A customer may request a policy extension within 14 days [Source 1]."
    mutated = "A customer must request a mandatory policy extension within 14 days [Source 1]."
    is_safe, reason = AnswerVerifier.verify_statement_mutation(original, mutated, required_modality="MAY")
    assert is_safe is False
    assert "modality_mutation" in reason


def test_mutation_verifier_rejects_numeric_drift():
    """Reject rewrites that alter numeric values (30 days -> 60 days)."""
    original = "Notice must be provided within 30 days of breach [Source 1]."
    mutated = "Notice must be provided within 60 days of breach [Source 1]."
    is_safe, reason = AnswerVerifier.verify_statement_mutation(original, mutated, required_modality="MUST")
    assert is_safe is False
    assert "numeric_mutation" in reason


def test_mutation_verifier_rejects_dropped_citation():
    """Reject rewrites that drop [Source X] references."""
    original = "Either party may terminate on 30 days notice [Source 1]."
    mutated = "Either party may terminate on 30 days notice."
    is_safe, reason = AnswerVerifier.verify_statement_mutation(original, mutated, required_modality="MAY")
    assert is_safe is False
    assert "citation_mutation" in reason


def test_mutation_verifier_accepts_clean_executive_polish():
    """Accept executive paraphrasing that preserves facts, modality, negation, and citations."""
    original = "Either party may terminate the agreement on 30 days' notice for material breach [Source 1]."
    polished = "Either party is permitted to terminate this contract on 30 days' notice in the event of material breach [Source 1]."
    is_safe, reason = AnswerVerifier.verify_statement_mutation(original, polished, required_modality="MAY")
    assert is_safe is True
    assert reason is None


def test_mutation_verifier_rejects_temporal_preposition_mutation():
    """Reject rewrites that flip temporal boundaries ('within 30 days' -> 'after 30 days')."""
    original = "Return requests must be submitted within 30 days of delivery [Source 1]."
    mutated = "Return requests must be submitted after 30 days of delivery [Source 1]."
    is_safe, reason = AnswerVerifier.verify_statement_mutation(original, mutated, required_modality="MUST")
    assert is_safe is False
    assert "temporal_mutation" in reason


def test_mutation_verifier_rejects_dropped_conditional_qualification():
    """Reject rewrites that drop material exception conditions like 'unless otherwise agreed'."""
    original = "Direct liability is capped at fees paid, unless otherwise agreed in writing [Source 1]."
    mutated = "Direct liability is capped at total fees paid [Source 1]."
    is_safe, reason = AnswerVerifier.verify_statement_mutation(original, mutated)
    assert is_safe is False
    assert "conditional_qualification_dropped" in reason


def test_mutation_verifier_rejects_conjunction_weakening():
    """Reject rewrites that weaken mandatory conjunction ('and') into disjunctive permission ('or')."""
    original = "Customer must provide both documented notice and written transferee consent [Source 1]."
    mutated = "Customer must provide documented notice or written transferee consent [Source 1]."
    is_safe, reason = AnswerVerifier.verify_statement_mutation(original, mutated, required_modality="MUST")
    assert is_safe is False
    assert "logical_weakening_mutation" in reason


def test_depth_content_differentiation(sample_citations):
    """Verifies that Brief, Standard, and Detailed produce genuinely differentiated content volumes."""
    contract_brief = PolicyAnswerSynthesizer.synthesize_structured(
        query="What notice is required before terminating for material breach?",
        citations=sample_citations,
        requested_depth="brief",
    )
    contract_standard = PolicyAnswerSynthesizer.synthesize_structured(
        query="What notice is required before terminating for material breach?",
        citations=sample_citations,
        requested_depth="standard",
    )
    contract_detailed = PolicyAnswerSynthesizer.synthesize_structured(
        query="What notice is required before terminating for material breach?",
        citations=sample_citations,
        requested_depth="detailed",
    )

    stmts_brief = [s for b in contract_brief.explanation_blocks for s in b.statements]
    stmts_standard = [s for b in contract_standard.explanation_blocks for s in b.statements]
    stmts_detailed = [s for b in contract_detailed.explanation_blocks for s in b.statements]

    assert len(stmts_brief) < len(stmts_standard)
    assert len(stmts_standard) < len(stmts_detailed)
    assert any(b.id == "block-detailed-governance" for b in contract_detailed.explanation_blocks)


@pytest.mark.asyncio
async def test_live_structured_wording_refinement_success(sample_citations):
    """Exercises the live wording refiner path when valid structured JSON is returned."""
    from app.llm.mock_provider import MockLLMProvider
    from app.services.policy_wording_refiner import PolicyWordingRefiner

    contract = PolicyAnswerSynthesizer.synthesize_structured(
        query="What must a customer do before transferring a license?",
        citations=sample_citations,
        requested_depth="standard",
    )

    # Valid structured JSON completion preserving facts, modality, negation, and citations
    valid_json = (
        '{\n'
        '  "statements": [\n'
        '    {\n'
        '      "id": "stmt-1",\n'
        '      "text": "No license transfer is valid unless the licensee provides 30 days prior written notice and written consent [Source 1]."\n'
        '    }\n'
        '  ]\n'
        '}'
    )

    mock_llm = MockLLMProvider()
    mock_llm.mock_completion_text = valid_json

    refined_contract, refined_md = await PolicyWordingRefiner.refine_contract(
        contract=contract,
        citations=sample_citations,
        llm_provider=mock_llm,
        enabled=True,
    )

    assert refined_contract.wording_metadata is not None
    assert refined_contract.wording_metadata.get("applied") is True
    assert "No license transfer is valid unless the licensee" in refined_contract.bottom_line_answer
    assert "[Source 1]" in refined_md


# ==============================================================================
# Group 5: Synthesizer Composition & Dual Envelope Synchronization
# ==============================================================================

def test_synthesizer_produces_synchronized_dual_envelope(sample_citations):
    contract = PolicyAnswerSynthesizer.synthesize_structured(
        query="What notice is required before terminating for material breach?",
        citations=sample_citations,
        workspace="procurement",
    )
    assert contract.schema_version == "2"
    assert contract.scope_summary is not None
    assert "Commercial Licensing Agreement" in contract.scope_summary.label
    assert len(contract.explanation_blocks) > 0

    markdown = PolicyAnswerSynthesizer.render_markdown(contract)
    assert "**Scope:**" in markdown
    assert "### 🛡️ Bottom-Line Answer" in markdown
    assert "[Source 1]" in markdown
    assert "🔒 **Verification Status:** `VERIFIED`" in markdown
