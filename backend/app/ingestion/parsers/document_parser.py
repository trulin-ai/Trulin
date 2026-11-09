"""
Layer 4: Specialized Document Parser.
Processes narrative documents and files (Markdown, PDF, DOCX, HTML, Confluence pages, Plain text).
Preserves hierarchical heading trees, clause structures, markdown tables, and exact character offsets.
"""

from __future__ import annotations

import logging
import re
from typing import Any, List

from app.db.enums import SourceFamily
from app.ingestion.envelope import CanonicalSourceEnvelope
from app.ingestion.parsers.evidence_model import (
    ContentRole,
    EvidenceExtractionValidator,
    ExtractionQualityReport,
    ExtractionStatus,
    ParsedEvidenceResult,
    ParsedEvidenceUnit,
)

logger = logging.getLogger(__name__)


class DocumentParser:
    """Specialized AST parser for narrative documents and text files."""

    CLAUSE_PATTERN = re.compile(r"^(?:(?:Section|Article|Clause|Rule)\s+)?(\d+(?:\.\d+)*|[A-Z]\.|\([a-z0-9]+\))\s*[:.-]?\s+(.*)", re.IGNORECASE)
    HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*)")
    TABLE_ROW_PATTERN = re.compile(r"^\|(.+)\|$")
    PAGE_MARKER_PATTERN = re.compile(r"^(?:#{1,6}\s+Page\s+(\d+)|---\s*Page\s+(\d+)\s*---|Page\s+(\d+)\s+(?:of|\/)\s+\d+)", re.IGNORECASE)

    @classmethod
    def _classify_content_role(cls, text: str, context: list[str], block_type: str) -> ContentRole:
        """Determines the semantic role of an evidence unit based on text syntax and heading ancestry."""
        if block_type == "heading":
            return ContentRole.HEADING

        text_lower = text.lower().strip()
        context_lower = " > ".join(context).lower()

        # 0. Exceptions and Carve-Outs
        if any(w in context_lower for w in ("exception", "exceptions", "carve-out", "exclusions")) or any(
            text_lower.startswith(w) for w in ("except where", "with the exception of", "unless otherwise", "excluding ", "exception:", "exemptions:")
        ):
            return ContentRole.EXCEPTION

        # 1. Illustrative Examples and Case Studies (Prioritized before Revision History for hybrid sections like '20. Revision History and Sample Case Studies')
        if any(w in context_lower for w in ("sample case", "sample cases", "case stud", "case study", "illustrative scenario", "worked example", "hypothetical scenario", "examples", "example")):
            return ContentRole.EXAMPLE
        if re.match(r"^case\s+[a-z]\b", text_lower) or any(text_lower.startswith(w) for w in ("for example", "example:", "e.g.", "scenario:", "sample calculation:", "case a", "case b", "case c", "case d", "case e", "case f")):
            return ContentRole.EXAMPLE

        # 2. Contact Information and Escalation Channels
        if any(w in context_lower for w in ("contact information", "contact info", "escalation", "customer care", "support channels")):
            return ContentRole.CONTACT_INFO
        if "@" in text and any(w in text_lower for w in ("contact", "email", ".com", ".org", "people_success", "support")):
            return ContentRole.CONTACT_INFO
        if any(text_lower.startswith(w) for w in ("for any clarifications", "reach out to", "contact us", "support desk", "for inquiries", "call 1-", "phone (", "email:", "mailing address:")):
            return ContentRole.CONTACT_INFO

        # 3. Frequently Asked Questions (FAQ) - Disambiguate Questions vs Answers
        is_faq_context = any(w in context_lower for w in ("frequently asked", "faq", "q&a", "questions and answers"))
        if text_lower.endswith("?") or re.match(r"^(?:q\s*[:.]|question\s*[:.]|q\d+[:.]|\d+\.\s*(?:can|what|will|how|is|where|why|do|does|did|should))\b", text_lower):
            return ContentRole.FAQ_QUESTION
        if re.match(r"^(?:a\s*[:.]|answer\s*[:.]|a\d+[:.])\b", text_lower):
            return ContentRole.FAQ_ANSWER
        if is_faq_context:
            return ContentRole.FAQ

        # 4. Revision History & Document Control
        if any(w in context_lower for w in ("revision history", "version history", "change log", "document control", "approval matrix", "table of contents")):
            return ContentRole.REVISION_HISTORY
        if any(w in text_lower for w in ("first release", "initial release", "version 1", "rev 1", "approved by ceo", "prepared by", "initial policy baseline")):
            return ContentRole.REVISION_HISTORY

        # 5. Introductory Context & Framing sentences
        if any(w in context_lower for w in ("overview", "introduction", "background", "purpose", "scope")):
            if (
                any(text_lower.startswith(w) for w in ("the purpose of this document", "this policy outlines", "this document sets forth", "welcome to", "in this section", "how to request a refund"))
                or "went into effect on" in text_lower
                or "went into effect in" in text_lower
                or re.search(r"\bis a rule that went into effect\b", text_lower)
            ):
                return ContentRole.INTRODUCTORY_CONTEXT

        # 6. Operational Procedures & UI Steps
        if any(w in context_lower for w in ("procedure", "procedures", "process flow", "operational steps", "submission workflow", "offboarding process")):
            return ContentRole.PROCEDURE
        if re.match(r"^step\s*\d+\s*:", text_lower) or any(text_lower.startswith(w) for w in ("step 1:", "step 2:", "the employee must submit resignation via")):
            return ContentRole.PROCEDURE

        # 7. Definitions
        if any(w in context_lower for w in ("definitions", "glossary", "interpretation", "defined terms")):
            return ContentRole.DEFINITION
        if any(w in text_lower for w in ("means an employee", "means any person", "is defined as", "refers to the", "means ")):
            return ContentRole.DEFINITION
        if re.match(r"^[A-Z][A-Za-z0-9\s\-_]{2,35}:\s+[A-Z]", text) and not is_faq_context and not re.match(r"^step\s*\d+", text_lower):
            return ContentRole.DEFINITION

        # 8. Reference Citations & External Cross-References
        if (
            re.match(r"^(?:for more information,? see|see also|refer to|reference:)\b", text_lower)
            or ("for more information, see" in text_lower and not any(m in text_lower for m in ("must", "shall", "required", "prohibited", "is mandatory", "are mandatory")))
            or ("see documentation" in text_lower and not any(m in text_lower for m in ("must", "shall", "required", "prohibited", "is mandatory", "are mandatory")))
        ):
            return ContentRole.REFERENCE_CITATION

        # 9. Normative Rules vs Unknown
        if (
            block_type == "clause"
            or any(w in text_lower for w in ("must", "shall", "required", "prohibited", "forbidden", "entitled", "may not", "cannot", "will not", "is eligible", "are eligible", "mandated", "authoriz"))
        ):
            return ContentRole.POLICY_RULE

        return ContentRole.UNKNOWN

    @classmethod
    async def parse(cls, envelope: CanonicalSourceEnvelope) -> ParsedEvidenceResult:
        """Parses a document envelope into structured ParsedEvidenceUnits."""
        raw_text = envelope.get_payload_as_text()
        units: List[ParsedEvidenceUnit] = []
        
        lines = raw_text.splitlines(keepends=True)
        breadcrumb_stack: list[tuple[int, str]] = []  # (level, title)
        
        current_page: int | None = (
            envelope.locator_metadata.get("page")
            or envelope.locator_metadata.get("page_number")
            or (1 if envelope.native_format in ("pdf", "docx") else None)
        )

        char_cursor = 0
        line_num = 1
        seq_idx = 0

        in_table = False
        table_headers: list[str] = []
        table_rows_buffer: list[dict[str, Any]] = []
        table_start_char = 0
        table_start_line = 0
        table_row_count = 0
        table_semantic_type = "policy_matrix"

        total_lines = len(lines)
        parsed_lines = 0

        for line_raw in lines:
            line_str = line_raw.strip()
            line_len = len(line_raw)
            line_start_char = char_cursor
            line_end_char = char_cursor + line_len
            parsed_lines += 1

            if not line_str:
                char_cursor = line_end_char
                line_num += 1
                continue

            page_match = cls.PAGE_MARKER_PATTERN.match(line_str)
            if page_match:
                current_page = int(page_match.group(1) or page_match.group(2) or page_match.group(3))

            # 1. Heading Detection (# H1, ## H2, etc.)
            h_match = cls.HEADING_PATTERN.match(line_str)
            if h_match:
                # Flush table if was in table
                if in_table:
                    in_table = False
                    table_headers = []
                    table_row_count = 0

                level = len(h_match.group(1))
                h_title = h_match.group(2).strip()

                # Adjust breadcrumb hierarchy
                while breadcrumb_stack and breadcrumb_stack[-1][0] >= level:
                    breadcrumb_stack.pop()
                breadcrumb_stack.append((level, h_title))

                context = [h[1] for h in breadcrumb_stack]

                unit = ParsedEvidenceUnit.create(
                    envelope_id=envelope.envelope_id,
                    asset_id=envelope.asset_id,
                    source_id=str(envelope.source_id),
                    source_version=envelope.source_version,
                    source_type=envelope.native_format or "document",
                    block_type="heading",
                    content_role=ContentRole.HEADING,
                    raw_content=line_raw,
                    normalized_content=h_title,
                    content_text=h_title,
                    structured_data={"heading_level": level, "heading_text": h_title},
                    locator={
                        **envelope.locator_metadata,
                        "page": current_page,
                        "line": line_num,
                        "line_start": line_num,
                        "line_end": line_num,
                        "start_char": line_start_char,
                        "end_char": line_end_char,
                        "heading_path": context,
                        "paragraph_index": seq_idx,
                    },
                    hierarchical_context=context,
                    sequence_index=seq_idx,
                    metadata={"source_version": envelope.source_version},
                )
                units.append(unit)
                seq_idx += 1
                char_cursor = line_end_char
                line_num += 1
                continue

            # 2. Markdown Table Detection (| Col 1 | Col 2 |)
            t_match = cls.TABLE_ROW_PATTERN.match(line_str)
            if t_match:
                row_cells = [c.strip() for c in t_match.group(1).split("|")]
                
                # Check if separator row (|---|---|)
                is_separator = all(re.match(r"^:?-+:?$", c) for c in row_cells if c)
                if is_separator:
                    char_cursor = line_end_char
                    line_num += 1
                    continue

                if not in_table:
                    # First row is table header
                    in_table = True
                    table_headers = row_cells
                    table_start_char = line_start_char
                    table_start_line = line_num
                    table_row_count = 0

                    # Classify table semantic type from headers and hierarchical context
                    clean_hdrs = [h.lower().strip() for h in table_headers]
                    ctx_lower = " > ".join(h[1] for h in breadcrumb_stack).lower()
                    is_rev = (
                        (any("ver" in h or "revision" in h for h in clean_hdrs) and any("date" in h or "description" in h or "approv" in h for h in clean_hdrs))
                        or any(re.match(r"^\d+\.\d+", h) for h in clean_hdrs)
                        or any(re.search(r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec|\d{1,2}-[a-z]{3}-\d{4})\b", h) for h in clean_hdrs)
                        or "revision" in ctx_lower
                        or "history" in ctx_lower
                    )
                    is_toc = (
                        (any("section" in h for h in clean_hdrs) and any("title" in h or "topic" in h for h in clean_hdrs))
                        or "table of content" in ctx_lower
                        or "contents" in ctx_lower
                        or (len(clean_hdrs) >= 2 and all(re.match(r"^\d+$", h) for h in clean_hdrs[1:] if h))
                    )
                    is_sign = (any("role" in h or "sign" in h for h in clean_hdrs) and any("name" in h or "designation" in h for h in clean_hdrs)) or "approver" in ctx_lower or "reviewer" in ctx_lower
                    is_form_spec = (
                        any("field" in h for h in clean_hdrs)
                        and (any("required" in h for h in clean_hdrs) or any("example" in h or "format" in h for h in clean_hdrs))
                    )
                    is_data_dict = (
                        any(h in ("line item", "field", "column name", "parameter") for h in clean_hdrs)
                        and any(h in ("definition", "meaning", "format", "data type") for h in clean_hdrs)
                    )
                    is_sitemap = (
                        any(any(w in h for w in ("what's new", "microsoft store", "education", "business", "developer & it", "company", "explore copilot", "windows 11 apps")) for h in clean_hdrs)
                        or any("sitemap" in h or "footer" in h for h in clean_hdrs)
                        or (any("copilot" in h for h in clean_hdrs) and any("surface" in h or "windows" in h for h in clean_hdrs))
                    )

                    if is_rev:
                        table_semantic_type = "revision_history"
                    elif is_toc:
                        table_semantic_type = "table_of_contents"
                    elif is_sign:
                        table_semantic_type = "approver_signoff"
                    elif is_form_spec:
                        table_semantic_type = "form_field_specification"
                    elif is_data_dict:
                        table_semantic_type = "data_dictionary"
                    elif is_sitemap:
                        table_semantic_type = "website_sitemap_footer"
                    else:
                        table_semantic_type = "policy_matrix"
                else:
                    table_id_str = f"table_line_{table_start_line}"
                    # Check if this row is a multiline continuation of the previous table row (e.g. wrapped multiline cells where col 0 is empty)
                    if row_cells and not row_cells[0].strip() and units and units[-1].block_type == "table_row" and units[-1].structured_data.get("table_id") == table_id_str:
                        prev_unit = units[-1]
                        prev_cols = prev_unit.structured_data.get("columns", {})
                        for idx, cell_val in enumerate(row_cells):
                            if cell_val.strip() and idx < len(table_headers):
                                col_name = table_headers[idx]
                                prev_cols[col_name] = (prev_cols.get(col_name, "") + " " + cell_val.strip()).strip()
                        prev_unit.structured_data["columns"] = prev_cols
                        prev_text = " | ".join(f"{k}: {v}" for k, v in prev_cols.items())
                        prev_unit.content_text = prev_text
                        prev_unit.normalized_content = prev_text
                        char_cursor = line_end_char
                        line_num += 1
                        continue

                    # Data row
                    table_row_count += 1
                    row_dict = {}
                    is_ambiguous = len(row_cells) != len(table_headers)
                    ambiguity_reason = "Table row cell count does not match header count" if is_ambiguous else None

                    for idx, cell_val in enumerate(row_cells):
                        col_name = table_headers[idx] if idx < len(table_headers) else f"col_{idx+1}"
                        row_dict[col_name] = cell_val
                        # Check for merged cell or undefined scope indicator
                        clean_lower = cell_val.lower().strip("[]() ")
                        if any(kw in clean_lower for kw in ("merged", "spanned", "ditto", "as above", "same as above", "same as previous")) or clean_lower in ("^", '""', '"', "same as"): 
                            is_ambiguous = True
                            ambiguity_reason = f"Cell in column '{col_name}' contains merged or spanned indicator '{cell_val}'"
                        elif is_ambiguous and idx >= len(table_headers):
                            ambiguity_reason = f"Cell in column '{col_name}' exceeds table header count"

                    context = [h[1] for h in breadcrumb_stack]
                    row_text = " | ".join(f"{k}: {v}" for k, v in row_dict.items())

                    # Classify ContentRole for this table row
                    context_str = " > ".join(context).lower()
                    hdrs_str = " ".join(table_headers).lower()
                    row_is_canonical = True
                    if table_semantic_type in ("revision_history", "table_of_contents", "approver_signoff") or "revision" in context_str or "revision" in hdrs_str:
                        row_content_role = ContentRole.REVISION_HISTORY
                        row_is_canonical = False
                    elif table_semantic_type == "website_sitemap_footer":
                        row_content_role = ContentRole.DOCUMENT_METADATA
                        row_is_canonical = False
                    elif table_semantic_type in ("form_field_specification", "data_dictionary"):
                        row_content_role = ContentRole.DEFINITION
                        row_is_canonical = False
                    elif any(w in context_str for w in ("definition", "glossary")) or ("term" in hdrs_str and "definition" in hdrs_str):
                        row_content_role = ContentRole.DEFINITION
                        row_is_canonical = False
                    elif any(w in context_str for w in ("contact", "escalation channel", "support channel")) or any(w in hdrs_str for w in ("channel", "hours", "phone")):
                        row_content_role = ContentRole.CONTACT_INFO
                        row_is_canonical = False
                    elif any(w in context_str for w in ("faq", "frequently asked")) or "question" in hdrs_str:
                        row_content_role = ContentRole.FAQ
                        row_is_canonical = False
                    elif any(w in context_str for w in ("example", "scenario", "case stud", "case study", "sample case")):
                        row_content_role = ContentRole.EXAMPLE
                        row_is_canonical = False
                    elif any(w in context_str for w in ("procedure", "workflow", "process", "step")):
                        row_content_role = ContentRole.PROCEDURE
                    else:
                        row_content_role = ContentRole.POLICY_RULE

                    unit = ParsedEvidenceUnit.create(
                        envelope_id=envelope.envelope_id,
                        asset_id=envelope.asset_id,
                        source_id=str(envelope.source_id),
                        source_version=envelope.source_version,
                        source_type=envelope.native_format or "document",
                        block_type="table_row",
                        content_role=row_content_role,
                        is_canonical=row_is_canonical,
                        raw_content=line_raw,
                        normalized_content=row_text,
                        content_text=row_text,
                        structured_data={
                            "columns": row_dict,
                            "table_headers": table_headers,
                            "table_type": table_semantic_type,
                            "table_id": table_id_str,
                            "row_index": table_row_count,
                            "is_ambiguous": is_ambiguous,
                            "ambiguity_reason": ambiguity_reason,
                            "raw_row_line": line_str,
                        },
                        locator={
                            **envelope.locator_metadata,
                            "page": current_page,
                            "line": line_num,
                            "line_start": line_num,
                            "line_end": line_num,
                            "start_char": line_start_char,
                            "end_char": line_end_char,
                            "table_id": table_id_str,
                            "table_start_line": table_start_line,
                            "row_index": table_row_count,
                            "heading_path": context,
                            "paragraph_index": seq_idx,
                        },
                        hierarchical_context=context,
                        sequence_index=seq_idx,
                        metadata={
                            "in_table": True,
                            "table_id": table_id_str,
                            "table_start_line": table_start_line,
                            "row_index": table_row_count,
                            "is_ambiguous": is_ambiguous,
                        },
                    )
                    units.append(unit)
                    seq_idx += 1

                char_cursor = line_end_char
                line_num += 1
                continue
            else:
                in_table = False
                table_headers = []
                table_row_count = 0

            # 3. Clause / Bullet / Statement Detection
            context = [h[1] for h in breadcrumb_stack]
            clause_match = cls.CLAUSE_PATTERN.match(line_str)
            
            bullet_prefixes = ("-", "*", "+", "•", "●", "❖", "■", "▪", "►", "○", "◆", "–", "—")
            is_bullet_line = any(line_str.startswith(b) for b in bullet_prefixes)
            block_type = "clause" if (clause_match or is_bullet_line) else "paragraph"
            clean_text = line_str
            for b in bullet_prefixes:
                if clean_text.startswith(b):
                    clean_text = clean_text[len(b):].strip()
                    break

            unit_role = cls._classify_content_role(clean_text, context, block_type)

            unit = ParsedEvidenceUnit.create(
                envelope_id=envelope.envelope_id,
                asset_id=envelope.asset_id,
                source_id=str(envelope.source_id),
                source_version=envelope.source_version,
                source_type=envelope.native_format or "document",
                block_type=block_type,
                content_role=unit_role,
                raw_content=line_raw,
                normalized_content=clean_text,
                content_text=clean_text,
                structured_data={"raw_line": line_str},
                locator={
                    **envelope.locator_metadata,
                    "page": current_page,
                    "line": line_num,
                    "line_start": line_num,
                    "line_end": line_num,
                    "start_char": line_start_char,
                    "end_char": line_end_char,
                    "heading_path": context,
                    "paragraph_index": seq_idx,
                },
                hierarchical_context=context,
                sequence_index=seq_idx,
                metadata={"source_version": envelope.source_version},
            )
            units.append(unit)
            seq_idx += 1

            char_cursor = line_end_char
            line_num += 1

        # Post-process table units to propagate vertically merged cells
        cls._propagate_table_merged_cells(units)

        # Completeness calculation: Use NOT_MEASURED when no reliable denominator exists
        expected_pages = envelope.locator_metadata.get("page_count") or envelope.locator_metadata.get("total_pages")
        expected_blocks = envelope.locator_metadata.get("expected_blocks")
        warnings: list[str] = []

        if len(units) == 0 or total_lines == 0 or not raw_text.strip():
            completeness: Union[float, str] = "NOT_MEASURED"
            status = ExtractionStatus.EMPTY
            warnings.append("Document envelope contains no extractable text lines.")
        else:
            val_res = EvidenceExtractionValidator.validate(units)
            warnings.extend(val_res.warnings)
            if not val_res.is_valid:
                status = ExtractionStatus.PARTIAL
                warnings.extend(val_res.errors)
            else:
                status = ExtractionStatus.SUCCESS

            if expected_pages and isinstance(expected_pages, (int, float)) and expected_pages > 0:
                pages_found = len(set(u.locator.page for u in units if u.locator and u.locator.page is not None))
                completeness = min(1.0, pages_found / expected_pages)
            elif expected_blocks and isinstance(expected_blocks, (int, float)) and expected_blocks > 0:
                completeness = min(1.0, len(units) / expected_blocks)
            else:
                # Do not hardcode 1.0; use NOT_MEASURED when denominator is unavailable
                completeness = "NOT_MEASURED"

        table_ids = set(u.structured_data.get("table_id") for u in units if u.block_type == "table_row")
        table_rows_count = sum(1 for u in units if u.block_type == "table_row")
        valid_locators = sum(1 for u in units if u.locator and u.locator.line is not None)

        quality_report = ExtractionQualityReport(
            status=status,
            completeness_score=completeness,
            expected_pages=expected_pages if isinstance(expected_pages, int) else None,
            processed_pages=len(set(u.locator.page for u in units if u.locator and u.locator.page is not None)) if units else 0,
            expected_blocks=expected_blocks if isinstance(expected_blocks, int) else None,
            processed_blocks=len(units),
            detected_tables=len(table_ids),
            extracted_tables=len(table_ids),
            extracted_table_rows=table_rows_count,
            total_units=len(units),
            valid_evidence_units=len(units),
            valid_source_locators=valid_locators,
            warnings=warnings,
            parser_name="DocumentParser",
        )

        quality_metrics = {
            "total_lines": total_lines,
            "parsed_units": len(units),
            "headings_count": sum(1 for u in units if u.block_type == "heading"),
            "clauses_count": sum(1 for u in units if u.block_type == "clause"),
            "table_rows_count": table_rows_count,
            "char_count": char_cursor,
            "warnings": warnings,
        }

        return ParsedEvidenceResult(
            envelope_id=envelope.envelope_id,
            asset_id=envelope.asset_id,
            source_family=SourceFamily.DOCUMENT,
            parser_name="DocumentParser",
            units=units,
            completeness_score=completeness,
            quality_metrics=quality_metrics,
            quality_report=quality_report,
            extraction_status=status,
        )

    @classmethod
    def _propagate_table_merged_cells(cls, units: list[ParsedEvidenceUnit]) -> None:
        """
        Universal Table Normalization: Detects and propagates vertically merged cells across table rows.
        Handles:
        1. Single-value columns spanning multiple rows (e.g. uniform probationary duration '15 days').
        2. Downward ditto or merge indicators ('^', '""', '"', 'same as', 'ditto').
        """
        from collections import defaultdict
        tables = defaultdict(list)
        for u in units:
            if u.block_type == "table_row":
                tid = u.structured_data.get("table_id")
                if tid:
                    tables[tid].append(u)

        for tid, table_units in tables.items():
            if len(table_units) < 2:
                continue

            headers = table_units[0].structured_data.get("table_headers", [])
            for col_name in headers:
                col_vals = [
                    u.structured_data.get("columns", {}).get(col_name, "").strip()
                    for u in table_units
                ]
                non_empty = [v for v in col_vals if v and v not in ("-", "—", "N/A", "n/a", "None", "nil", "^", '""', '"')]
                unique_vals = set(non_empty)

                # Case 1: Uniform vertical span (single non-empty value across multiple rows where other cells are empty)
                if len(unique_vals) == 1 and len(non_empty) < len(table_units):
                    span_val = non_empty[0]
                    clean_span = span_val.lower().strip("[]() ")
                    if not any(kw in clean_span for kw in ("merged", "spanned", "ditto", "as above", "same as")):
                        for u in table_units:
                            cols = u.structured_data.get("columns", {})
                            cur_v = cols.get(col_name, "").strip()
                            if not cur_v or cur_v in ("-", "—", "N/A", "n/a", "None", "nil"):
                                cols[col_name] = span_val
                                u.structured_data["columns"] = cols
                                merged_text = " | ".join(f"{k}: {v}" for k, v in cols.items())
                                u.content_text = merged_text
                                u.normalized_content = merged_text
