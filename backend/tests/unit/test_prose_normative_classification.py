"""
Unit and regression test suite for Layer 5 Prose Normative Classification.
Guarantees:
1. Prose Filter P1: Hedging / promotional language -> ContentRole.NON_RULE_CONTEXT
2. Prose Filter P2: Definitional patterns -> ContentRole.DEFINITION (with predicate has_definition)
3. Prose Filter P3: Capability descriptions -> ContentRole.NON_RULE_CONTEXT
4. Prose Filter P4: Deontic/normative obligations -> ContentRole.POLICY_RULE (eligible for Verified)
5. Microsoft Entra PDF regression fixture with 8 locked claim classifications (2/8 Verified).
"""

from __future__ import annotations

import os
from pathlib import Path
import pytest

from app.extraction.prose_normative_classifier import ProseNormativeClassifier
from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions
from app.ingestion.parsers.evidence_model import ContentRole
from app.validation_gate.models import ClaimLifecycleDecision

EXPECTED = {
    "cl_b9bfd4ee": ContentRole.NON_RULE_CONTEXT,  # "Increasingly..."
    "cl_3708d8a7": ContentRole.NON_RULE_CONTEXT,  # "Otherwise..."
    "cl_a80572ac": ContentRole.DEFINITION,         # "MFA requires..."
    "cl_4dc4a221": ContentRole.NON_RULE_CONTEXT,  # "This approach..."
    "cl_10fb5f92": ContentRole.DEFINITION,         # "Group-based licensing..."
    "cl_3044b056": ContentRole.POLICY_RULE,        # "Device-based CA..."
    "cl_31091783": ContentRole.NON_RULE_CONTEXT,  # "Self-service group..."
    "cl_73c246ba": ContentRole.POLICY_RULE,        # "Owner can approve..."
}

CLAIM_SENTENCES = {
    "cl_b9bfd4ee": "Increasingly, organizations must embrace a mixture of on-premises and cloud applications, which users access with both on–premises and cloud-only accounts.",
    "cl_3708d8a7": "Otherwise, you can build alerts using the preceding tools.",
    "cl_a80572ac": "Microsoft Entra multifactor authentication - multifactor authentication requires a user to provide more than one form of proof for authentication.",
    "cl_4dc4a221": "This approach can provide a proactive first step to securing your environment.",
    "cl_10fb5f92": "Group-based licensing - Licenses can be assigned to groups rather than directly to users.",
    "cl_3044b056": "With device-based Conditional Access policies, you can ensure that access to resources in your environment is only possible with managed devices.",
    "cl_31091783": "Self-service group management - You can enable users to create and manage their own security groups or Microsoft 365 groups in Microsoft Entra ID.",
    "cl_73c246ba": "The owner of the group can approve or deny membership requests and can delegate control of group membership.",
}

ENTRA_PDF_PATHS = [
    Path("research/validation_50/raw_documents/Microsoft/Technical documentation/Microsoft Entra security operations guide - Microsoft Entra _ Microsoft Learn.pdf"),
    Path("backend/storage/uploads/396f9322-9bca-46bd-842e-a6b0034aca93/Microsoft Entra security operations guide - Microsoft Entra _ Microsoft Learn.pdf"),
]


def test_prose_classifier_unit_rules():
    """Tests Filters P1–P4 in isolation across the 8 Entra claims."""
    for claim_id, expected_role in EXPECTED.items():
        sentence = CLAIM_SENTENCES[claim_id]
        classified_role = ProseNormativeClassifier.classify(sentence)
        assert classified_role == expected_role, (
            f"Claim {claim_id} expected {expected_role}, got {classified_role} for text: {sentence}"
        )


def test_prose_classifier_hedging_filter_p1():
    """Filter P1: Hedging and promotional framing must be classified as NON_RULE_CONTEXT."""
    samples = [
        "This approach can provide a significant advantage for modern enterprises.",
        "Increasingly, firms must adopt modern authentication solutions.",
        "We recommend configuring automated backups daily.",
        "This configuration can help reduce attack surface.",
        "Using conditional access may help organizations prevent token theft.",
    ]
    for text in samples:
        role = ProseNormativeClassifier.classify(text)
        assert role == ContentRole.NON_RULE_CONTEXT, f"Expected NON_RULE_CONTEXT for hedging text: '{text}', got {role}"


def test_prose_classifier_capability_filter_p3():
    """Filter P3: Capability statements must be classified as NON_RULE_CONTEXT."""
    samples = [
        "Otherwise, you can build custom alerts using the preceding tools.",
        "You can enable users to self-reset their passwords in the portal.",
        "Administrators: you can create custom security groups dynamically.",
        "You can manage access reviews via Identity Governance.",
    ]
    for text in samples:
        role = ProseNormativeClassifier.classify(text)
        assert role == ContentRole.NON_RULE_CONTEXT, f"Expected NON_RULE_CONTEXT for capability text: '{text}', got {role}"


def test_prose_classifier_definition_filter_p2():
    """Filter P2: Definitional glossary and 'X is Y' patterns must be classified as DEFINITION."""
    samples = [
        "MFA - Multi-factor authentication requires multiple credentials.",
        "Group-based licensing - Licenses can be assigned directly to security groups.",
        "Business Day is defined as any day other than Saturday or Sunday.",
        "Conditional Access is an automated security policy engine.",
    ]
    for text in samples:
        role = ProseNormativeClassifier.classify(text)
        assert role == ContentRole.DEFINITION, f"Expected DEFINITION for text: '{text}', got {role}"


def test_prose_classifier_normative_filter_p4():
    """Filter P4: Operative normative obligations must be classified as POLICY_RULE."""
    samples = [
        "With device-based Conditional Access policies, you can ensure that access to resources in your environment is only possible with managed devices.",
        "The owner of the group can approve or deny membership requests and can delegate control of group membership.",
        "Employees must submit all expense receipts within 30 days of expense date.",
        "The vendor shall provide 30 days prior written notice before scheduled downtime.",
        "Security token verification is required for all external access requests.",
    ]
    for text in samples:
        role = ProseNormativeClassifier.classify(text)
        assert role == ContentRole.POLICY_RULE, f"Expected POLICY_RULE for text: '{text}', got {role}"


@pytest.mark.asyncio
async def test_microsoft_entra_pdf_e2e_regression():
    """
    End-to-end regression on Microsoft Entra PDF:
    Verifies 8/8 claim classifications match EXPECTED fixture,
    definitions get 'has_definition' predicate, and exactly 2/8 are Verified.
    """
    target_path = None
    for p in ENTRA_PDF_PATHS:
        if p.exists():
            target_path = p
            break
        # Also check relative to workspace root
        alt = Path(f"B:/Trulin/{p.as_posix()}")
        if alt.exists():
            target_path = alt
            break

    assert target_path is not None, f"Entra PDF not found in search paths: {ENTRA_PDF_PATHS}"

    raw_bytes = target_path.read_bytes()
    pipeline_res = await UnifiedExtractionPipeline.execute(
        filename=target_path.name,
        raw_bytes=raw_bytes,
        options=UnifiedPipelineOptions(persist_to_db=False),
    )

    claims_by_id = {}
    evals_by_id = {}

    for cand in pipeline_res.candidates:
        for cid, expected_text in CLAIM_SENTENCES.items():
            # Match by normalized prefix or substring
            key_words = expected_text.split()[:4]
            cand_text = cand.claim_text or ""
            if all(w.lower() in cand_text.lower() for w in key_words):
                claims_by_id[cid] = cand
                eval_res = next((e for e in pipeline_res.evaluations if e.candidate_id == cand.candidate_id), None)
                if eval_res:
                    evals_by_id[cid] = eval_res

    # 1. All 8 claims must be discovered and resolved
    assert len(claims_by_id) == 8, f"Expected 8 Entra claims, matched {len(claims_by_id)}: {list(claims_by_id.keys())}"

    # 2. Confirm 8/8 classifications match EXPECTED
    for cid, exp_role in EXPECTED.items():
        cand = claims_by_id[cid]
        assert cand.content_role == exp_role, (
            f"Claim {cid} expected role {exp_role}, got {cand.content_role} (text: '{cand.claim_text[:60]}...')"
        )

    # 3. Confirm #3 and #5 have 'has_definition' predicate
    assert claims_by_id["cl_a80572ac"].predicate == "has_definition", (
        f"MFA claim expected predicate 'has_definition', got '{claims_by_id['cl_a80572ac'].predicate}'"
    )
    assert claims_by_id["cl_10fb5f92"].predicate == "has_definition", (
        f"Group licensing claim expected predicate 'has_definition', got '{claims_by_id['cl_10fb5f92'].predicate}'"
    )

    # 4. Confirm exactly 2/8 claims are certified as Verified (APPROVE)
    approved_cids = [cid for cid, ev in evals_by_id.items() if ev.lifecycle_decision == ClaimLifecycleDecision.APPROVE]
    assert len(approved_cids) == 2, f"Expected exactly 2 Verified claims, got {len(approved_cids)}: {approved_cids}"
    assert set(approved_cids) == {"cl_3044b056", "cl_73c246ba"}, (
        f"Expected #6 (cl_3044b056) and #8 (cl_73c246ba) to be Verified, got {approved_cids}"
    )

    # 5. Confirm the other 6 claims are NOT certified as Verified
    rejected_or_reviewed = [cid for cid, ev in evals_by_id.items() if ev.lifecycle_decision != ClaimLifecycleDecision.APPROVE]
    assert len(rejected_or_reviewed) == 6, f"Expected 6 non-approved claims, got {len(rejected_or_reviewed)}"

