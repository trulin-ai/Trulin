"""
Table Context Collector (Sections 4 & 11).

Collects semantic context surrounding each reconstructed table across the ordered
ParsedEvidenceUnit stream while enforcing strict section-boundary scoping so
unrelated distant paragraphs are never attached.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any, Dict, List, Optional, Tuple

from app.extraction.table_context.header_resolver import HeaderContextResolver
from app.extraction.table_context.models import (
    CanonicalTable,
    CanonicalTableRow,
    ContextProvenanceItem,
    NormalizedCellValue,
    TableContextBundle,
)
from app.extraction.table_context.normalizer import TableValueNormalizer
from app.ingestion.parsers.evidence_model import ParsedEvidenceResult, ParsedEvidenceUnit


class TableContextCollector:
    """Collects table-level, section-level, and footnote context for every table."""

    EXPLICIT_TITLE_PAT = re.compile(
        r"^(?:Table\s+\d+(?:\.\d+)?\s*[:\-–—]\s*(.+)|Title\s*[:\-]\s*(.+)|\*\*([^*]{3,120})\*\*)$",
        re.IGNORECASE,
    )
    EXPLICIT_CAPTION_PAT = re.compile(
        r"^(?:Table\s+)?Caption\s*[:\-]\s*(.+)$",
        re.IGNORECASE,
    )
    FOOTNOTE_PAT = re.compile(
        r"^(?:(\*+|†|‡|\[\d+\]|\(\d+\)|[¹²³⁴⁵⁶⁷⁸⁹]+)\s*(.+)|(?:Foot)?notes?\s*[:\-]\s*(.+)|Exceptions?\s*[:\-]\s*(.+))$",
        re.IGNORECASE,
    )
    TABLE_INTRO_CUES = (
        "following table", "table below", "matrix below", "schedule below",
        "as follows", "outlined below", "summarized below", "entitled to",
        "eligibility", "applies to", "defines", "specifies", "thresholds",
    )
    FOLLOWING_RELEVANCE_CUES = (
        "note", "footnote", "exception", "unless", "except", "above table",
        "table above", "grade", "tier", "entitlement", "leave", "allowance",
        "refund", "threshold", "rate", "formula", "calculated", "*", "[1]", "(1)",
    )

    # Opposing domain/topic pairs for context inconsistency detection (Test 13)
    MUTUALLY_EXCLUSIVE_TOPIC_CUES = [
        ({"annual leave", "vacation leave", "paid time off", "pto"}, {"sick leave", "medical leave", "illness leave"}),
        ({"annual leave", "sick leave", "leave"}, {"training allowance", "tuition", "learning budget", "travel expense", "severance"}),
        ({"refund", "return policy"}, {"employee onboarding", "disciplinary", "notice period"}),
        ({"salary", "compensation"}, {"password policy", "encryption"}),
    ]

    @classmethod
    def _is_page_heading(cls, unit: ParsedEvidenceUnit) -> bool:
        if unit.block_type != "heading":
            return False
        return bool(re.match(r"^Page\s+\d+\b", (unit.content_text or "").strip(), re.IGNORECASE))

    @classmethod
    def _group_tables(
        cls, units: List[ParsedEvidenceUnit]
    ) -> List[Tuple[str, List[int], List[ParsedEvidenceUnit]]]:
        """
        Groups contiguous table_row units into logical tables.
        Automatically merges multi-page split tables separated only by 'Page N' headings
        when headers match.
        Returns list of (table_id, unit_indices, row_units).
        """
        groups: List[Tuple[str, List[int], List[ParsedEvidenceUnit]]] = []
        current_tid: Optional[str] = None
        current_indices: List[int] = []
        current_rows: List[ParsedEvidenceUnit] = []
        current_headers: List[str] = []

        def _flush():
            nonlocal current_tid, current_indices, current_rows, current_headers
            if current_tid and current_rows:
                groups.append((current_tid, list(current_indices), list(current_rows)))
            current_tid = None
            current_indices = []
            current_rows = []
            current_headers = []

        idx = 0
        while idx < len(units):
            u = units[idx]
            if u.block_type == "table_row":
                tid = u.table_id or (u.structured_data or {}).get("table_id") or f"table_{idx}"
                u_hdrs = [str(h).strip().lower() for h in (u.column_headers or (u.structured_data or {}).get("table_headers") or [])]

                if current_tid is None:
                    current_tid = tid
                    current_indices = [idx]
                    current_rows = [u]
                    current_headers = u_hdrs
                elif tid == current_tid or (u_hdrs and u_hdrs == current_headers):
                    current_indices.append(idx)
                    current_rows.append(u)
                else:
                    _flush()
                    current_tid = tid
                    current_indices = [idx]
                    current_rows = [u]
                    current_headers = u_hdrs
            elif u.block_type == "table_cell":
                # Keep table open while scanning granular table_cell units from XlsxAdapter
                pass
            elif cls._is_page_heading(u) and current_tid is not None:
                # Look ahead past optional page heading to see if table continues
                peek = idx + 1
                while peek < len(units) and units[peek].block_type == "table_cell":
                    peek += 1
                if peek < len(units) and units[peek].block_type == "table_row":
                    next_hdrs = [str(h).strip().lower() for h in (units[peek].column_headers or (units[peek].structured_data or {}).get("table_headers") or [])]
                    if next_hdrs == current_headers:
                        idx += 1
                        continue
                _flush()
            else:
                _flush()
            idx += 1

        _flush()
        return groups

    @classmethod
    def _detect_context_inconsistency(
        cls,
        bundle: TableContextBundle,
        headers: List[str],
    ) -> Tuple[bool, List[str]]:
        """Detects contradictions between explicit title, caption, description, or headers."""
        reasons: List[str] = []
        title_txt = (bundle.table_title.text if bundle.table_title else "").lower()
        cap_txt = (bundle.table_caption.text if bundle.table_caption else "").lower()
        desc_txt = (bundle.table_description.text if bundle.table_description else "").lower()
        prec_txt = (bundle.preceding_paragraph.text if bundle.preceding_paragraph else "").lower()
        hdr_txt = " ".join(headers).lower()

        sources = [
            ("title", title_txt),
            ("caption", cap_txt),
            ("description", desc_txt),
            ("preceding_paragraph", prec_txt),
            ("headers", hdr_txt),
        ]

        for set_a, set_b in cls.MUTUALLY_EXCLUSIVE_TOPIC_CUES:
            matched_a = [(name, kw) for name, txt in sources if txt for kw in set_a if kw in txt]
            matched_b = [(name, kw) for name, txt in sources if txt for kw in set_b if kw in txt]
            if matched_a and matched_b:
                src_a = {n for n, _ in matched_a}
                src_b = {n for n, _ in matched_b}
                if src_a != src_b or ("title" in src_a and ("caption" in src_b or "preceding_paragraph" in src_b or "headers" in src_b)):
                    reasons.append(
                        f"Context source mismatch: {sorted(src_a)} indicates '{matched_a[0][1]}' "
                        f"while {sorted(src_b)} indicates '{matched_b[0][1]}'."
                    )

        return bool(reasons), reasons

    @classmethod
    def collect_tables(
        cls,
        evidence_result: ParsedEvidenceResult,
        document_title: Optional[str] = None,
    ) -> List[CanonicalTable]:
        """Reconstructs all tables in the document and collects their bounded semantic context."""
        units = evidence_result.units or []
        groups = cls._group_tables(units)
        if not groups:
            return []

        # Determine document-level title from first H1 heading if not provided
        doc_title = document_title
        if not doc_title:
            for u in units:
                if u.block_type == "heading" and (u.structured_data or {}).get("heading_level") == 1:
                    doc_title = u.content_text.strip()
                    break

        canonical_tables: List[CanonicalTable] = []

        for table_id, row_indices, row_units in groups:
            first_idx = row_indices[0]
            last_idx = row_indices[-1]
            first_unit = row_units[0]

            # 1. Headers & Header Hierarchy
            raw_headers = list(
                first_unit.column_headers
                or (first_unit.structured_data or {}).get("table_headers")
                or list((first_unit.cells or (first_unit.structured_data or {}).get("columns") or {}).keys())
            )
            raw_header_rows = (first_unit.structured_data or {}).get("raw_header_rows") or []
            sample_rows = [u.cells or (u.structured_data or {}).get("columns") or {} for u in row_units[:5]]
            header_hierarchy = HeaderContextResolver.resolve(
                headers=raw_headers,
                raw_header_rows=raw_header_rows,
                sample_rows=sample_rows,
            )

            # Collect all footnote markers present inside headers or cells
            table_markers: set[str] = set()
            for hn in header_hierarchy.columns:
                table_markers.update(hn.footnote_markers)

            # 2. Build CanonicalTableRows + Normalized Cells
            canon_rows: List[CanonicalTableRow] = []
            page_nums: List[int] = []
            for r_pos, u in enumerate(row_units, start=1):
                s_data = u.structured_data or {}
                cols = dict(u.cells or s_data.get("columns") or {})

                # Skip horizontally merged section-divider rows (e.g. | A. Benefits | A. Benefits | ... |)
                non_empty_vals = [str(v).strip() for v in cols.values() if str(v).strip()]
                if len(raw_headers) >= 3 and len(non_empty_vals) >= 3 and len(set(non_empty_vals)) == 1:
                    continue

                # Skip secondary header rows emitted as data rows (e.g. | Plan | Co-pay % | ... |)
                if r_pos == 1 and header_hierarchy.columns:
                    hdr_matches = sum(
                        1
                        for hn in header_hierarchy.columns
                        if str(cols.get(hn.raw_header, "")).strip().lower()
                        in (hn.clean_header.lower(), hn.raw_header.lower())
                    )
                    if hdr_matches >= max(2, len(header_hierarchy.columns) // 2):
                        continue

                cells_meta_list = s_data.get("cells_meta") or []
                inherited_cols = set(s_data.get("inherited_cols") or [])
                blank_cols = set(s_data.get("original_blank_cols") or [])

                norm_cells: Dict[str, NormalizedCellValue] = {}
                for c_idx, h_raw in enumerate(raw_headers):
                    c_val = cols.get(h_raw, "")
                    c_meta = cells_meta_list[c_idx] if c_idx < len(cells_meta_list) else None
                    h_node = header_hierarchy.columns[c_idx] if c_idx < len(header_hierarchy.columns) else None
                    norm_v = TableValueNormalizer.normalize_cell(
                        raw_value=c_val,
                        cell_meta=c_meta,
                        header_unit=h_node.embedded_unit if h_node else None,
                        header_currency=h_node.embedded_currency if h_node else None,
                        is_inherited=h_raw in inherited_cols,
                        is_original_blank=(h_raw in blank_cols) or (str(c_val).strip() == ""),
                    )
                    norm_cells[h_raw] = norm_v
                    table_markers.update(norm_v.footnote_markers)

                p_num = (u.locator or {}).get("page_number") or (u.locator or {}).get("page")
                if isinstance(p_num, int) and p_num not in page_nums:
                    page_nums.append(p_num)

                row_loc = dict(u.locator or {})
                if s_data.get("raw_row_line"):
                    row_loc["raw_row_line"] = s_data["raw_row_line"]
                elif u.content_text and u.content_text.strip().startswith("|"):
                    row_loc["raw_row_line"] = u.content_text.strip()

                canon_rows.append(CanonicalTableRow(
                    row_id=u.row_id or s_data.get("row_id") or f"{table_id}_row_{r_pos}",
                    row_index=s_data.get("row_index") or r_pos,
                    unit_id=u.unit_id,
                    raw_text=u.content_text,
                    page_number=p_num if isinstance(p_num, int) else None,
                    char_start=u.char_start,
                    char_end=u.char_end,
                    cells=cols,
                    normalized_cells=norm_cells,
                    is_ambiguous=bool(s_data.get("is_ambiguous", False)),
                    ambiguity_reason=s_data.get("ambiguity_reason"),
                    locator=row_loc,
                ))

            # 3. Bounded Context Collection (Upstream within same section)
            table_section = list(first_unit.section_path or first_unit.hierarchical_context or [])
            table_title_item: Optional[ContextProvenanceItem] = None
            table_caption_item: Optional[ContextProvenanceItem] = None
            table_desc_item: Optional[ContextProvenanceItem] = None
            preceding_para_item: Optional[ContextProvenanceItem] = None
            parent_sec_item: Optional[ContextProvenanceItem] = None
            subsec_item: Optional[ContextProvenanceItem] = None

            # Check adapter-embedded table title & caption (e.g., XLSX banner title, HTML <caption>)
            embedded_title = (first_unit.structured_data or {}).get("table_title")
            if embedded_title:
                table_title_item = ContextProvenanceItem(
                    context_type="title",
                    text=str(embedded_title).strip(),
                    unit_id=first_unit.unit_id,
                    distance_units=0,
                )
            embedded_caption = (first_unit.structured_data or {}).get("table_caption")
            if embedded_caption:
                table_caption_item = ContextProvenanceItem(
                    context_type="caption",
                    text=str(embedded_caption).strip(),
                    unit_id=first_unit.unit_id,
                    distance_units=0,
                )

            # Section hierarchy items
            non_doc_sections = [s for s in table_section if not re.match(r"^Page\s+\d+$", str(s), re.IGNORECASE)]
            if len(non_doc_sections) >= 2:
                parent_sec_item = ContextProvenanceItem(context_type="section_heading", text=non_doc_sections[-2], distance_units=1)
                subsec_item = ContextProvenanceItem(context_type="subsection_heading", text=non_doc_sections[-1], distance_units=1)
            elif len(non_doc_sections) == 1:
                parent_sec_item = ContextProvenanceItem(context_type="section_heading", text=non_doc_sections[0], distance_units=1)

            # Walk backward at most 4 units within the same section (never crossing a non-page heading after finding one)
            steps_back = 0
            for b_idx in range(first_idx - 1, max(-1, first_idx - 5), -1):
                u_prev = units[b_idx]
                steps_back += 1
                if u_prev.block_type == "table":
                    continue
                if u_prev.block_type in ("table_row", "table_cell"):
                    break
                if cls._is_page_heading(u_prev):
                    continue

                prev_txt = (u_prev.content_text or "").strip()
                if not prev_txt:
                    continue

                if u_prev.block_type == "heading":
                    # Immediately preceding heading (distance <= 3) provides section/table title context
                    h_lvl = (u_prev.structured_data or {}).get("heading_level", 2)
                    if steps_back <= 3 and h_lvl >= 2:
                        if not subsec_item:
                            subsec_item = ContextProvenanceItem(
                                context_type="subsection_heading",
                                text=prev_txt,
                                unit_id=u_prev.unit_id,
                                char_start=u_prev.char_start,
                                char_end=u_prev.char_end,
                                page_number=(u_prev.locator or {}).get("page_number"),
                                distance_units=steps_back,
                            )
                        if steps_back <= 2 and not table_title_item:
                            table_title_item = ContextProvenanceItem(
                                context_type="title",
                                text=prev_txt,
                                unit_id=u_prev.unit_id,
                                char_start=u_prev.char_start,
                                char_end=u_prev.char_end,
                                page_number=(u_prev.locator or {}).get("page_number"),
                                distance_units=steps_back,
                            )
                    break  # Stop at section heading boundary

                # Stop if unit belongs to a different section
                u_sec = [s for s in (u_prev.section_path or []) if not re.match(r"^Page\s+\d+$", str(s), re.IGNORECASE)]
                if non_doc_sections and u_sec and u_sec != non_doc_sections:
                    break

                # Check explicit caption
                m_cap = cls.EXPLICIT_CAPTION_PAT.match(prev_txt)
                if m_cap and not table_caption_item:
                    table_caption_item = ContextProvenanceItem(
                        context_type="caption",
                        text=m_cap.group(1).strip(),
                        unit_id=u_prev.unit_id,
                        char_start=u_prev.char_start,
                        char_end=u_prev.char_end,
                        page_number=(u_prev.locator or {}).get("page_number"),
                        distance_units=steps_back,
                    )
                    continue

                # Check explicit title ("Table 1: ...", "**Title**")
                m_tit = cls.EXPLICIT_TITLE_PAT.match(prev_txt)
                if m_tit and not table_title_item:
                    tit_val = (m_tit.group(1) or m_tit.group(2) or m_tit.group(3) or "").strip()
                    table_title_item = ContextProvenanceItem(
                        context_type="title",
                        text=tit_val,
                        unit_id=u_prev.unit_id,
                        char_start=u_prev.char_start,
                        char_end=u_prev.char_end,
                        page_number=(u_prev.locator or {}).get("page_number"),
                        distance_units=steps_back,
                    )
                    continue

                # Preceding explanatory paragraph / description (only immediate 1-2 units before table)
                if steps_back <= 2 and not preceding_para_item:
                    is_intro = (
                        prev_txt.endswith(":")
                        or any(cue in prev_txt.lower() for cue in cls.TABLE_INTRO_CUES)
                        or any(h.lower() in prev_txt.lower() for h in raw_headers if len(h) > 3)
                    )
                    # Check if short title-like phrase right above table (<= 8 words, no period)
                    if not table_title_item and len(prev_txt.split()) <= 10 and not prev_txt.endswith(".") and not is_intro:
                        table_title_item = ContextProvenanceItem(
                            context_type="title",
                            text=prev_txt.rstrip(":"),
                            unit_id=u_prev.unit_id,
                            char_start=u_prev.char_start,
                            char_end=u_prev.char_end,
                            page_number=(u_prev.locator or {}).get("page_number"),
                            distance_units=steps_back,
                        )
                    else:
                        preceding_para_item = ContextProvenanceItem(
                            context_type="preceding_paragraph",
                            text=prev_txt,
                            unit_id=u_prev.unit_id,
                            char_start=u_prev.char_start,
                            char_end=u_prev.char_end,
                            page_number=(u_prev.locator or {}).get("page_number"),
                            distance_units=steps_back,
                            confidence=1.0 if is_intro else 0.75,
                        )
                        if is_intro and not table_desc_item:
                            table_desc_item = ContextProvenanceItem(
                                context_type="description",
                                text=prev_txt,
                                unit_id=u_prev.unit_id,
                                char_start=u_prev.char_start,
                                char_end=u_prev.char_end,
                                page_number=(u_prev.locator or {}).get("page_number"),
                                distance_units=steps_back,
                            )

            # 4. Bounded Context Collection (Downstream footnotes & relevant following paragraphs)
            footnotes: List[ContextProvenanceItem] = []
            referenced_notes: List[ContextProvenanceItem] = []
            following_paras: List[ContextProvenanceItem] = []

            steps_fwd = 0
            for f_idx in range(last_idx + 1, min(len(units), last_idx + 6)):
                u_next = units[f_idx]
                if u_next.block_type == "table_cell":
                    continue
                if cls._is_page_heading(u_next):
                    continue
                if u_next.block_type in ("heading", "table_row"):
                    break

                steps_fwd += 1
                raw_next = ((u_next.structured_data or {}).get("raw_line") or u_next.content_text or "").strip()
                next_txt = (u_next.content_text or "").strip()
                if not next_txt:
                    continue

                # Stop if next unit belongs to a different section
                u_sec = [s for s in (u_next.section_path or []) if not re.match(r"^Page\s+\d+$", str(s), re.IGNORECASE)]
                if non_doc_sections and u_sec and u_sec != non_doc_sections:
                    break

                m_fn = cls.FOOTNOTE_PAT.match(raw_next) or cls.FOOTNOTE_PAT.match(next_txt)
                if m_fn:
                    marker = m_fn.group(1)
                    body = (m_fn.group(2) or m_fn.group(3) or m_fn.group(4) or next_txt).strip()
                    fn_item = ContextProvenanceItem(
                        context_type="footnote" if marker else "referenced_note",
                        text=body,
                        unit_id=u_next.unit_id,
                        char_start=u_next.char_start,
                        char_end=u_next.char_end,
                        page_number=(u_next.locator or {}).get("page_number"),
                        distance_units=steps_fwd,
                        marker=marker,
                    )
                    if marker:
                        footnotes.append(fn_item)
                    else:
                        referenced_notes.append(fn_item)
                    continue

                # Only attach following paragraph if immediately adjacent and topically anchored to the table
                next_low = next_txt.lower()
                is_relevant_follow = (
                    steps_fwd <= 2
                    and (
                        any(cue in next_low for cue in cls.FOLLOWING_RELEVANCE_CUES)
                        or any(m.lower() in next_low for m in table_markers)
                        or (table_title_item and any(w in next_low for w in table_title_item.text.lower().split() if len(w) > 4))
                    )
                )
                if is_relevant_follow:
                    following_paras.append(ContextProvenanceItem(
                        context_type="following_paragraph",
                        text=next_txt,
                        unit_id=u_next.unit_id,
                        char_start=u_next.char_start,
                        char_end=u_next.char_end,
                        page_number=(u_next.locator or {}).get("page_number"),
                        distance_units=steps_fwd,
                    ))
                else:
                    # Unrelated following paragraph -> stop collecting to prevent context contamination (Test 15)
                    break

            all_ctx_items = [
                item for item in (
                    [table_title_item, table_caption_item, table_desc_item, parent_sec_item, subsec_item, preceding_para_item]
                    + following_paras
                    + footnotes
                    + referenced_notes
                ) if item is not None
            ]

            bundle = TableContextBundle(
                table_id=table_id,
                document_title=doc_title,
                table_title=table_title_item,
                table_caption=table_caption_item,
                table_description=table_desc_item,
                parent_section_heading=parent_sec_item,
                subsection_heading=subsec_item,
                preceding_paragraph=preceding_para_item,
                following_paragraphs=following_paras,
                footnotes=footnotes,
                referenced_notes=referenced_notes,
                all_items=all_ctx_items,
            )

            has_inconsistency, inc_reasons = cls._detect_context_inconsistency(bundle, raw_headers)
            bundle.has_inconsistency = has_inconsistency
            bundle.inconsistency_reasons = inc_reasons

            # Compute context fingerprint for cache invalidation (Section 18)
            fp_payload = {
                "doc_title": doc_title,
                "headers": raw_headers,
                "context": [(it.context_type, it.text) for it in all_ctx_items],
                "sample": [r.cells for r in canon_rows[:3]],
            }
            bundle.context_fingerprint = hashlib.sha256(
                json.dumps(fp_payload, sort_keys=True, default=str).encode("utf-8")
            ).hexdigest()

            canonical_tables.append(CanonicalTable(
                table_id=table_id,
                asset_id=evidence_result.asset_id,
                page_numbers=page_nums or [1],
                extraction_method=evidence_result.parser_name,
                headers=raw_headers,
                header_hierarchy=header_hierarchy,
                rows=canon_rows,
                context_bundle=bundle,
            ))

        return canonical_tables

