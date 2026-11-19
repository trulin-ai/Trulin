import asyncio
import os
import sys
from pathlib import Path

# Add backend directory to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions
from app.ingestion.parsers.evidence_model import ContentRole
from app.validation_gate.models import ClaimLifecycleDecision

EXPECTED = {
    "cl_b9bfd4ee": ContentRole.NON_RULE_CONTEXT,  # "Increasingly..."
    "cl_3708d8a7": ContentRole.NON_RULE_CONTEXT,  # "Otherwise..."
    "cl_a80572ac": ContentRole.DEFINITION,        # "MFA requires..."
    "cl_4dc4a221": ContentRole.NON_RULE_CONTEXT,  # "This approach..."
    "cl_10fb5f92": ContentRole.DEFINITION,        # "Group-based licensing..."
    "cl_3044b056": ContentRole.POLICY_RULE,       # "Device-based CA..."
    "cl_31091783": ContentRole.NON_RULE_CONTEXT,  # "Self-service group..."
    "cl_73c246ba": ContentRole.POLICY_RULE,       # "Owner can approve..."
}

CLAIM_SENTENCES = {
    "cl_b9bfd4ee": "Increasingly, organizations must embrace a mixture of on-premises and cloud applications",
    "cl_3708d8a7": "Otherwise, you can build alerts using the preceding tools",
    "cl_a80572ac": "Microsoft Entra multifactor authentication - multifactor authentication requires a user",
    "cl_4dc4a221": "This approach can provide a proactive first step",
    "cl_10fb5f92": "Group-based licensing - Licenses can be assigned",
    "cl_3044b056": "With device-based Conditional Access policies, you can ensure that access to resources",
    "cl_31091783": "Self-service group management - You can enable users to create",
    "cl_73c246ba": "The owner of the group can approve or deny membership requests",
}

SEARCH_PATHS = [
    REPO_ROOT / "research/validation_50/raw_documents/Microsoft/Technical documentation/Microsoft Entra security operations guide - Microsoft Entra _ Microsoft Learn.pdf",
    REPO_ROOT / "backend/storage/uploads/396f9322-9bca-46bd-842e-a6b0034aca93/Microsoft Entra security operations guide - Microsoft Entra _ Microsoft Learn.pdf",
]

async def run():
    target_path = None
    for p in SEARCH_PATHS:
        if p.exists():
            target_path = p
            break

    if not target_path:
        raise FileNotFoundError(f"Entra PDF not found in search paths: {SEARCH_PATHS}")

    print(f"Loading Microsoft Entra PDF from: {target_path}")
    raw_bytes = target_path.read_bytes()

    res = await UnifiedExtractionPipeline.execute(
        filename=target_path.name,
        raw_bytes=raw_bytes,
        options=UnifiedPipelineOptions(persist_to_db=False),
    )

    claims_by_id = {}
    evals_by_id = {}
    for cand in res.candidates:
        for cid, expected_text in CLAIM_SENTENCES.items():
            key_words = expected_text.split()[:4]
            cand_text = cand.claim_text or ""
            if all(w.lower() in cand_text.lower() for w in key_words):
                claims_by_id[cid] = cand
                eval_res = next((e for e in res.evaluations if e.candidate_id == cand.candidate_id), None)
                if eval_res:
                    evals_by_id[cid] = eval_res

    print("\n" + "=" * 70)
    print("MICROSOFT ENTRA PDF EXTRACTION & GOVERNANCE REPORT")
    print("=" * 70)
    print(f"Total extracted candidates: {len(res.candidates)}")
    print(f"Matched target claims: {len(claims_by_id)}/8\n")

    approved_count = 0
    non_rule_count = 0
    def_count = 0

    for idx, (cid, exp_role) in enumerate(EXPECTED.items(), 1):
        cand = claims_by_id.get(cid)
        ev = evals_by_id.get(cid)
        actual_role = cand.content_role if cand else None
        decision = ev.lifecycle_decision.value if ev else "UNKNOWN"

        if decision == ClaimLifecycleDecision.APPROVE.value:
            approved_count += 1
        if actual_role == ContentRole.NON_RULE_CONTEXT:
            non_rule_count += 1
        elif actual_role == ContentRole.DEFINITION:
            def_count += 1

        match_mark = "✓" if actual_role == exp_role else "✗"
        print(f"#{idx} [{cid}] {match_mark} Role: {actual_role} | Status: {decision} | Pred: {cand.predicate if cand else None}")
        print(f"    Claim text: {cand.claim_text[:80] if cand else 'NOT FOUND'}...\n")

    print("-" * 70)
    print(f"Summary Verification:")
    print(f"  Verified / Approved Policy Rules: {approved_count}/8 (Expected: 2 - #6, #8)")
    print(f"  Non-Rule Context Claims:         {non_rule_count}/8 (Expected: 4 - #1, #2, #4, #7)")
    print(f"  Definitional Claims:             {def_count}/8 (Expected: 2 - #3, #5)")
    print("-" * 70)

    assert len(claims_by_id) == 8, f"Expected 8 claims, matched {len(claims_by_id)}"
    assert approved_count == 2, f"Expected 2 approved, got {approved_count}"
    assert non_rule_count == 4, f"Expected 4 non-rule context, got {non_rule_count}"
    assert def_count == 2, f"Expected 2 definitions, got {def_count}"
    assert claims_by_id["cl_3044b056"].predicate == "is_restricted_to", "Expected #6 predicate 'is_restricted_to'"
    assert claims_by_id["cl_73c246ba"].predicate == "can_approve_or_deny", "Expected #8 predicate 'can_approve_or_deny'"
    assert claims_by_id["cl_a80572ac"].predicate == "has_definition", "Expected #3 predicate 'has_definition'"
    assert claims_by_id["cl_10fb5f92"].predicate == "has_definition", "Expected #5 predicate 'has_definition'"
    print("ALL ACCEPTANCE CRITERIA PASSED!")

if __name__ == "__main__":
    asyncio.run(run())

