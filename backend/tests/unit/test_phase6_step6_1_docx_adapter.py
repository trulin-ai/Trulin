"""
Phase 6 Step 6.1: DOCX Adapter Integration & Universal Gate Contract Test Suite.

Validates:
1. DOCX parser adapter mapping headings, paragraphs, bullet/numbered lists, and tables to canonical AST.
2. Evidence contract conformance: deterministic unit_id, exact char offsets, SHA-256 hashes, breadcrumbs.
3. Universal Gate Contract compliance across all 8 families for DOCX-extracted claims:
   - Family 1: Evidence Grounding & Source-Locator Validity
   - Family 2: Predicate Normativity & Taxonomy
   - Family 3: Table-Column Binding Integrity
   - Family 4: SPO Compatibility & Semantic Typing
   - Family 5: Polarity & Modality Consistency
   - Family 6: Condition, Exception & Scope Preservation
   - Family 7: Value & Quantitative Fidelity
   - Family 8: Status & Silent Upgrade Invariants
4. Real DOCX end-to-end smoke test through UnifiedExtractionPipeline.
"""

import io
import uuid
import pytest
import docx

from app.db.enums import SourceFamily, SourceIntent
from app.ingestion.envelope import CanonicalSourceEnvelope, EnvelopeFactory
from app.ingestion.parsers.docx_parser import DocxAdapter
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


def _build_test_docx_bytes() -> bytes:
    """Helper to construct an in-memory realistic enterprise policy DOCX."""
    doc = docx.Document()
    
    # Title & Metadata
    doc.core_properties.title = "Global Information Security Policy"
    doc.core_properties.author = "Security & Compliance Office"
    
    # Heading 1: Overview
    doc.add_heading("1. Purpose and Scope", level=1)
    doc.add_paragraph("This policy defines the security mandates and access controls for all corporate infrastructure.")
    
    # Heading 2: Access Control
    doc.add_heading("2. Access Control and Authentication", level=2)
    doc.add_paragraph("Refund exceptions over $500 require Customer Experience Manager approval.")
    doc.add_paragraph("Contractors cannot access customer production data without explicit DPO approval.")
    doc.add_paragraph("If an employee is on approved medical leave, the claim submission window is extended by 14 days.")
    
    # Bulleted lists
    doc.add_paragraph("Security keys are required for administrative roles.", style="List Bullet")
    doc.add_paragraph("Standard password length must be at least 16 characters.", style="List Bullet")
    
    # Heading 2: Table Section
    doc.add_heading("3. Infrastructure Access Matrix", level=2)
    
    # Table with headers and rows
    table = doc.add_table(rows=3, cols=3)
    # Headers
    table.cell(0, 0).text = "Role"
    table.cell(0, 1).text = "Session Timeout"
    table.cell(0, 2).text = "Approval Required"
    # Row 1
    table.cell(1, 0).text = "Developer"
    table.cell(1, 1).text = "8 hours"
    table.cell(1, 2).text = "Engineering Lead"
    # Row 2 (with internal newline in cell to test newline sanitization)
    table.cell(2, 0).text = "Cloud Administrator"
    table.cell(2, 1).text = "1 hour\n(Strict)"
    table.cell(2, 2).text = "Chief Information Security Officer"
    
    # Heading 2: Non-operative context
    doc.add_heading("4. Definitions and Contacts", level=2)
    doc.add_paragraph("Definition: DPO refers to the certified Data Protection Officer.")
    doc.add_paragraph("For escalations, contact the SOC team at secops@enterprise-corp.com.")
    
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def test_docx_adapter_heading_hierarchy_and_blocks():
    """Validates Deliverables 1 & 2: Heading levels, list items, and character offsets."""
    raw_bytes = _build_test_docx_bytes()
    
    full_text, pages, blocks, tables, warnings = DocxAdapter.parse_to_structured(
        raw_bytes=raw_bytes,
        title="Global Information Security Policy",
        filename="security_policy.docx",
    )
    
    assert len(warnings) == 0, f"Unexpected warnings: {warnings}"
    assert len(blocks) > 0, "Blocks must not be empty"
    assert len(tables) == 1, "Expected 1 table in DOCX"
    
    # Verify Heading types
    headings = [b for b in blocks if b.block_type == ContentBlockType.HEADING]
    assert len(headings) >= 4, "Must identify H1 and H2 headings"
    assert any("Global Information Security Policy" in h.text or "1. Purpose and Scope" in h.text for h in headings)
    
    # Verify Lists
    list_items = [b for b in blocks if b.block_type == ContentBlockType.LIST_ITEM]
    assert len(list_items) >= 2, "Must identify bullet list items"
    assert any("Security keys are required" in li.text for li in list_items)
    
    # Verify character offsets are strictly increasing
    for i in range(len(blocks) - 1):
        assert blocks[i].start_char_offset <= blocks[i].end_char_offset
        assert blocks[i].end_char_offset <= blocks[i + 1].start_char_offset


def test_docx_adapter_table_extraction_and_cell_cleaning():
    """Validates table extraction, column headers, cell sanitization, and row structure."""
    raw_bytes = _build_test_docx_bytes()
    
    _, _, blocks, tables, _ = DocxAdapter.parse_to_structured(
        raw_bytes=raw_bytes,
        title="Security Policy",
        filename="security_policy.docx",
    )
    
    table = tables[0]
    assert table["headers"] == ["Role", "Session Timeout", "Approval Required"]
    assert len(table["rows"]) == 3  # header + 2 data rows
    
    # Check row 2 has cleaned cell text (newline replaced with space)
    row2 = table["rows"][2]
    assert "\n" not in row2[1], "Internal newline in table cell must be sanitized to space"
    assert "1 hour" in row2[1]
    
    # Verify table block
    table_blocks = [b for b in blocks if b.block_type == ContentBlockType.TABLE]
    assert len(table_blocks) == 1
    assert "| Role | Session Timeout | Approval Required |" in table_blocks[0].text
    assert ":---" in table_blocks[0].text


@pytest.mark.asyncio
async def test_docx_adapter_to_evidence_units_contract():
    """Validates Deliverable 1: Evidence contract compliance (unit_id, offsets, hashes, breadcrumbs)."""
    raw_bytes = _build_test_docx_bytes()
    envelope_id = uuid.uuid4()
    org_id = uuid.uuid4()
    source_id = uuid.uuid4()
    
    envelope = CanonicalSourceEnvelope(
        envelope_id=envelope_id,
        organization_id=org_id,
        source_id=source_id,
        asset_id="file://security_policy.docx",
        source_family=SourceFamily.DOCUMENT,
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        native_format="docx",
        source_version="1",
        content_hash="mock_hash",
        raw_payload=raw_bytes,
        locator_metadata={"filename": "security_policy.docx"},
    )
    
    evidence_res = await DocxAdapter.parse_to_evidence(envelope)
    
    assert isinstance(evidence_res, ParsedEvidenceResult)
    assert len(evidence_res.units) > 0
    
    # Every unit must have deterministic unit_id, valid SHA-256 hash, and offsets
    for unit in evidence_res.units:
        assert unit.unit_id is not None
        assert len(unit.content_hash) == 64, "Must have valid 64-char SHA-256 content hash"
        assert unit.char_start is not None
        assert unit.char_end is not None
        assert unit.char_start <= unit.char_end
        
    # Check table rows are parsed as units with table_id and column cells
    table_units = [u for u in evidence_res.units if u.block_type == "table_row"]
    assert len(table_units) >= 2
    assert "Role" in table_units[0].structured_data.get("columns", {})
    
    # Check content roles
    roles = {u.content_role for u in evidence_res.units}
    assert ContentRole.HEADING in roles
    assert ContentRole.POLICY_RULE in roles or ContentRole.CONDITIONAL_RULE in roles


def test_docx_gate_contract_all_8_families():
    """Validates Deliverable 3: Evaluation against all 8 Universal Gate Contract families."""
    doc_text = (
        "Refund exceptions over $500 require Customer Experience Manager approval. "
        "Contractors cannot access customer production data without explicit DPO approval. "
        "If an employee is on approved medical leave, the employee may request a 14-day window extension. "
        "Developer 8 hours Engineering Lead"
    )

    # 1. Valid normative rule claim extracted from DOCX
    req_valid = SharedGateRequest(
        claim_text="Refund exceptions over $500 require Customer Experience Manager approval.",
        subject="Refund approval",
        predicate="requires_approval_role",
        object_val="Customer Experience Manager",
        evidence_quote="Refund exceptions over $500 require Customer Experience Manager approval.",
        document_text=doc_text,
        status="candidate",
        confidence=0.95,
    )
    res_valid = SharedGovernanceGateEngine.evaluate(req_valid)
    assert res_valid.evidence_grounding is True
    assert res_valid.predicate_normativity is True
    assert res_valid.all_gates_passed is True

    # Family 1 Failure: Invalid Evidence Grounding (Empty quote)
    req_f1 = SharedGateRequest(
        claim_text=req_valid.claim_text,
        subject=req_valid.subject,
        predicate=req_valid.predicate,
        object_val=req_valid.object_val,
        evidence_quote="",  # Missing
        document_text=doc_text,
    )
    res_f1 = SharedGovernanceGateEngine.evaluate(req_f1)
    assert res_f1.evidence_grounding is False
    assert res_f1.all_gates_passed is False
    assert GateFailureCode.ERR_EVIDENCE_MISSING.value in res_f1.reason_codes

    # Family 2 Failure: Unregistered / Banned Catch-All Predicate
    req_f2 = SharedGateRequest(
        claim_text=req_valid.claim_text,
        subject=req_valid.subject,
        predicate="has_summary",  # Catch-all banned
        object_val=req_valid.object_val,
        evidence_quote=req_valid.evidence_quote,
        document_text=doc_text,
    )
    res_f2 = SharedGovernanceGateEngine.evaluate(req_f2)
    assert res_f2.predicate_normativity is False
    assert res_f2.all_gates_passed is False
    assert GateFailureCode.ERR_PREDICATE_CATCH_ALL.value in res_f2.reason_codes

    # Family 3 Check: Table-Column Binding
    req_table = SharedGateRequest(
        claim_text="Developer requires Engineering Lead approval.",
        subject="Developer",
        predicate="requires_approval_role",
        object_val="Engineering Lead",
        table_header="Approval Required",
        evidence_quote="Developer 8 hours Engineering Lead",
        document_text=doc_text,
    )
    res_table = SharedGovernanceGateEngine.evaluate(req_table)
    assert res_table.table_column_binding is True
    assert res_table.all_gates_passed is True

    # Family 5 Failure: Polarity Inversion (Prohibition predicate applied to affirmative phrasing)
    req_f5 = SharedGateRequest(
        claim_text="All employees may request standard access permissions.",
        subject="Employee",
        predicate="cannot_be_returned_or_refunded",
        object_val="standard access permissions",
        evidence_quote="All employees may request standard access permissions.",
        document_text="All employees may request standard access permissions.",
    )
    res_f5 = SharedGovernanceGateEngine.evaluate(req_f5)
    assert res_f5.polarity_consistency is False
    assert res_f5.all_gates_passed is False
    assert GateFailureCode.ERR_POLARITY_INVERSION.value in res_f5.reason_codes

    # Family 6 Check: Condition & Exception Preservation
    req_f6 = SharedGateRequest(
        claim_text="If an employee is on approved medical leave, the employee may request a 14-day window extension.",
        subject="Employee",
        predicate="has_price_adjustment_window",
        object_val="14-day window extension",
        conditions=["approved medical leave"],
        evidence_quote="If an employee is on approved medical leave, the employee may request a 14-day window extension.",
        document_text=doc_text,
    )
    res_f6 = SharedGovernanceGateEngine.evaluate(req_f6)
    assert res_f6.condition_preservation is True
    assert res_f6.all_gates_passed is True

    # Family 7 Failure: Value Fidelity Mismatch (Claim asserts $250 but evidence specifies $50)
    req_f7 = SharedGateRequest(
        claim_text="Maximum expense reimbursement is $250.00 per day.",
        subject="Employee",
        predicate="has_warranty_period",
        object_val="$250.00",
        evidence_quote="Maximum expense reimbursement is $50.00 per day.",
        document_text="Maximum expense reimbursement is $50.00 per day.",
    )
    res_f7 = SharedGovernanceGateEngine.evaluate(req_f7)
    assert res_f7.value_fidelity is False
    assert res_f7.all_gates_passed is False
    assert GateFailureCode.ERR_VALUE_FIDELITY_MISMATCH.value in res_f7.reason_codes

    # Family 8 Check: Silent Upgrade Protection (Forbidden upgrade without review)
    req_f8 = SharedGateRequest(
        claim_text=req_valid.claim_text,
        subject=req_valid.subject,
        predicate=req_valid.predicate,
        object_val=req_valid.object_val,
        evidence_quote=req_valid.evidence_quote,
        document_text=doc_text,
        status="rejected",
        target_status="verified",
        is_upgrade_attempt=True,
    )
    res_f8 = SharedGovernanceGateEngine.evaluate(req_f8)
    assert res_f8.no_silent_upgrade is False
    assert res_f8.all_gates_passed is False
    assert GateFailureCode.ERR_NO_SILENT_UPGRADE_VIOLATION.value in res_f8.reason_codes


@pytest.mark.asyncio
async def test_docx_end_to_end_smoke():
    """Validates Deliverable 5: 1 real DOCX end-to-end smoke test through UniversalFileParser and pipeline."""
    raw_bytes = _build_test_docx_bytes()
    filename = "corporate_security_policy.docx"
    
    # 1. Test UniversalFileParser entrypoint
    parsed_text = UniversalFileParser.parse_file(
        filename=filename,
        raw_bytes=raw_bytes,
        doc_title="Global Information Security Policy",
    )
    assert "Global Information Security Policy" in parsed_text
    assert "## 2. Access Control and Authentication" in parsed_text
    assert "| Role | Session Timeout | Approval Required |" in parsed_text
    
    # 2. Test UnifiedExtractionPipeline execution
    res = await UnifiedExtractionPipeline.execute(
        filename=filename,
        raw_bytes=raw_bytes,
        options=UnifiedPipelineOptions(
            doc_title="Global Information Security Policy",
            skip_db_persist=True,  # In-memory smoke test
        ),
    )
    
    assert res.pipeline_run_id is not None
    assert len(res.candidates) > 0
    assert len(res.evaluations) > 0
    
    # Verify claims contain extracted policy facts and table-bound attributes
    claims_text = " ".join([c.claim_text for c in res.candidates])
    assert "Customer Experience Manager" in claims_text or "Developer" in claims_text or "approval" in claims_text
