"""
Layer 4: Specialized HTML Parser Adapter (Phase 6 Step 6.4).

Converts HTML documents into canonical structured evidence units and markdown AST.
Preserves:
- DOM structure & semantic hierarchy: H1 to H6 headings with breadcrumb ancestry
- Semantic paragraphs, articles, sections, and blockquotes
- Tables: headers, rows, cells, colspan handling, and markdown pipe representation
- Nested lists: ordered (ol) and unordered (ul) with depth indentation
- Code & preformatted blocks (<pre>, <code>)
- Safe tag filtering (scripts, styles, noscript, svg, metadata stripped)
- Deterministic evidence units (unit_id, char_offsets, SHA-256 hashes, breadcrumbs)
- Direct integration with the 8 Universal Gate Contract families
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
import uuid
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple

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
    split_markdown_table_row,
)

logger = logging.getLogger(__name__)


class _SemanticHTMLParser(HTMLParser):
    """Event-driven parser that extracts structured semantic elements from HTML DOM."""

    IGNORE_TAGS = {"script", "style", "noscript", "svg", "head", "meta", "link", "iframe"}

    def __init__(self, doc_title: str = "HTML Document"):
        super().__init__()
        self.doc_title = doc_title
        self.ignore_depth = 0

        # Hierarchical tracking
        self.heading_stack: List[str] = [doc_title]
        self.list_depth = 0
        self.list_types: List[str] = []  # "ul" or "ol"
        self.list_counters: List[int] = []

        # Current state
        self.current_tag: Optional[str] = None
        self.text_buffer: List[str] = []

        # Table state
        self.in_table = False
        self.table_headers: List[str] = []
        self.table_rows: List[List[str]] = []
        self.current_row: List[str] = []
        self.current_cell: List[str] = []
        self.in_header_cell = False
        self.current_colspan = 1

        # Code block state
        self.in_pre = False
        self.code_buffer: List[str] = []

        # Blockquote state
        self.in_blockquote = False

        # Output collections
        self.raw_elements: List[Dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: List[Tuple[str, Optional[str]]]):
        t = tag.lower()
        if t in self.IGNORE_TAGS:
            self.ignore_depth += 1
            return
        if self.ignore_depth > 0:
            return

        attr_dict = dict(attrs)

        # Check for page break indicators
        classes = (attr_dict.get("class") or "").lower()
        if t == "hr" or "page-break" in classes or "pagebreak" in classes:
            self._flush_text()
            self.raw_elements.append({"type": "page_break"})
            return

        self.current_tag = t

        # Headings (h1 - h6)
        if re.match(r"^h[1-6]$", t):
            self._flush_text()

        # Lists (ul, ol)
        elif t in ("ul", "ol"):
            self._flush_text()
            self.list_depth += 1
            self.list_types.append(t)
            self.list_counters.append(0)

        elif t == "li":
            self._flush_text()
            if self.list_counters:
                self.list_counters[-1] += 1

        # Tables
        elif t == "table":
            self._flush_text()
            self.in_table = True
            self.table_headers = []
            self.table_rows = []

        elif t == "tr" and self.in_table:
            self.current_row = []

        elif t in ("td", "th") and self.in_table:
            self.current_cell = []
            self.in_header_cell = (t == "th")
            try:
                self.current_colspan = int(attr_dict.get("colspan", "1"))
            except ValueError:
                self.current_colspan = 1

        # Preformatted code
        elif t == "pre":
            self._flush_text()
            self.in_pre = True
            self.code_buffer = []

        # Blockquote
        elif t == "blockquote":
            self._flush_text()
            self.in_blockquote = True

        elif t == "br":
            if self.in_pre:
                self.code_buffer.append("\n")
            elif self.in_table:
                self.current_cell.append(" ")
            else:
                self.text_buffer.append(" ")

    def handle_endtag(self, tag: str):
        t = tag.lower()
        if t in self.IGNORE_TAGS:
            self.ignore_depth = max(0, self.ignore_depth - 1)
            return
        if self.ignore_depth > 0:
            return

        # Headings
        if re.match(r"^h[1-6]$", t):
            level = int(t[1])
            h_text = "".join(self.text_buffer).strip()
            self.text_buffer.clear()
            if h_text:
                self.heading_stack = self.heading_stack[:level] + [h_text]
                self.raw_elements.append({
                    "type": "heading",
                    "level": level,
                    "text": h_text,
                    "heading_path": list(self.heading_stack),
                })

        # Lists
        elif t in ("ul", "ol"):
            self._flush_text()
            if self.list_depth > 0:
                self.list_depth -= 1
                self.list_types.pop()
                self.list_counters.pop()

        elif t == "li":
            item_text = "".join(self.text_buffer).strip()
            self.text_buffer.clear()
            if item_text:
                idx = self.list_counters[-1] if self.list_counters else 1
                is_ordered = bool(self.list_types and self.list_types[-1] == "ol")
                self.raw_elements.append({
                    "type": "list_item",
                    "text": item_text,
                    "depth": max(0, self.list_depth - 1),
                    "is_ordered": is_ordered,
                    "item_index": idx,
                    "heading_path": list(self.heading_stack),
                })

        # Table cells and rows
        elif t in ("td", "th") and self.in_table:
            cell_val = re.sub(r"\s+", " ", "".join(self.current_cell)).strip()
            cell_val = cell_val.replace("|", r"\|")
            # Handle colspan by repeating or padding
            for _ in range(max(1, self.current_colspan)):
                self.current_row.append(cell_val)
            self.current_cell.clear()

        elif t == "tr" and self.in_table:
            if self.current_row:
                # If first row contains 'th' cells or headers are empty, treat as header
                if not self.table_headers and (self.in_header_cell or not self.table_rows):
                    self.table_headers = list(self.current_row)
                else:
                    self.table_rows.append(list(self.current_row))
            self.current_row = []

        elif t == "table" and self.in_table:
            self.in_table = False
            if self.table_headers or self.table_rows:
                self.raw_elements.append({
                    "type": "table",
                    "headers": self.table_headers,
                    "rows": self.table_rows,
                    "heading_path": list(self.heading_stack),
                })
            self.table_headers = []
            self.table_rows = []

        # Preformatted code
        elif t == "pre" and self.in_pre:
            self.in_pre = False
            code_text = "".join(self.code_buffer).strip()
            self.code_buffer.clear()
            if code_text:
                self.raw_elements.append({
                    "type": "code_block",
                    "text": code_text,
                    "heading_path": list(self.heading_stack),
                })

        # Blockquote
        elif t == "blockquote" and self.in_blockquote:
            self._flush_text()
            self.in_blockquote = False

        elif t in ("p", "div", "article", "section"):
            self._flush_text()

    def handle_data(self, data: str):
        if self.ignore_depth > 0:
            return

        if self.in_pre:
            self.code_buffer.append(data)
        elif self.in_table and self.current_tag in ("td", "th"):
            self.current_cell.append(data)
        else:
            self.text_buffer.append(data)

    def _flush_text(self):
        raw = "".join(self.text_buffer).strip()
        self.text_buffer.clear()
        if raw:
            cleaned = re.sub(r"\s+", " ", raw).strip()
            if cleaned:
                self.raw_elements.append({
                    "type": "paragraph",
                    "text": cleaned,
                    "is_blockquote": self.in_blockquote,
                    "heading_path": list(self.heading_stack),
                })


class HtmlAdapter:
    """Specialized adapter for HTML (.html, .htm, .xhtml) documents."""

    @classmethod
    def parse_to_structured(
        cls,
        raw_bytes: bytes,
        title: str = "HTML Document",
        filename: str = "document.html",
    ) -> Tuple[str, List[DocumentPage], List[ContentBlock], List[Dict[str, Any]], List[str]]:
        """
        Parses HTML content into structured blocks, tables, and synthetic pages.
        Returns: (full_text, pages, blocks, tables, warnings)
        """
        warnings: List[str] = []

        # 1. Multi-encoding decode
        html_str = ""
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                html_str = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if not html_str:
            html_str = raw_bytes.decode("utf-8", errors="replace")

        # 2. Extract title tag if present
        title_match = re.search(r"<title[^>]*>(.*?)</title>", html_str, re.IGNORECASE | re.DOTALL)
        if title_match and title_match.group(1).strip():
            extracted_title = re.sub(r"\s+", " ", title_match.group(1)).strip()
            doc_title = extracted_title
        else:
            doc_title = title

        # 3. DOM Parse
        parser = _SemanticHTMLParser(doc_title=doc_title)
        try:
            parser.feed(html_str)
            parser.close()
        except Exception as e:
            warnings.append(f"HTML DOM parsing warning: {str(e)}")

        blocks: List[ContentBlock] = []
        tables: List[Dict[str, Any]] = []
        pages: List[DocumentPage] = []
        markdown_lines: List[str] = []

        current_page_blocks: List[ContentBlock] = []
        current_page_text: List[str] = []
        current_page_num = 1
        page_char_count = 0
        char_cursor = 0
        b_idx = 0
        t_idx = 0

        for elem in parser.raw_elements:
            e_type = elem.get("type")

            # Page Break
            if e_type == "page_break":
                if current_page_text or current_page_blocks:
                    pages.append(DocumentPage(
                        page_number=current_page_num,
                        text="\n\n".join(current_page_text),
                        char_count=page_char_count,
                        blocks=list(current_page_blocks),
                    ))
                    current_page_num += 1
                    page_char_count = 0
                    current_page_blocks.clear()
                    current_page_text.clear()
                continue

            # Heading
            elif e_type == "heading":
                level = elem["level"]
                h_text = elem["text"]
                formatted = f"{'#' * level} {h_text}"
                b_idx += 1
                start_offset = char_cursor
                end_offset = char_cursor + len(formatted)
                char_cursor = end_offset + 2

                block = ContentBlock(
                    id=f"blk_html_h_{b_idx}",
                    block_type=ContentBlockType.HEADING,
                    text=formatted,
                    raw_text=h_text,
                    page_number=current_page_num,
                    start_char_offset=start_offset,
                    end_char_offset=end_offset,
                    heading_path=elem.get("heading_path", [doc_title]),
                    metadata={"heading_level": level},
                )
                blocks.append(block)
                current_page_blocks.append(block)
                current_page_text.append(formatted)
                page_char_count += len(formatted)
                markdown_lines.append(formatted)

            # List Item
            elif e_type == "list_item":
                depth = elem.get("depth", 0)
                is_ordered = elem.get("is_ordered", False)
                idx = elem.get("item_index", 1)
                prefix = f"{idx}. " if is_ordered else "- "
                formatted = f"{'  ' * depth}{prefix}{elem['text']}"

                b_idx += 1
                start_offset = char_cursor
                end_offset = char_cursor + len(formatted)
                char_cursor = end_offset + 2

                block = ContentBlock(
                    id=f"blk_html_list_{b_idx}",
                    block_type=ContentBlockType.LIST_ITEM,
                    text=formatted,
                    raw_text=elem["text"],
                    page_number=current_page_num,
                    start_char_offset=start_offset,
                    end_char_offset=end_offset,
                    heading_path=elem.get("heading_path", [doc_title]),
                    metadata={"depth": depth, "is_ordered": is_ordered},
                )
                blocks.append(block)
                current_page_blocks.append(block)
                current_page_text.append(formatted)
                page_char_count += len(formatted)
                markdown_lines.append(formatted)

            # Table
            elif e_type == "table":
                t_idx += 1
                headers = elem.get("headers", [])
                rows = elem.get("rows", [])
                if not headers and rows:
                    headers = [f"col_{c+1}" for c in range(len(rows[0]))]

                # Align row column counts
                col_count = len(headers)
                aligned_rows = []
                for r in rows:
                    if len(r) < col_count:
                        r = r + [""] * (col_count - len(r))
                    aligned_rows.append(r[:col_count])

                hdr_line = "| " + " | ".join(headers) + " |"
                sep_line = "| " + " | ".join([":---"] * col_count) + " |"
                data_lines = ["| " + " | ".join(r) + " |" for r in aligned_rows]
                tbl_text = "\n".join([hdr_line, sep_line] + data_lines)

                row_dicts = []
                for r in aligned_rows:
                    row_dicts.append({headers[ci]: r[ci] for ci in range(col_count)})

                t_data = {
                    "table_id": f"tbl_html_{t_idx}",
                    "headers": headers,
                    "rows": aligned_rows,
                    "row_dicts": row_dicts,
                }
                tables.append(t_data)

                b_idx += 1
                start_offset = char_cursor
                end_offset = char_cursor + len(tbl_text)
                char_cursor = end_offset + 2

                block = ContentBlock(
                    id=f"blk_html_tbl_{b_idx}",
                    block_type=ContentBlockType.TABLE,
                    text=tbl_text,
                    raw_text=tbl_text,
                    page_number=current_page_num,
                    start_char_offset=start_offset,
                    end_char_offset=end_offset,
                    heading_path=elem.get("heading_path", [doc_title]),
                    table_data=t_data,
                )
                blocks.append(block)
                current_page_blocks.append(block)
                current_page_text.append(tbl_text)
                page_char_count += len(tbl_text)
                markdown_lines.append(tbl_text)

            # Code Block
            elif e_type == "code_block":
                code_text = f"```\n{elem['text']}\n```"
                b_idx += 1
                start_offset = char_cursor
                end_offset = char_cursor + len(code_text)
                char_cursor = end_offset + 2

                block = ContentBlock(
                    id=f"blk_html_code_{b_idx}",
                    block_type=ContentBlockType.CODE_BLOCK,
                    text=code_text,
                    raw_text=elem["text"],
                    page_number=current_page_num,
                    start_char_offset=start_offset,
                    end_char_offset=end_offset,
                    heading_path=elem.get("heading_path", [doc_title]),
                )
                blocks.append(block)
                current_page_blocks.append(block)
                current_page_text.append(code_text)
                page_char_count += len(code_text)
                markdown_lines.append(code_text)

            # Paragraph / Blockquote
            elif e_type == "paragraph":
                p_text = elem["text"]
                if elem.get("is_blockquote"):
                    p_text = f"> {p_text}"

                b_idx += 1
                start_offset = char_cursor
                end_offset = char_cursor + len(p_text)
                char_cursor = end_offset + 2

                block = ContentBlock(
                    id=f"blk_html_p_{b_idx}",
                    block_type=ContentBlockType.PARAGRAPH,
                    text=p_text,
                    raw_text=elem["text"],
                    page_number=current_page_num,
                    start_char_offset=start_offset,
                    end_char_offset=end_offset,
                    heading_path=elem.get("heading_path", [doc_title]),
                    metadata={"is_blockquote": elem.get("is_blockquote", False)},
                )
                blocks.append(block)
                current_page_blocks.append(block)
                current_page_text.append(p_text)
                page_char_count += len(p_text)
                markdown_lines.append(p_text)

        # Finalize last page
        if current_page_text or current_page_blocks:
            pages.append(DocumentPage(
                page_number=current_page_num,
                text="\n\n".join(current_page_text),
                char_count=page_char_count,
                blocks=list(current_page_blocks),
            ))

        full_text = "\n\n".join(markdown_lines).strip()
        return full_text, pages, blocks, tables, warnings

    @classmethod
    async def parse_to_evidence(cls, envelope: CanonicalSourceEnvelope) -> ParsedEvidenceResult:
        """
        Parses an HTML CanonicalSourceEnvelope into structured ParsedEvidenceUnits.
        Directly satisfies Layer 4 Evidence Contract with SHA-256 hashes, exact offsets,
        hierarchical breadcrumbs, and table row binding.
        """
        if isinstance(envelope.raw_payload, bytes):
            raw_bytes = envelope.raw_payload
        elif hasattr(envelope, "metadata") and envelope.metadata.get("raw_bytes"):
            raw_bytes = envelope.metadata["raw_bytes"]
        else:
            raw_bytes = envelope.get_payload_as_text().encode("utf-8")

        filename = (envelope.locator_metadata or {}).get("filename", "document.html")
        title = filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()

        full_text, pages, blocks, tables, warnings = cls.parse_to_structured(
            raw_bytes=raw_bytes,
            title=title,
            filename=filename,
        )

        units: List[ParsedEvidenceUnit] = []
        seq_idx = 0

        for block in blocks:
            seq_idx += 1
            b_hash = hashlib.sha256(block.text.encode("utf-8")).hexdigest()
            unit_seed = f"{envelope.envelope_id}:{envelope.asset_id}:{block.id}:{seq_idx}:{b_hash[:16]}"
            u_id = str(uuid.uuid5(uuid.NAMESPACE_URL, unit_seed))

            c_role = ContentRole.POLICY_RULE
            if block.block_type == ContentBlockType.HEADING:
                c_role = ContentRole.HEADING
            elif block.block_type == ContentBlockType.TABLE:
                c_role = ContentRole.POLICY_RULE

            sec_name = block.heading_path[-1] if block.heading_path else "General"

            unit = ParsedEvidenceUnit(
                unit_id=u_id,
                envelope_id=envelope.envelope_id,
                asset_id=envelope.asset_id,
                block_type=block.block_type.value if hasattr(block.block_type, "value") else str(block.block_type),
                content_role=c_role,
                is_canonical=(c_role != ContentRole.HEADING),
                content_text=block.text,
                structured_data=block.table_data or {},
                locator={
                    "page_number": block.page_number,
                    "section_heading": sec_name,
                    "start_offset": block.start_char_offset,
                    "end_offset": block.end_char_offset,
                    "block_id": block.id,
                },
                hierarchical_context=block.heading_path,
                content_hash=b_hash,
                sequence_index=seq_idx,
                structure_type=block.block_type.value if hasattr(block.block_type, "value") else str(block.block_type),
                section_path=block.heading_path,
                char_start=block.start_char_offset,
                char_end=block.end_char_offset,
            )

            # Table row & cell unit decomposition for granular Family 3 / Family 7 gate binding
            if block.block_type == ContentBlockType.TABLE and block.table_data:
                t_data = block.table_data
                headers = t_data.get("headers", [])
                rows = t_data.get("rows", [])
                unit.table_id = t_data.get("table_id")
                unit.column_headers = headers

                # Emit primary table block
                units.append(unit)

                # Emit TABLE_ROW child units
                for r_idx, row in enumerate(rows, start=1):
                    seq_idx += 1
                    row_text = "| " + " | ".join(row) + " |"
                    row_hash = hashlib.sha256(row_text.encode("utf-8")).hexdigest()
                    r_dict = {headers[col_i] if col_i < len(headers) else f"col_{col_i+1}": row[col_i] for col_i in range(len(row))}

                    r_seed = f"{envelope.envelope_id}:{envelope.asset_id}:row_{r_idx}:{row_hash[:16]}"
                    r_unit_id = str(uuid.uuid5(uuid.NAMESPACE_URL, r_seed))

                    row_unit = ParsedEvidenceUnit(
                        unit_id=r_unit_id,
                        envelope_id=envelope.envelope_id,
                        asset_id=envelope.asset_id,
                        block_type="table_row",
                        content_role=ContentRole.POLICY_RULE,
                        is_canonical=True,
                        content_text=row_text,
                        structured_data={"columns": r_dict, **r_dict},
                        locator={
                            "page_number": block.page_number,
                            "section_heading": sec_name,
                            "table_id": t_data.get("table_id"),
                            "row_index": r_idx,
                            "start_offset": block.start_char_offset,
                            "end_offset": block.end_char_offset,
                        },
                        hierarchical_context=block.heading_path + [f"Row {r_idx}"],
                        content_hash=row_hash,
                        sequence_index=seq_idx,
                        structure_type="table_row",
                        table_id=t_data.get("table_id"),
                        row_id=f"row_{r_idx}",
                        column_headers=headers,
                        cells=r_dict,
                        section_path=block.heading_path,
                        char_start=block.start_char_offset,
                        char_end=block.end_char_offset,
                    )
                    units.append(row_unit)
                continue

            units.append(unit)

        return ParsedEvidenceResult(
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            source_family=SourceFamily.DOCUMENT,
            parser_name="HtmlAdapter",
            units=units,
            metadata={
                "parser": "HtmlAdapter",
                "total_blocks": len(blocks),
                "total_tables": len(tables),
                "total_pages": len(pages),
                "warnings": warnings,
            },
        )
