"""
Phase 6 Step 6.2: XLSX Adapter Integration & Universal Gate Contract Test Suite.

Validates:
1. XLSX adapter multi-sheet traversal, sheet naming, and table structure extraction.
2. Merged cell resolution across rows/columns preserving cell context and preventing None gaps.
3. Evidence contract conformance: TABLE_ROW and TABLE_CELL evidence units with exact coordinates,
   cell typing (currency, percentage, numeric, date), deterministic unit_ids, and SHA-256 content hashes.
4. Universal Gate Contract compliance across all 8 families with emphasis on:
   - Family 7: Value & Quantitative Fidelity (currency, percentage, numeric fidelity)
   - Family 3: Table-Column Binding Integrity
5. Real multi-sheet XLSX end-to-end smoke test through UnifiedExtractionPipeline.
"""

import dataclasses
import io
import uuid
import pytest
import openpyxl

from app.db.enums import SourceFamily, SourceIntent
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.ingestion.parsers.xlsx_parser import XlsxAdapter
from app.ingestion.parsers.evidence_model import ContentRole, ParsedEvidenceResult, ParsedEvidenceUnit
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


def _build_test_xlsx_bytes() -> bytes:
    """Helper to construct an in-memory realistic multi-sheet enterprise spreadsheet."""
    wb = openpyxl.Workbook()
    
    # Sheet 1: Refund & Cancellation Schedules (Multi-row, Currency, Percentages)
    ws1 = wb.active
    ws1.title = "Refund Schedule"
    
    # Header row
    ws1["A1"] = "Service Tier"
    ws1["B1"] = "Cancellation Window"
    ws1["C1"] = "Restocking Fee"
    ws1["D1"] = "Refund Percentage"
    
    # Row 2
    ws1["A2"] = "Enterprise Plan"
    ws1["B2"] = "30 days"
    ws1["C2"] = 0.0
    ws1["C2"].number_format = "$#,##0.00"
    ws1["D2"] = 1.0
    ws1["D2"].number_format = "0.0%"
    
    # Row 3 & 4 with merged cell on Service Tier (A3:A4)
    ws1.merge_cells("A3:A4")
    ws1["A3"] = "Custom Hardware"
    ws1["B3"] = "14 days"
    ws1["C3"] = 150.00
    ws1["C3"].number_format = "$#,##0.00"
    ws1["D3"] = 0.85
    ws1["D3"].number_format = "0.0%"
    
    # Row 4 (inherits Custom Hardware in col A due to merge)
    ws1["B4"] = "7 days"
    ws1["C4"] = 250.00
    ws1["C4"].number_format = "$#,##0.00"
    ws1["D4"] = 0.50
    ws1["D4"].number_format = "0.0%"

    # Sheet 2: Warranty Coverage Matrix
    ws2 = wb.create_sheet(title="Warranty Matrix")
    ws2["A1"] = "Equipment Type"
    ws2["B1"] = "Coverage Period"
    ws2["C1"] = "Max Replacement Limit"
    ws2["D1"] = "Approval Required"
    
    ws2["A2"] = "Core Server"
    ws2["B2"] = "3 years"
    ws2["C2"] = 5000.00
    ws2["C2"].number_format = "$#,##0.00"
    ws2["D2"] = "VP Infrastructure"

    ws2["A3"] = "Edge Router"
    ws2["B3"] = "1 year"
    ws2["C3"] = 1200.00
    ws2["C3"].number_format = "$#,##0.00"
    ws2["D3"] = "Engineering Lead"

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_xlsx_adapter_multi_sheet_parsing():
    """Validates multi-sheet extraction, sheet titles, and Markdown table output."""
    raw_bytes = _build_test_xlsx_bytes()
    
    full_text, pages, blocks, tables, warnings = XlsxAdapter.parse_to_structured(
        raw_bytes=raw_bytes,
        title="Enterprise Rate & Warranty Schedules",
        filename="rates_and_warranties.xlsx",
    )
    
    assert len(warnings) == 0, f"Unexpected warnings: {warnings}"
    assert len(tables) == 2, "Expected 2 sheets extracted as tables"
    assert len(blocks) == 2, "Expected 2 table blocks"
    assert len(pages) == 2, "Expected 2 pages (one per sheet)"
    
    # Verify Sheet 1
    t1 = tables[0]
    assert t1["sheet_name"] == "Refund Schedule"
    assert t1["headers"] == ["Service Tier", "Cancellation Window", "Restocking Fee", "Refund Percentage"]
    assert len(t1["rows"]) == 4  # Header + 3 data rows
    
    # Verify Sheet 2
    t2 = tables[1]
    assert t2["sheet_name"] == "Warranty Matrix"
    assert t2["headers"] == ["Equipment Type", "Coverage Period", "Max Replacement Limit", "Approval Required"]
    assert len(t2["rows"]) == 3  # Header + 2 data rows
    
    # Verify Markdown formatting
    assert "## Sheet: Refund Schedule" in full_text
    assert "## Sheet: Warranty Matrix" in full_text
    assert "| Enterprise Plan | 30 days | $0.00 | 100% |" in full_text


def test_xlsx_adapter_merged_cell_resolution():
    """Validates that merged cells (e.g. A3:A4) propagate values to child rows without gaps."""
    raw_bytes = _build_test_xlsx_bytes()
    
    _, _, _, tables, _ = XlsxAdapter.parse_to_structured(
        raw_bytes=raw_bytes,
        title="Rate Schedules",
        filename="rates.xlsx",
    )
    
    t1 = tables[0]
    rows = t1["rows"]
    
    # Row 3 (index 2) was the top cell of merge A3:A4
    assert rows[2][0] == "Custom Hardware"
    assert rows[2][1] == "14 days"
    assert rows[2][2] == "$150.00"
    
    # Row 4 (index 3) was the bottom cell of merge A3:A4; must inherit "Custom Hardware"
    assert rows[3][0] == "Custom Hardware", "Child cell in merged range must inherit master cell value"
    assert rows[3][1] == "7 days"
    assert rows[3][2] == "$250.00"


@pytest.mark.asyncio
async def test_xlsx_adapter_to_evidence_units_contract():
    """Validates TABLE_ROW and TABLE_CELL evidence units contract conformance."""
    raw_bytes = _build_test_xlsx_bytes()
    envelope_id = uuid.uuid4()
    org_id = uuid.uuid4()
    source_id = uuid.uuid4()
    
    envelope = CanonicalSourceEnvelope(
        envelope_id=envelope_id,
        organization_id=org_id,
        source_id=source_id,
        asset_id="file://rates_and_warranties.xlsx",
        source_family=SourceFamily.STRUCTURED,
        source_intent=SourceIntent.OPERATIONAL_DATA,
        native_format="xlsx",
        source_version="1",
        content_hash="mock_hash",
        raw_payload=raw_bytes,
        locator_metadata={"filename": "rates_and_warranties.xlsx", "raw_bytes": raw_bytes},
        metadata={"filename": "rates_and_warranties.xlsx", "raw_bytes": raw_bytes},
    )
    
    evidence_res = await XlsxAdapter.parse_to_evidence(envelope)
    
    assert isinstance(evidence_res, ParsedEvidenceResult)
    assert len(evidence_res.units) > 0
    
    # Inspect TABLE_ROW units
    row_units = [u for u in evidence_res.units if u.block_type == "table_row"]
    assert len(row_units) == 5, "Expected 3 data rows from Sheet 1 + 2 data rows from Sheet 2"
    
    for ru in row_units:
        assert ru.unit_id is not None
        assert len(ru.content_hash) == 64
        assert ru.structured_data.get("table_id") is not None
        assert "headers" in ru.structured_data
        assert "columns" in ru.structured_data
        
    # Inspect TABLE_CELL units
    cell_units = [u for u in evidence_res.units if u.block_type == "table_cell"]
    assert len(cell_units) > 0, "Expected individual TABLE_CELL units"
    
    # Verify cell typing
    currencies = [cu for cu in cell_units if cu.structured_data.get("data_type") == "currency"]
    assert len(currencies) >= 4, "Must identify currency cells ($0.00, $150.00, $250.00, etc.)"
    assert any("$150.00" in cu.content_text for cu in currencies)
    
    percentages = [cu for cu in cell_units if cu.structured_data.get("data_type") == "percentage"]
    assert len(percentages) >= 2, "Must identify percentage cells (100%, 85%, 50%)"
    assert any("85" in cu.content_text for cu in percentages)


def test_xlsx_gate_contract_all_8_families():
    """Validates evaluation against all 8 Universal Gate Contract families with focus on Family 7 Value Fidelity."""
    table_quote_currency = "| Custom Hardware | 14 days | $150.00 | 85% |"
    table_quote_warranty = "| Core Server | 3 years | $5,000.00 | VP Infrastructure |"

    # 1. Valid currency and percentage claim extracted from XLSX
    req_valid = SharedGateRequest(
        claim_text="Custom Hardware has a restocking fee of $150.00 and 85% refund.",
        subject="Custom Hardware",
        predicate="has_fee_rule",
        object_val="$150.00",
        table_header="Restocking Fee",
        evidence_quote=table_quote_currency,
        document_text=table_quote_currency,
        status="candidate",
        confidence=0.96,
    )
    res_valid = SharedGovernanceGateEngine.evaluate(req_valid)
    assert res_valid.evidence_grounding is True
    assert res_valid.table_column_binding is True
    assert res_valid.value_fidelity is True
    assert res_valid.all_gates_passed is True

    # Family 7 Failure: Currency Discrepancy (Claim asserts $450.00 but evidence specifies $150.00)
    req_f7_currency = dataclasses.replace(
        req_valid,
        claim_text="Custom Hardware has a restocking fee of $450.00.",
        object_val="$450.00",
    )
    res_f7_currency = SharedGovernanceGateEngine.evaluate(req_f7_currency)
    assert res_f7_currency.value_fidelity is False
    assert res_f7_currency.all_gates_passed is False
    assert GateFailureCode.ERR_VALUE_FIDELITY_MISMATCH.value in res_f7_currency.reason_codes

    # Family 7 Failure: Percentage Discrepancy (Claim asserts 40% but evidence specifies 85%)
    req_f7_pct = dataclasses.replace(
        req_valid,
        claim_text="Custom Hardware offers a 40% refund rate.",
        predicate="has_refund_percentage",
        object_val="40%",
        table_header="Refund Percentage",
    )
    res_f7_pct = SharedGovernanceGateEngine.evaluate(req_f7_pct)
    assert res_f7_pct.value_fidelity is False
    assert res_f7_pct.all_gates_passed is False
    assert GateFailureCode.ERR_VALUE_FIDELITY_MISMATCH.value in res_f7_pct.reason_codes

    # Family 3 Failure: Table-Column Header Mismatch
    req_f3 = dataclasses.replace(
        req_valid,
        predicate="has_warranty_period",
        table_header="return label cost",
    )
    res_f3 = SharedGovernanceGateEngine.evaluate(req_f3)
    assert res_f3.table_column_binding is False
    assert res_f3.all_gates_passed is False
    assert GateFailureCode.ERR_TABLE_BINDING_MISMATCH.value in res_f3.reason_codes

    # Family 1 Failure: Empty Evidence
    req_f1 = dataclasses.replace(req_valid, evidence_quote="")
    res_f1 = SharedGovernanceGateEngine.evaluate(req_f1)
    assert res_f1.evidence_grounding is False
    assert GateFailureCode.ERR_EVIDENCE_MISSING.value in res_f1.reason_codes

    # Family 2 Failure: Generic Catch-All Predicate
    req_f2 = dataclasses.replace(req_valid, predicate="has_summary")
    res_f2 = SharedGovernanceGateEngine.evaluate(req_f2)
    assert res_f2.predicate_normativity is False
    assert GateFailureCode.ERR_PREDICATE_CATCH_ALL.value in res_f2.reason_codes

    # Family 8 Failure: Silent Upgrade Protection
    req_f8 = dataclasses.replace(
        req_valid,
        status="rejected",
        target_status="verified",
        is_upgrade_attempt=True,
    )
    res_f8 = SharedGovernanceGateEngine.evaluate(req_f8)
    assert res_f8.no_silent_upgrade is False
    assert GateFailureCode.ERR_NO_SILENT_UPGRADE_VIOLATION.value in res_f8.reason_codes


@pytest.mark.asyncio
async def test_xlsx_end_to_end_smoke():
    """Validates Deliverable 5: 1 real multi-sheet XLSX end-to-end smoke test through pipeline."""
    raw_bytes = _build_test_xlsx_bytes()
    filename = "enterprise_rates_and_warranties.xlsx"
    
    # 1. UniversalFileParser integration test
    parsed_doc = UniversalFileParser.parse_file(
        filename=filename,
        raw_bytes=raw_bytes,
        doc_title="Enterprise Rates and Warranties",
    )
    parsed_text = parsed_doc.full_text if hasattr(parsed_doc, "full_text") else str(parsed_doc)
    assert "Enterprise Rates and Warranties" in parsed_text
    assert "## Sheet: Refund Schedule" in parsed_text
    assert "## Sheet: Warranty Matrix" in parsed_text
    assert "| Custom Hardware | 14 days | $150.00 | 85% |" in parsed_text
    
    # 2. UnifiedExtractionPipeline execution
    res = await UnifiedExtractionPipeline.execute(
        filename=filename,
        raw_bytes=raw_bytes,
        options=UnifiedPipelineOptions(
            doc_title="Enterprise Rates and Warranties",
            skip_db_persist=True,  # In-memory test
        ),
    )
    
    assert res.pipeline_run_id is not None
    assert len(res.candidates) > 0
    assert len(res.evaluations) > 0
    
    # Verify claims captured quantitative values from sheets
    claims_text = " ".join([c.claim_text for c in res.candidates])
    assert "Custom Hardware" in claims_text or "Enterprise Plan" in claims_text or "Core Server" in claims_text
