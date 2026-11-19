"""
Layer 4: Specialized Markdown Parser Adapter (Phase 6 Step 6.4).

Converts Markdown documents into canonical structured evidence units and markdown AST.
Preserves:
- Heading hierarchies (H1 to H6) with breadcrumb hierarchy tracking
- Nested bullet and numbered lists with indentation depth preservation
- Markdown pipe tables with header-column bindings and row/cell extraction
- Fenced code blocks with language tags
- Blockquotes and callouts
- YAML frontmatter metadata extraction
- Deterministic evidence units (unit_id, char_offsets, SHA-256 hashes, breadcrumbs)
- Direct integration with the 8 Universal Gate Contract families
"""

from __future__ import annotations

import hashlib
import io
import logging
import re
import uuid
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


class MarkdownAdapter:
    """Specialized adapter for Markdown (.md, .markdown) documents."""

    @classmethod
    def _parse_frontmatter(cls, text: str) -> Tuple[str, Dict[str, Any]]:
        """Extracts YAML frontmatter if present and returns (body_text, metadata)."""
        metadata: Dict[str, Any] = {}
        if not text.startswith("---"):
            return text, metadata

        parts = text.split("---", 2)
        if len(parts) < 3:
            return text, metadata

        yaml_content = parts[1].strip()
        body = parts[2].lstrip("\r\n")

        for line in yaml_content.splitlines():
            line_str = line.strip()
            if ":" in line_str and not line_str.startswith("#"):
                k, v = line_str.split(":", 1)
                metadata[k.strip()] = v.strip().strip('"').strip("'")

        return body, metadata

    @classmethod
    def parse_to_structured(
        cls,
        raw_bytes: bytes,
        title: str = "Markdown Document",
        filename: str = "document.md",
    ) -> Tuple[str, List[DocumentPage], List[ContentBlock], List[Dict[str, Any]], List[str]]:
        """
        Parses Markdown text into structured blocks, tables, and synthetic pages.
        Returns: (full_text, pages, blocks, tables, warnings)
        """
        warnings: List[str] = []

        # 1. Multi-encoding decode
        text = ""
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                text = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        if not text:
            text = raw_bytes.decode("utf-8", errors="replace")

        # 2. Extract YAML frontmatter
        body_text, frontmatter = cls._parse_frontmatter(text)

        lines = body_text.splitlines()
        blocks: List[ContentBlock] = []
        tables: List[Dict[str, Any]] = []
        markdown_output_lines: List[str] = []

        current_hier: List[str] = [frontmatter.get("title") or title]
        current_page_blocks: List[ContentBlock] = []
        current_page_text: List[str] = []
        pages: List[DocumentPage] = []
        current_page_num = 1
        page_char_count = 0

        char_cursor = 0
        b_idx = 0
        t_idx = 0

        i = 0
        n_lines = len(lines)

        while i < n_lines:
            line = lines[i]
            stripped = line.strip()

            # Synthetic Page Break: '---' or '***' on its own line when not frontmatter
            if re.match(r"^(\-{3,}|\*{3,}|_{3,})$", stripped):
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
                i += 1
                continue

            # Empty line
            if not stripped:
                i += 1
                continue

            # 3. Fenced Code Block Detection
            code_fence_match = re.match(r"^(```|~~~)(.*)$", stripped)
            if code_fence_match:
                fence_tag = code_fence_match.group(1)
                lang = code_fence_match.group(2).strip()
                code_lines = []
                i += 1
                while i < n_lines:
                    if lines[i].strip().startswith(fence_tag):
                        i += 1
                        break
                    code_lines.append(lines[i])
                    i += 1

                code_block_text = f"```{lang}\n" + "\n".join(code_lines) + "\n```"
                b_idx += 1
                start_offset = char_cursor
                end_offset = char_cursor + len(code_block_text)
                char_cursor = end_offset + 2

                block = ContentBlock(
                    id=f"blk_md_code_{b_idx}",
                    block_type=ContentBlockType.CODE_BLOCK,
                    text=code_block_text,
                    raw_text=code_block_text,
                    page_number=current_page_num,
                    start_char_offset=start_offset,
                    end_char_offset=end_offset,
                    heading_path=list(current_hier),
                    metadata={"language": lang},
                )
                blocks.append(block)
                current_page_blocks.append(block)
                current_page_text.append(code_block_text)
                page_char_count += len(code_block_text)
                markdown_output_lines.append(code_block_text)
                continue

            # 4. Heading Detection (# to ######)
            heading_match = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            if heading_match:
                level = len(heading_match.group(1))
                h_text = heading_match.group(2).strip()
                # Maintain hierarchical breadcrumb trail
                if level == 1:
                    current_hier = [h_text]
                else:
                    current_hier = current_hier[:level - 1] + [h_text]

                b_idx += 1
                start_offset = char_cursor
                formatted_heading = f"{'#' * level} {h_text}"
                end_offset = char_cursor + len(formatted_heading)
                char_cursor = end_offset + 2

                block = ContentBlock(
                    id=f"blk_md_h_{b_idx}",
                    block_type=ContentBlockType.HEADING,
                    text=formatted_heading,
                    raw_text=line,
                    page_number=current_page_num,
                    start_char_offset=start_offset,
                    end_char_offset=end_offset,
                    heading_path=list(current_hier),
                    metadata={"heading_level": level, "heading_title": h_text},
                )
                blocks.append(block)
                current_page_blocks.append(block)
                current_page_text.append(formatted_heading)
                page_char_count += len(formatted_heading)
                markdown_output_lines.append(formatted_heading)
                i += 1
                continue

            # 5. Markdown Pipe Table Detection
            if stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2:
                table_lines = []
                while i < n_lines and lines[i].strip().startswith("|") and lines[i].strip().endswith("|"):
                    table_lines.append(lines[i].strip())
                    i += 1

                if len(table_lines) >= 2:
                    t_idx += 1
                    headers = split_markdown_table_row(table_lines[0])
                    start_row_idx = 1
                    # Check for alignment separator row (:---, :---:, ---:)
                    sep_cells = split_markdown_table_row(table_lines[1])
                    if all(re.match(r"^:?-+:?$", c) for c in sep_cells if c):
                        start_row_idx = 2

                    table_data_rows: List[List[str]] = []
                    for r_line in table_lines[start_row_idx:]:
                        row_cells = split_markdown_table_row(r_line)
                        # Pad row cells to match header count
                        if len(row_cells) < len(headers):
                            row_cells.extend([""] * (len(headers) - len(row_cells)))
                        table_data_rows.append(row_cells[:len(headers)])

                    # Build normalized markdown table
                    hdr_line = "| " + " | ".join(headers) + " |"
                    align_line = "| " + " | ".join([":---"] * len(headers)) + " |"
                    data_lines = ["| " + " | ".join(r) + " |" for r in table_data_rows]
                    full_tbl_text = "\n".join([hdr_line, align_line] + data_lines)

                    row_dicts = []
                    for r in table_data_rows:
                        row_dicts.append({headers[c_idx] if c_idx < len(headers) else f"col_{c_idx+1}": r[c_idx] for c_idx in range(len(r))})

                    t_data = {
                        "table_id": f"tbl_md_{t_idx}",
                        "headers": headers,
                        "rows": table_data_rows,
                        "row_dicts": row_dicts,
                    }
                    tables.append(t_data)

                    b_idx += 1
                    start_offset = char_cursor
                    end_offset = char_cursor + len(full_tbl_text)
                    char_cursor = end_offset + 2

                    block = ContentBlock(
                        id=f"blk_md_tbl_{b_idx}",
                        block_type=ContentBlockType.TABLE,
                        text=full_tbl_text,
                        raw_text="\n".join(table_lines),
                        page_number=current_page_num,
                        start_char_offset=start_offset,
                        end_char_offset=end_offset,
                        heading_path=list(current_hier),
                        table_data=t_data,
                    )
                    blocks.append(block)
                    current_page_blocks.append(block)
                    current_page_text.append(full_tbl_text)
                    page_char_count += len(full_tbl_text)
                    markdown_output_lines.append(full_tbl_text)
                    continue

            # 6. Nested Bullet and Numbered List Items
            list_match = re.match(r"^(\s*)([-*+]|\d+[\.\)]|[a-zA-Z][\.\)])\s+(.*)$", line)
            if list_match:
                indent_spaces = len(list_match.group(1))
                list_marker = list_match.group(2)
                item_content = list_match.group(3).strip()
                indent_level = indent_spaces // 2

                # Prefix formatted line
                formatted_item = f"{'  ' * indent_level}- {item_content}"

                b_idx += 1
                start_offset = char_cursor
                end_offset = char_cursor + len(formatted_item)
                char_cursor = end_offset + 2

                block = ContentBlock(
                    id=f"blk_md_list_{b_idx}",
                    block_type=ContentBlockType.LIST_ITEM,
                    text=formatted_item,
                    raw_text=line,
                    page_number=current_page_num,
                    start_char_offset=start_offset,
                    end_char_offset=end_offset,
                    heading_path=list(current_hier),
                    metadata={"indent_level": indent_level, "marker": list_marker},
                )
                blocks.append(block)
                current_page_blocks.append(block)
                current_page_text.append(formatted_item)
                page_char_count += len(formatted_item)
                markdown_output_lines.append(formatted_item)
                i += 1
                continue

            # 7. Blockquotes and Callout Blocks
            if stripped.startswith(">"):
                quote_lines = []
                while i < n_lines and lines[i].strip().startswith(">"):
                    clean_q = re.sub(r"^>\s*", "", lines[i].strip())
                    quote_lines.append(clean_q)
                    i += 1

                combined_quote = " ".join(quote_lines).strip()
                formatted_quote = f"> {combined_quote}"

                b_idx += 1
                start_offset = char_cursor
                end_offset = char_cursor + len(formatted_quote)
                char_cursor = end_offset + 2

                block = ContentBlock(
                    id=f"blk_md_quote_{b_idx}",
                    block_type=ContentBlockType.PARAGRAPH,
                    text=formatted_quote,
                    raw_text=formatted_quote,
                    page_number=current_page_num,
                    start_char_offset=start_offset,
                    end_char_offset=end_offset,
                    heading_path=list(current_hier),
                    metadata={"is_blockquote": True},
                )
                blocks.append(block)
                current_page_blocks.append(block)
                current_page_text.append(formatted_quote)
                page_char_count += len(formatted_quote)
                markdown_output_lines.append(formatted_quote)
                continue

            # 8. Standard Prose Paragraph (accumulate multi-line paragraphs)
            para_lines = [stripped]
            i += 1
            while i < n_lines:
                next_stripped = lines[i].strip()
                if not next_stripped or next_stripped.startswith(("#", "|", ">", "```", "~~~", "---", "***")) or re.match(r"^\s*[-*+]\s+", lines[i]) or re.match(r"^\s*\d+[\.\)]\s+", lines[i]):
                    break
                para_lines.append(next_stripped)
                i += 1

            combined_para = " ".join(para_lines).strip()
            b_idx += 1
            start_offset = char_cursor
            end_offset = char_cursor + len(combined_para)
            char_cursor = end_offset + 2

            block = ContentBlock(
                id=f"blk_md_p_{b_idx}",
                block_type=ContentBlockType.PARAGRAPH,
                text=combined_para,
                raw_text=combined_para,
                page_number=current_page_num,
                start_char_offset=start_offset,
                end_char_offset=end_offset,
                heading_path=list(current_hier),
            )
            blocks.append(block)
            current_page_blocks.append(block)
            current_page_text.append(combined_para)
            page_char_count += len(combined_para)
            markdown_output_lines.append(combined_para)

        # Finalize last page
        if current_page_text or current_page_blocks:
            pages.append(DocumentPage(
                page_number=current_page_num,
                text="\n\n".join(current_page_text),
                char_count=page_char_count,
                blocks=list(current_page_blocks),
            ))

        full_text = "\n\n".join(markdown_output_lines).strip()
        return full_text, pages, blocks, tables, warnings

    @classmethod
    async def parse_to_evidence(cls, envelope: CanonicalSourceEnvelope) -> ParsedEvidenceResult:
        """
        Parses a Markdown CanonicalSourceEnvelope into structured ParsedEvidenceUnits.
        Directly satisfies Layer 4 Evidence Contract with SHA-256 hashes, exact offsets,
        hierarchical breadcrumbs, table row binding, and cell-level locators.
        """
        if isinstance(envelope.raw_payload, bytes):
            raw_bytes = envelope.raw_payload
        elif hasattr(envelope, "metadata") and envelope.metadata.get("raw_bytes"):
            raw_bytes = envelope.metadata["raw_bytes"]
        else:
            raw_bytes = envelope.get_payload_as_text().encode("utf-8")

        filename = (envelope.locator_metadata or {}).get("filename", "document.md")
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
            parser_name="MarkdownAdapter",
            units=units,
            metadata={
                "parser": "MarkdownAdapter",
                "total_blocks": len(blocks),
                "total_tables": len(tables),
                "total_pages": len(pages),
                "warnings": warnings,
            },
        )
