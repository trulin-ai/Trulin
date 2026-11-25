"""
Golden Benchmark Test Suite: Verified Policy Q&A & Conflict-Aware Pathways (Milestones 1 & 2).

Validates the 6 Golden Query Invariants:
1. License Transfer Obligation ("What must a customer do before transferring a license?")
   - Returns consent/notice obligation with verified citations.
2. Administrative Entitlement ("Can an admin use Microsoft Graph to manage groups?")
   - Returns permission with correct tenant scope.
3. Hardware Refund Window ("What is the refund window for physical hardware?")
   - Returns verified window with conditions and exceptions.
4. Tri-State Conflict Pathways ("How long is OneDrive data retained after cancellation?")
   - Returns CONTEXT_DEPENDENT pathways (Path A vs Path B), not a single unsupported number.
5. Non-Normative Section Context ("Explain the general policy section")
   - Returns section context strictly labeled non-normative, not an operative obligation.
6. Fail-Closed Handling ("What is the policy for an unrelated topic?")
   - Returns NO_VERIFIED_RULE with 0.0 grounding score and zero hallucinations.
"""

import pytest
from app.schemas.chat import (
    ConflictClassificationType,
    PolicyAnswerContract,
)
from app.schemas.context import SectionContextItem
from app.services.answer_verifier import AnswerVerifier
from app.services.policy_answer_synthesizer import PolicyAnswerSynthesizer


# =====================================================================
# 1. License Transfer Obligation Benchmark
# =====================================================================

def test_license_transfer_obligation_contract():
    query = "What must a customer do before transferring a license?"
    citations = [
        {
            "source_index": 1,
            "claim_id": "clm-transfer-01",
            "document_id": "doc-mca-01",
            "source_title": "Microsoft Customer Agreement",
            "section": "12.1",
            "claim_text": "No License transfer will be valid unless Customer provides documents sufficient to enable transferee to act as licensee, subject to prior written consent.",
            "subject": "Customer",
            "predicate": "must_obtain_consent_for",
            "object": "License transfer",
            "trust_score": 0.95,
            "certification_tier": "HUMAN_CERTIFIED",
        }
    ]

    contract = PolicyAnswerSynthesizer.synthesize_structured(query, citations)
    markdown = PolicyAnswerSynthesizer.render_markdown(contract)

    assert contract.verification_status == "VERIFIED"
    assert contract.grounding_score >= 0.90
    assert len(contract.verified_claims_used) == 1
    assert contract.verified_claims_used[0].claim_id == "clm-transfer-01"
    assert "consent" in contract.bottom_line_answer.lower() or "transfer" in contract.bottom_line_answer.lower()
    assert "[Source 1]" in contract.bottom_line_answer or "[Source 1]" in markdown
    assert "### 🛡️ Bottom-Line Answer" in markdown
    assert "### 📜 Verified Operative Claims" in markdown


# =====================================================================
# 2. Administrative Role Entitlement Benchmark
# =====================================================================

def test_admin_graph_management_entitlement():
    query = "Can an admin use Microsoft Graph to manage groups?"
    citations = [
        {
            "source_index": 1,
            "claim_id": "clm-graph-01",
            "document_id": "doc-entra-01",
            "source_title": "Microsoft Entra Security Operations Guide",
            "section": "Identity & Access",
            "claim_text": "Administrators are authorized to use Microsoft Graph APIs to manage directory groups and administrative units, provided that role assignments are verified.",
            "subject": "Administrator",
            "predicate": "authorized_to_use",
            "object": "Microsoft Graph APIs",
            "trust_score": 0.92,
            "certification_tier": "AUTOMATED_CERTIFIED",
        }
    ]

    contract = PolicyAnswerSynthesizer.synthesize_structured(query, citations)

    assert contract.verification_status == "VERIFIED"
    assert len(contract.verified_claims_used) == 1
    assert "administrator" in contract.bottom_line_answer.lower()
    assert "groups" in contract.bottom_line_answer.lower() or "microsoft" in contract.bottom_line_answer.lower()
    assert contract.answer_scope.workspace == "policy"
    assert "doc-entra-01" in contract.answer_scope.document_ids


# =====================================================================
# 3. Hardware Refund Window Benchmark
# =====================================================================

def test_hardware_refund_window_and_conditions():
    query = "What is the refund window for physical hardware?"
    citations = [
        {
            "source_index": 1,
            "claim_id": "clm-refund-01",
            "document_id": "doc-terms-01",
            "source_title": "Microsoft Terms of Sale",
            "section": "Returns",
            "claim_text": "Physical hardware returns must be requested within 30 days from delivery, provided that items are in original condition and packaging.",
            "subject": "Customer",
            "predicate": "has_return_window",
            "object": "30 days from delivery",
            "trust_score": 0.98,
            "certification_tier": "HUMAN_CERTIFIED",
        }
    ]

    contract = PolicyAnswerSynthesizer.synthesize_structured(query, citations)
    markdown = PolicyAnswerSynthesizer.render_markdown(contract)

    assert contract.verification_status == "VERIFIED"
    assert "30 days" in contract.bottom_line_answer.lower()
    assert len(contract.conditions) >= 1 or len(contract.verified_claims_used) >= 1
    assert "[Source 1]" in contract.bottom_line_answer


# =====================================================================
# 4. Tri-State Conflict Pathways (OneDrive Retention)
# =====================================================================

def test_onedrive_retention_conflict_pathways():
    query = "How long is OneDrive data retained after cancellation?"
    citations = [
        {
            "source_index": 1,
            "claim_id": "clm-onedrive-01",
            "document_id": "doc-sub-01",
            "source_title": "Cancel a Microsoft 365 Subscription",
            "section": "Data Retention",
            "claim_text": "After cancellation, OneDrive files are retained for 30 days allowing subscription reactivation.",
            "trust_score": 0.91,
        },
        {
            "source_index": 2,
            "claim_id": "clm-onedrive-02",
            "document_id": "doc-refund-01",
            "source_title": "How to Get a Refund on a Microsoft Subscription",
            "section": "Account Closure",
            "claim_text": "After 90 days, we may delete your OneDrive and all files with account closure.",
            "trust_score": 0.89,
        },
    ]
    conflicts_data = [
        {
            "conflict_id": "conf-onedrive-01",
            "conflict_type": "incompatible_numeric_value",
            "severity": "high",
            "description": "Contradiction detected: 30 days post-cancellation vs 90 days post-refund deletion.",
            "claim_a_id": "clm-onedrive-01",
            "claim_b_id": "clm-onedrive-02",
            "source_a": "Cancel a Microsoft 365 Subscription",
            "source_b": "How to Get a Refund on a Microsoft Subscription",
            "claim_a_text": "After cancellation, OneDrive files are retained for 30 days allowing subscription reactivation.",
            "claim_b_text": "After 90 days, we may delete your OneDrive and all files with account closure.",
        }
    ]

    contract = PolicyAnswerSynthesizer.synthesize_structured(
        query=query,
        citations=citations,
        has_conflicts=True,
        conflicts_data=conflicts_data,
    )
    markdown = PolicyAnswerSynthesizer.render_markdown(contract)

    # Invariants for Phase 2 Conflict Handling:
    assert contract.verification_status == "DISPUTED"
    assert contract.conflict_analysis is not None
    assert contract.conflict_analysis.is_conflicted is True
    # Asserts tri-state classification: CONTEXT_DEPENDENT
    assert contract.conflict_analysis.conflict_type == ConflictClassificationType.CONTEXT_DEPENDENT.value
    assert len(contract.conflict_analysis.pathways) == 2
    assert "Path A" in contract.conflict_analysis.pathways[0].path_label
    assert "Path B" in contract.conflict_analysis.pathways[1].path_label
    assert "No autonomous action recommended" in contract.conflict_analysis.recommended_action
    assert "### 🔀 Policy Pathways & Conflict Audit" in markdown


def test_conflict_classification_needs_clarification_on_tables():
    query = "What is the Windows Embedded license matrix?"
    citations = [
        {
            "source_index": 1,
            "claim_id": "clm-tab-01",
            "source_title": "Software Licensing Terms",
            "claim_text": "macOS 3 Windows Embedded Operating Systems | has_col5 | X |",
        }
    ]
    conflicts_data = [
        {
            "conflict_id": "conf-tab-01",
            "conflict_type": "direct_contradiction",
            "severity": "high",
            "description": "Table cell conflict across matrix columns",
            "claim_a_id": "clm-tab-01",
            "claim_b_id": "clm-tab-02",
            "source_a": "Software Licensing Terms Table 1",
            "source_b": "Software Licensing Terms Table 2",
            "claim_a_text": "macOS 3 Windows Embedded | has_col5 | X | scope: col_1",
            "claim_b_text": "Systems Windows 10/11 | has_col5 | X | scope: col_1",
        }
    ]

    contract = PolicyAnswerSynthesizer.synthesize_structured(
        query=query,
        citations=citations,
        has_conflicts=True,
        conflicts_data=conflicts_data,
    )

    assert contract.conflict_analysis is not None
    assert contract.conflict_analysis.conflict_type == ConflictClassificationType.NEEDS_SOURCE_CLARIFICATION.value
    assert "tabular matrices" in contract.conflict_analysis.conflict_summary.lower()


# =====================================================================
# 5. Non-Normative Section Context Decoupling Benchmark
# =====================================================================

def test_section_context_strictly_non_normative():
    query = "Explain the general policy section"
    citations = [
        {
            "source_index": 1,
            "claim_id": "clm-rule-01",
            "document_id": "doc-gen-01",
            "source_title": "Enterprise Agreement",
            "section": "1. Overview",
            "claim_text": "Affiliates may acquire licenses under this Agreement by executing an Enrollment.",
            "section_context": [
                {
                    "document_title": "Enterprise Agreement",
                    "section": "1. Overview",
                    "text": "This Section provides background information on corporate organizational structures and introductory terms.",
                    "is_normative": False,
                }
            ],
            "trust_score": 0.90,
        }
    ]

    contract = PolicyAnswerSynthesizer.synthesize_structured(query, citations)
    markdown = PolicyAnswerSynthesizer.render_markdown(contract)

    # Invariants:
    assert len(contract.section_context) == 1
    assert contract.section_context[0].is_normative is False
    assert "Section Context" in markdown
    assert "Explanatory background only; does not establish an independent rule" in markdown
    # Verify the section text is not cited as a source rule
    assert "[Source 1]" not in contract.section_context[0].text


# =====================================================================
# 6. Fail-Closed Handling on Unrelated Topics
# =====================================================================

def test_fail_closed_unrelated_topic():
    query = "What is our company quantum computing export policy?"
    citations = []  # No verified operative claims found

    contract = PolicyAnswerSynthesizer.synthesize_structured(query, citations)
    markdown = PolicyAnswerSynthesizer.render_markdown(contract)

    assert contract.verification_status == "NO_VERIFIED_RULE"
    assert contract.grounding_score == 0.0
    assert len(contract.verified_claims_used) == 0
    assert "no verified policy records" in contract.bottom_line_answer.lower() or "no verified rule found" in contract.bottom_line_answer.lower()

    # Pass through AnswerVerifier to ensure zero hallucinations / false passes
    v_res = AnswerVerifier.verify(markdown, citations, has_conflicts=False)
    assert v_res.verification_status == "NO_VERIFIED_RULE"
    assert v_res.is_verified is True
    assert len(v_res.hallucination_warnings) == 0
