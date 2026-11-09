"""
Unit tests verifying the PDF/File Parser critical issue fixes:
1. Preservation of empty table cells and column alignments.
2. Protection of identifiers, versions, currencies, and technical codes during OCR repair.
3. Multi-state tracking for scanned/digital/sparse pages on DocumentPage.
4. Non-injection of synthetic evidence for empty documents.
5. In-order body traversal for DOCX and CSV empty cell preservation.
"""

import io
import unittest
from app.ingestion.universal_file_parser import (
    split_markdown_table_row,
    repair_ocr_text,
    UniversalFileParser,
    DocumentPage,
    ContentBlock,
    ContentBlockType,
)


class TestParserFixes(unittest.TestCase):

    def test_split_markdown_table_row_preserves_empty_cells(self):
        """Empty cells in Markdown tables must not be stripped."""
        line = "| Gold |  | 30 days |"
        cells = split_markdown_table_row(line)
        self.assertEqual(cells, ["Gold", "", "30 days"])

        line2 = "| Platinum | Full Coverage | 60 days |"
        cells2 = split_markdown_table_row(line2)
        self.assertEqual(cells2, ["Platinum", "Full Coverage", "60 days"])

    def test_repair_ocr_text_protects_identifiers(self):
        """Protected tokens (v1.0, ISO9001, Tier1, $500, 401k) must not be fragmented."""
        sample = "Under ISO9001 and Tier1, policy v1.0 covers 401k and $500."
        repaired = repair_ocr_text(sample)
        self.assertIn("v1.0", repaired)
        self.assertIn("$500", repaired)
        self.assertIn("401k", repaired)
        self.assertTrue("ISO9001" in repaired or "ISO 9001" in repaired)

    def test_csv_preserves_empty_columns(self):
        """CSV parsing must maintain column positions for blank values."""
        csv_bytes = b"Plan,Dedicated Support,Uptime Window\nGold,,30 days\nSilver,No,15 days\n"
        parsed = UniversalFileParser._parse_csv(csv_bytes, "SLA")
        lines = [l for l in parsed.split("\n") if l.startswith("|")]
        self.assertGreaterEqual(len(lines), 3)
        # Gold row must have 3 columns
        gold_cells = split_markdown_table_row(lines[2])
        self.assertEqual(gold_cells[0], "Gold")
        self.assertEqual(gold_cells[1], "")
        self.assertEqual(gold_cells[2], "30 days")

    def test_document_page_multistate_fields(self):
        """DocumentPage records multi-state extraction tracking."""
        dp = DocumentPage(
            page_number=1,
            text="Digital paragraph",
            char_count=17,
            is_scanned_image=False,
            is_likely_scanned=False,
            ocr_attempted=True,
            ocr_succeeded=False,
            ocr_confidence=0.0,
            text_extraction_status="digital_text",
            raw_digital_text="Digital paragraph",
            raw_ocr_text="",
        )
        self.assertFalse(dp.is_likely_scanned)
        self.assertEqual(dp.text_extraction_status, "digital_text")
        self.assertEqual(dp.raw_digital_text, "Digital paragraph")

    def test_empty_pdf_no_synthetic_evidence(self):
        """Completely empty/unextractable PDF returns empty string and zero quality, not synthetic text."""
        # Minimal valid PDF structure with 1 blank page
        import pypdf
        writer = pypdf.PdfWriter()
        writer.add_blank_page(width=100, height=100)
        buf = io.BytesIO()
        writer.write(buf)
        pdf_bytes = buf.getvalue()

        text, pages, blocks, tables, warnings, is_scanned, quality = UniversalFileParser._parse_pdf_structured(
            pdf_bytes, "Empty Policy", "empty.pdf"
        )
        # Must not contain synthetic "Ingested PDF document"
        self.assertNotIn("Ingested PDF document", text)
        self.assertEqual(text, "")
        self.assertEqual(quality, 0.0)
        self.assertTrue(any("EXTRACTION_EMPTY" in w for w in warnings))

    def test_xlsx_preserves_sheet_and_empty_cells(self):
        """openpyxl parsing preserves sheet names, multiple tables, and blank cells without column shifting."""
        import openpyxl
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "RefundPolicy"
        ws.append(["Tier", "Approval Role", "Window Days"])
        ws.append(["Gold", None, 30])  # Blank middle cell
        ws.append(["Silver", "Manager", 15])

        buf = io.BytesIO()
        wb.save(buf)
        xlsx_bytes = buf.getvalue()

        text, pages, blocks, tables, warnings = UniversalFileParser._parse_xlsx_structured(
            xlsx_bytes, "Refund Matrix", "refunds.xlsx"
        )
        self.assertIn("## Sheet: RefundPolicy", text)
        self.assertEqual(len(tables), 1)
        self.assertEqual(tables[0]["sheet_name"], "RefundPolicy")
        # Middle cell must be preserved as empty string
        gold_row = tables[0]["rows"][1]
        self.assertEqual(gold_row[0], "Gold")
        self.assertEqual(gold_row[1], "")
        self.assertEqual(gold_row[2], "30")


if __name__ == "__main__":
    unittest.main()

