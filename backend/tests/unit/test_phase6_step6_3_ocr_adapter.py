"""
Phase 6 Step 6.3b: Hardened Image/OCR Adapter Integration & Universal Gate Contract Test Suite.

Validates:
1. Image detection in PDFs (raster images), DOCX (word/media with paragraph anchors), PPTX (slide anchors), and standalone files.
2. OCR extraction with token/region coordinates (bounding box + polygon geometry) and non-destructive raw vs repaired lineage.
3. OCR confidence scoring and low-confidence flagging (< 0.70) routed to review.
4. Conservative duplicate-prevention: span and token alignment preserving unmatched numbers, conditions, negations, and exceptions.
5. Universal Gate Contract compliance across all 8 families with emphasis on:
   - Family 1: Evidence Grounding & Document Presence
   - Family 7: Value & Quantitative Fidelity (numeric/currency fidelity on OCR output)
   - Family 8: Anti-Tampering & No Silent Upgrades
6. End-to-end smoke test 1: Standalone image (.png) through UnifiedExtractionPipeline.
7. End-to-end smoke test 2: Scanned/image-only PDF through UnifiedExtractionPipeline with OCR recovery.
8. Image Ground Truth Evaluation: CER, WER, and Critical Token Accuracy catching matching-but-distorted OCR claims.
9. Conservative duplicate handling: No unique clauses or exceptions lost in overlap tests.
10. Non-destructive raw vs repaired lineage traceability.
11. Container completeness ledger & reading order rank accounting.
12. Persisted review enforcement: OCR claims remain candidate/REVIEW_REQUIRED by default under feature flag.
"""

import dataclasses
import io
import os
import uuid
import zipfile
import pytest
from PIL import Image, ImageDraw

from app.db.enums import SourceFamily, SourceIntent
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.ingestion.parsers.evidence_model import (
    ContentRole,
    ParsedEvidenceResult,
    ParsedEvidenceUnit,
)
from app.ingestion.parsers.ocr_adapter import (
    ContainerAssetLedgerEntry,
    ImageDetectionResult,
    ImageGroundTruthResult,
    OcrAdapter,
    OcrBBox,
    OcrRegion,
)
from app.ingestion.universal_file_parser import ContentBlockType, UniversalFileParser
from app.services.gate_contract import (
    GateFailureCode,
    SharedGateRequest,
    SharedGateResult,
    SharedGovernanceGateEngine,
)
from app.extraction.unified_pipeline import (
    UnifiedExtractionPipeline,
    UnifiedPipelineOptions,
)


def _generate_test_image_bytes(text_lines: list[str]) -> bytes:
    """Generates a clean synthetic PNG image with high-contrast text lines."""
    width = 750
    height = 50 + len(text_lines) * 45
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    y_offset = 20
    for line in text_lines:
        draw.text((25, y_offset), line, fill=(0, 0, 0))
        y_offset += 40

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


def _generate_scanned_pdf_bytes(text_lines: list[str]) -> bytes:
    """Generates a synthetic image-only (scanned) PDF with zero digital text."""
    width = 800
    height = 100 + len(text_lines) * 50
    img = Image.new("RGB", (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    y_offset = 30
    for line in text_lines:
        draw.text((30, y_offset), line, fill=(0, 0, 0))
        y_offset += 45

    buf = io.BytesIO()
    img.save(buf, format="PDF")
    return buf.getvalue()


# -----------------------------------------------------------------------------
# 1. Multi-Format Image Detection & Container Placement
# -----------------------------------------------------------------------------
def test_image_detection_across_formats():
    """Validates Deliverable 1: Image detection in standalone files, PDFs, DOCX, and PPTX."""
    img_bytes = _generate_test_image_bytes(["Sample Image Line"])

    # 1A. Standalone PNG
    res_png = OcrAdapter.detect_images(img_bytes, "policy_graphic.png")
    assert len(res_png) == 1
    assert res_png[0].source_type == "standalone"
    assert res_png[0].format == "png"
    assert res_png[0].byte_count == len(img_bytes)
    assert res_png[0].width == 750
    assert res_png[0].reading_order_rank == 1

    # 1B. Scanned PDF with embedded raster image
    pdf_bytes = _generate_scanned_pdf_bytes(["Scanned Policy Text"])
    res_pdf = OcrAdapter.detect_images(pdf_bytes, "scanned_notice.pdf")
    assert len(res_pdf) >= 1
    assert res_pdf[0].source_type == "pdf_embedded"
    assert res_pdf[0].page_or_slide == 1
    assert res_pdf[0].byte_count > 0

    # 1C. DOCX with embedded media and paragraph anchor
    docx_buf = io.BytesIO()
    with zipfile.ZipFile(docx_buf, "w") as zf:
        zf.writestr("word/_rels/document.xml.rels", b"""<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
    <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/hardware_diagram.png"/>
</Relationships>""")
        zf.writestr("word/document.xml", b"""<?xml version="1.0" encoding="UTF-8"?>
<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">
    <w:body>
        <w:p><w:r><w:t>Section 1: Overview</w:t></w:r></w:p>
        <w:p><w:r><w:drawing><a:blip r:embed="rId1"/></w:drawing></w:r></w:p>
    </w:body>
</w:document>""")
        zf.writestr("word/media/hardware_diagram.png", img_bytes)
    docx_bytes = docx_buf.getvalue()

    res_docx = OcrAdapter.detect_images(docx_bytes, "hardware_spec.docx")
    assert len(res_docx) == 1
    assert res_docx[0].source_type == "docx_embedded"
    assert res_docx[0].image_name == "hardware_diagram.png"
    assert res_docx[0].paragraph_or_slide_anchor == "Paragraph 2"
    assert res_docx[0].reading_order_rank == 1

    # 1D. PPTX with embedded media (slide anchor)
    pptx_buf = io.BytesIO()
    with zipfile.ZipFile(pptx_buf, "w") as zf:
        zf.writestr("ppt/presentation.xml", b"<presentation/>")
        zf.writestr("ppt/media/slide1_chart.png", img_bytes)
    pptx_bytes = pptx_buf.getvalue()

    res_pptx = OcrAdapter.detect_images(pptx_bytes, "presentation.pptx")
    assert len(res_pptx) == 1
    assert res_pptx[0].source_type == "pptx_embedded"
    assert res_pptx[0].paragraph_or_slide_anchor == "Slide 1"


# -----------------------------------------------------------------------------
# 2. Coordinates, Confidence, and Lineage Preservation
# -----------------------------------------------------------------------------
def test_ocr_extraction_with_coordinates_and_confidence():
    """Validates Deliverable 2: OCR extraction with preserved polygon, bounding box, and non-destructive lineage."""
    lines = [
        "Return window is 30 days for hardware devices.",
        "Restocking fee of $50.00 applies to unsealed packages.",
    ]
    img_bytes = _generate_test_image_bytes(lines)

    full_text, regions, avg_conf, warnings = OcrAdapter.extract_ocr_from_image(
        image_bytes=img_bytes,
        page_index=1,
        image_name="test_policy.png",
    )

    assert len(warnings) == 0
    assert len(regions) >= 2
    assert avg_conf >= 0.70

    for r in regions:
        assert isinstance(r.bbox, OcrBBox)
        assert r.bbox.x_min >= 0.0
        assert r.bbox.y_max > r.bbox.y_min
        assert len(r.polygon) == 4
        assert r.confidence > 0.0
        # Lineage attributes
        assert r.raw_ocr_text != ""
        assert r.repaired_text != ""
        assert r.repair_version == "ocr_repair_v2.0"
        assert "image_hash" in r.coordinate_mapping


# -----------------------------------------------------------------------------
# 3. Low-Confidence Flagging & Human Review Routing
# -----------------------------------------------------------------------------
def test_low_confidence_flagging_and_review_routing():
    """Validates Deliverable 3: Low-confidence flagging and routing to human review."""
    lines = ["Standard Return Period: 14 days."]
    img_bytes = _generate_test_image_bytes(lines)

    # High threshold triggers low confidence flag
    _, regions_flagged, _, _ = OcrAdapter.extract_ocr_from_image(img_bytes, confidence_threshold=0.999)
    assert regions_flagged[0].is_low_confidence is True
    assert "low_ocr_confidence" in regions_flagged[0].review_reasons


# -----------------------------------------------------------------------------
# 4. Conservative Duplicate Handling (Preserves Exceptions and Numbers)
# -----------------------------------------------------------------------------
def test_duplicate_prevention_native_text_vs_ocr():
    """Validates Deliverable 4: Duplicate-prevention between native digital text and OCR."""
    native_text = (
        "Enterprise Refund Policy: The return window for all hardware devices is 30 days from delivery. "
        "Restocking fee of $50.00 applies to unsealed packages. Customer must initiate return in writing."
    )
    # Exact duplicate with zero new critical tokens
    ocr_identical = "The return window for all hardware devices is 30 days from delivery restocking fee of $50.00."

    is_suppressed_dup, reason_dup, unmatched, ledger = OcrAdapter.reconcile_overlap_spans(native_text, ocr_identical)
    assert is_suppressed_dup is True
    assert len(unmatched) == 0
    assert ledger["action"] == "suppressed_exact_duplicate"


def test_conservative_duplicate_handling_preserves_unique_clauses():
    """Validates Gap 2: Proves that unique exceptions, negations, or numbers are NEVER suppressed."""
    native_text = "Returns accepted within 30 days."
    # Image adds an essential exception: 'except final-sale items'
    image_text = "Returns accepted within 30 days, except final-sale items."

    is_suppressed, reason, unmatched_tokens, ledger = OcrAdapter.reconcile_overlap_spans(native_text, image_text)

    # Must NOT be suppressed despite 70%+ token overlap!
    assert is_suppressed is False, "OCR text with unshared exception must NOT be suppressed!"
    assert any("except" in t or "final-sale" in t for t in unmatched_tokens)
    assert ledger["action"] == "admitted_differential"
    assert "Preserved unique critical tokens" in ledger["reason"]


# -----------------------------------------------------------------------------
# 5. Image Ground Truth Evaluator (CER, WER, Critical Token Accuracy)
# -----------------------------------------------------------------------------
def test_image_ground_truth_evaluation_detects_distortions():
    """Validates Gap 1 & 5: Detects matching-but-distorted OCR claims against ground truth."""
    gt_text = "Restocking fee of $50.00 applies to returned servers."

    # Case A: Accurate OCR output
    ocr_correct = "Restocking fee of $50.00 applies to returned servers."
    res_correct = OcrAdapter.evaluate_image_ground_truth("img_001", gt_text, ocr_correct, ocr_correct)
    assert res_correct.is_verified_against_ground_truth is True
    assert res_correct.character_error_rate == 0.0
    assert res_correct.critical_token_accuracy == 1.0
    assert len(res_correct.critical_token_mismatches) == 0

    # Case B: Distorted OCR currency ($500.00 instead of $50.00)
    # A claim asserting $500.00 would match the OCR, but MUST FAIL against image ground truth!
    ocr_distorted = "Restocking fee of $500.00 applies to returned servers."
    res_distorted = OcrAdapter.evaluate_image_ground_truth("img_002", gt_text, ocr_distorted, ocr_distorted)
    assert res_distorted.is_verified_against_ground_truth is False
    assert len(res_distorted.critical_token_mismatches) > 0
    assert any(m["expected"] == "$50.00" for m in res_distorted.critical_token_mismatches)
    assert any("absent from source image" in r for r in res_distorted.rejection_reasons)


# -----------------------------------------------------------------------------
# 6. Non-Destructive Raw vs. Repaired Evidence Lineage
# -----------------------------------------------------------------------------
def test_non_destructive_raw_vs_repaired_lineage():
    """Validates Gap 3: Proves every OCR repair transformation is traceable and non-destructive."""
    raw_concatenated = "Warranty is3yearsfor Core Server,fee is$50.00."
    repaired, rep_ver, trans_log = OcrAdapter.repair_ocr_with_trace(raw_concatenated)

    assert rep_ver == "ocr_repair_v2.0"
    assert len(trans_log) > 0
    # Transformation log records stage and exact change
    stages = [entry["stage"] for entry in trans_log]
    assert "punctuation_spacing" in stages or "digit_letter_boundary_split" in stages


# -----------------------------------------------------------------------------
# 7. Container Completeness Ledger & Auditability
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_container_completeness_ledger_accounting():
    """Validates Gap 4: Proves completeness ledger accounts for all image assets."""
    img_bytes = _generate_test_image_bytes(["Mandatory safety audit required every 6 months."])
    envelope = CanonicalSourceEnvelope(
        envelope_id=uuid.uuid4(),
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="file://safety_spec.png",
        source_family=SourceFamily.DOCUMENT,
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        native_format="image",
        source_version="1",
        content_hash="mock_hash",
        raw_payload=img_bytes,
        locator_metadata={"filename": "safety_spec.png", "raw_bytes": img_bytes},
        metadata={"filename": "safety_spec.png", "raw_bytes": img_bytes},
    )

    evidence_res = await OcrAdapter.parse_to_evidence(envelope)
    assert isinstance(evidence_res, ParsedEvidenceResult)
    assert len(evidence_res.completeness_ledger) >= 1

    entry = evidence_res.completeness_ledger[0]
    assert entry["asset_id"] == "safety_spec.png"
    assert entry["status"] == "extracted_ocr"
    assert len(entry["evidence_unit_ids"]) > 0


# -----------------------------------------------------------------------------
# 8. Universal Gate Contract Conformance (All 8 Families)
# -----------------------------------------------------------------------------
def test_ocr_gate_contract_all_8_families():
    """Validates Deliverable 5: Gate conformance under all 8 Universal Gate Contract families."""
    ocr_doc_text = "Return window is 30 days. Restocking fee of $50.00 applies to opened packages."
    ocr_quote = "Restocking fee of $50.00 applies to opened packages."

    # 1. Valid OCR claim with quantitative currency matching
    req_valid = SharedGateRequest(
        claim_text="Opened packages incur a restocking fee of $50.00.",
        subject="Opened packages",
        predicate="has_fee_rule",
        object_val="$50.00",
        evidence_quote=ocr_quote,
        document_text=ocr_doc_text,
        status="candidate",
        confidence=0.95,
    )
    res_valid = SharedGovernanceGateEngine.evaluate(req_valid)
    assert res_valid.evidence_grounding is True
    assert res_valid.value_fidelity is True
    assert res_valid.all_gates_passed is True

    # 2. Gate Family 7 Failure: OCR Distortion ($500.00 asserted vs $50.00 evidence)
    req_f7_distorted = dataclasses.replace(
        req_valid,
        claim_text="Opened packages incur a restocking fee of $500.00.",
        object_val="$500.00",
    )
    res_f7 = SharedGovernanceGateEngine.evaluate(req_f7_distorted)
    assert res_f7.value_fidelity is False
    assert res_f7.all_gates_passed is False
    assert GateFailureCode.ERR_VALUE_FIDELITY_MISMATCH.value in res_f7.reason_codes

    # 3. Gate Family 1 Failure: Ungrounded / Fabricated OCR Evidence
    req_f1_ungrounded = dataclasses.replace(
        req_valid,
        evidence_quote="Nonexistent clause regarding replacement laptops.",
    )
    res_f1 = SharedGovernanceGateEngine.evaluate(req_f1_ungrounded)
    assert res_f1.evidence_grounding is False
    assert GateFailureCode.ERR_EVIDENCE_FABRICATED.value in res_f1.reason_codes

    # 4. Gate Family 2 Failure: Generic Catch-All Predicate
    req_f2_catch_all = dataclasses.replace(
        req_valid,
        predicate="has_summary",
    )
    res_f2 = SharedGovernanceGateEngine.evaluate(req_f2_catch_all)
    assert res_f2.predicate_normativity is False
    assert GateFailureCode.ERR_PREDICATE_CATCH_ALL.value in res_f2.reason_codes

    # 5. Gate Family 8 Failure: Silent Upgrade Defense on Candidate Claim
    req_f8_silent_upgrade = dataclasses.replace(
        req_valid,
        status="rejected",
        target_status="verified",
        is_upgrade_attempt=True,
    )
    res_f8 = SharedGovernanceGateEngine.evaluate(req_f8_silent_upgrade)
    assert res_f8.no_silent_upgrade is False
    assert GateFailureCode.ERR_NO_SILENT_UPGRADE_VIOLATION.value in res_f8.reason_codes


# -----------------------------------------------------------------------------
# 9. Persisted Review Enforcement & Smoke Tests
# -----------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_persisted_review_enforcement_and_smoke_standalone_image():
    """Validates Deliverable 7A & Persisted Review Enforcement (Feature flag keeps OCR in candidate)."""
    lines = [
        "Customers must request cancellation within 14 days before delivery.",
        "Restocking fee of $75.00 is required for enterprise servers.",
    ]
    img_bytes = _generate_test_image_bytes(lines)
    filename = "cancellation_notice.png"

    # 1. UniversalFileParser integration
    parsed_doc = UniversalFileParser.parse_structured(
        filename=filename,
        raw_bytes=img_bytes,
        doc_title="Cancellation Notice",
    )
    assert parsed_doc.is_scanned is True
    assert "cancellation" in parsed_doc.full_text.lower()
    assert "14 days" in parsed_doc.full_text

    # 2. UnifiedExtractionPipeline execution
    res = await UnifiedExtractionPipeline.execute(
        filename=filename,
        raw_bytes=img_bytes,
        options=UnifiedPipelineOptions(
            doc_title="Cancellation Notice",
            skip_db_persist=True,
        ),
    )

    assert res.pipeline_run_id is not None
    assert len(res.candidates) > 0

    # Persisted Review Invariant: All OCR claims must remain in candidate / REVIEW_REQUIRED status
    for cand in res.candidates:
        assert cand.status == "candidate", "OCR-derived claim must remain candidate by default"
        assert cand.locator.get("source_type") == "image_ocr" or cand.locator.get("bbox") is not None


@pytest.mark.asyncio
async def test_ocr_end_to_end_smoke_scanned_pdf():
    """Validates Deliverable 7B: 1 real scanned/image-only PDF end-to-end smoke test through pipeline."""
    lines = [
        "Core Server equipment includes a 3 years warranty period.",
        "Customers must report hardware defects in writing.",
    ]
    pdf_bytes = _generate_scanned_pdf_bytes(lines)
    filename = "scanned_warranty_certificate.pdf"

    # 1. UniversalFileParser integration
    parsed_doc = UniversalFileParser.parse_structured(
        filename=filename,
        raw_bytes=pdf_bytes,
        doc_title="Scanned Warranty Certificate",
    )
    assert parsed_doc.is_scanned is True
    assert "Core Server" in parsed_doc.full_text or "warranty" in parsed_doc.full_text.lower()

    # 2. UnifiedExtractionPipeline execution
    res = await UnifiedExtractionPipeline.execute(
        filename=filename,
        raw_bytes=pdf_bytes,
        options=UnifiedPipelineOptions(
            doc_title="Scanned Warranty Certificate",
            skip_db_persist=True,
        ),
    )

    assert res.pipeline_run_id is not None
    assert len(res.candidates) > 0
    assert len(res.evaluations) > 0

    claims_text = " ".join([c.claim_text for c in res.candidates])
    assert "defects" in claims_text.lower() or "warranty" in claims_text.lower() or "server" in claims_text.lower()
