"""
Layer 4: Specialized XLSX Parser Adapter.

Converts XLSX / spreadsheet documents into canonical structured evidence units and markdown AST.
Preserves:
- Multi-sheet architectures with sheet names as section scopes
- Merged-cell resolution (propagates master cell values across merged ranges)
- High-fidelity cell typing: currencies, percentages, formulas, integers, floats, dates
- Table row (`TABLE_ROW`) and cell (`TABLE_CELL`) evidence units
- Evidence contract compatibility (deterministic unit_id, exact char_offsets, SHA-256 hashes, breadcrumbs)
- Reuses Value-Fidelity Gate (Family 7) and Table-Column Binding Gate (Family 3)
"""

from __future__ import annotations

import io
import logging
import re
import uuid
import hashlib
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional, Set, Tuple

import openpyxl
from openpyxl.worksheet.worksheet import Worksheet

from app.db.enums import SourceFamily, SourceIntent
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.ingestion.parsers.evidence_model import (
    ContentRole,
    ParsedEvidenceResult,
    ParsedEvidenceUnit,
)
from app.ingestion.universal_file_parser import (
    ContentBlock,
    ContentBlockType,
    DocumentPage,
)

logger = logging.getLogger(__name__)


class XlsxAdapter:
    """Specialized adapter for Microsoft Excel (.xlsx) spreadsheets."""

    @classmethod
    def _clean_cell_text(cls, text: str) -> str:
        """Cleans cell text by stripping excessive whitespace and escaping pipes."""
        if not text:
            return ""
        cleaned = re.sub(r"[\r\n]+", " ", str(text)).strip()
        cleaned = cleaned.replace("|", r"\|")
        return cleaned

    @classmethod
    def _resolve_merged_cells(cls, ws: Worksheet) -> Dict[Tuple[int, int], Tuple[Any, str, Tuple[int, int]]]:
        """
        Resolves openpyxl merged cell ranges so that child cells inherit the master value.
        Returns a mapping from (row_idx, col_idx) -> (master_value, merged_range_str, (min_row, min_col)).
        """
        merged_map: Dict[Tuple[int, int], Tuple[Any, str, Tuple[int, int]]] = {}
        try:
            for rng in list(ws.merged_cells.ranges):
                min_col, min_row, max_col, max_row = rng.min_col, rng.min_row, rng.max_col, rng.max_row
                master_cell = ws.cell(row=min_row, column=min_col)
                master_val = master_cell.value
                rng_str = str(rng)
                for r in range(min_row, max_row + 1):
                    for c in range(min_col, max_col + 1):
                        merged_map[(r, c)] = (master_val, rng_str, (min_row, min_col))
        except Exception as e:
            logger.debug("Merged cells resolution warning: %s", e)
        return merged_map

    @classmethod
    def _format_cell_value(cls, cell: Any, master_val: Any = None) -> Tuple[str, str, Any]:
        """
        Formats cell value preserving numeric, currency, percentage, and date fidelity.
        Returns (formatted_text, data_type, raw_value).
        """
        val = master_val if master_val is not None else cell.value
        if val is None:
            return "", "empty", None

        num_fmt = (getattr(cell, "number_format", None) or "").lower()

        # Date / Datetime
        if isinstance(val, (datetime, date)):
            formatted = val.strftime("%Y-%m-%d")
            return formatted, "date", formatted

        # Numeric (Float / Int)
        if isinstance(val, (int, float)):
            # Currency detection ($#,##0.00, etc.)
            if any(sym in num_fmt for sym in ("$", "€", "£", "usd", "eur", "gbp")):
                formatted = f"${val:,.2f}"
                return formatted, "currency", val

            # Percentage detection (0.00%, etc.)
            if "%" in num_fmt:
                pct_val = val * 100.0
                formatted = f"{pct_val:.1f}%" if (pct_val % 1 != 0) else f"{int(pct_val)}%"
                return formatted, "percentage", val

            # Standard numeric
            if isinstance(val, float) and val.is_integer():
                formatted = str(int(val))
            elif isinstance(val, float):
                formatted = f"{val:.4f}".rstrip("0").rstrip(".")
            else:
                formatted = str(val)

            return formatted, "numeric", val

        # Boolean
        if isinstance(val, bool):
            formatted = "Yes" if val else "No"
            return formatted, "boolean", val

        # Plain string or other
        str_val = cls._clean_cell_text(str(val))
        # Check string for embedded currency or percent formatting
        if re.match(r"^\$[0-9]+(?:,[0-9]{3})*(?:\.[0-9]{2})?$", str_val):
            return str_val, "currency", str_val
        if re.match(r"^[0-9]+(?:\.[0-9]+)?%$", str_val):
            return str_val, "percentage", str_val

        return str_val, "text", str_val

    @classmethod
    def parse_to_structured(
        cls, raw_bytes: bytes, title: str, filename: str
    ) -> Tuple[str, List[DocumentPage], List[ContentBlock], List[Dict[str, Any]], List[str]]:
        """
        Parses XLSX bytes into multi-sheet markdown AST, content blocks, pages, and table metadata.
        Compatible with UniversalFileParser._parse_xlsx_structured contract.
        """
        blocks: List[ContentBlock] = []
        tables: List[Dict[str, Any]] = []
        warnings: List[str] = []
        pages: List[DocumentPage] = []
        markdown_sections: List[str] = []

        try:
            wb = openpyxl.load_workbook(io.BytesIO(raw_bytes), data_only=True)
            wb_formulas = openpyxl.load_workbook(io.BytesIO(raw_bytes), data_only=False)
        except Exception as e:
            logger.error("Failed to load workbook %s: %s", filename, e)
            warnings.append(f"XLSX parser error: {str(e)}")
            return "", [], [], [], warnings

        doc_title = title or filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
        char_cursor = 0

        # Title line
        title_line = f"# {doc_title}"
        markdown_sections.append(title_line)
        markdown_sections.append("")
        char_cursor += len(title_line) + 2

        for sheet_idx, ws in enumerate(wb.worksheets, start=1):
            sheet_name = (ws.title or f"Sheet_{sheet_idx}").strip()
            ws_f = wb_formulas[ws.title] if ws.title in wb_formulas.sheetnames else None
            merged_map = cls._resolve_merged_cells(ws)
            merged_formula_map = cls._resolve_merged_cells(ws_f) if ws_f else {}

            sheet_raw_rows: List[List[str]] = []
            sheet_cell_meta: List[List[Dict[str, Any]]] = []
            sheet_headers: List[str] = []
            sheet_table_title: Optional[str] = None

            all_raw_rows: List[Tuple[List[str], List[Dict[str, Any]]]] = []
            for r_idx, row in enumerate(ws.iter_rows(values_only=False), start=1):
                row_formatted: List[str] = []
                row_meta: List[Dict[str, Any]] = []

                for c_idx, cell in enumerate(row, start=1):
                    master_entry = merged_map.get((r_idx, c_idx))
                    master_val = master_entry[0] if master_entry else None
                    is_merged = master_entry is not None
                    merged_rng = master_entry[1] if master_entry else None
                    master_coord = master_entry[2] if master_entry else None
                    is_inherited = bool(is_merged and master_coord != (r_idx, c_idx))
                    is_original_blank = cell.value is None or str(cell.value).strip() == ""

                    formula_str: Optional[str] = None
                    formula_status: Optional[str] = None
                    if ws_f is not None:
                        f_cell = ws_f.cell(row=r_idx, column=c_idx)
                        f_master = merged_formula_map.get((r_idx, c_idx))
                        f_raw = f_master[0] if (f_master and f_cell.value is None) else f_cell.value
                        if isinstance(f_raw, str) and f_raw.startswith("="):
                            formula_str = f_raw

                    fmt_val, data_type, raw_val = cls._format_cell_value(cell, master_val)
                    cached_val = raw_val if formula_str else None
                    if formula_str:
                        if raw_val is None and (master_val is None):
                            # Never interpret unavailable formula result as 0
                            formula_status = "cached_unavailable"
                            fmt_val = formula_str
                            data_type = "formula"
                            raw_val = None
                        else:
                            formula_status = "cached_available"

                    coord = cell.coordinate or f"R{r_idx}C{c_idx}"
                    num_fmt = getattr(cell, "number_format", None)

                    row_formatted.append(fmt_val)
                    row_meta.append({
                        "coordinate": coord,
                        "row_index": r_idx,
                        "column_index": c_idx,
                        "formatted_value": fmt_val,
                        "raw_value": raw_val,
                        "data_type": data_type,
                        "number_format": num_fmt,
                        "formula": formula_str,
                        "cached_value": cached_val,
                        "formula_status": formula_status,
                        "is_merged": is_merged,
                        "is_inherited": is_inherited,
                        "is_original_blank": is_original_blank,
                        "merged_range": merged_rng,
                    })

                if any(v for v in row_formatted):
                    all_raw_rows.append((row_formatted, row_meta))

            if not all_raw_rows:
                continue

            # Detect banner title row (Row 1 has 1 unique non-empty value while Row 2+ has multiple distinct columns)
            start_row_idx = 0
            if len(all_raw_rows) >= 3:
                r0_non_empty = [v for v in all_raw_rows[0][0] if v]
                r1_non_empty = [v for v in all_raw_rows[1][0] if v]
                if len(set(r0_non_empty)) == 1 and len(r1_non_empty) >= 2:
                    sheet_table_title = r0_non_empty[0]
                    start_row_idx = 1

            for row_formatted, row_meta in all_raw_rows[start_row_idx:]:
                if not sheet_headers:
                    # Trim trailing empty header columns
                    last_non_empty = max((idx for idx, v in enumerate(row_formatted) if v), default=len(row_formatted) - 1)
                    row_formatted = row_formatted[:last_non_empty + 1]
                    row_meta = row_meta[:last_non_empty + 1]
                    sheet_headers = [h or f"Column_{i+1}" for i, h in enumerate(row_formatted)]
                else:
                    if len(row_formatted) < len(sheet_headers):
                        row_formatted.extend([""] * (len(sheet_headers) - len(row_formatted)))
                    row_formatted = row_formatted[:len(sheet_headers)]
                    row_meta = row_meta[:len(sheet_headers)]

                sheet_raw_rows.append(row_formatted)
                sheet_cell_meta.append(row_meta)

            if not sheet_raw_rows:
                continue

            col_count = len(sheet_headers) or len(sheet_raw_rows[0])
            header_line = "| " + " | ".join(sheet_headers) + " |"
            separator_line = "| " + " | ".join([":---"] * col_count) + " |"
            data_lines = ["| " + " | ".join(r) + " |" for r in sheet_raw_rows[1:]] if len(sheet_raw_rows) > 1 else []

            sheet_header_md = f"## Sheet: {sheet_name}"
            tbl_lines = [sheet_header_md, ""]
            if sheet_table_title:
                tbl_lines.extend([f"**{sheet_table_title}**", ""])
            tbl_lines.extend([header_line, separator_line] + data_lines)
            sheet_full_md = "\n".join(tbl_lines)

            start_offset = char_cursor
            end_offset = char_cursor + len(sheet_full_md)
            char_cursor = end_offset + 2

            # Build row dicts
            row_dicts = []
            for r in sheet_raw_rows[1:]:
                r_dict = {sheet_headers[i] if i < len(sheet_headers) else f"col_{i+1}": r[i] for i in range(len(r))}
                row_dicts.append(r_dict)

            t_data = {
                "sheet_name": sheet_name,
                "table_id": f"tbl_{sheet_idx}_{re.sub(r'[^a-zA-Z0-9]', '_', sheet_name).lower()}",
                "table_title": sheet_table_title,
                "headers": sheet_headers,
                "rows": sheet_raw_rows,
                "row_dicts": row_dicts,
                "row_count": len(sheet_raw_rows),
                "col_count": col_count,
                "cells_meta": sheet_cell_meta,
            }
            tables.append(t_data)

            block = ContentBlock(
                id=f"blk_xlsx_sheet_{sheet_idx}",
                block_type=ContentBlockType.TABLE,
                text=sheet_full_md,
                raw_text=sheet_full_md,
                page_number=sheet_idx,
                start_char_offset=start_offset,
                end_char_offset=end_offset,
                table_data=t_data,
                metadata={"sheet_name": sheet_name},
            )
            blocks.append(block)

            # Map sheet to a synthetic DocumentPage
            pages.append(DocumentPage(
                page_number=sheet_idx,
                text=sheet_full_md,
                char_count=len(sheet_full_md),
                blocks=[block],
            ))

            markdown_sections.append(sheet_full_md)
            markdown_sections.append("")

        full_text = "\n".join(markdown_sections).strip()
        return full_text, pages, blocks, tables, warnings

    @classmethod
    async def parse_to_evidence(cls, envelope: CanonicalSourceEnvelope) -> ParsedEvidenceResult:
        """
        Parses an XLSX CanonicalSourceEnvelope into structured TABLE_ROW and TABLE_CELL evidence units.
        Directly satisfies Layer 4 Evidence Contract with SHA-256 hashes, coordinates, and breadcrumbs.
        """
        raw_bytes = None
        if isinstance(envelope.raw_payload, bytes):
            raw_bytes = envelope.raw_payload
        elif hasattr(envelope, "metadata") and envelope.metadata and envelope.metadata.get("raw_bytes"):
            raw_bytes = envelope.metadata["raw_bytes"]
        elif hasattr(envelope, "locator_metadata") and envelope.locator_metadata and envelope.locator_metadata.get("raw_bytes"):
            raw_bytes = envelope.locator_metadata["raw_bytes"]

        if raw_bytes is None:
            raw_bytes = envelope.get_payload_as_text().encode("utf-8")
        elif isinstance(raw_bytes, str):
            raw_bytes = raw_bytes.encode("utf-8")

        filename = (envelope.locator_metadata or {}).get("filename", "workbook.xlsx")
        title = filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()

        markdown_text, pages, blocks, tables, warnings = cls.parse_to_structured(
            raw_bytes=raw_bytes,
            title=title,
            filename=filename,
        )

        # Defensive fallback: If openpyxl couldn't parse bytes but envelope has Markdown table text
        if not tables and isinstance(envelope.raw_payload, str) and "|" in envelope.raw_payload:
            from app.ingestion.parsers.document_parser import DocumentParser
            return await DocumentParser.parse(envelope)

        units: List[ParsedEvidenceUnit] = []
        seq_idx = 0

        for t_info in tables:
            sheet_name = t_info["sheet_name"]
            table_id = t_info["table_id"]
            headers = t_info["headers"]
            rows = t_info["rows"]
            cells_meta = t_info.get("cells_meta", [])

            # 1. Sheet Heading Unit
            sheet_heading_text = f"## Sheet: {sheet_name}"
            units.append(ParsedEvidenceUnit.create(
                envelope_id=envelope.envelope_id,
                asset_id=envelope.asset_id,
                block_type="heading",
                content_text=sheet_heading_text,
                content_role=ContentRole.HEADING,
                hierarchical_context=[title, f"Sheet: {sheet_name}"],
                sequence_index=seq_idx,
                section_path=[title, sheet_name],
            ))
            seq_idx += 1

            # 2. TABLE_ROW and TABLE_CELL Evidence Units (Data rows 1..N)
            for r_idx, row_vals in enumerate(rows[1:], start=1):
                row_str = "| " + " | ".join(row_vals) + " |"
                cols_dict = {headers[i] if i < len(headers) else f"col_{i+1}": row_vals[i] for i in range(len(row_vals))}
                r_cells = cells_meta[r_idx] if r_idx < len(cells_meta) else []

                row_unit = ParsedEvidenceUnit.create(
                    envelope_id=envelope.envelope_id,
                    asset_id=envelope.asset_id,
                    block_type="table_row",
                    content_text=row_str,
                    content_role=ContentRole.POLICY_RULE,
                    structure_type="table_row",
                    table_id=table_id,
                    row_id=f"{table_id}_r{r_idx}",
                    column_headers=headers,
                    cells=cols_dict,
                    structured_data={
                        "table_id": table_id,
                        "sheet_name": sheet_name,
                        "table_title": t_info.get("table_title"),
                        "row_index": r_idx,
                        "columns": cols_dict,
                        "headers": headers,
                        "table_headers": headers,
                        "cells_meta": r_cells,
                    },
                    hierarchical_context=[title, f"Sheet: {sheet_name}"],
                    sequence_index=seq_idx,
                    section_path=[title, sheet_name],
                )
                units.append(row_unit)
                seq_idx += 1

                # 3. Individual TABLE_CELL Evidence Units for granular value validation
                for c_idx, cell_data in enumerate(r_cells):
                    val_str = cell_data["formatted_value"]
                    if not val_str:
                        continue

                    col_hdr = headers[c_idx] if c_idx < len(headers) else f"col_{c_idx+1}"
                    cell_text = f"{col_hdr}: {val_str}"
                    cell_coord = cell_data["coordinate"]

                    cell_unit = ParsedEvidenceUnit.create(
                        envelope_id=envelope.envelope_id,
                        asset_id=envelope.asset_id,
                        block_type="table_cell",
                        content_text=cell_text,
                        content_role=ContentRole.POLICY_RULE,
                        structure_type="table_cell",
                        table_id=table_id,
                        row_id=f"{table_id}_r{r_idx}",
                        column_headers=[col_hdr],
                        cells={col_hdr: val_str},
                        structured_data={
                            "table_id": table_id,
                            "sheet_name": sheet_name,
                            "coordinate": cell_coord,
                            "column_header": col_hdr,
                            "row_index": r_idx,
                            "raw_value": cell_data["raw_value"],
                            "formatted_value": val_str,
                            "data_type": cell_data["data_type"],
                            "is_merged": cell_data["is_merged"],
                            "merged_range": cell_data.get("merged_range"),
                        },
                        hierarchical_context=[title, f"Sheet: {sheet_name}", f"Row {r_idx}"],
                        sequence_index=seq_idx,
                        section_path=[title, sheet_name, f"Row {r_idx}"],
                    )
                    units.append(cell_unit)
                    seq_idx += 1

        result = ParsedEvidenceResult(
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            source_family=SourceFamily.STRUCTURED,
            parser_name="XlsxAdapter",
            units=units,
            completeness_score=1.0,
            quality_metrics={
                "sheet_count": len(tables),
                "total_units": len(units),
                "warnings": warnings,
                "evidence_hash": hashlib.sha256(raw_bytes).hexdigest(),
            },
        )
        return result
