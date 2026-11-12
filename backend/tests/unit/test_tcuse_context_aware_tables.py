"""
Comprehensive Automated Test Suite for TCUSE (Table-Level Semantic Context Enrichment Engine).

Covers all 16 Required Test Cases from Section 17 + PPTX native table extraction +
UnifiedExtractionPipeline end-to-end integration + accuracy & completeness metrics.
"""

from __future__ import annotations

import io
import uuid
import zipfile
import pytest
import openpyxl

from app.conflict_engine.compatibility_gate import CompatibilityGate
from app.db.enums import SourceFamily, SourceIntent
from app.extraction.pipeline import Layer5ExtractionPipeline
from app.extraction.table_context import (
    TableCompletenessAuditor,
    TableContextCollector,
    TableContextPipeline,
    TableSemanticConsistencyValidator,
    TableSemanticInterpreter,
    TableType,
    TableValueNormalizer,
)
from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions
from app.ingestion.envelope import CanonicalSourceEnvelope, EnvelopeFactory
from app.ingestion.parsers.document_parser import DocumentParser
from app.ingestion.parsers.html_adapter import HtmlAdapter
from app.ingestion.parsers.pptx_adapter import PptxAdapter
from app.ingestion.parsers.xlsx_parser import XlsxAdapter
from app.normalization.document_restructurer import DocumentSemanticRestructurer
from app.validation_gate.models import ClaimLifecycleDecision


def _make_md_envelope(text: str, asset_id: str = "test_doc.md") -> CanonicalSourceEnvelope:
    return EnvelopeFactory.create_from_file_upload(
        filename=asset_id,
        raw_bytes=text.encode("utf-8"),
        parsed_content=text,
        organization_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        source_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        document_type="policy",
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        source_family=SourceFamily.DOCUMENT,
    )


# ---------------------------------------------------------------------------
# TEST 1: SAME ROWS, DIFFERENT TITLES
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_01_same_rows_different_titles():
    md = """# HR Benefits Policy

## Section 1: Leave Policies

Table 1: Employee Annual Leave Entitlement

| Employee Grade | Days |
|---|---|
| Grade A | 30 |
| Grade B | 20 |
| Grade C | 15 |

Table 2: Employee Annual Sick Leave Entitlement

| Employee Grade | Days |
|---|---|
| Grade A | 30 |
| Grade B | 20 |
| Grade C | 15 |
"""
    res = await UnifiedExtractionPipeline.execute(
        filename="hr_leave.md",
        options=UnifiedPipelineOptions(parsed_content=md, doc_title="HR Benefits Policy"),
    )
    assert len(res.candidates) == 6, f"Expected 6 distinct claims (3 annual + 3 sick), got {len(res.candidates)}"

    annual_claims = [c for c in res.candidates if "annual_leave" in c.predicate]
    sick_claims = [c for c in res.candidates if "sick_leave" in c.predicate]
    assert len(annual_claims) == 3
    assert len(sick_claims) == 3

    grade_a_annual = next(c for c in annual_claims if "Grade A" in c.subject)
    grade_a_sick = next(c for c in sick_claims if "Grade A" in c.subject)
    assert grade_a_annual.predicate != grade_a_sick.predicate
    assert "annual leave" in grade_a_annual.claim_text.lower()
    assert "sick leave" in grade_a_sick.claim_text.lower()
    assert "30 days" in grade_a_annual.object.lower()
    assert "30 days" in grade_a_sick.object.lower()

    # Both must be approved by UniversalGateEvaluator (not collapsed or rejected)
    approved = [e for e in res.evaluations if e.lifecycle_decision == ClaimLifecycleDecision.APPROVE]
    assert len(approved) == 6


# ---------------------------------------------------------------------------
# TEST 2: SAME ROWS, DIFFERENT DESCRIPTIONS
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_02_same_rows_different_descriptions():
    md = """# Benefits Manual

### 1.1 Paid Time Off
**Employee Entitlement Schedule**

This table defines annual vacation leave entitlements for full-time staff.

| Employee Grade | Days |
|---|---|
| Grade A | 30 |

### 1.2 Medical Absence
**Employee Entitlement Schedule**

This table governs paid sick leave entitlements for medical absences.

| Employee Grade | Days |
|---|---|
| Grade A | 30 |
"""
    env = _make_md_envelope(md)
    ev = await DocumentParser.parse(env)
    tcuse_res = TableContextPipeline.run(ev, env.envelope_id, env.asset_id, use_cache=False)

    assert len(tcuse_res.claims) == 2
    preds = {c.predicate for c in tcuse_res.claims}
    assert len(preds) == 2, f"Descriptions should disambiguate identical titles, got {preds}"
    texts = " ".join(c.claim_text.lower() for c in tcuse_res.claims)
    assert "vacation" in texts or "annual" in texts
    assert "sick" in texts or "medical" in texts


# ---------------------------------------------------------------------------
# TEST 3: SAME TITLE, DIFFERENT VALUES
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_03_same_title_different_values():
    md1 = """# Policy US
Table 1: Employee Annual Leave Entitlement

| Employee Grade | Days |
|---|---|
| Grade A | 30 |
"""
    md2 = """# Policy EU
Table 1: Employee Annual Leave Entitlement

| Employee Grade | Days |
|---|---|
| Grade A | 25 |
"""
    ev1 = await DocumentParser.parse(_make_md_envelope(md1, "us.md"))
    ev2 = await DocumentParser.parse(_make_md_envelope(md2, "eu.md"))
    r1 = TableContextPipeline.run(ev1, ev1.envelope_id, ev1.asset_id, use_cache=False)
    r2 = TableContextPipeline.run(ev2, ev2.envelope_id, ev2.asset_id, use_cache=False)

    assert r1.interpretations[0].business_topic == r2.interpretations[0].business_topic
    assert r1.claims[0].predicate == r2.claims[0].predicate
    assert r1.claims[0].object == "30 days"
    assert r2.claims[0].object == "25 days"
    # Same business topic & predicate with differing values SHOULD be comparable in CompatibilityGate
    compat = CompatibilityGate.evaluate_compatibility(r1.claims[0], r2.claims[0])
    assert compat.is_comparable is True


# ---------------------------------------------------------------------------
# TEST 4: MISSING TABLE TITLE (Context Recovery vs Non-Hallucination)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_04_missing_table_title_no_hallucination():
    # Case 4A: No explicit title, but section heading + preceding paragraph exist
    md_with_sec = """# Security Policy

## Password Complexity Requirements

All corporate user accounts must adhere to the following minimum length requirements:

| Account Type | Minimum Length |
|---|---|
| Admin | 16 characters |
"""
    ev_a = await DocumentParser.parse(_make_md_envelope(md_with_sec))
    res_a = TableContextPipeline.run(ev_a, ev_a.envelope_id, ev_a.asset_id, use_cache=False)
    assert len(res_a.claims) == 1
    assert "password" in (res_a.interpretations[0].business_topic or "").lower()

    # Case 4B: Completely contextless generic table -> MUST NOT hallucinate topic
    md_bare = """| Col1 | Value |
|---|---|
| Alpha | 42 |
"""
    ev_b = await DocumentParser.parse(_make_md_envelope(md_bare))
    res_b = TableContextPipeline.run(ev_b, ev_b.envelope_id, ev_b.asset_id, use_cache=False)
    assert res_b.interpretations[0].is_ambiguous is True
    assert res_b.interpretations[0].business_topic is None
    assert len(res_b.interpretations[0].missing_context_reasons) > 0
    assert res_b.claims[0].is_ambiguous is True
    assert res_b.claims[0].atomic_fact is not None


# ---------------------------------------------------------------------------
# TEST 5: MULTI-LEVEL HEADERS (Markdown & HTML colspan)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_05_multi_level_headers():
    html = """<html><head><title>Refund Policy</title></head><body>
    <h1>Customer Refunds</h1>
    <table>
      <caption>Customer Refund Eligibility Matrix</caption>
      <thead>
        <tr><th rowspan="2">Customer</th><th colspan="2">Refund Amount (USD)</th></tr>
        <tr><th>Within 7 days</th><th>After 7 days</th></tr>
      </thead>
      <tbody>
        <tr><td>Premium</td><td>100%</td><td>50%</td></tr>
        <tr><td>Standard</td><td>80%</td><td>30%</td></tr>
      </tbody>
    </table>
    </body></html>"""
    env = EnvelopeFactory.create_from_file_upload(
        filename="refund.html",
        raw_bytes=html.encode("utf-8"),
        parsed_content="",
        organization_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        source_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        source_family=SourceFamily.DOCUMENT,
        source_intent=SourceIntent.GOVERNANCE_POLICY,
    )
    ev = await HtmlAdapter.parse_to_evidence(env)
    res = TableContextPipeline.run(ev, env.envelope_id, env.asset_id, use_cache=False)

    assert len(res.tables) == 1
    tbl = res.tables[0]
    assert tbl.header_hierarchy.has_grouped_headers is True
    assert tbl.context_bundle.table_caption is not None
    assert "Customer Refund Eligibility Matrix" in tbl.context_bundle.table_caption.text
    assert len(res.claims) == 4

    prem_within = next(c for c in res.claims if "Premium" in c.subject and c.object == "100%")
    assert any(isinstance(cd, dict) and cd.get("value") == 7 and cd.get("operator") == "less_than_or_equal_to" for cd in prem_within.conditions)
    assert prem_within.table_binding.header_hierarchy == ["Refund Amount (USD)", "Within 7 days"]


# ---------------------------------------------------------------------------
# TEST 6: CONDITIONAL TABLES
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_06_conditional_tables():
    md = """# Return Policy
Table 1: Refund Percentage Schedule

| Refund Amount (USD) | | |
|---|---|---|
| Customer | Within 7 days | After 7 days |
| Premium | 100% | 50% |
"""
    ev = await DocumentParser.parse(_make_md_envelope(md))
    res = TableContextPipeline.run(ev, ev.envelope_id, ev.asset_id, use_cache=False)
    assert len(res.claims) == 2
    within_c = next(c for c in res.claims if c.object == "100%")
    after_c = next(c for c in res.claims if c.object == "50%")
    assert any(isinstance(x, dict) and x.get("operator") == "less_than_or_equal_to" for x in within_c.conditions)
    assert any(isinstance(x, dict) and x.get("operator") == "greater_than" for x in after_c.conditions)


# ---------------------------------------------------------------------------
# TEST 7: EXCEPTION TABLES
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_07_exception_tables():
    md = """# Expense Policy
Table 1: Travel Reimbursement Exceptions

| Expense Category | Standard Cap |
|---|---|
| Hotel Lodging* | $250 |

* Except during major trade conferences with prior VP approval.
"""
    ev = await DocumentParser.parse(_make_md_envelope(md))
    res = TableContextPipeline.run(ev, ev.envelope_id, ev.asset_id, use_cache=False)
    assert res.interpretations[0].table_type == TableType.EXCEPTION
    assert len(res.claims) == 1
    assert len(res.claims[0].exceptions) == 1
    assert "trade conferences" in res.claims[0].exceptions[0].lower()


# ---------------------------------------------------------------------------
# TEST 8: FOOTNOTE-DEPENDENT VALUES
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_08_footnote_dependent_values():
    md = """# HR Policy
Table 1: Employee Annual Leave Entitlement

| Employee Grade | Days |
|---|---|
| Grade A | 30* |
| Grade B | 20 [1] |

* Applies only after completing 90-day probation.
[1] Excludes part-time contractors.
"""
    ev = await DocumentParser.parse(_make_md_envelope(md))
    res = TableContextPipeline.run(ev, ev.envelope_id, ev.asset_id, use_cache=False)
    c_a = next(c for c in res.claims if "Grade A" in c.subject)
    c_b = next(c for c in res.claims if "Grade B" in c.subject)
    assert any("90-day probation" in str(x) for x in c_a.conditions)
    assert any("part-time contractors" in str(x) for x in c_b.exceptions)
    assert c_a.table_binding.cell_value == "30*"
    assert c_a.object == "30 days"


# ---------------------------------------------------------------------------
# TEST 9: MERGED CELLS (XLSX & Markdown provenance)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_09_merged_cells_provenance():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Leave Entitlement"
    ws.append(["Employee Annual Leave Entitlement", None])
    ws.merge_cells("A1:B1")
    ws.append(["Department", "Leave Days"])
    ws.append(["Engineering", 25])
    ws.append([None, 20])
    ws.merge_cells("A3:A4")

    buf = io.BytesIO()
    wb.save(buf)
    raw_bytes = buf.getvalue()

    env = EnvelopeFactory.create_from_file_upload(
        filename="merged_leave.xlsx",
        raw_bytes=raw_bytes,
        parsed_content="",
        organization_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        source_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        source_family=SourceFamily.STRUCTURED,
        source_intent=SourceIntent.GOVERNANCE_POLICY,
    )
    ev = await XlsxAdapter.parse_to_evidence(env)
    res = TableContextPipeline.run(ev, env.envelope_id, env.asset_id, use_cache=False)

    assert len(res.tables) == 1
    assert res.tables[0].context_bundle.table_title is not None
    assert "Employee Annual Leave Entitlement" in res.tables[0].context_bundle.table_title.text
    assert len(res.claims) == 2
    assert all("Engineering" in c.subject for c in res.claims)


# ---------------------------------------------------------------------------
# TEST 10: MULTI-PAGE TABLES
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_10_multipage_tables():
    md = """# Corporate Policy

## Page 1

Table 1: Employee Annual Leave Entitlement

| Employee Grade | Days |
|---|---|
| Grade A | 30 |

## Page 2

| Employee Grade | Days |
|---|---|
| Grade B | 20 |
| Grade C | 15 |
"""
    ev = await DocumentParser.parse(_make_md_envelope(md))
    res = TableContextPipeline.run(ev, ev.envelope_id, ev.asset_id, use_cache=False)
    assert len(res.tables) == 1, "Split table across Page 1 and Page 2 should be reconstructed as 1 logical table"
    assert len(res.tables[0].rows) == 3
    assert all("annual_leave" in c.predicate for c in res.claims)


# ---------------------------------------------------------------------------
# TEST 11: SCANNED TABLES (OCR Word Bounding Box Spatial Reconstruction)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_11_scanned_tables_ocr_word_boxes():
    word_boxes = [
        {"text": "Employee", "bbox": [10, 10, 80, 28]},
        {"text": "Grade", "bbox": [85, 10, 130, 28]},
        {"text": "Days", "bbox": [240, 10, 280, 28]},
        {"text": "Grade A", "bbox": [10, 42, 75, 60]},
        {"text": "30", "bbox": [240, 42, 265, 60]},
        {"text": "Grade B", "bbox": [10, 74, 75, 92]},
        {"text": "20", "bbox": [240, 74, 265, 92]},
    ]
    md_tbl = DocumentSemanticRestructurer.reconstruct_tables_from_word_boxes(word_boxes)
    assert "| Employee Grade | Days |" in md_tbl
    assert "| Grade A | 30 |" in md_tbl

    full_md = f"Table 1: Employee Annual Leave Entitlement\n\n{md_tbl}"
    ev = await DocumentParser.parse(_make_md_envelope(full_md, "scanned_leave.png"))
    res = TableContextPipeline.run(ev, ev.envelope_id, ev.asset_id, use_cache=False)
    assert len(res.claims) == 2
    assert all("annual_leave" in c.predicate for c in res.claims)


# ---------------------------------------------------------------------------
# TEST 12: IDENTICAL VALUES, DIFFERENT BUSINESS DOMAINS (Conflict Engine)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_12_identical_values_different_domains_no_false_conflict():
    md = """# Enterprise Policy Handbook

Table 1: Employee Annual Leave Entitlement

| Employee Grade | Days |
|---|---|
| Grade A | 30 |

Table 2: Employee Annual Sick Leave Entitlement

| Employee Grade | Days |
|---|---|
| Grade A | 30 |

Table 3: Employee Annual Training Allowance

| Employee Grade | Days |
|---|---|
| Grade A | 30 |
"""
    res = await UnifiedExtractionPipeline.execute(
        filename="handbook.md",
        options=UnifiedPipelineOptions(parsed_content=md),
    )
    assert len(res.candidates) == 3
    assert len(res.conflicts) == 0, f"Distinct business topics with identical value '30 days' must NOT conflict: {res.conflicts}"


# ---------------------------------------------------------------------------
# TEST 13: MISLEADING OR CONTRADICTORY TITLES
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_13_misleading_or_contradictory_titles():
    md = """# HR Policy

Table 1: Employee Annual Leave Entitlement

Caption: Sick leave days allowed per year for medical illness.

| Employee Grade | Days |
|---|---|
| Grade A | 15 |
"""
    res = await UnifiedExtractionPipeline.execute(
        filename="contradictory.md",
        options=UnifiedPipelineOptions(parsed_content=md),
    )
    assert len(res.candidates) == 1
    claim = res.candidates[0]
    assert claim.is_ambiguous is True
    assert "mismatch" in (claim.ambiguity_reason or "").lower()
    assert res.evaluations[0].lifecycle_decision == ClaimLifecycleDecision.REVIEW


# ---------------------------------------------------------------------------
# TEST 14: FORMULA-BASED TABLES (Cached Available vs Unavailable != 0)
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_14_formula_based_tables():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Bonus Calculation"
    ws.append(["Bonus Calculation Table", None, None])
    ws.merge_cells("A1:C1")
    ws.append(["Tier", "Base", "Total Bonus"])
    ws.append(["Senior", 1000, "=B3*1.5"])  # Newly created without Excel -> cached value is None!

    buf = io.BytesIO()
    wb.save(buf)
    env = EnvelopeFactory.create_from_file_upload(
        filename="formulas.xlsx",
        raw_bytes=buf.getvalue(),
        parsed_content="",
        organization_id=uuid.UUID("11111111-1111-1111-1111-111111111111"),
        source_id=uuid.UUID("44444444-4444-4444-4444-444444444444"),
        source_family=SourceFamily.STRUCTURED,
        source_intent=SourceIntent.GOVERNANCE_POLICY,
    )
    ev = await XlsxAdapter.parse_to_evidence(env)
    res = TableContextPipeline.run(ev, env.envelope_id, env.asset_id, use_cache=False)

    assert res.interpretations[0].table_type == TableType.CALCULATION
    formula_claim = next(c for c in res.claims if "Total Bonus" in (c.locator or {}).get("col_header", ""))
    assert formula_claim.table_binding.formula == "=B3*1.5"
    assert formula_claim.value is None, "Unavailable formula result must NEVER be interpreted as 0"
    assert formula_claim.is_ambiguous is True


# ---------------------------------------------------------------------------
# TEST 15: UNRELATED SURROUNDING PARAGRAPHS
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_15_unrelated_surrounding_paragraphs_not_attached():
    md = """# Operations Guide

## Section 1: Cafeteria Menu

The cafeteria serves vegetarian lunch options every Tuesday and Thursday.

## Section 2: Security Access Matrix

Table 1: System Access Timeout Limits

| Role | Timeout |
|---|---|
| Admin | 15 minutes |

The annual company picnic will take place in Central Park next July.
"""
    ev = await DocumentParser.parse(_make_md_envelope(md))
    tables = TableContextCollector.collect_tables(ev)
    assert len(tables) == 1
    ctx_text = " ".join(it.text.lower() for it in tables[0].context_bundle.all_items)
    assert "cafeteria" not in ctx_text
    assert "picnic" not in ctx_text
    assert "system access timeout limits" in ctx_text


# ---------------------------------------------------------------------------
# TEST 16: CLAIM EVIDENCE VALIDATION, COMPLETENESS AUDITS & PPTX TABLES
# ---------------------------------------------------------------------------
@pytest.mark.asyncio
async def test_16_evidence_validation_completeness_and_pptx():
    # Part A: Complete evidence + Level 1/Level 2 + Validator + Completeness Audit
    md = """# HR Policy
Table 1: Employee Annual Leave Entitlement

| Employee Grade | Days |
|---|---|
| Grade A | 30 |
| Grade B | 20 |
"""
    ev = await DocumentParser.parse(_make_md_envelope(md))
    res = TableContextPipeline.run(ev, ev.envelope_id, ev.asset_id, use_cache=False)

    assert len(res.consistency_reports) == 1
    assert res.consistency_reports[0].passed is True
    assert all(res.consistency_reports[0].checks.values())
    assert len(res.completeness_reports) == 1
    assert res.completeness_reports[0].cell_completeness_passed is True
    assert res.completeness_reports[0].relationship_completeness_passed is True

    for claim in res.claims:
        assert claim.atomic_fact is not None
        assert claim.semantic_context is not None
        assert claim.confidence_breakdown is not None
        assert len(claim.evidence_refs) >= 3  # scope cell + value cell + row + title context

    # Part B: PPTX native table extraction
    slide_xml = b"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<p:sld xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"
       xmlns:p="http://schemas.openxmlformats.org/presentationml/2006/main">
  <p:cSld><p:spTree>
    <p:sp>
      <p:nvSpPr><p:cNvPr id="1" name="Title"/><p:cNvSpPr/><p:nvPr><p:ph type="title"/></p:nvPr></p:nvSpPr>
      <p:txBody><a:p><a:r><a:t>Employee Annual Leave Entitlement</a:t></a:r></a:p></p:txBody>
    </p:sp>
    <p:graphicFrame><a:graphic><a:graphicData><a:tbl>
      <a:tr>
        <a:tc><a:txBody><a:p><a:r><a:t>Employee Grade</a:t></a:r></a:p></a:txBody></a:tc>
        <a:tc><a:txBody><a:p><a:r><a:t>Days</a:t></a:r></a:p></a:txBody></a:tc>
      </a:tr>
      <a:tr>
        <a:tc><a:txBody><a:p><a:r><a:t>Grade A</a:t></a:r></a:p></a:txBody></a:tc>
        <a:tc><a:txBody><a:p><a:r><a:t>30</a:t></a:r></a:p></a:txBody></a:tc>
      </a:tr>
    </a:tbl></a:graphicData></a:graphic></p:graphicFrame>
  </p:spTree></p:cSld>
</p:sld>"""
    pptx_buf = io.BytesIO()
    with zipfile.ZipFile(pptx_buf, "w") as zf:
        zf.writestr("ppt/slides/slide1.xml", slide_xml)

    pptx_res = await UnifiedExtractionPipeline.execute(
        filename="leave_deck.pptx",
        raw_bytes=pptx_buf.getvalue(),
    )
    assert len(pptx_res.candidates) == 1
    assert "annual_leave" in pptx_res.candidates[0].predicate
    assert "30 days" in pptx_res.candidates[0].object.lower()

    # Part C: Data normalization invariants (inclusive/exclusive, negative, approximate, currency)
    nv_neg = TableValueNormalizer.normalize_cell("($1,250.50)")
    assert nv_neg.is_negative is True
    assert nv_neg.currency_code == "USD"
    assert nv_neg.normalized_value == -1250.5
    assert nv_neg.raw_value == "($1,250.50)"

    nv_approx = TableValueNormalizer.normalize_cell("approx. 14 business days")
    assert nv_approx.is_approximate is True
    assert nv_approx.normalized_value == 14
    assert nv_approx.unit == "business days"


@pytest.mark.asyncio
async def test_17_unified_pipeline_certifies_real_multi_table_enterprise_doc_and_read_gates():
    from app.extraction.unified_pipeline import UnifiedExtractionPipeline
    from app.services.claim_gate_evaluator import ClaimGateEvaluator
    from app.validation_gate.models import ClaimLifecycleDecision

    md = """# Enterprise Policy Pack

### Annual Paid Leave Entitlement
Annual paid leave schedules distinguish between grades.

| Employee Grade | Days |
|---|---|
| Grade A | 30 |
| Grade B | 20 |

### Employee Benefit Allowances
The next table uses grouped headers with a parent.

| Benefit category | Grade A | Grade B | Grade C |
|---|---|---|---|
| Annual learning stipend | ₹5,000 | ₹3,000 | ₹1,500 |

### Compensation Reference by Grade
| Employee Grade | Base Salary | Bonus Target |
|---|---|---|
| Grade A | ₹180,000 | 20% |

### Monthly Payroll Calendar
| Milestone | Target date | Responsible team |
|---|---|---|
| Attendance cutoff | 20th calendar day | People Ops |

### Security RACI Matrix
| Control / Activity | Employee | Manager | IT Security | CISO |
|---|---|---|---|---|
| Report suspected phishing | R | A | C | I |

### Budget Utilization Summary
Budget tracking is finalized after annual review and approval.

| Department | Approved budget | Actual spend |
|---|---|---|
| Engineering | $500,000 | $420,000 |
"""
    res = await UnifiedExtractionPipeline.execute(
        filename="enterprise_policy_pack.md",
        raw_bytes=md.encode("utf-8"),
    )

    eval_by_id = {e.candidate_id: e for e in res.evaluations}
    table_cands = [c for c in res.candidates if c.semantic_context]
    assert len(table_cands) >= 9

    for cand in table_cands:
        ev = eval_by_id[cand.candidate_id]
        assert ev.lifecycle_decision == ClaimLifecycleDecision.APPROVE, (
            f"Expected APPROVE for '{cand.claim_text}', got decision={ev.lifecycle_decision}, "
            f"reasons={ev.rejection_reasons}, span={cand.evidence_text_span!r}"
        )
        assert "distinguish" not in cand.predicate
        assert "next_uses_grouped_headers" not in cand.predicate

        # Verify read-path ClaimGateEvaluator also passes all gates cleanly
        read_eval = ClaimGateEvaluator.evaluate(
            claim_text=cand.claim_text,
            subject=cand.subject,
            predicate=cand.predicate,
            object_text=cand.object,
            claim_type="rule",
            status="verified",
            evidence_snippet=cand.evidence_text_span,
            confidence_or_trust=cand.confidence,
        )
        assert read_eval.gates["claim_type_allowed"] is True, read_eval.rejection_reasons
        assert read_eval.all_9_gates_passed is True, read_eval.rejection_reasons
        assert read_eval.certification_tier == "AUTOMATED_CERTIFIED"

    # Benefit allowance Grade A/B/C must NOT be collapsed into subject
    benefit_cands = [c for c in table_cands if "learning stipend" in c.subject.lower()]
    assert len(benefit_cands) == 3
    assert all(
        "grade a" not in c.subject.lower()
        and "grade b" not in c.subject.lower()
        and "grade c" not in c.subject.lower()
        for c in benefit_cands
    )

    # Monthly Payroll Calendar must stay schedule (not is_responsible_for_*)
    payroll_cands = [c for c in table_cands if "attendance cutoff" in c.subject.lower()]
    assert payroll_cands
    assert all(not c.predicate.startswith("is_responsible_for_") for c in payroll_cands)

    # Budget Utilization Summary must NOT be is_responsible_for_* due to "approval" in prose
    budget_cands = [c for c in table_cands if "engineering" in c.subject.lower()]
    assert len(budget_cands) == 2
    assert all(not c.predicate.startswith("is_responsible_for_") for c in budget_cands)

    # RACI matrix roles must stay rule columns, NOT collapsed into subject
    raci_cands = [c for c in table_cands if "phishing" in c.subject.lower()]
    assert len(raci_cands) == 4
    assert all(c.subject == "Report suspected phishing" for c in raci_cands)
    assert any("Manager must act as A (Accountable)" in c.claim_text for c in raci_cands)


@pytest.mark.asyncio
async def test_18_docx_multi_table_certification_and_text_override():
    import docx
    from app.extraction.unified_pipeline import UnifiedExtractionPipeline
    from app.validation_gate.models import ClaimLifecycleDecision

    doc = docx.Document()
    doc.add_heading("Leave Policy", level=2)
    t1 = doc.add_table(rows=2, cols=2)
    t1.rows[0].cells[0].text = "Employee Grade"
    t1.rows[0].cells[1].text = "Days"
    t1.rows[1].cells[0].text = "Grade A"
    t1.rows[1].cells[1].text = "30"

    buf = io.BytesIO()
    doc.save(buf)

    docx_res = await UnifiedExtractionPipeline.execute(
        filename="leave_policy.docx",
        raw_bytes=buf.getvalue(),
    )
    docx_evals = {e.candidate_id: e for e in docx_res.evaluations}
    table_cands = [c for c in docx_res.candidates if c.semantic_context]
    assert len(table_cands) == 1
    assert docx_evals[table_cands[0].candidate_id].lifecycle_decision == ClaimLifecycleDecision.APPROVE
    assert "30 days" in table_cands[0].object.lower()

    # Also verify parsed_content text override works on .docx filename without ZIP error
    md_override = "### Leave Policy\n\n| Employee Grade | Days |\n|---|---|\n| Grade A | 30 |\n"
    override_res = await UnifiedExtractionPipeline.execute(
        filename="leave_policy.docx",
        raw_bytes=md_override.encode("utf-8"),
        parsed_content=md_override,
    )
    ov_evals = {e.candidate_id: e for e in override_res.evaluations}
    override_table_cands = [c for c in override_res.candidates if c.semantic_context]
    assert len(override_table_cands) == 1
    assert ov_evals[override_table_cands[0].candidate_id].lifecycle_decision == ClaimLifecycleDecision.APPROVE


@pytest.mark.asyncio
async def test_19_northbridge_pdf_and_short_normalized_predicates():
    import pathlib
    from app.extraction.unified_pipeline import UnifiedExtractionPipeline

    pdf_path = pathlib.Path(
        r"C:\Users\praga\Trulin\backend\storage\uploads\7d3fe54b-f489-48ce-9fcf-bfaf71ba5cfc\Northbridge_Policy_Page1.pdf"
    )
    if not pdf_path.exists():
        pytest.skip("Northbridge_Policy_Page1.pdf fixture not present")

    res = await UnifiedExtractionPipeline.execute(
        filename=pdf_path.name,
        raw_bytes=pdf_path.read_bytes(),
    )

    # 1. Table 1: All 10 Document Control records extracted with short normalized predicates
    kv_preds = {c.predicate: c.object for c in res.candidates if c.subject == "Policy"}
    assert kv_preds.get("has_version") == "4.2"
    assert kv_preds.get("has_status") == "Approved - Final"
    assert kv_preds.get("has_effective_date") == "01 January 2027"
    assert kv_preds.get("has_review_date") == "31 December 2027"
    assert kv_preds.get("has_owner") == "Chief People Officer"
    assert kv_preds.get("approved_by") == "Board Human Resources Committee"
    assert "Northbridge Global Industries" in kv_preds.get("applies_to", "")
    assert kv_preds.get("has_classification") == "Internal - Restricted"
    assert kv_preds.get("has_document_number") == "NGI-HR-POL-014"
    assert "Group Employee Benefits" in kv_preds.get("has_title", "")

    # No bloated doc-title/doc-number predicates
    assert all("ngi_hr_pol_014" not in c.predicate for c in res.candidates)
    assert all(len(c.predicate) <= 40 for c in res.candidates)

    # 2. Table 2: All 5 Revision History records with mixed date formats preserved
    rev_dates = {
        c.subject: c.object
        for c in res.candidates
        if c.predicate == "has_revision_date"
    }
    assert rev_dates == {
        "Policy version 3.0": "2024-03-15",
        "Policy version 3.1": "2024-11-02",
        "Policy version 4.0": "12/09/2025",
        "Policy version 4.1": "02 April 2026",
        "Policy version 4.2": "28-Oct-2026",
    }

    # 3. Table 3: All 4 Approval Signatories, dates only for first 2, zero empty Signature claims
    signatories = {c.subject: c.object for c in res.candidates if c.predicate == "has_signatory"}
    assert signatories == {
        "Chief People Officer": "Ananya Kapoor",
        "Chief Financial Officer": "Vikram Desai",
        "General Counsel": "Meera Rao",
        "Chair, HR Committee": "Dr. Suresh Nair",
    }
    approval_dates = {c.subject: c.object for c in res.candidates if c.predicate == "has_approval_date"}
    assert approval_dates == {
        "Chief People Officer": "05-Nov-2026",
        "Chief Financial Officer": "06-Nov-2026",
    }
    assert not any(c.predicate == "has_signature" for c in res.candidates)
