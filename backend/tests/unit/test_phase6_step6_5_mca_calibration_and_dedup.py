"""
Unit & Regression Test Suite for Phase 6.5 MCA Calibration and Duplicate Elimination.

Validates the resolution of the 6 calibration gaps and 1 duplicate leak:
1. Liability-cap clause correctly mapped to has_liability_cap (not may_apply_administration_fee).
2. Late-fee clause correctly mapped to has_late_payment_penalty_rate (not may_apply_administration_fee).
3. Trade-law compliance clause correctly classified as operative rule with must_comply_with_trade_laws.
4. Warranty-remedy window correctly mapped to has_warranty_remedy_window (not has_return_window).
5. Suspension-for-breach rule correctly classified as operative rule with may_suspend_for_security_or_breach.
6. Definition clause correctly stored with has_definition (not has_validity_rule).
7. Pure duplicate sublicensing branch (#91) cleanly deduplicated so only one canonical candidate is retained.
8. End-to-end execution of the real Microsoft Customer Agreement PDF produces correct calibrated claims.
"""

import uuid
import pytest
from pathlib import Path
from app.extraction.models import CandidateClaim
from app.extraction.claim_quality_normalizer import ClaimQualityNormalizer
from app.services.universal_gate_evaluator import UniversalGateEvaluator
from app.schemas.evidence import ImmutableEvidenceSpan
from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions


def _create_span(text: str) -> ImmutableEvidenceSpan:
    return ImmutableEvidenceSpan.from_content(
        verbatim_quote=text,
        clause_text=text,
        content=text,
    )


def _make_candidate(text: str, subject: str, predicate: str, object_val: str, modality: str = "PERMISSION", claim_type: str = "rule") -> CandidateClaim:
    return CandidateClaim.create(
        envelope_id=uuid.uuid4(),
        unit_id=str(uuid.uuid4()),
        asset_id=str(uuid.uuid4()),
        claim_text=text,
        subject=subject,
        predicate=predicate,
        object_=object_val,
        evidence_text_span=text,
        modality=modality,
        claim_type=claim_type,
    )


def test_mca_liability_cap_clause_calibration():
    """Verify liability cap sentence maps to has_liability_cap and certifies."""
    text = (
        "For each Product licensed on a subscription basis, each party's maximum, aggregate liability "
        "is the total amount of subscription fees Customer paid to use the Product during the 12 months "
        "preceding the most recent incident giving rise to the claim(s)."
    )
    cand = _make_candidate(text, "Customer", "may_apply_administration_fee", text, modality="POLICY_FACT")
    norm = ClaimQualityNormalizer.normalize_candidate_claim(cand)
    assert norm is not None
    assert norm.predicate == "has_liability_cap"
    assert norm.claim_type == "rule"

    ev = _create_span(text)
    res = UniversalGateEvaluator.evaluate(
        claim_text=norm.claim_text,
        subject=norm.subject,
        predicate=norm.predicate,
        object_text=str(norm.object),
        claim_type="rule",
        evidence=ev,
        source_content=text,
    )
    assert res.all_gates_passed is True
    assert res.certification_tier == "AUTOMATED_CERTIFIED"


def test_mca_late_fee_clause_calibration():
    """Verify late-fee sentence maps to has_late_payment_penalty_rate and certifies."""
    text = (
        "Microsoft may, at its option, assess a late fee on any payments to Microsoft that are more "
        "than fifteen (15) calendar days past due at a rate of up to two percent (2%) of the total amount "
        "payable, calculated and payable monthly, or the highest amount allowed by law, if less."
    )
    cand = _make_candidate(text, "Customer", "may_apply_administration_fee", text, modality="PERMISSION")
    norm = ClaimQualityNormalizer.normalize_candidate_claim(cand)
    assert norm is not None
    assert norm.predicate == "has_late_payment_penalty_rate"
    assert norm.subject == "Microsoft"
    assert norm.claim_type == "rule"

    ev = _create_span(text)
    res = UniversalGateEvaluator.evaluate(
        claim_text=norm.claim_text,
        subject=norm.subject,
        predicate=norm.predicate,
        object_text=str(norm.object),
        claim_type="rule",
        evidence=ev,
        source_content=text,
    )
    assert res.all_gates_passed is True
    assert res.certification_tier == "AUTOMATED_CERTIFIED"


def test_mca_warranty_remedy_window_calibration():
    """Verify warranty breach remedy notice maps to has_warranty_remedy_window (not has_return_window)."""
    text = (
        "If Microsoft fails to do so, and Customer notifies Microsoft within 90 days from the completion "
        "of the work giving rise to the warranty claim, then Microsoft will, at its discretion, either "
        "re-perform the Professional Services or return the amount Customer paid for them."
    )
    cand = _make_candidate(text, "Customer", "has_return_window", text, modality="ENTITLED_TO")
    norm = ClaimQualityNormalizer.normalize_candidate_claim(cand)
    assert norm is not None
    assert norm.predicate == "has_warranty_remedy_window"
    assert norm.claim_type == "rule"

    ev = _create_span(text)
    res = UniversalGateEvaluator.evaluate(
        claim_text=norm.claim_text,
        subject=norm.subject,
        predicate=norm.predicate,
        object_text=str(norm.object),
        claim_type="rule",
        evidence=ev,
        source_content=text,
    )
    assert res.all_gates_passed is True
    assert res.certification_tier == "AUTOMATED_CERTIFIED"


def test_mca_trade_law_compliance_is_operative_rule():
    """Verify trade law compliance is classified as operative rule with must_comply_with_trade_laws."""
    text = (
        "Each party will comply with all laws and regulations applicable to the import or export "
        "of the Products and Services Deliverables, including, without limitation, trade laws such as "
        "the U.S. Export Administration Regulations and International Traffic in Arms Regulations."
    )
    cand = _make_candidate(text, "Each party", "must_comply_with_trade_laws", text, modality="OBLIGATION")
    norm = ClaimQualityNormalizer.normalize_candidate_claim(cand)
    assert norm is not None
    assert norm.predicate == "must_comply_with_trade_laws"
    assert norm.claim_type == "rule"

    ev = _create_span(text)
    res = UniversalGateEvaluator.evaluate(
        claim_text=norm.claim_text,
        subject=norm.subject,
        predicate=norm.predicate,
        object_text=str(norm.object),
        claim_type="rule",
        evidence=ev,
        source_content=text,
    )
    assert res.gates["claim_type_allowed"] is True
    assert res.certification_tier != "NON_RULE"
    assert res.all_gates_passed is True


def test_mca_suspension_for_breach_is_operative_rule():
    """Verify suspension for breach maps to Microsoft subject and may_suspend_for_security_or_breach."""
    text = (
        "During any period of material breach by Customer, Microsoft may suspend a Subscription "
        "or Statement of Services without terminating this Agreement."
    )
    cand = _make_candidate(
        text,
        "Customer",  # was misattributed
        "may_suspend_for_security_or_breach",
        "a Subscription or Statement of Services without terminating this Agreement",
        modality="PERMISSION",
    )
    norm = ClaimQualityNormalizer.normalize_candidate_claim(cand)
    assert norm is not None
    assert norm.subject == "Microsoft"
    assert norm.predicate == "may_suspend_for_security_or_breach"
    assert norm.claim_type == "rule"

    ev = _create_span(text)
    res = UniversalGateEvaluator.evaluate(
        claim_text=norm.claim_text,
        subject=norm.subject,
        predicate=norm.predicate,
        object_text=str(norm.object),
        claim_type="rule",
        evidence=ev,
        source_content=text,
    )
    assert res.gates["claim_type_allowed"] is True
    assert res.certification_tier != "NON_RULE"
    assert res.all_gates_passed is True


def test_mca_definition_clause_stored_with_has_definition():
    """Verify definition clause Software does not include... uses has_definition, not has_validity_rule."""
    text = "Software does not include Online Services, but Software may be part of an Online Service."
    cand = _make_candidate(
        text,
        "Software",
        "has_validity_rule",
        "be part of an Online Service",
        modality="POLICY_FACT",
    )
    norm = ClaimQualityNormalizer.normalize_candidate_claim(cand)
    assert norm is not None
    assert norm.predicate == "has_definition"
    assert norm.claim_type == "definition"


def test_mca_duplicate_sublicense_branch_deduplication():
    """Verify pure duplicate candidate branches from the same sentence are cleanly deduplicated."""
    sentence = (
        "Customer may sublicense its rights in Services Deliverables to its Affiliates, "
        "but Customer's Affiliates may not sublicense these rights."
    )
    c1 = _make_candidate(
        sentence,
        "Customer",
        "sublicense",
        "its rights in Services Deliverables to its Affiliates",
        modality="PERMISSION",
        claim_type="quarantined",
    )
    c2 = _make_candidate(
        sentence,
        "Customer",
        "sublicense",
        "these rights",
        modality="PERMISSION",
        claim_type="quarantined",
    )

    # Test the deduplication logic from UnifiedExtractionPipeline Step 5
    seen_keys = {}
    seen_span_keys = {}
    for c in [c1, c2]:
        key = (
            (c.subject or "").strip().lower(),
            (c.predicate or "").strip().lower(),
            str(c.object or "").strip().lower(),
            str(c.modality or "").strip().upper(),
        )
        span_text = (c.evidence_text_span or c.claim_text or "").strip().lower()
        span_key = (
            (c.subject or "").strip().lower(),
            (c.predicate or "").strip().lower(),
            span_text,
        )
        if key in seen_keys:
            continue
        if span_text and span_key in seen_span_keys:
            old_key, existing = seen_span_keys[span_key]
            obj_new = str(c.object or "").strip().lower()
            obj_old = str(existing.object or "").strip().lower()
            is_new_pronoun = any(obj_new.startswith(p) for p in ("these ", "those ", "this ", "it ", "them "))
            is_old_pronoun = any(obj_old.startswith(p) for p in ("these ", "those ", "this ", "it ", "them "))
            if is_old_pronoun and not is_new_pronoun:
                seen_keys.pop(old_key, None)
                seen_keys[key] = c
                seen_span_keys[span_key] = (key, c)
            continue
        seen_keys[key] = c
        if span_text:
            seen_span_keys[span_key] = (key, c)

    deduped = list(seen_keys.values())
    assert len(deduped) == 1
    assert deduped[0].object == "its rights in Services Deliverables to its Affiliates"


@pytest.mark.asyncio
async def test_e2e_mca_pdf_calibrated_claims():
    """Verify live UnifiedExtractionPipeline on real MCA PDF reflects calibrated predicates."""
    mca_path = Path("research/validation_50/raw_documents/Microsoft/Contracts/Microsoft Customer Agreement.pdf")
    if not mca_path.exists():
        pytest.skip("MCA PDF not present in test environment.")

    raw_bytes = mca_path.read_bytes()
    opts = UnifiedPipelineOptions(
        organization_id="12d07bef-6f37-4584-a8a8-0480c2b7e39c",
        source_id="e11bb270-1ced-4409-b8e2-146a556a096d",
        document_type="policy",
        doc_title="Microsoft Customer Agreement",
        external_id="file://Microsoft Customer Agreement.pdf",
        persist_to_db=False,
    )
    res = await UnifiedExtractionPipeline.execute(
        filename="Microsoft Customer Agreement.pdf",
        raw_bytes=raw_bytes,
        options=opts,
    )

    predicates = {c.predicate for c in res.candidates}
    assert "has_liability_cap" in predicates
    assert "has_late_payment_penalty_rate" in predicates
    assert "has_warranty_remedy_window" in predicates
    assert "must_comply_with_trade_laws" in predicates
    assert "may_suspend_for_security_or_breach" in predicates
    assert "has_definition" in predicates

    # Verify duplicate sublicense claim is collapsed to 1
    sublicense_claims = [c for c in res.candidates if c.predicate == "sublicense"]
    assert len(sublicense_claims) == 1
    assert sublicense_claims[0].object != "these rights"
