"""
Tests for Deontic Modality Classification and Table Metadata Segregation.
Ensures that:
1. Revision history tables are routed to metadata/provenance, NOT emitted as policy claims.
2. Table of contents / section tables are routed to outline metadata, NOT emitted as policy claims.
3. Sign-off / approver tables are routed to authority records, NOT emitted as policy claims.
4. Purely descriptive guidance (e.g. 'The primary goal is...') is filtered out.
5. Table matrix claims and normative obligations/prohibitions are extracted with clean S-P-O and explicit deontic modalities.
"""

import uuid
import pytest
from app.ingestion.envelope import EnvelopeFactory, SourceIntent
from app.ingestion.parsers.document_parser import DocumentParser
from app.extraction.candidate_discovery import CandidateDiscoveryEngine
from app.extraction.extractors.deterministic_extractor import DeterministicSchemaExtractor
from app.extraction.extractors.domain_rule_extractor import DomainRuleExtractor
from app.extraction.deontic_classifier import DeonticClassifier
from app.extraction.models import ExtractionStrategyType


@pytest.fixture
def org_and_source():
    return uuid.uuid4(), uuid.uuid4()


@pytest.mark.asyncio
async def test_notice_period_metadata_segregation(org_and_source):
    org_id, src_id = org_and_source

    document_content = """# Employees Notice Period Policy v1.5
The unauthorized use or disclosure of this information in any media is prohibited.

## 1. Table of Contents
| Scope | Section | Title |
| Policy objectives and transition guidelines | Section 1 | Purpose |
| Permanent employees, interns & contractors | Section 2 | Applicability |
| Operational notice requirements | Section 3 | Policy Framework |

## 2. Policy Purpose
The primary goal is to provide clear guidance on maximum durations and payout options if the notice period cannot be fully served.
It outlines the expected duration an employee must continue working after indicating their intention to leave.

## 3. Grade & Duration Matrix
| Level & Grade | Group Category | Maximum Duration Confirmed | Probationers |
| A (A1 & A2) | CXO | 90 Days | 15 days |
| B (B1 & B2) | Senior Management | 90 Days | 15 days |
| C (C1, C2 & C3) | Middle Management | 60 Days | 15 days |
| D (D1, D2 & D3) | Junior Management | 30 Days | 15 days |
| E (E1, E2 & E3) | Fellow | 30 Days | 15 days |

## 4. Offboarding Rules
- Employees must return all Wingify property upon offboarding.
- Shipping costs will be fully covered by Wingify through a mutually agreed-upon method.
- Full & Final Settlement Deductions: Covers deductions including asset retention, loans, and tax reconciliation.
- WFH Allowance will be recovered based on the Home Office Allowance Policy if the exit is within a year of joining.

## 5. Revision History
| Ver # | Ver. Date | Description | Prepared By | Approved By |
| 1.0 | 19-Jun-2017 | First Release | People Success | CEO |
| 1.5 | 15-Jan-2025 | Comprehensive Policy Revision and Updation | People Success | CEO |

## 6. Approvers
| Role | Name | Designation | Status / Sign-off |
| Chief Executive Officer | Sparsh Gupta | Document Approver | Signed off: 7-May-2025 |
| Director, People Success | Tanisha Goyal | Document Reviewer | Reviewed: 15-Jan-2025 |
"""

    envelope = EnvelopeFactory.create_from_file_upload(
        filename="Employees_Notice_Period_Policy_v1.5.md",
        raw_bytes=document_content.encode("utf-8"),
        parsed_content=document_content,
        organization_id=org_id,
        source_id=src_id,
        document_type="policy",
        source_intent=SourceIntent.GOVERNANCE_POLICY,
    )

    # 1. Parse document into evidence units
    evidence = await DocumentParser.parse(envelope)
    assert len(evidence.units) > 0

    # 2. Candidate Discovery: Verify metadata tables and descriptive prose are filtered
    candidates = []
    skipped_reasons = []
    for u in evidence.units:
        is_cand, strat, reason = CandidateDiscoveryEngine.is_candidate(u)
        if is_cand:
            candidates.append((u, strat))
        else:
            skipped_reasons.append(reason)

    # Table of contents, revision history, and sign-offs must be skipped
    toc_skipped = any("table of contents" in r.lower() or "section outline" in r.lower() for r in skipped_reasons)
    rev_skipped = any("revision history" in r.lower() for r in skipped_reasons)
    signoff_skipped = any("approver sign-off" in r.lower() for r in skipped_reasons)
    descriptive_skipped = any("guidance or purpose" in r.lower() for r in skipped_reasons)

    assert toc_skipped, "Table of contents rows should be filtered from candidate claims"
    assert rev_skipped, "Revision history rows should be filtered from candidate claims"
    assert signoff_skipped, "Sign-off rows should be filtered from candidate claims"
    assert descriptive_skipped, "Descriptive purpose clauses should be filtered from candidate claims"

    # 3. Extract claims from eligible candidate units
    all_extracted_claims = []
    for u, strat in candidates:
        if strat == ExtractionStrategyType.TABLE_AWARE:
            claims = DeterministicSchemaExtractor.extract_from_unit(u)
            all_extracted_claims.extend(claims)
        elif strat in (ExtractionStrategyType.DOMAIN_RULES, ExtractionStrategyType.LLM_SEMANTIC):
            claims = DomainRuleExtractor.extract_from_unit(u)
            all_extracted_claims.extend(claims)

    # Should have exactly 10 table matrix claims (5 confirmed + 5 probationers) + 5 atomic deductions + ~3 operative rules
    # Total claims should be ~18 (NOT 63!)
    assert 14 <= len(all_extracted_claims) <= 20, f"Expected 14-20 crisp policy claims, got {len(all_extracted_claims)}"

    # 4. Check Deontic Modalities
    modalities = {c.modality for c in all_extracted_claims}
    assert "POLICY_FACT" in modalities, "Grade durations should be typed as POLICY_FACT"
    assert "PROHIBITION" in modalities or "OBLIGATION" in modalities, "Operative rules should have OBLIGATION or PROHIBITION"

    # Check that NO claims have raw markdown `**Section` or `Scope ... specifies`
    for c in all_extracted_claims:
        assert "**" not in c.claim_text, f"Claim text contains raw markdown bold: {c.claim_text}"
        assert "`" not in c.claim_text, f"Claim text contains raw backticks: {c.claim_text}"
        assert not c.claim_text.startswith("Scope"), f"Claim text should not be a TOC row: {c.claim_text}"
        assert not c.claim_text.startswith("Ver #"), f"Claim text should not be a revision row: {c.claim_text}"
        assert not c.claim_text.startswith("Role"), f"Claim text should not be a sign-off row: {c.claim_text}"

    # Verify Grade C Middle Management claim details and table grid locator
    grade_c_claim = next((c for c in all_extracted_claims if "Grade C" in c.subject and "60" in str(c.object)), None)
    assert grade_c_claim is not None, "Grade C confirmed 60-day claim not found"
    assert grade_c_claim.modality == "POLICY_FACT"
    assert grade_c_claim.subject == "Employees in Grade C (C1, C2 & C3) (Middle Management)"
    assert "60 Days" in grade_c_claim.object
    assert "60 Days" in grade_c_claim.claim_text and "has_confirmed_notice_duration" in grade_c_claim.claim_text
    assert "table_grid" in grade_c_claim.locator, "Table claim must preserve table_grid locator coordinates"
    assert grade_c_claim.locator["table_grid"]["cell_value"] == "60 Days"

    # Verify atomic WFH allowance deduction claim and condition
    wfh_claim = next((c for c in all_extracted_claims if "wfh allowance" in c.claim_text.lower()), None)
    assert wfh_claim is not None, "Atomic WFH allowance recovery claim not found"
    assert len(wfh_claim.conditions) > 0, "WFH allowance recovery must retain explicit condition"
    assert "1 year" in wfh_claim.conditions[0], f"Condition should specify 1 year, got {wfh_claim.conditions}"

    # Verify shipping costs is classified as POLICY_FACT, not OBLIGATION
    shipping_claim = next((c for c in all_extracted_claims if "Shipping costs" in c.claim_text), None)
    assert shipping_claim is not None, "Shipping costs claim not found"
    assert shipping_claim.modality == "POLICY_FACT", f"Shipping costs should be POLICY_FACT, got {shipping_claim.modality}"

    # Verify no deduction claims have hallucinated 'annual' or 'beyond accrual'
    for c in all_extracted_claims:
        if "tax" in c.claim_text.lower():
            assert "annual" not in c.claim_text.lower(), f"Tax claim must not hallucinate 'annual': {c.claim_text}"
        if "leave" in c.claim_text.lower():
            assert "beyond accrual" not in c.claim_text.lower(), f"Leave claim must not hallucinate 'beyond accrual': {c.claim_text}"

    # Regression Test for Claim #20: Subject and predicate must be supported by that claim's own evidence
    from app.extraction.models import CandidateClaim
    from app.validation_gate.evaluators import MeaningEvaluator
    from app.validation_gate.decision_engine import ClaimLifecycleDecisionEngine
    from app.validation_gate.models import ClaimLifecycleDecision, MeaningStatus

    # Fabricate the exact erroneous Claim #20
    mismatched_claim_20 = CandidateClaim.create(
        envelope_id=envelope.envelope_id,
        unit_id=str(uuid.uuid4()),
        asset_id=envelope.asset_id,
        claim_text="The primary goal is to provide clear guidance on maximum durations and payout options if the notice period cannot be fully served.",
        subject="Enterprise Information Recipients",
        predicate="prohibited_from_unauthorized_disclosure",
        object_="Confidential Policy Information",
        evidence_text_span="The primary goal is to provide clear guidance on maximum durations and payout options if the notice period cannot be fully served.",
        modal_operator="prohibits",
        modality="PROHIBITION",
        claim_type="security_policy",
        extraction_strategy=ExtractionStrategyType.DOMAIN_RULES,
        confidence=0.95,
    )

    mismatched_claim_20.status = "verified"
    mismatched_claim_20.verification_plugin = "ExactMatchVerificationPlugin"
    meaning_eval = MeaningEvaluator.evaluate(mismatched_claim_20)
    assert not meaning_eval.passed, "MeaningEvaluator must fail when asserted subject has no grounding in evidence"
    assert meaning_eval.status == MeaningStatus.UNSUPPORTED.value
    assert "Subject-Evidence mismatch" in meaning_eval.reason

    gate_eval = ClaimLifecycleDecisionEngine.evaluate_candidate(mismatched_claim_20, envelope)
    assert gate_eval.lifecycle_decision == ClaimLifecycleDecision.REJECT, "Mismatched Claim #20 must be REJECTED, never approved"
    assert "REJECTED" in gate_eval.decision_reason
    assert "Subject-Evidence mismatch" in gate_eval.decision_reason


@pytest.mark.asyncio
async def test_detailed_deduction_and_modality_precision(org_and_source):
    """
    Validates precision fixes from audit:
    1. Short notice recovery is PERMISSION (company holds the right), not MUST
    2. Joining bonus preserves offer letter phrasing without ungrounded 'formal' or 'enforced'
    3. EPF/VPF policy fact preserved without inferring external legal validity
    4. Property return S-P-O has clean boundaries: subject='Employees', predicate='must_return'
    5. Confidentiality prohibition subject matches policy information
    6. Macro summary list does not create duplicate competing claims against detailed rules
    """
    org_id, src_id = org_and_source

    full_policy_content = """# Employees Notice Period Policy v1.5
The unauthorized use or disclosure of this information in any media is prohibited.

## Policy Summary
Deductions from Full & Final Salary may include laptop and asset values, loan adjustments, taxes, WFH allowance recovery, excess leaves, short notice periods, joining bonus recovery, and EPF/VPF deductions.

## 3.2 Points to Remember
Employees must return all Wingify property upon offboarding.
Shipping costs will be covered by Wingify through a mutually agreed-upon method.

## 3.3 Deduction from Full & Final Salary
If the employee retains the laptop and other company assets, their value will be deducted from the Full and Final Salary as per the Asset Management Policy.
Any outstanding loans or advances the employee takes will be fully adjusted from their Full and Final Salary.
If investment proofs, as declared on the HR Portal, are not provided during exit, taxes will be deducted accordingly.
WFH Allowance will be recovered based on the Home Office Allowance Policy if the exit is within a year of joining.
Recovery will be made for any excess leaves taken beyond the allotted quota.
If the employee does not serve the full notice period, the company holds the right to recover the amount equivalent to the short notice period.
Joining Bonus recovery will be as per the terms mentioned in the offer letter.
EPF (Employee Provident Fund) and VPF (Voluntary Provident Fund) deductions will be made and deposited into the employee's account.
"""

    envelope = EnvelopeFactory.create_from_file_upload(
        filename="Full_Policy_Notice.md",
        raw_bytes=full_policy_content.encode("utf-8"),
        parsed_content=full_policy_content,
        organization_id=org_id,
        source_id=src_id,
        document_type="policy",
        source_intent=SourceIntent.GOVERNANCE_POLICY,
    )

    evidence = await DocumentParser.parse(envelope)
    candidates = CandidateDiscoveryEngine.discover_candidates(evidence.units)

    extracted_claims = []
    for u, strat, reason in candidates:
        claims = DomainRuleExtractor.extract_from_unit(u)
        extracted_claims.extend(claims)

    canonical_claims = [c for c in extracted_claims if c.claim_type != "derived_summary"]

    # 1. Short notice recovery must be PERMISSION, not MUST / OBLIGATION
    short_notice = next((c for c in canonical_claims if "holds the right" in c.claim_text.lower()), None)
    assert short_notice is not None, "Short notice claim must be extracted"
    assert short_notice.modality == "PERMISSION", f"Short notice must have PERMISSION modality, got {short_notice.modality}"
    assert short_notice.modal_operator == "holds_the_right"

    # 2. Joining bonus preserves offer letter phrasing without 'enforced' or 'formal'
    bonus_claim = next((c for c in canonical_claims if "joining bonus" in c.claim_text.lower()), None)
    assert bonus_claim is not None, "Joining bonus claim must be extracted"
    assert "enforced" not in bonus_claim.claim_text.lower()
    assert "formal" not in bonus_claim.claim_text.lower()
    assert "offer letter" in bonus_claim.claim_text.lower()

    # 3. EPF/VPF policy fact preserved
    epf_claim = next((c for c in canonical_claims if "epf" in c.claim_text.lower()), None)
    assert epf_claim is not None, "EPF/VPF claim must be extracted"
    assert epf_claim.modality == "POLICY_FACT"
    assert "deposited" in epf_claim.predicate

    # 4. Property return clean S-P-O separation (no Employeesmust_return concatenation)
    prop_claim = next((c for c in extracted_claims if "return all wingify property" in c.claim_text.lower()), None)
    assert prop_claim is not None, "Property return claim must be extracted"
    assert prop_claim.subject == "Employees"
    assert prop_claim.predicate in ("return", "must_return_company_property")
    assert prop_claim.modal_operator == "must"
    assert prop_claim.modality == "OBLIGATION"
    assert "Employeesmust" not in prop_claim.subject and "Employeesmust" not in prop_claim.predicate

    # 5. Shipping costs is company benefit / policy fact, NOT obligation
    shipping_claim = next((c for c in extracted_claims if "shipping costs" in c.claim_text.lower()), None)
    assert shipping_claim is not None, "Shipping costs claim must be extracted"
    assert shipping_claim.modality == "POLICY_FACT"
    assert shipping_claim.claim_type == "company_benefit"
    assert shipping_claim.predicate in ("cover", "covers_shipping_costs")

    # 6. Confidentiality prohibition subject
    conf_claim = next((c for c in extracted_claims if "unauthorized use or disclosure" in c.claim_text.lower()), None)
    assert conf_claim is not None, "Confidentiality claim must be extracted"
    assert "Unauthorized Use" in conf_claim.subject or "Policy Information" in conf_claim.subject
    assert conf_claim.modality == "PROHIBITION"

    # 7. Policy summary deduction list is categorized as derived_summary and not duplicated
    summary_claim = next((c for c in extracted_claims if c.claim_type == "derived_summary" and "deductions" in c.claim_text.lower()), None)
    assert summary_claim is not None, "Summary deduction sentence should be captured as derived_summary"
    assert summary_claim.claim_type == "derived_summary"

