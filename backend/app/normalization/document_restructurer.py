import re
from typing import Any, Dict, List, Optional, Tuple


class DocumentSemanticRestructurer:
    """
    Universal Document Semantic Restructurer (NIST AI RMF / Document Intelligence).
    
    Transforms spatial layout text (from layout-aware PDF parsers, OCR, or monospace text)
    into high-fidelity Markdown representations:
    1. Detects multi-column tabular matrices via spatial alignment and whitespace gutter analysis.
    2. Converts spatial tables into standard Markdown pipe tables without hardcoding.
    3. Normalizes section and subsection heading hierarchies (e.g. '1. Purpose' -> '## 1. Purpose').
    4. Strips repetitive running headers and footers.
    5. Preserves bullet points, blockquotes, and paragraph boundaries for reliable downstream S-P-O extraction.
    """

    DISALLOWED_HEADER_WORDS = {
        "the", "our", "this", "these", "effective", "applies", "defined",
        "defines", "ensures", "provides", "designed", "whether", "within", "during", "all",
        "is", "was", "are", "were", "will", "would", "shall", "can", "could", "may", "must",
        "released", "serving", "expected", "in", "of", "at", "by", "for", "with", "hout"
    }

    @classmethod
    def is_valid_table_header(cls, header_cells: List[str]) -> bool:
        """Verifies candidate cells look like short column headers rather than running prose."""
        if len(header_cells) < 2:
            return False
        for cell in header_cells:
            c = cell.strip()
            if not c:
                continue
            # Currency amounts or pure numbers cannot be column headers
            if re.match(r"^[\$€£₹¥]?\s*\d+(?:\.\d+)?%?$", c):
                return False
            # Disallow bullet markers or list numbers in table headers
            if c.startswith(("-", "*", "•", "• ", "1.", "2.", "3.", "-?", "?-", "? ", "-? ", "?- ")):
                return False
            # Disallow mid-phrase colons
            if ":" in c:
                return False
            words = [w.lower() for w in re.findall(r"\b[a-zA-Z]+\b", c)]
            # Only reject if header starts with a strong narrative stopword AND looks like prose
            if words and words[0] in {"the", "our", "this", "these", "is", "are", "was", "were"} and len(words) >= 3:
                return False
            if any(w in {"applies", "defined", "defines", "ensures", "provides", "designed", "serving"} for w in words):
                return False
            # Disallow 1-2 letter fragments in headers (wh, ere, wil, l)
            valid_short = ("id", "no", "hr", "to", "on", "in", "at", "by", "of", "or", "as", "is", "up", "if", "re", "hr", "it", "us", "uk", "eu")
            if any(len(w) <= 2 and w not in valid_short for w in words):
                return False
            max_len = 90 if len(header_cells) == 2 and header_cells.index(cell) == 1 else 45
            if len(c) > max_len or c.endswith((".", ",", ";", ":")):
                return False
        return True

    @classmethod
    def is_prose_line(cls, line: str) -> bool:
        """Detects if a line looks like justified narrative text rather than a table row."""
        stripped = line.strip()
        if not stripped:
            return False

        # Numbered headings must have a dot (e.g., '1.' or '1.1') before text, preventing '5 years.' from matching
        if re.match(r"^(?:\d+(?:\.\d+)+|\d+\.)\s+[A-Za-z]", stripped):
            return True
        if stripped.startswith(("- ", "* ", "• ", "● ", "❖ ", "#", ">", "---", "|")):
            return True
        # Multi-column whitespace/tab-separated lines (e.g. 'Applies to   All employees...') are tabular rows
        if len(re.split(r'\s{3,}|\t+', stripped)) >= 2:
            return False
        words = [w.lower() for w in re.findall(r"\b[a-zA-Z]+\b", stripped)]
        prose_markers = {
            "our", "we", "the", "this", "these", "applies", "ensures",
            "facilitating", "promoting", "effective", "whether"
        }
        if len(words) >= 6 and any(w in prose_markers for w in words[:3]):
            return True
        return False

    @classmethod
    def parse_table_block_anchors(cls, block_lines: List[str]) -> List[List[str]]:
        """Parses a multi-line spatial layout block into tabular rows via column anchor discovery."""
        non_empty = [l for l in block_lines if l.strip()]
        if len(non_empty) < 2:
            return []

        col_starts = []
        for line in non_empty:
            tokens = list(re.finditer(r"\S+(?:\s(?!\s{2,})\S+)*", line))
            if len(tokens) >= 2:
                for t in tokens:
                    col_starts.append(t.start())

        if not col_starts:
            return []

        col_starts.sort()
        clusters = []
        for cs in col_starts:
            if not clusters or abs(cs - clusters[-1][-1]) > 3:
                clusters.append([cs])
            else:
                clusters[-1].append(cs)

        raw_anchors = [(int(sum(c) / len(c)), len(c)) for c in clusters if len(c) >= 2]
        filtered_anchors = []
        for pos, count in sorted(raw_anchors, key=lambda x: x[0]):
            if not filtered_anchors:
                filtered_anchors.append((pos, count))
            else:
                prev_pos, prev_count = filtered_anchors[-1]
                if (pos - prev_pos) < 12:
                    if count > prev_count:
                        filtered_anchors[-1] = (pos, count)
                else:
                    filtered_anchors.append((pos, count))

        valid_anchors = [pos for pos, _ in filtered_anchors]
        valid_anchors.sort()

        if len(valid_anchors) < 2:
            return []

        rows: List[List[str]] = []
        for line in non_empty:
            cells = []
            for idx, anchor in enumerate(valid_anchors):
                next_anchor = valid_anchors[idx + 1] if idx + 1 < len(valid_anchors) else len(line)
                start = max(0, anchor - 2)
                end = next_anchor - 2 if idx + 1 < len(valid_anchors) else len(line)
                cell = line[start:end].strip() if start < len(line) else ""
                cell = re.sub(r"\s{2,}", " ", cell)
                cells.append(cell)

            if any(cells):
                # Multiline row continuation: if primary entity column (col 0) is empty and we have a preceding row,
                # all non-empty cells in this line are continuations of the corresponding cells in rows[-1]
                if rows and not cells[0]:
                    for idx, c in enumerate(cells):
                        if c:
                            if idx < len(rows[-1]):
                                rows[-1][idx] = (rows[-1][idx] + " " + c).strip()
                            else:
                                rows[-1].append(c)
                elif sum(1 for c in cells if c) == 1 and rows:
                    non_empty_idx = [i for i, c in enumerate(cells) if c][0]
                    if non_empty_idx < len(rows[-1]):
                        rows[-1][non_empty_idx] = (rows[-1][non_empty_idx] + " " + cells[non_empty_idx]).strip()
                else:
                    rows.append(cells)

        return rows

    @classmethod
    def extract_tables_from_layout(cls, text: str) -> str:
        """Converts detected multi-column layout table blocks into clean Markdown tables."""
        lines = text.split("\n")
        output: List[str] = []
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            cols = [c.strip() for c in re.split(r"\s{3,}|\t+", stripped) if c.strip()]
            is_struct = cls.is_prose_line(line)

            if len(cols) >= 2 and not is_struct and not stripped.startswith("|"):
                block = []
                j = i
                blank_cnt = 0
                while j < len(lines):
                    cur = lines[j]
                    cur_s = cur.strip()
                    if not cur_s:
                        blank_cnt += 1
                        if blank_cnt > 1:
                            break
                        j += 1
                        continue
                    blank_cnt = 0

                    if cls.is_prose_line(cur):
                        break

                    cur_cols = [c.strip() for c in re.split(r"\s{3,}|\t+", cur_s) if c.strip()]
                    if len(cur_cols) >= 2 or (len(cur_cols) == 1 and len(block) > 0 and len(cur_s) < 40):
                        block.append(cur)
                        j += 1
                    else:
                        break

                table_rows = cls.parse_table_block_anchors(block)
                if len(table_rows) >= 2 and cls.is_valid_table_header(table_rows[0]):
                    header = table_rows[0]
                    data_rows = table_rows[1:]

                    # Handle multiline header wrapped across 2 lines
                    if len(data_rows) > 1 and all(len(c.split()) <= 2 for c in data_rows[0] if c):
                        r1 = data_rows[0]
                        has_numeric_data = any(re.match(r"^[\$€£₹¥]?\s*\d+(?:\.\d+)?%?$", c.strip()) for c in r1 if c.strip())
                        has_data_label = any(re.match(r"^(?:Grade|Tier|Level|Band|Class)\s+[A-Z0-9]\b", c.strip(), re.IGNORECASE) for c in r1 if c.strip())
                        if not has_numeric_data and not has_data_label and any("Confirmed" in c or "Probation" in c or "Date" in c or "Grade" in c for c in r1):
                            header = [f"{h} {r1[idx]}".strip() if idx < len(r1) and r1[idx] else h for idx, h in enumerate(header)]
                            data_rows = data_rows[1:]

                    # Propagate vertically merged single-value columns across data rows
                    if len(data_rows) >= 2:
                        for c_idx in range(len(header)):
                            col_vals = [r[c_idx].strip() for r in data_rows if c_idx < len(r) and r[c_idx].strip()]
                            non_empty = [v for v in col_vals if v not in ("-", "—", "N/A", "n/a", "None", "nil")]
                            if len(non_empty) > 0 and len(set(non_empty)) == 1 and len(non_empty) < len(data_rows):
                                fill_val = non_empty[0]
                                for r in data_rows:
                                    while len(r) <= c_idx:
                                        r.append("")
                                    if not r[c_idx].strip():
                                        r[c_idx] = fill_val

                    header = [h if h else f"Col_{idx+1}" for idx, h in enumerate(header)]
                    output.append("")
                    output.append("| " + " | ".join(header) + " |")
                    output.append("| " + " | ".join(["---"] * len(header)) + " |")
                    for r in data_rows:
                        output.append("| " + " | ".join(r) + " |")
                    output.append("")
                    i = j
                    continue

            output.append(line)
            i += 1

        return "\n".join(output)

    @classmethod
    def normalize_headings_and_structure(cls, text: str) -> str:
        """Promotes unformatted numbered sections to Markdown heading levels (#, ##, ###)."""
        lines = text.split("\n")
        processed: List[str] = []
        for line in lines:
            s = line.strip()
            if not s:
                processed.append("")
                continue
            if s.startswith(("#", "|", ">", "---", "- ", "* ")):
                processed.append(s)
                continue

            # Detect inline subsection headers e.g. "3.2 Returns without a receipt Returns without proof of purchase..."
            m_inline = re.match(r"^(\d+\.\d+)\s+([A-Z][A-Za-z\s/&()-]{2,35}?)(?:\s{2,}|\s+)(?=[A-Z][a-z])(.*)$", s)
            if m_inline:
                sec_num = m_inline.group(1)
                title = m_inline.group(2).strip()
                rest = m_inline.group(3).strip()
                words = set(title.lower().split())
                verbs = {"is", "are", "shall", "must", "will", "can", "cannot", "has", "have", "should", "may", "covenants", "agrees"}
                if not (words & verbs) and len(rest.split()) >= 3:
                    processed.append(f"### {sec_num} {title}")
                    s = rest

            is_clause = bool(
                len(s.split()) > 10
                or s.endswith((".", ";"))
                or any(m in f" {s.lower()} " for m in (" shall ", " must ", " will ", " covenants ", " agrees ", " is required "))
            )

            # Level 2 sections: e.g. "3. Policy" -> "## 3. Policy"
            m_sec = re.match(r"^(\d+)\.\s+([A-Z].*)$", s)
            if m_sec and not is_clause:
                processed.append(f"## {m_sec.group(1)}. {m_sec.group(2)}")
                continue

            # Level 3 subsections: e.g. "3.1 Notice Periods Duration" -> "### 3.1 Notice Periods Duration"
            m_subsec = re.match(r"^(\d+\.\d+)\s+([A-Z].*)$", s)
            if m_subsec and not is_clause:
                processed.append(f"### {m_subsec.group(1)} {m_subsec.group(2)}")
                continue

            # Level 4 sub-subsections: e.g. "3.1.1 Something" -> "#### 3.1.1 Something"
            m_subsubsec = re.match(r"^(\d+\.\d+\.\d+)\s+([A-Z].*)$", s)
            if m_subsubsec and not is_clause:
                processed.append(f"#### {m_subsubsec.group(1)} {m_subsubsec.group(2)}")
                continue

            # Standard document structure title lines
            if s.lower() in (
                "statement of confidentiality",
                "table of contents",
                "policy summary",
                "document revision history",
                "document reviewers & approvers",
            ):
                processed.append(f"## {s.title()}")
                continue

            processed.append(s)

        return "\n".join(processed)

    @staticmethod
    def restructure(raw_text: str) -> str:
        if not raw_text:
            return ""

        # 1. Normalize unicode encoding artifacts and symbols
        text = (
            raw_text.replace("\ufffd", '"')
            .replace("“", '"')
            .replace("”", '"')
            .replace("’", "'")
            .replace("‘", "'")
        )

        # 2. Check if the document has page splits ("## Page ")
        if "## Page " not in text:
            tables_extracted = DocumentSemanticRestructurer.extract_tables_from_layout(text)
            return DocumentSemanticRestructurer.normalize_headings_and_structure(tables_extracted)

        # 3. Strip statistical running headers and footers across page boundaries
        from app.normalization.normalizer import DocumentNormalizer
        text_no_banners = DocumentNormalizer.strip_statistical_headers_footers(text)

        pages = text_no_banners.split("## Page ")
        doc_header = pages[0].strip()
        reconstructed_pages: List[str] = []

        for p_str in pages[1:]:
            lines = p_str.split("\n", 1)
            page_num = lines[0].strip()
            page_body = lines[1] if len(lines) > 1 else ""

            # Universal layout table extraction
            tbl_converted = DocumentSemanticRestructurer.extract_tables_from_layout(page_body)
            # Universal heading hierarchy standardization
            norm_body = DocumentSemanticRestructurer.normalize_headings_and_structure(tbl_converted)

            reconstructed_pages.append(f"## Page {page_num}\n\n{norm_body.strip()}")

        title_header = (doc_header + "\n\n") if doc_header else "# Document\n\n"
        combined = title_header + "\n\n".join(reconstructed_pages)
        return DocumentSemanticRestructurer.merge_multipage_markdown_tables(combined)

    @classmethod
    def merge_multipage_markdown_tables(cls, text: str) -> str:
        """
        Detects tables split across '## Page N' markers where the second table immediately
        follows the page marker (with identical header or matching column count) and stitches
        them into a single continuous Markdown table while preserving page comments.
        """
        if not text or "## Page " not in text:
            return text

        lines = text.split("\n")
        out: List[str] = []
        i = 0
        last_table_headers: Optional[List[str]] = None

        def _is_tbl_line(l: str) -> bool:
            s = l.strip()
            return s.startswith("|") and s.endswith("|") and s.count("|") >= 2

        def _is_sep_line(l: str) -> bool:
            s = l.strip()
            if not _is_tbl_line(s):
                return False
            cells = [c.strip() for c in s.strip("|").split("|")]
            return all(re.match(r"^:?-+:?$", c) for c in cells if c)

        def _split_row(l: str) -> List[str]:
            return [c.strip() for c in l.strip().strip("|").split("|")]

        while i < len(lines):
            cur = lines[i]
            if _is_tbl_line(cur):
                if not _is_sep_line(cur) and (i + 1 < len(lines) and _is_sep_line(lines[i + 1])):
                    last_table_headers = _split_row(cur)
                out.append(cur)
                i += 1
                continue

            # Detect page break immediately after a table
            if last_table_headers and cur.strip().startswith("## Page "):
                # Look ahead past blank lines and page header
                j = i + 1
                while j < len(lines) and not lines[j].strip():
                    j += 1
                if j < len(lines) and _is_tbl_line(lines[j]):
                    cand_row = _split_row(lines[j])
                    has_sep = (j + 1 < len(lines) and _is_sep_line(lines[j + 1]))
                    if has_sep and [c.lower() for c in cand_row] == [c.lower() for c in last_table_headers]:
                        # Repeated header across page break: drop the repeated page header + table header + sep
                        # Ensure previous trailing blank lines in out are stripped so table rows stay contiguous
                        while out and not out[-1].strip():
                            out.pop()
                        i = j + 2
                        continue
                    elif not has_sep and len(cand_row) == len(last_table_headers):
                        # Direct row continuation across page break
                        while out and not out[-1].strip():
                            out.pop()
                        i = j
                        continue
                last_table_headers = None
            elif cur.strip():
                last_table_headers = None

            out.append(cur)
            i += 1

        return "\n".join(out)

    @classmethod
    def reconstruct_tables_from_word_boxes(
        cls,
        word_boxes: List[Dict[str, Any]],
        y_tolerance: float = 10.0,
        x_cluster_gap: float = 25.0,
    ) -> str:
        """
        Reconstructs spatially aligned text lines and Markdown tables from OCR / PDF word bounding boxes.
        Each item in word_boxes should contain {'text': str, 'bbox': [x1, y1, x2, y2]}
        (or polygon [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]).
        Handles skewed rows via y-center clustering and columns via x-start clustering.
        """
        if not word_boxes:
            return ""

        norm_items: List[Dict[str, Any]] = []
        for item in word_boxes:
            txt = str(item.get("text") or "").strip()
            bbox = item.get("bbox")
            if not txt or not bbox:
                continue
            if isinstance(bbox[0], (list, tuple)):
                xs = [float(pt[0]) for pt in bbox]
                ys = [float(pt[1]) for pt in bbox]
                x1, y1, x2, y2 = min(xs), min(ys), max(xs), max(ys)
            else:
                x1, y1, x2, y2 = float(bbox[0]), float(bbox[1]), float(bbox[2]), float(bbox[3])
            norm_items.append({
                "text": txt,
                "x1": x1,
                "x2": x2,
                "y_center": (y1 + y2) / 2.0,
                "height": max(1.0, y2 - y1),
            })

        if not norm_items:
            return ""

        # Adaptive y tolerance based on median line height
        heights = sorted(it["height"] for it in norm_items)
        med_h = heights[len(heights) // 2]
        eff_y_tol = max(y_tolerance, med_h * 0.55)

        # Sort vertically and cluster into rows
        norm_items.sort(key=lambda it: (it["y_center"], it["x1"]))
        line_clusters: List[List[Dict[str, Any]]] = []
        for it in norm_items:
            if not line_clusters or abs(it["y_center"] - line_clusters[-1][0]["y_center"]) > eff_y_tol:
                line_clusters.append([it])
            else:
                line_clusters[-1].append(it)

        # Render spatially-aligned lines preserving true horizontal X-coordinates
        min_x = min(it["x1"] for it in norm_items)
        char_px = max(5.0, min(14.0, med_h * 0.45))
        rendered_lines: List[str] = []
        for cluster in line_clusters:
            cluster.sort(key=lambda it: it["x1"])
            line_buf: List[str] = []
            cur_len = 0
            prev_x2 = min_x
            for it in cluster:
                gap_px = max(0.0, it["x1"] - prev_x2)
                target_col = max(cur_len, int(round((it["x1"] - min_x) / char_px)))
                if line_buf:
                    if gap_px >= x_cluster_gap:
                        spaces = max(4, target_col - cur_len)
                    else:
                        spaces = 1
                    line_buf.append(" " * spaces)
                    cur_len += spaces
                elif target_col > 0 and (it["x1"] - min_x) >= x_cluster_gap:
                    line_buf.append(" " * target_col)
                    cur_len += target_col
                line_buf.append(it["text"])
                cur_len += len(it["text"])
                prev_x2 = max(prev_x2, it["x2"])
            rendered_lines.append("".join(line_buf))

        raw_layout = "\n".join(rendered_lines)
        return cls.extract_tables_from_layout(raw_layout)

    @classmethod
    def extract_native_pdf_page_layout(
        cls,
        fitz_page: Any,
        page_num: int,
    ) -> Tuple[Optional[str], List[Dict[str, Any]]]:
        """
        Reconstructs native-text PDF page layout using PyMuPDF ruling lines,
        cell boundaries, and word coordinates when tables are detected.
        Returns (markdown_page_text, extracted_tables_metadata) or (None, [])
        when no tables are detected so callers fall back to standard layout flow.
        """
        try:
            tabs = fitz_page.find_tables()
        except Exception:
            return None, []

        detected_tables = getattr(tabs, "tables", None) or []
        if not detected_tables:
            return None, []

        table_bboxes = [tuple(t.bbox) for t in detected_tables]
        items: List[Tuple[float, str]] = []
        tables_meta: List[Dict[str, Any]] = []

        # 1. Extract non-table text blocks in reading order
        try:
            blocks = fitz_page.get_text("blocks") or []
        except Exception:
            blocks = []

        for blk in blocks:
            if len(blk) < 7 or blk[6] != 0:
                continue
            bx0, by0, bx1, by1, btext = float(blk[0]), float(blk[1]), float(blk[2]), float(blk[3]), str(blk[4] or "")
            if not btext.strip():
                continue
            cx = (bx0 + bx1) / 2.0
            cy = (by0 + by1) / 2.0
            inside_table = any(
                (tb[0] - 2.0) <= cx <= (tb[2] + 2.0) and (tb[1] - 1.0) <= cy <= (tb[3] + 1.0)
                for tb in table_bboxes
            )
            if inside_table:
                continue
            clean_lines = [re.sub(r"\s+", " ", ln).strip() for ln in btext.splitlines() if ln.strip()]
            if clean_lines:
                items.append((by0, "\n".join(clean_lines)))

        # 2. Extract each table preserving cell boundaries, empty cells, and wrapped text
        kv_header_labels = {"key", "field", "attribute", "property", "parameter", "item", "label", "name", "setting"}
        known_kv_first_rows = {
            "policy title", "document title", "document number", "policy number",
            "version", "status", "effective date", "next review date", "review date",
            "policy owner", "owner", "approving body", "applies to", "classification",
        }

        for t_idx, t in enumerate(detected_tables, start=1):
            try:
                raw_rows = t.extract() or []
            except Exception:
                continue

            cleaned_rows: List[List[str]] = []
            for r in raw_rows:
                c_row = [re.sub(r"\s+", " ", str(c or "").replace("\n", " ")).strip() for c in r]
                if any(c_row):
                    cleaned_rows.append(c_row)

            if not cleaned_rows:
                continue

            col_count = max(len(r) for r in cleaned_rows)
            norm_rows = [r + [""] * (col_count - len(r)) for r in cleaned_rows]

            # Detect headerless 2-column key-value tables so row 0 is not lost as a header
            if col_count == 2 and len(norm_rows) >= 2:
                r0_k = norm_rows[0][0].strip().lower()
                r0_v = norm_rows[0][1].strip()
                is_explicit_kv_hdr = r0_k in kv_header_labels and r0_v.lower() in {"value", "details", "description", "content"}
                looks_like_data_row0 = (
                    r0_k in known_kv_first_rows
                    or (r0_k not in kv_header_labels and (len(r0_v) > 25 or bool(re.search(r"\d", r0_v))))
                )
                if not is_explicit_kv_hdr and looks_like_data_row0:
                    norm_rows.insert(0, ["Key", "Value"])

            if len(norm_rows) < 2:
                continue

            header = [h if h else f"Col_{i+1}" for i, h in enumerate(norm_rows[0])]
            data_rows = norm_rows[1:]
            md_lines = [
                "| " + " | ".join(header) + " |",
                "| " + " | ".join(["---"] * len(header)) + " |",
            ]
            for dr in data_rows:
                md_lines.append("| " + " | ".join(dr) + " |")

            items.append((float(t.bbox[1]), "\n".join(md_lines)))
            tables_meta.append({
                "table_id": f"pdf_p{page_num}_t{t_idx}",
                "page_number": page_num,
                "bbox": [float(v) for v in t.bbox],
                "headers": header,
                "row_count": len(data_rows),
                "extraction_method": "pymupdf_spatial",
            })

        if not tables_meta:
            return None, []

        items.sort(key=lambda x: x[0])
        return "\n\n".join(txt for _, txt in items), tables_meta


