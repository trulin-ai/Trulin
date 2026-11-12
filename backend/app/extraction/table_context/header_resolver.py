"""
Header Context and Relationship Resolution (Section 6).

Interprets single-level, multi-level, and grouped column headers, row headers,
embedded units/currencies, header-level conditions, and footnote markers.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from app.extraction.table_context.models import HeaderHierarchy, HeaderNode
from app.extraction.table_context.normalizer import CURRENCY_CODES, TableValueNormalizer


class HeaderContextResolver:
    """Resolves header hierarchies, units, conditions, and scope vs rule column roles."""

    SCOPE_KEYWORDS = (
        "level", "grade", "group", "role", "tier", "department", "category",
        "scope", "customer", "employee", "plan", "product", "item", "region",
        "country", "status", "stage", "channel", "method", "type", "metric",
        "code", "reason", "user", "account", "entity", "parameter", "field",
    )

    CONDITION_PATTERNS = [
        re.compile(r"^(within\s+\d+\s*(?:days?|hours?|months?|years?|weeks?))$", re.IGNORECASE),
        re.compile(r"^(after\s+\d+\s*(?:days?|hours?|months?|years?|weeks?))$", re.IGNORECASE),
        re.compile(r"^(before\s+.*)$", re.IGNORECASE),
        re.compile(r"^(if\s+.*)$", re.IGNORECASE),
        re.compile(r"^(when\s+.*)$", re.IGNORECASE),
        re.compile(r"^(under\s+.*)$", re.IGNORECASE),
        re.compile(r"^(over\s+.*)$", re.IGNORECASE),
        re.compile(r"^(during\s+.*)$", re.IGNORECASE),
        re.compile(r"^(upon\s+.*)$", re.IGNORECASE),
        re.compile(r"^(probation(?:ers|ary)?)$", re.IGNORECASE),
        re.compile(r"^(confirmed(?:\s+employees?)?)$", re.IGNORECASE),
    ]

    UNIT_IN_PARENS_PAT = re.compile(r"\(([^)]+)\)")

    @classmethod
    def _extract_embedded_unit_and_currency(cls, header_text: str) -> tuple[Optional[str], Optional[str]]:
        """Extracts measurement unit or currency embedded in header labels, e.g. 'Refund Amount (USD)' or 'Days'."""
        unit: Optional[str] = None
        currency: Optional[str] = None

        for m in cls.UNIT_IN_PARENS_PAT.finditer(header_text or ""):
            inner = m.group(1).strip()
            inner_up = inner.upper()
            if inner_up in CURRENCY_CODES or inner in ("$", "€", "£", "₹"):
                currency = inner_up if inner_up in CURRENCY_CODES else {"$": "USD", "€": "EUR", "£": "GBP", "₹": "INR"}.get(inner)
                unit = currency
            elif inner.lower() in ("%", "percent", "percentage"):
                unit = "%"
            elif inner.lower() in ("days", "day", "hours", "hour", "months", "month", "years", "year", "weeks", "week", "minutes", "usd", "eur", "gbp"):
                unit = inner.lower()

        h_low = (header_text or "").strip().lower()
        if not unit:
            if h_low in ("days", "day count", "duration (days)") or h_low.endswith(" days"):
                unit = "days"
            elif h_low in ("hours", "hour"):
                unit = "hours"
            elif h_low in ("months", "month"):
                unit = "months"
            elif h_low in ("years", "year"):
                unit = "years"
            elif "%" in h_low or "percentage" in h_low:
                unit = "%"

        if not currency:
            for code in CURRENCY_CODES:
                if re.search(rf"\b{code}\b", header_text or "", re.IGNORECASE):
                    currency = code
                    break
            if not currency and "$" in (header_text or ""):
                currency = "USD"

        return unit, currency

    @classmethod
    def _extract_header_conditions(cls, header_text: str) -> List[str]:
        conds: List[str] = []
        clean = (header_text or "").strip()
        for pat in cls.CONDITION_PATTERNS:
            if pat.match(clean):
                conds.append(clean)
                break
        return conds

    @classmethod
    def resolve(
        cls,
        headers: List[str],
        raw_header_rows: Optional[List[List[str]]] = None,
        sample_rows: Optional[List[Dict[str, str]]] = None,
    ) -> HeaderHierarchy:
        """Resolves flat or multi-level headers into a structured HeaderHierarchy."""
        nodes: List[HeaderNode] = []
        has_grouped = bool(raw_header_rows and len(raw_header_rows) > 1)

        # Build parent map if multi-row headers exist
        parent_map: Dict[int, str] = {}
        if raw_header_rows and len(raw_header_rows) > 1:
            parent_row = raw_header_rows[-2]
            active_parent = ""
            for idx, cell in enumerate(parent_row):
                c_str = (cell or "").strip()
                if c_str:
                    active_parent = c_str
                if idx > 0 and active_parent:
                    parent_map[idx] = active_parent

        scope_cols: List[str] = []
        rule_cols: List[str] = []

        for idx, raw_hdr in enumerate(headers):
            raw_str = (raw_hdr or "").strip()
            body, markers = TableValueNormalizer.extract_footnote_markers(raw_str)

            parent_hdr: Optional[str] = None
            leaf_hdr = body
            header_path: List[str] = []

            if " > " in body:
                parts = [p.strip() for p in body.split(">") if p.strip()]
                if len(parts) >= 2:
                    parent_hdr = " > ".join(parts[:-1])
                    leaf_hdr = parts[-1]
                    header_path = parts
                    has_grouped = True
            elif idx in parent_map:
                p_cand = parent_map[idx]
                if p_cand.lower() != body.lower():
                    parent_hdr = p_cand
                    header_path = [p_cand, body]

            if not header_path:
                header_path = [leaf_hdr] if leaf_hdr else [raw_str]

            # Extract units/currency from both parent and leaf header
            leaf_unit, leaf_curr = cls._extract_embedded_unit_and_currency(leaf_hdr)
            parent_unit, parent_curr = cls._extract_embedded_unit_and_currency(parent_hdr or "")
            eff_unit = leaf_unit or parent_unit
            eff_curr = leaf_curr or parent_curr

            # Extract conditions from leaf header
            conds = cls._extract_header_conditions(leaf_hdr)

            # Determine scope vs rule role
            hdr_low = leaf_hdr.lower()
            sample_vals = [str(r.get(raw_str, "")).strip() for r in (sample_rows or []) if str(r.get(raw_str, "")).strip()]
            has_value_cells = bool(sample_vals) and all(
                bool(
                    re.match(r"^[RACI]$", sv)
                    or re.match(r"^[\$€£₹¥]?\s*-?\d", sv)
                    or re.match(r"^(?:yes|no|true|false|n/a|not applicable)$", sv, re.IGNORECASE)
                )
                for sv in sample_vals
            )

            is_numeric_step_col = (
                idx == 0
                and len(headers) >= 2
                and (
                    hdr_low in {"step", "#", "no", "no.", "s.no", "s.no.", "sr", "sr.", "seq", "item"}
                    or (bool(sample_vals) and all(re.match(r"^\d{1,3}\.?$", sv) for sv in sample_vals))
                )
            )
            is_scope = any(sk in hdr_low for sk in cls.SCOPE_KEYWORDS)
            if idx == 0 and not conds and not eff_unit and not eff_curr and not is_numeric_step_col:
                is_scope = True
            if is_numeric_step_col:
                is_scope = False
            if idx > 0 and (conds or eff_unit or eff_curr or parent_hdr or has_value_cells):
                is_scope = False
            if idx == 1 and len(headers) >= 2 and not scope_cols and not conds and not eff_unit and not eff_curr and not has_value_cells:
                is_scope = True

            role = "scope" if is_scope else ("condition" if conds else "rule")
            if is_scope:
                scope_cols.append(raw_str)
            else:
                rule_cols.append(raw_str)

            nodes.append(HeaderNode(
                col_index=idx,
                raw_header=raw_str,
                clean_header=leaf_hdr,
                parent_header=parent_hdr,
                header_path=header_path,
                embedded_unit=eff_unit,
                embedded_currency=eff_curr,
                inferred_conditions=conds,
                footnote_markers=markers,
                role=role,
            ))

        # Guarantee at least one scope column and one rule column when >= 2 columns
        if not scope_cols and nodes:
            scope_cols.append(nodes[0].raw_header)
            nodes[0].role = "scope"
            if nodes[0].raw_header in rule_cols:
                rule_cols.remove(nodes[0].raw_header)
        if not rule_cols and len(nodes) > 1:
            last = nodes[-1]
            rule_cols.append(last.raw_header)
            last.role = "rule"
            if last.raw_header in scope_cols:
                scope_cols.remove(last.raw_header)

        # Detect cross-column dependencies (e.g. Condition column paired with Outcome/Limit column)
        deps: List[Dict[str, Any]] = []
        if len(nodes) >= 2:
            for n in nodes:
                if n.parent_header:
                    deps.append({
                        "type": "parent_child_header",
                        "parent": n.parent_header,
                        "child": n.clean_header,
                        "unit": n.embedded_unit,
                        "currency": n.embedded_currency,
                    })

        return HeaderHierarchy(
            columns=nodes,
            raw_header_rows=raw_header_rows or [],
            scope_columns=scope_cols,
            rule_columns=rule_cols,
            has_grouped_headers=has_grouped,
            cross_column_dependencies=deps,
        )

