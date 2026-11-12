"""
Layer 4: Specialized PPTX Parser Adapter.

Converts PowerPoint (.pptx) presentations into canonical structured evidence units and markdown AST.
Preserves:
- Slide numbers and slide titles
- Native PPTX table shapes (<a:tbl>, <a:tr>, <a:tc>, gridSpan, rowSpan/vMerge)
- Visually aligned tabular text shapes where feasible
- Slide body text and speaker notes
- Evidence contract compatibility (unit_id, char_offsets, SHA-256 hashes, slide breadcrumbs)
"""

from __future__ import annotations

import io
import logging
import re
import xml.etree.ElementTree as ET
import zipfile
from typing import Any, Dict, List, Optional, Tuple

from app.db.enums import SourceFamily
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

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}


class PptxAdapter:
    """Specialized adapter for Microsoft PowerPoint (.pptx) presentations."""

    @classmethod
    def _clean_cell_text(cls, text: str) -> str:
        if not text:
            return ""
        cleaned = re.sub(r"[\r\n]+", " ", text).strip()
        return cleaned.replace("|", r"\|")

    @classmethod
    def _extract_shape_text(cls, sp_elem: ET.Element) -> Tuple[str, Optional[str], Optional[Tuple[int, int]]]:
        """Extracts text from a <p:sp> shape along with its placeholder type and (x, y) coordinates."""
        ph = sp_elem.find(".//p:nvSpPr/p:nvPr/p:ph", NS)
        ph_type = ph.attrib.get("type") if ph is not None else None

        off = sp_elem.find(".//p:spPr/a:xfrm/a:off", NS)
        coords: Optional[Tuple[int, int]] = None
        if off is not None:
            try:
                coords = (int(off.attrib.get("x", 0)), int(off.attrib.get("y", 0)))
            except ValueError:
                coords = None

        paras: List[str] = []
        for p_elem in sp_elem.findall(".//p:txBody/a:p", NS):
            runs = [t.text for t in p_elem.findall(".//a:t", NS) if t.text]
            joined = "".join(runs).strip()
            if joined:
                paras.append(joined)
        return "\n".join(paras), ph_type, coords

    @classmethod
    def _extract_native_table(cls, tbl_elem: ET.Element) -> Tuple[List[str], List[List[str]], List[List[Dict[str, Any]]]]:
        """Extracts rows, headers, and cell span/merge metadata from an <a:tbl> element."""
        raw_rows: List[List[str]] = []
        cells_meta: List[List[Dict[str, Any]]] = []
        vmerge_carry: Dict[int, str] = {}

        for r_idx, tr in enumerate(tbl_elem.findall("./a:tr", NS)):
            row_vals: List[str] = []
            row_meta: List[Dict[str, Any]] = []
            tcs = tr.findall("./a:tc", NS)
            c_idx = 0
            for tc in tcs:
                grid_span = int(tc.attrib.get("gridSpan", "1") or "1")
                row_span = int(tc.attrib.get("rowSpan", "1") or "1")
                v_merge = tc.attrib.get("vMerge") == "1"
                h_merge = tc.attrib.get("hMerge") == "1"

                paras = []
                for p_elem in tc.findall("./a:txBody/a:p", NS):
                    runs = [t.text for t in p_elem.findall(".//a:t", NS) if t.text]
                    p_txt = "".join(runs).strip()
                    if p_txt:
                        paras.append(p_txt)
                cell_txt = cls._clean_cell_text(" ".join(paras))

                is_inherited = False
                is_original_blank = cell_txt == ""
                if (v_merge or h_merge) and not cell_txt:
                    if v_merge and c_idx in vmerge_carry:
                        cell_txt = vmerge_carry[c_idx]
                        is_inherited = True
                    elif h_merge and row_vals:
                        cell_txt = row_vals[-1]
                        is_inherited = True
                elif row_span > 1 and cell_txt:
                    vmerge_carry[c_idx] = cell_txt
                elif not v_merge:
                    vmerge_carry.pop(c_idx, None)

                for span_offset in range(max(1, grid_span)):
                    val = cell_txt if span_offset == 0 else cell_txt
                    row_vals.append(val)
                    row_meta.append({
                        "row_index": r_idx,
                        "col_index": c_idx + span_offset,
                        "grid_span": grid_span,
                        "row_span": row_span,
                        "is_merged": grid_span > 1 or row_span > 1 or v_merge or h_merge,
                        "is_inherited": is_inherited or span_offset > 0,
                        "is_original_blank": is_original_blank,
                    })
                c_idx += max(1, grid_span)

            if any(v for v in row_vals):
                raw_rows.append(row_vals)
                cells_meta.append(row_meta)

        if not raw_rows:
            return [], [], []

        max_cols = max(len(r) for r in raw_rows)
        for r in raw_rows:
            if len(r) < max_cols:
                r.extend([""] * (max_cols - len(r)))

        headers = [h if h else f"Column_{i+1}" for i, h in enumerate(raw_rows[0])]
        return headers, raw_rows, cells_meta

    @classmethod
    def parse_to_structured(
        cls, raw_bytes: bytes, title: str, filename: str
    ) -> Tuple[str, List[DocumentPage], List[ContentBlock], List[Dict[str, Any]], List[str]]:
        """Parses PPTX bytes into markdown AST, pages (slides), content blocks, and tables."""
        blocks: List[ContentBlock] = []
        tables: List[Dict[str, Any]] = []
        warnings: List[str] = []
        pages: List[DocumentPage] = []
        markdown_lines: List[str] = []

        doc_title = title or filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
        markdown_lines.append(f"# {doc_title}")
        markdown_lines.append("")
        char_cursor = len(markdown_lines[0]) + 2
        t_idx = 0
        b_idx = 0

        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                slide_files = sorted(
                    [f for f in zf.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", f)],
                    key=lambda x: int(re.search(r"slide(\d+)\.xml$", x).group(1)),
                )

                for slide_num, sfile in enumerate(slide_files, start=1):
                    tree = ET.fromstring(zf.read(sfile))
                    slide_blocks: List[ContentBlock] = []
                    slide_text_parts: List[str] = []
                    slide_title = f"Slide {slide_num}"

                    # 1. Extract shapes (titles and text bodies)
                    positioned_shapes: List[Tuple[int, int, str]] = []
                    for sp in tree.findall(".//p:spTree/p:sp", NS):
                        txt, ph_type, coords = cls._extract_shape_text(sp)
                        if not txt:
                            continue
                        if ph_type in ("title", "ctrTitle"):
                            slide_title = txt.replace("\n", " ").strip()
                        else:
                            x, y = coords if coords else (0, 0)
                            positioned_shapes.append((y, x, txt))

                    # Emit slide heading
                    slide_hdg = f"## Slide {slide_num}: {slide_title}" if slide_title != f"Slide {slide_num}" else f"## Slide {slide_num}"
                    b_idx += 1
                    hdg_blk = ContentBlock(
                        id=f"blk_pptx_{b_idx}",
                        block_type=ContentBlockType.HEADING,
                        text=slide_hdg,
                        raw_text=slide_title,
                        page_number=slide_num,
                        start_char_offset=char_cursor,
                        end_char_offset=char_cursor + len(slide_hdg),
                        metadata={"slide_number": slide_num, "slide_title": slide_title},
                    )
                    blocks.append(hdg_blk)
                    slide_blocks.append(hdg_blk)
                    slide_text_parts.append(slide_hdg)
                    markdown_lines.extend([slide_hdg, ""])
                    char_cursor += len(slide_hdg) + 2

                    # Sort non-title text shapes by vertical then horizontal position
                    positioned_shapes.sort(key=lambda item: (item[0], item[1]))
                    for _, _, txt in positioned_shapes:
                        b_idx += 1
                        p_blk = ContentBlock(
                            id=f"blk_pptx_{b_idx}",
                            block_type=ContentBlockType.PARAGRAPH,
                            text=txt,
                            raw_text=txt,
                            page_number=slide_num,
                            start_char_offset=char_cursor,
                            end_char_offset=char_cursor + len(txt),
                            metadata={"slide_number": slide_num},
                        )
                        blocks.append(p_blk)
                        slide_blocks.append(p_blk)
                        slide_text_parts.append(txt)
                        markdown_lines.extend([txt, ""])
                        char_cursor += len(txt) + 2

                    # 2. Extract native PPTX tables (<a:tbl>)
                    for tbl_elem in tree.findall(".//a:tbl", NS):
                        headers, all_rows, cells_meta = cls._extract_native_table(tbl_elem)
                        if not all_rows:
                            continue
                        t_idx += 1
                        header_line = "| " + " | ".join(headers) + " |"
                        sep_line = "| " + " | ".join(["---"] * len(headers)) + " |"
                        data_lines = ["| " + " | ".join(r) + " |" for r in all_rows[1:]]
                        tbl_md = "\n".join([header_line, sep_line] + data_lines)

                        row_dicts = [
                            {headers[i] if i < len(headers) else f"col_{i+1}": r[i] for i in range(len(r))}
                            for r in all_rows[1:]
                        ]
                        t_data = {
                            "table_id": f"tbl_pptx_{t_idx}",
                            "slide_number": slide_num,
                            "slide_title": slide_title,
                            "headers": headers,
                            "rows": all_rows,
                            "row_dicts": row_dicts,
                            "cells_meta": cells_meta,
                        }
                        tables.append(t_data)

                        b_idx += 1
                        tbl_blk = ContentBlock(
                            id=f"blk_pptx_tbl_{t_idx}",
                            block_type=ContentBlockType.TABLE,
                            text=tbl_md,
                            raw_text=tbl_md,
                            page_number=slide_num,
                            start_char_offset=char_cursor,
                            end_char_offset=char_cursor + len(tbl_md),
                            table_data=t_data,
                            metadata={"slide_number": slide_num, "slide_title": slide_title},
                        )
                        blocks.append(tbl_blk)
                        slide_blocks.append(tbl_blk)
                        slide_text_parts.append(tbl_md)
                        markdown_lines.extend([header_line, sep_line] + data_lines + [""])
                        char_cursor += len(tbl_md) + 2

                    # 3. Speaker notes if present
                    notes_file = f"ppt/notesSlides/notesSlide{slide_num}.xml"
                    if notes_file in zf.namelist():
                        ntree = ET.fromstring(zf.read(notes_file))
                        ntexts = [t.text.strip() for t in ntree.findall(".//a:t", NS) if t.text and t.text.strip()]
                        # Filter slide-number-only notes
                        note_body = " ".join(nt for nt in ntexts if nt != str(slide_num)).strip()
                        if note_body:
                            note_line = f"Note: {note_body}"
                            b_idx += 1
                            n_blk = ContentBlock(
                                id=f"blk_pptx_{b_idx}",
                                block_type=ContentBlockType.PARAGRAPH,
                                text=note_line,
                                raw_text=note_line,
                                page_number=slide_num,
                                start_char_offset=char_cursor,
                                end_char_offset=char_cursor + len(note_line),
                                metadata={"slide_number": slide_num, "is_speaker_note": True},
                            )
                            blocks.append(n_blk)
                            slide_blocks.append(n_blk)
                            slide_text_parts.append(note_line)
                            markdown_lines.extend([note_line, ""])
                            char_cursor += len(note_line) + 2

                    slide_full_text = "\n\n".join(slide_text_parts)
                    pages.append(DocumentPage(
                        page_number=slide_num,
                        text=slide_full_text,
                        char_count=len(slide_full_text),
                        blocks=slide_blocks,
                    ))
        except Exception as e:
            logger.error("Failed to parse PPTX presentation %s: %s", filename, e)
            warnings.append(f"PPTX parser error: {str(e)}")
            return "", [], [], [], warnings

        full_text = "\n".join(markdown_lines).strip()
        return full_text, pages, blocks, tables, warnings

    @classmethod
    async def parse_to_evidence(cls, envelope: CanonicalSourceEnvelope) -> ParsedEvidenceResult:
        """Parses a PPTX CanonicalSourceEnvelope into structured ParsedEvidenceUnits."""
        if isinstance(envelope.raw_payload, bytes):
            raw_bytes = envelope.raw_payload
        elif hasattr(envelope, "metadata") and envelope.metadata and envelope.metadata.get("raw_bytes"):
            raw_bytes = envelope.metadata["raw_bytes"]
        else:
            raw_bytes = envelope.get_payload_as_text().encode("utf-8")

        filename = (envelope.locator_metadata or {}).get("filename", "presentation.pptx")
        title = filename.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()

        markdown_text, pages, blocks, tables, warnings = cls.parse_to_structured(
            raw_bytes=raw_bytes,
            title=title,
            filename=filename,
        )

        from app.ingestion.parsers.document_parser import DocumentParser

        if not markdown_text and isinstance(envelope.raw_payload, str):
            markdown_text = envelope.raw_payload

        md_envelope = CanonicalSourceEnvelope(
            envelope_id=envelope.envelope_id,
            organization_id=envelope.organization_id,
            source_id=envelope.source_id,
            asset_id=envelope.asset_id,
            source_family=SourceFamily.DOCUMENT,
            source_intent=envelope.source_intent,
            native_format="pptx",
            source_version=envelope.source_version,
            content_hash=envelope.content_hash,
            raw_payload=markdown_text,
            locator_metadata=envelope.locator_metadata,
            evidence_locator=envelope.evidence_locator,
            access_scope=envelope.access_scope,
            metadata=envelope.metadata,
        )
        parsed = await DocumentParser.parse(md_envelope)

        # Attach slide/page numbers and merge metadata onto parsed units
        slide_by_title: Dict[str, int] = {}
        for blk in blocks:
            if blk.block_type == ContentBlockType.HEADING and blk.metadata.get("slide_number"):
                slide_by_title[blk.text.lstrip("# ").strip()] = blk.metadata["slide_number"]

        for u in parsed.units:
            for h in reversed(u.hierarchical_context or []):
                if h in slide_by_title:
                    u.locator["page_number"] = slide_by_title[h]
                    u.locator["slide_number"] = slide_by_title[h]
                    break

        parsed.parser_name = "PptxAdapter"
        parsed.quality_metrics["slides_count"] = len(pages)
        parsed.quality_metrics["tables_count"] = len(tables)
        return parsed

