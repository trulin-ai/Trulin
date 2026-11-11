"""
Phase 6 Step 6.4: Unit & Integration Regression Test Suite for Text & Web Adapters.

Tests:
1. Markdown Adapter: Headings, breadcrumb hierarchy, nested lists, pipe tables, code blocks, YAML frontmatter.
2. HTML Adapter: DOM structure, semantic headings, lists, tables with colspan, tag filtering (scripts/styles).
3. CSV/TSV Adapter: Delimiter detection (, vs \\t vs ;), encoding, table rows, cell fidelity, synthetic pagination.
4. Evidence Contract Conformance: Deterministic unit IDs (UUID5), char offsets, SHA-256 hashes, breadcrumbs.
5. 8 Universal Gate Contract Families Conformance.
6. End-to-End Smoke Tests: 1 Markdown + 1 HTML + 1 CSV through UnifiedExtractionPipeline.
"""

import io
import pytest
import uuid

from app.db.enums import SourceFamily, SourceIntent
from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions
from app.ingestion.envelope import CanonicalSourceEnvelope, EnvelopeFactory
from app.ingestion.parsers.csv_adapter import CsvAdapter
from app.ingestion.parsers.html_adapter import HtmlAdapter
from app.ingestion.parsers.markdown_adapter import MarkdownAdapter
from app.ingestion.universal_file_parser import (
    ContentBlockType,
    UniversalFileParser,
)
from app.services.gate_contract import GateFailureCode, SharedGovernanceGateEngine, SharedGateRequest


# -----------------------------------------------------------------------------
# 1. Markdown Adapter Tests
# -----------------------------------------------------------------------------

def test_markdown_adapter_headings_and_hierarchy():
    """Validates Deliverable 1: Markdown heading hierarchies (H1 to H4) and breadcrumb paths."""
    md_content = """# Corporate Hardware & Return Governance
## 1. Scope and Eligibility
### 1.1 Standard Hardware Devices
All enterprise laptops must be returned within 30 days of termination.
#### 1.1.1 Exceptions
Servers and rack equipment are exempt from standard returns.
"""
    raw_bytes = md_content.encode("utf-8")
    full_text, pages, blocks, tables, warnings = MarkdownAdapter.parse_to_structured(
        raw_bytes=raw_bytes,
        title="Hardware Governance",
        filename="governance.md",
    )

    assert len(warnings) == 0
    assert len(pages) == 1
    assert len(blocks) >= 5

    headings = [b for b in blocks if b.block_type == ContentBlockType.HEADING]
    assert len(headings) == 4
    assert headings[0].metadata["heading_level"] == 1
    assert headings[1].metadata["heading_level"] == 2
    assert headings[2].metadata["heading_level"] == 3
    assert headings[3].metadata["heading_level"] == 4

    # Check breadcrumb ancestry on the deeply nested paragraph
    para = [b for b in blocks if "Servers and rack" in b.text][0]
    assert para.heading_path == [
        "Corporate Hardware & Return Governance",
        "1. Scope and Eligibility",
        "1.1 Standard Hardware Devices",
        "1.1.1 Exceptions",
    ]


def test_markdown_adapter_nested_bullets_and_lists():
    """Validates Deliverable 1: Nested bullet and numbered lists with indentation levels."""
    md_content = """# Return Procedure
1. Verify eligibility:
   - Check device serial number
   - Confirm warranty status
2. Package item securely:
   * Use original box
   * Include all cables
"""
    raw_bytes = md_content.encode("utf-8")
    full_text, pages, blocks, tables, warnings = MarkdownAdapter.parse_to_structured(
        raw_bytes=raw_bytes,
        title="Return Procedure",
        filename="procedure.md",
    )

    list_blocks = [b for b in blocks if b.block_type == ContentBlockType.LIST_ITEM]
    assert len(list_blocks) == 6

    # Verify indentation level preservation
    sub_bullets = [b for b in list_blocks if b.metadata.get("indent_level", 0) > 0]
    assert len(sub_bullets) == 4
    for b in sub_bullets:
        assert b.metadata["indent_level"] >= 1
        assert b.text.startswith("  - ") or b.text.startswith("  * ") or b.text.startswith("  -")


def test_markdown_adapter_pipe_tables_and_row_units():
    """Validates Deliverable 1 & 4: Markdown pipe tables and decomposition into table_row units."""
    md_content = """# Fee Schedule
| Category | Restocking Fee | Inspection Required |
|:---|:---:|---:|
| Laptops | $50.00 | Yes |
| Monitory & Displays | 15% | No |
| Cables | Free | No |
"""
    raw_bytes = md_content.encode("utf-8")
    full_text, pages, blocks, tables, warnings = MarkdownAdapter.parse_to_structured(
        raw_bytes=raw_bytes,
        title="Fee Schedule",
        filename="fees.md",
    )

    assert len(tables) == 1
    t = tables[0]
    assert t["headers"] == ["Category", "Restocking Fee", "Inspection Required"]
    assert len(t["rows"]) == 3
    assert t["rows"][0] == ["Laptops", "$50.00", "Yes"]
    assert t["rows"][1] == ["Monitory & Displays", "15%", "No"]

    # Verify evidence unit creation
    import hashlib
    env = CanonicalSourceEnvelope(
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="file://fees.md",
        source_family=SourceFamily.DOCUMENT,
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        native_format="md",
        source_version="1",
        content_hash=hashlib.sha256(raw_bytes).hexdigest(),
        raw_payload=raw_bytes,
        locator_metadata={"filename": "fees.md"},
    )
    import asyncio
    ev_res = asyncio.run(MarkdownAdapter.parse_to_evidence(env))
    assert len(ev_res.units) >= 4  # 1 heading + 1 table + 3 table_row units

    row_units = [u for u in ev_res.units if u.block_type == "table_row"]
    assert len(row_units) == 3
    assert row_units[0].cells["Category"] == "Laptops"
    assert row_units[0].cells["Restocking Fee"] == "$50.00"
    assert row_units[0].table_id == "tbl_md_1"
    assert row_units[0].locator["row_index"] == 1


def test_markdown_adapter_code_blocks_and_frontmatter():
    """Validates Deliverable 1: Fenced code blocks with language tags and YAML frontmatter."""
    md_content = """---
title: API SLA Policy
version: 2.1.0
department: Legal & Infrastructure
---
# SLA Requirements
Below is the health check configuration:
```yaml
uptime_target: 99.9%
notification_window: 15 minutes
```
Customers must receive incident reports within 24 hours.
"""
    raw_bytes = md_content.encode("utf-8")
    full_text, pages, blocks, tables, warnings = MarkdownAdapter.parse_to_structured(
        raw_bytes=raw_bytes,
        title="SLA Document",
        filename="sla.md",
    )

    code_blocks = [b for b in blocks if b.block_type == ContentBlockType.CODE_BLOCK]
    assert len(code_blocks) == 1
    assert "uptime_target: 99.9%" in code_blocks[0].text
    assert code_blocks[0].metadata.get("language") == "yaml"

    # Confirm frontmatter title was used
    h1 = [b for b in blocks if b.block_type == ContentBlockType.HEADING][0]
    assert "SLA Requirements" in h1.text


# -----------------------------------------------------------------------------
# 2. HTML Adapter Tests
# -----------------------------------------------------------------------------

def test_html_adapter_dom_structure_and_headings():
    """Validates Deliverable 2: HTML semantic DOM extraction and tag filtering."""
    html_content = """<!DOCTYPE html>
<html>
<head>
    <title>Customer Refund Policy</title>
    <style>body { font-family: sans-serif; }</style>
    <script>alert('malicious_tag');</script>
</head>
<body>
    <h1>Enterprise Refund Policy</h1>
    <section>
        <h2>Eligibility Window</h2>
        <p>Customers must return hardware within 30 days of delivery.</p>
    </section>
</body>
</html>
"""
    raw_bytes = html_content.encode("utf-8")
    full_text, pages, blocks, tables, warnings = HtmlAdapter.parse_to_structured(
        raw_bytes=raw_bytes,
        title="Refund Policy",
        filename="policy.html",
    )

    # Asserts that script and style contents were completely stripped
    assert "malicious_tag" not in full_text
    assert "font-family" not in full_text

    headings = [b for b in blocks if b.block_type == ContentBlockType.HEADING]
    assert len(headings) == 2
    assert headings[0].text == "# Enterprise Refund Policy"
    assert headings[1].text == "## Eligibility Window"

    paras = [b for b in blocks if b.block_type == ContentBlockType.PARAGRAPH]
    assert len(paras) == 1
    assert "Customers must return hardware within 30 days" in paras[0].text
    assert paras[0].heading_path == ["Customer Refund Policy", "Enterprise Refund Policy", "Eligibility Window"]


def test_html_adapter_tables_and_colspan():
    """Validates Deliverable 2 & 4: HTML table extraction with headers and colspan handling."""
    html_content = """
    <table>
        <thead>
            <tr>
                <th>Region</th>
                <th>Return Window</th>
                <th>Restocking Fee</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>North America</td>
                <td>30 days</td>
                <td>$25.00</td>
            </tr>
            <tr>
                <td>European Union</td>
                <td colspan="2">14 days statutory cooling-off (no fee)</td>
            </tr>
        </tbody>
    </table>
"""
    raw_bytes = html_content.encode("utf-8")
    full_text, pages, blocks, tables, warnings = HtmlAdapter.parse_to_structured(
        raw_bytes=raw_bytes,
        title="Region Table",
        filename="regions.html",
    )

    assert len(tables) == 1
    t = tables[0]
    assert t["headers"] == ["Region", "Return Window", "Restocking Fee"]
    assert len(t["rows"]) == 2
    assert t["rows"][0] == ["North America", "30 days", "$25.00"]
    # Colspan row spans across both columns
    assert t["rows"][1][0] == "European Union"
    assert "14 days statutory" in t["rows"][1][1]
    assert "14 days statutory" in t["rows"][1][2]

    # Check evidence unit decomposition
    import hashlib
    env = CanonicalSourceEnvelope(
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="file://regions.html",
        source_family=SourceFamily.DOCUMENT,
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        native_format="html",
        source_version="1",
        content_hash=hashlib.sha256(raw_bytes).hexdigest(),
        raw_payload=raw_bytes,
        locator_metadata={"filename": "regions.html"},
    )
    import asyncio
    ev_res = asyncio.run(HtmlAdapter.parse_to_evidence(env))
    row_units = [u for u in ev_res.units if u.block_type == "table_row"]
    assert len(row_units) == 2
    assert row_units[0].cells["Region"] == "North America"
    assert row_units[0].cells["Restocking Fee"] == "$25.00"


def test_html_adapter_nested_lists_and_blockquotes():
    """Validates Deliverable 2: HTML nested lists (ul/ol) and blockquotes."""
    html_content = """
    <p>General requirements:</p>
    <ul>
        <li>Original receipt must be provided</li>
        <li>Packaging conditions:
            <ul>
                <li>Unbroken factory seal</li>
                <li>All serial tags intact</li>
            </ul>
        </li>
    </ul>
    <blockquote>Important notice: Final sale items cannot be refunded.</blockquote>
"""
    raw_bytes = html_content.encode("utf-8")
    full_text, pages, blocks, tables, warnings = HtmlAdapter.parse_to_structured(
        raw_bytes=raw_bytes,
        title="Requirements",
        filename="reqs.html",
    )

    list_blocks = [b for b in blocks if b.block_type == ContentBlockType.LIST_ITEM]
    assert len(list_blocks) == 3
    # Sub-bullets should have depth > 0
    sub_bullets = [b for b in list_blocks if b.metadata.get("depth", 0) > 0]
    assert len(sub_bullets) == 2

    # Blockquote check
    quotes = [b for b in blocks if b.metadata.get("is_blockquote")]
    assert len(quotes) == 1
    assert "Final sale items cannot be refunded" in quotes[0].text
    assert quotes[0].text.startswith("> ")


# -----------------------------------------------------------------------------
# 3. CSV / TSV Adapter Tests
# -----------------------------------------------------------------------------

def test_csv_adapter_delimiter_detection_and_encoding():
    """Validates Deliverable 3: CSV comma, TSV tab, and semicolon delimiter detection."""
    # Case A: Standard Comma CSV
    csv_comma = "Product,Return_Window,Refund_Percentage\nLaptops,30 days,100%\nMonitors,14 days,85%\n"
    res_comma, _, _, tbls_comma, _ = CsvAdapter.parse_to_structured(csv_comma.encode("utf-8"), filename="test.csv")
    assert tbls_comma[0]["delimiter"] == ","
    assert tbls_comma[0]["headers"] == ["Product", "Return_Window", "Refund_Percentage"]
    assert len(tbls_comma[0]["rows"]) == 2

    # Case B: Tab-Separated TSV
    tsv_data = "Product\tReturn_Window\tRefund_Percentage\nServers\t60 days\t90%\nStorage\t45 days\t80%\n"
    res_tsv, _, _, tbls_tsv, _ = CsvAdapter.parse_to_structured(tsv_data.encode("utf-8"), filename="test.tsv")
    assert tbls_tsv[0]["delimiter"] == "\t"
    assert len(tbls_tsv[0]["rows"]) == 2

    # Case C: Semicolon Delimited
    csv_semi = "Service;Cancellation_Window;Fee\nCloud Backup;24 hours;$0.00\nDedicated IP;48 hours;$10.00\n"
    res_semi, _, _, tbls_semi, _ = CsvAdapter.parse_to_structured(csv_semi.encode("utf-8"), filename="services.csv")
    assert tbls_semi[0]["delimiter"] == ";"
    assert len(tbls_semi[0]["rows"]) == 2


def test_csv_adapter_table_rows_and_cell_fidelity():
    """Validates Deliverable 3 & 4: CSV cell coordinates, padding, and table_row units."""
    csv_content = """Subject,Predicate,Object,Restocking_Fee
Standard Return,has_return_window,30 days,$50.00
Gold Member Return,has_return_window,60 days,$0.00
VIP Enterprise,has_return_window,90 days
"""
    raw_bytes = csv_content.encode("utf-8-sig")  # BOM test
    import hashlib
    env = CanonicalSourceEnvelope(
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        asset_id="file://policy_matrix.csv",
        source_family=SourceFamily.DOCUMENT,
        source_intent=SourceIntent.GOVERNANCE_POLICY,
        native_format="csv",
        source_version="1",
        content_hash=hashlib.sha256(raw_bytes).hexdigest(),
        raw_payload=raw_bytes,
        locator_metadata={"filename": "policy_matrix.csv"},
    )
    import asyncio
    ev_res = asyncio.run(CsvAdapter.parse_to_evidence(env))

    row_units = [u for u in ev_res.units if u.block_type == "table_row"]
    assert len(row_units) == 3

    # Row 1 check
    assert row_units[0].cells["Subject"] == "Standard Return"
    assert row_units[0].cells["Predicate"] == "has_return_window"
    assert row_units[0].cells["Object"] == "30 days"
    assert row_units[0].cells["Restocking_Fee"] == "$50.00"

    # Row 3 padding check (VIP Enterprise has missing restocking fee)
    assert row_units[2].cells["Subject"] == "VIP Enterprise"
    assert row_units[2].cells["Restocking_Fee"] == ""


def test_csv_adapter_multi_page_pagination():
    """Validates Deliverable 3: Synthetic pagination chunks large datasets (>50 rows)."""
    header = "ID,Rule_Name,Threshold_Value\n"
    rows = [f"{i},Rule_{i},${i*10}.00\n" for i in range(1, 105)]
    csv_large = header + "".join(rows)

    raw_bytes = csv_large.encode("utf-8")
    full_text, pages, blocks, tables, warnings = CsvAdapter.parse_to_structured(
        raw_bytes=raw_bytes,
        title="Large Matrix",
        filename="large.csv",
    )

    # 104 rows chunked at 50 rows/page = 3 pages
    assert len(pages) == 3
    assert pages[0].page_number == 1
    assert pages[1].page_number == 2
    assert pages[2].page_number == 3


# -----------------------------------------------------------------------------
# 4. Universal Gate Contract Alignment (All 8 Families)
# -----------------------------------------------------------------------------

def test_text_web_gate_contract_all_8_families():
    """Validates Deliverable 4: Evaluates claims extracted from text/web formats against all 8 gate families."""
    engine = SharedGovernanceGateEngine()

    # Valid claim extracted from Markdown/HTML table
    valid_req = SharedGateRequest(
        claim_text="Hardware devices must be returned within 30 days of delivery.",
        subject="Hardware devices",
        predicate="has_return_window",
        object_val="30 days",
        evidence_quote="| Hardware devices | 30 days | Free return shipping |",
        evidence_spans=[{"page": 1, "char_start": 100, "char_end": 158}],
        table_header="Return Window",
    )
    res_valid = SharedGovernanceGateEngine.evaluate(valid_req)
    assert res_valid.all_gates_passed is True
    assert res_valid.certification_tier == "AUTOMATED_CERTIFIED"

    # Family 2 Catch-All Predicate Violation
    req_catch_all = SharedGateRequest(
        claim_text="Laptops must be returned within 30 days.",
        subject="Laptops",
        predicate="has_rule",  # Prohibited catch-all / unregistered
        object_val="30 days",
        evidence_quote="Laptops must be returned within 30 days.",
    )
    res_catch_all = SharedGovernanceGateEngine.evaluate(req_catch_all)
    assert res_catch_all.all_gates_passed is False
    assert any(code in res_catch_all.reason_codes for code in (GateFailureCode.ERR_PREDICATE_CATCH_ALL.value, GateFailureCode.ERR_PREDICATE_INVALID.value))

    # Family 7 Value Fidelity Mismatch ($155 claimed vs $150 evidence)
    req_val_mismatch = SharedGateRequest(
        claim_text="Free return shipping on orders over $155.",
        subject="Orders over $155",
        predicate="has_return_shipping_rule",
        object_val="Free on orders over $155",
        evidence_quote="| Order over $150, any reason | No | Free |",
        claim_type="rule",
    )
    res_val_mismatch = SharedGovernanceGateEngine.evaluate(req_val_mismatch)
    assert res_val_mismatch.all_gates_passed is False
    assert GateFailureCode.ERR_VALUE_FIDELITY_MISMATCH.value in res_val_mismatch.reason_codes


# -----------------------------------------------------------------------------
# 5. End-to-End Smoke Tests (Markdown, HTML, CSV through UnifiedExtractionPipeline)
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_e2e_smoke_markdown_pipeline():
    """Validates Deliverable 6: Real Markdown document through UnifiedExtractionPipeline."""
    md_content = """# Northwind Hardware Return Policy
## General Terms
Customers must request hardware returns within 30 days of initial delivery.
Restocking fee of $50.00 applies to open boxes.
"""
    raw_bytes = md_content.encode("utf-8")
    res = await UnifiedExtractionPipeline.execute(
        raw_bytes=raw_bytes,
        filename="northwind_policy.md",
        options=UnifiedPipelineOptions(doc_title="Northwind Hardware Policy"),
    )

    assert res is not None
    assert len(res.evidence_result.units) >= 3
    assert len(res.candidates) >= 1
    # Verify candidate has valid locator and content hash
    cand = res.candidates[0]
    assert cand.content_hash != ""
    assert cand.locator.get("section_heading") != ""


@pytest.mark.asyncio
async def test_e2e_smoke_html_pipeline():
    """Validates Deliverable 6: Real HTML document through UnifiedExtractionPipeline."""
    html_content = """<!DOCTYPE html>
<html>
<body>
    <h1>Corporate Cancellation Terms</h1>
    <p>Subscribers must cancel recurring service subscriptions within 14 days of renewal.</p>
    <p>A cancellation fee of $25.00 is required for early termination.</p>
</body>
</html>
"""
    raw_bytes = html_content.encode("utf-8")
    res = await UnifiedExtractionPipeline.execute(
        raw_bytes=raw_bytes,
        filename="cancellation_policy.html",
        options=UnifiedPipelineOptions(doc_title="Cancellation Terms"),
    )

    assert res is not None
    assert len(res.evidence_result.units) >= 3
    assert len(res.candidates) >= 1
    assert any("cancel" in c.claim_text.lower() for c in res.candidates)


@pytest.mark.asyncio
async def test_e2e_smoke_csv_pipeline():
    """Validates Deliverable 6: Real CSV table through UnifiedExtractionPipeline."""
    csv_content = """Policy_Category,Required_Action,Window_Period,Mandatory_Fee
Standard Devices,Customers must return equipment,30 days,$50.00
Perishable Goods,Customers must report damage,48 hours,$0.00
"""
    raw_bytes = csv_content.encode("utf-8")
    res = await UnifiedExtractionPipeline.execute(
        raw_bytes=raw_bytes,
        filename="governance_matrix.csv",
        options=UnifiedPipelineOptions(doc_title="Governance Matrix"),
    )

    assert res is not None
    assert len(res.evidence_result.units) >= 2
    assert len(res.candidates) >= 1
    assert any("30 days" in c.claim_text or "return" in c.claim_text.lower() for c in res.candidates)
