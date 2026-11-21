"""
Adaptive Response System: 12-Scenario Focused Acceptance Suite.

Executes and verifies the 12 key scenarios outlined in the acceptance review:
- S01: Simple lookup (Brief direct answer + qualifications)
- S02: Interpretation (Standard explanation without invented implications)
- S03: Multi-part question (Multi-clause coverage with explicit unanswered flagging)
- S04: Comparison (Separate criteria and isolated rule pathways)
- S05: Procedure (Numbered Required Steps, no premature completion checks)
- S06: Conflict (Isolated Path A vs Path B at all depths)
- S07: Partial evidence (Distinguishes verified cap from unverified threshold)
- S08: Follow-up scope (Conversational scope inheritance)
- S09: Depth differentiation (Brief vs Standard vs Detailed content volume)
- S10: Successful LLM rewrite (Full semantic preservation & structured JSON)
- S11: Failed rewrite fallback (Mutation rejected & clean fallback recorded)
- S12: Legacy response rendering (V1 contract renders without error)
"""

import asyncio
import json
import os
import sys
import uuid
from typing import Any, Dict, List

# Ensure backend path is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.db.database import AsyncSessionLocal
from app.llm.mock_provider import MockLLMProvider
from app.schemas.chat import DisplayDepth, PolicyAnswerContract, QuestionType
from app.services.answer_verifier import AnswerVerifier
from app.services.chat_service import ChatService
from app.services.policy_answer_synthesizer import PolicyAnswerSynthesizer
from app.services.policy_wording_refiner import PolicyWordingRefiner
from app.services.response_planner import ResponsePlanner

ORG_ID = uuid.UUID("12d07bef-6f37-4584-a8a8-0480c2b7e39c")


async def run_scenario_battery() -> Dict[str, Any]:
    print("=" * 70)
    print("STARTING 12-SCENARIO ADAPTIVE RESPONSE ACCEPTANCE SUITE")
    print("=" * 70)

    results = []

    # --------------------------------------------------------------------------
    # S01: Simple Lookup
    # --------------------------------------------------------------------------
    print("\n--- [S01] Simple Lookup ---")
    plan1 = ResponsePlanner.plan_response(
        query="What is the refund window for physical Microsoft hardware?",
        citations=[{"source_index": 1, "claim_text": "30 days from delivery", "evidence": "30 days"}],
    )
    s01_pass = (plan1.question_type == QuestionType.LOOKUP and plan1.resolved_depth == DisplayDepth.BRIEF)
    print(f"Question Type: {plan1.question_type.value}, Depth: {plan1.resolved_depth.value} -> {'PASSED' if s01_pass else 'FAILED'}")
    results.append({"scenario": "S01_Simple_Lookup", "passed": s01_pass})

    # --------------------------------------------------------------------------
    # S02: Interpretation
    # --------------------------------------------------------------------------
    print("\n--- [S02] Interpretation ---")
    plan2 = ResponsePlanner.plan_response(
        query="What does the customer data protection restriction mean?",
        citations=[{"source_index": 1, "claim_text": "Customer data is used only for services", "evidence": "used only"}],
    )
    s02_pass = (plan2.question_type == QuestionType.INTERPRETATION and plan2.resolved_depth == DisplayDepth.STANDARD)
    print(f"Question Type: {plan2.question_type.value}, Depth: {plan2.resolved_depth.value} -> {'PASSED' if s02_pass else 'FAILED'}")
    results.append({"scenario": "S02_Interpretation", "passed": s02_pass})

    # --------------------------------------------------------------------------
    # S03: Multi-part Question
    # --------------------------------------------------------------------------
    print("\n--- [S03] Multi-part Question ---")
    unanswered = ResponsePlanner.detect_unanswered_parts(
        query="What is the notice period for breach, and what about our quantum teleportation policy?",
        citations=[{"source_index": 1, "claim_text": "30 days notice for breach", "evidence": "30 days"}],
    )
    s03_pass = len(unanswered) > 0 and "quantum teleportation" in unanswered[0].lower()
    print(f"Unanswered Clauses Flagged: {unanswered} -> {'PASSED' if s03_pass else 'FAILED'}")
    results.append({"scenario": "S03_Multi_Part_Question", "passed": s03_pass})

    # --------------------------------------------------------------------------
    # S04: Comparison
    # --------------------------------------------------------------------------
    print("\n--- [S04] Comparison ---")
    plan4 = ResponsePlanner.plan_response(
        query="What is the difference between Enterprise and Standard warranty terms?",
        citations=[{"source_index": 1, "claim_text": "Enterprise 30 days"}, {"source_index": 2, "claim_text": "Standard 14 days"}],
    )
    s04_pass = (plan4.question_type == QuestionType.COMPARISON and plan4.group_by == "criterion")
    print(f"Question Type: {plan4.question_type.value}, Group By: {plan4.group_by} -> {'PASSED' if s04_pass else 'FAILED'}")
    results.append({"scenario": "S04_Comparison", "passed": s04_pass})

    # --------------------------------------------------------------------------
    # S05: Procedure
    # --------------------------------------------------------------------------
    print("\n--- [S05] Procedure ---")
    plan5 = ResponsePlanner.plan_response(
        query="What must a customer do before transferring a license?",
        citations=[{"source_index": 1, "claim_text": "Provide notice and written consent"}],
    )
    contract5 = PolicyAnswerSynthesizer.synthesize_structured(
        query="What must a customer do before transferring a license?",
        citations=[{
            "source_index": 1, "claim_id": "c1", "source_title": "Licensing Terms",
            "claim_text": "Provide notice and written consent", "evidence": "Provide notice and written consent",
            "subject": "Customer", "predicate": "must provide", "object": "documented notice and written consent",
            "modality": "MUST"
        }],
    )
    proc_blocks = [b for b in contract5.explanation_blocks if b.block_type == "checklist"]
    s05_pass = (plan5.question_type == QuestionType.PROCEDURE and len(proc_blocks) > 0 and proc_blocks[0].heading == "Required Operational Steps")
    print(f"Procedure Block: {proc_blocks[0].heading if proc_blocks else 'None'} -> {'PASSED' if s05_pass else 'FAILED'}")
    results.append({"scenario": "S05_Procedure", "passed": s05_pass})

    # --------------------------------------------------------------------------
    # S06: Conflict
    # --------------------------------------------------------------------------
    print("\n--- [S06] Conflict ---")
    plan6 = ResponsePlanner.plan_response(
        query="How long is data retained after cancellation?",
        citations=[{"source_index": 1, "claim_text": "Retained 6 months"}, {"source_index": 2, "claim_text": "Retained 12 months"}],
        has_conflicts=True,
    )
    s06_pass = (plan6.question_type == QuestionType.CONFLICT and plan6.group_by == "pathway")
    print(f"Conflict Pathway Grouping: {plan6.group_by} -> {'PASSED' if s06_pass else 'FAILED'}")
    results.append({"scenario": "S06_Conflict", "passed": s06_pass})

    # --------------------------------------------------------------------------
    # S07: Partial Evidence
    # --------------------------------------------------------------------------
    print("\n--- [S07] Partial Evidence ---")
    res7 = AnswerVerifier.verify(
        synthesized_answer="Tier 2 support can issue up to $500 discretionary credits [Source 1].",
        citations=[{"source_index": 1, "claim_text": "Discretionary credits capped at $250 without approval."}],
    )
    s07_pass = (res7.is_verified is False or len(res7.unverified_numbers) > 0)
    print(f"Unverified threshold flagged: {res7.unverified_numbers} -> {'PASSED' if s07_pass else 'FAILED'}")
    results.append({"scenario": "S07_Partial_Evidence", "passed": s07_pass})

    # --------------------------------------------------------------------------
    # S08: Follow-up Scope
    # --------------------------------------------------------------------------
    print("\n--- [S08] Follow-up Scope ---")
    async with AsyncSessionLocal() as session:
        chat_service = ChatService(session)
        resolved_q = await chat_service.resolver.resolve_query(
            "What is the notice period under this agreement?",
            [{"role": "user", "content": "Tell me about the Master Services Agreement"}]
        )
    s08_pass = bool("master services agreement" in resolved_q.lower() or "msa" in resolved_q.lower())
    print(f"Resolved Multi-turn Query: '{resolved_q}' -> {'PASSED' if s08_pass else 'FAILED'}")
    results.append({"scenario": "S08_Follow_Up_Scope", "passed": s08_pass})

    # --------------------------------------------------------------------------
    # S09: Depth Differentiation
    # --------------------------------------------------------------------------
    print("\n--- [S09] Depth Differentiation ---")
    c_brief = PolicyAnswerSynthesizer.synthesize_structured(
        query="Explain license termination",
        citations=[{"source_index": 1, "claim_id": "c1", "source_title": "MSA", "claim_text": "30 days notice", "evidence": "30 days"}],
        requested_depth="brief",
    )
    c_detailed = PolicyAnswerSynthesizer.synthesize_structured(
        query="Explain license termination",
        citations=[{"source_index": 1, "claim_id": "c1", "source_title": "MSA", "claim_text": "30 days notice", "evidence": "30 days"}],
        requested_depth="detailed",
    )
    stmts_b = sum(len(b.statements) for b in c_brief.explanation_blocks)
    stmts_d = sum(len(b.statements) for b in c_detailed.explanation_blocks)
    s09_pass = (stmts_b < stmts_d and any(b.id == "block-detailed-governance" for b in c_detailed.explanation_blocks))
    print(f"Brief statements: {stmts_b}, Detailed statements: {stmts_d} -> {'PASSED' if s09_pass else 'FAILED'}")
    results.append({"scenario": "S09_Depth_Differentiation", "passed": s09_pass})

    # --------------------------------------------------------------------------
    # S10: Successful LLM Rewrite
    # --------------------------------------------------------------------------
    print("\n--- [S10] Successful LLM Rewrite ---")
    contract10 = PolicyAnswerSynthesizer.synthesize_structured(
        query="What notice is required before terminating for breach?",
        citations=[{"source_index": 1, "claim_id": "c1", "source_title": "MSA", "claim_text": "Either party may terminate on 30 days notice for breach.", "evidence": "30 days"}],
        requested_depth="standard",
    )
    mock_success = MockLLMProvider()
    mock_success.mock_completion_text = (
        '{"statements": [{"id": "stmt-1", "text": "Either party is permitted to terminate this agreement upon 30 days notice for material breach [Source 1]."}]}'
    )
    ref_contract, _ = await PolicyWordingRefiner.refine_contract(
        contract=contract10,
        citations=[{"source_index": 1, "claim_id": "c1", "source_title": "MSA", "claim_text": "Either party may terminate on 30 days notice for breach.", "evidence": "30 days"}],
        llm_provider=mock_success,
        enabled=True,
    )
    s10_pass = (ref_contract.wording_metadata is not None and ref_contract.wording_metadata.get("applied") is True)
    print(f"Wording refiner applied: {ref_contract.wording_metadata} -> {'PASSED' if s10_pass else 'FAILED'}")
    results.append({"scenario": "S10_Successful_LLM_Rewrite", "passed": s10_pass})

    # --------------------------------------------------------------------------
    # S11: Failed Rewrite Fallback (Mutation Detected)
    # --------------------------------------------------------------------------
    print("\n--- [S11] Failed Rewrite Fallback ---")
    contract11 = PolicyAnswerSynthesizer.synthesize_structured(
        query="What notice is required before terminating for breach?",
        citations=[{"source_index": 1, "claim_id": "c1", "source_title": "MSA", "claim_text": "30 days notice", "evidence": "30 days"}],
    )
    mock_fail = MockLLMProvider()
    # Mutates 30 days to 90 days and flips modality to MUST
    mock_fail.mock_completion_text = (
        '{"statements": [{"id": "stmt-1", "text": "Both parties must terminate after 90 days notice [Source 1]."}]}'
    )
    ref_fail_contract, _ = await PolicyWordingRefiner.refine_contract(
        contract=contract11,
        citations=[{"source_index": 1, "claim_id": "c1", "source_title": "MSA", "claim_text": "30 days notice", "evidence": "30 days"}],
        llm_provider=mock_fail,
        enabled=True,
    )
    s11_pass = (ref_fail_contract.wording_metadata is not None and ref_fail_contract.wording_metadata.get("applied") is False)
    print(f"Unsafe rewrite rejected cleanly: {ref_fail_contract.wording_metadata} -> {'PASSED' if s11_pass else 'FAILED'}")
    results.append({"scenario": "S11_Failed_Rewrite_Fallback", "passed": s11_pass})

    # --------------------------------------------------------------------------
    # S12: Legacy Saved Response Compatibility
    # --------------------------------------------------------------------------
    print("\n--- [S12] Legacy Saved Response Compatibility ---")
    legacy = PolicyAnswerContract(
        bottom_line_answer="Governing policy specifies return within 30 days [Source 1].",
        conditions=["Item in original packaging."],
        exceptions=["Software products."],
        verified_claims_used=[],
    )
    rendered_legacy_md = PolicyAnswerSynthesizer.render_markdown(legacy)
    s12_pass = ("### 🛡️ Bottom-Line Answer" in rendered_legacy_md and "### ⚖️ Conditions & Exceptions" in rendered_legacy_md)
    print(f"Legacy Markdown Rendered without error -> {'PASSED' if s12_pass else 'FAILED'}")
    results.append({"scenario": "S12_Legacy_Saved_Response", "passed": s12_pass})

    passed_count = sum(1 for r in results if r["passed"])
    print("\n" + "=" * 70)
    print(f"ACCEPTANCE BATTERY COMPLETE: {passed_count}/{len(results)} PASSED ({passed_count/len(results)*100:.1f}%)")
    print("=" * 70)

    return {"total": len(results), "passed": passed_count, "results": results}


if __name__ == "__main__":
    asyncio.run(run_scenario_battery())
