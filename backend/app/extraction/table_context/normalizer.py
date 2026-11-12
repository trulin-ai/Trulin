"""
Table Data Normalization (Section 3.3).

Normalizes cell values into typed quantitative/temporal/currency structures while
strictly preserving the original cell string, formula metadata, and blank/inherited provenance.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from app.extraction.table_context.models import NormalizedCellValue

CURRENCY_SYMBOL_MAP = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "₹": "INR",
    "¥": "JPY",
}

CURRENCY_CODES = ("USD", "EUR", "GBP", "INR", "JPY", "CAD", "AUD", "CHF", "SGD")


class TableValueNormalizer:
    """Deterministic normalizer for table cell values."""

    FOOTNOTE_MARKER_PAT = re.compile(r"(?:\s*(\*+|†|‡|\[\d+\]|\(\d+\)|[¹²³⁴⁵⁶⁷⁸⁹]+))\s*$")
    APPROX_PAT = re.compile(r"(?:^\s*~\s*|\bapprox(?:imately)?\.?\b|\baround\b|\babout\b)", re.IGNORECASE)
    QUALIFIER_PATTERNS: List[Tuple[str, re.Pattern[str]]] = [
        ("up_to", re.compile(r"\bup\s+to\b|\bnot\s+exceeding\b|\bmaximum\b|\bmax\.?\b", re.IGNORECASE)),
        ("at_least", re.compile(r"\bat\s+least\b|\bminimum\b|\bmin\.?\b", re.IGNORECASE)),
        ("more_than", re.compile(r"\bmore\s+than\b|\bgreater\s+than\b|\bover\b|\bexceeding\b", re.IGNORECASE)),
        ("less_than", re.compile(r"\bless\s+than\b|\bunder\b|\bbelow\b", re.IGNORECASE)),
        ("approximate", APPROX_PAT),
        ("typical", re.compile(r"\btypical(?:ly)?\b|\busually\b|\bnormally\b", re.IGNORECASE)),
        ("at_discretion", re.compile(r"\bdiscretion\b", re.IGNORECASE)),
        ("within", re.compile(r"\bwithin\b", re.IGNORECASE)),
    ]

    @classmethod
    def extract_footnote_markers(cls, raw_text: str) -> Tuple[str, List[str]]:
        """Separates trailing footnote markers (e.g. '*', '[1]') from cell text."""
        text = (raw_text or "").strip()
        markers: List[str] = []
        while True:
            m = cls.FOOTNOTE_MARKER_PAT.search(text)
            if not m:
                break
            marker = m.group(1).strip()
            if marker and marker not in markers:
                markers.append(marker)
            text = text[:m.start()].strip()
        return text, list(reversed(markers))

    @classmethod
    def normalize_cell(
        cls,
        raw_value: str,
        cell_meta: Optional[Dict[str, Any]] = None,
        header_unit: Optional[str] = None,
        header_currency: Optional[str] = None,
        is_inherited: bool = False,
        is_original_blank: bool = False,
    ) -> NormalizedCellValue:
        """Normalizes a single cell value while preserving original representation."""
        raw_str = "" if raw_value is None else str(raw_value)
        meta = cell_meta or {}

        formula = meta.get("formula")
        cached_val = meta.get("cached_value")
        formula_status = meta.get("formula_status")
        is_formula_unavailable = bool(formula and formula_status == "cached_unavailable")
        inherited_flag = bool(is_inherited or meta.get("is_inherited", False))
        blank_flag = bool(is_original_blank or meta.get("is_original_blank", raw_str.strip() == ""))

        if is_formula_unavailable:
            return NormalizedCellValue(
                raw_value=raw_str,
                normalized_value=None,
                data_type="formula",
                formula=formula,
                cached_value=None,
                is_formula_unavailable=True,
                is_inherited=inherited_flag,
                is_original_blank=blank_flag,
            )

        clean_body, markers = cls.extract_footnote_markers(raw_str)
        if not clean_body:
            return NormalizedCellValue(
                raw_value=raw_str,
                normalized_value=None,
                data_type="empty",
                formula=formula,
                cached_value=cached_val,
                is_inherited=inherited_flag,
                is_original_blank=blank_flag,
                footnote_markers=markers,
            )

        qualifiers = [q_name for q_name, pat in cls.QUALIFIER_PATTERNS if pat.search(clean_body)]
        is_approx = "approximate" in qualifiers

        # Comparison operators
        comp_op: Optional[str] = None
        min_inc: Optional[bool] = None
        max_inc: Optional[bool] = None
        if re.search(r">=", clean_body) or "at_least" in qualifiers:
            comp_op = ">="
            min_inc = True
        elif re.search(r"<=", clean_body) or "up_to" in qualifiers:
            comp_op = "<="
            max_inc = True
        elif re.search(r"(?<![<>])>", clean_body) or "more_than" in qualifiers:
            comp_op = ">"
            min_inc = False
        elif re.search(r"(?<![<>])<", clean_body) or "less_than" in qualifiers:
            comp_op = "<"
            max_inc = False
        elif is_approx:
            comp_op = "~"

        # Negative values (leading '-' or accounting parentheses '(123)')
        is_negative = False
        working = clean_body.strip()
        if re.match(r"^\(\s*[\$€£₹¥]?\s*\d+(?:,\d{3})*(?:\.\d+)?\s*%?\s*\)$", working):
            is_negative = True
            working = "-" + working.strip("() ").strip()
        elif re.match(r"^-\s*[\$€£₹¥]?\s*\d+", working):
            is_negative = True

        # Currency detection
        currency_code: Optional[str] = header_currency
        for sym, code in CURRENCY_SYMBOL_MAP.items():
            if sym in working:
                currency_code = code
                break
        if not currency_code:
            for code in CURRENCY_CODES:
                if re.search(rf"\b{code}\b", working, re.IGNORECASE):
                    currency_code = code
                    break

        # ISO Date / Month-Day detection
        if re.match(r"^\d{4}-\d{2}-\d{2}$", working):
            return NormalizedCellValue(
                raw_value=raw_str,
                normalized_value=working,
                data_type="date",
                qualifiers=qualifiers,
                formula=formula,
                cached_value=cached_val,
                is_inherited=inherited_flag,
                is_original_blank=blank_flag,
                footnote_markers=markers,
            )

        # Numeric range (e.g. "10-20%", "5 to 10 days", "$100 - $200")
        range_m = re.search(
            r"(-?\d+(?:,\d{3})*(?:\.\d+)?)\s*(%?)\s*(?:-|–|to)\s*(-?\d+(?:,\d{3})*(?:\.\d+)?)\s*(%?)\s*(days?|business\s+days?|calendar\s+days?|hours?|months?|years?|weeks?)?",
            working,
            re.IGNORECASE,
        )
        if range_m and not re.match(r"^\d{4}-\d{2}", working):
            r_min = float(range_m.group(1).replace(",", ""))
            r_max = float(range_m.group(3).replace(",", ""))
            unit = "%" if (range_m.group(2) == "%" or range_m.group(4) == "%") else (range_m.group(5).lower() if range_m.group(5) else header_unit)
            return NormalizedCellValue(
                raw_value=raw_str,
                normalized_value=f"{r_min:g}-{r_max:g}",
                data_type="range",
                currency_code=currency_code,
                unit=unit,
                range_min=r_min,
                range_max=r_max,
                min_inclusive=True if min_inc is None else min_inc,
                max_inclusive=True if max_inc is None else max_inc,
                comparison_operator=comp_op,
                is_approximate=is_approx,
                is_negative=r_min < 0 or is_negative,
                qualifiers=qualifiers,
                formula=formula,
                cached_value=cached_val,
                is_inherited=inherited_flag,
                is_original_blank=blank_flag,
                footnote_markers=markers,
            )

        # Percentage
        pct_m = re.search(r"(-?\d+(?:\.\d+)?)\s*%", working)
        if pct_m:
            val = float(pct_m.group(1))
            norm_val: Any = int(val) if val.is_integer() else val
            return NormalizedCellValue(
                raw_value=raw_str,
                normalized_value=norm_val,
                data_type="percentage",
                unit="%",
                comparison_operator=comp_op,
                min_inclusive=min_inc,
                max_inclusive=max_inc,
                is_approximate=is_approx,
                is_negative=val < 0 or is_negative,
                qualifiers=qualifiers,
                formula=formula,
                cached_value=cached_val,
                is_inherited=inherited_flag,
                is_original_blank=blank_flag,
                footnote_markers=markers,
            )

        # Currency scalar
        if currency_code:
            curr_num_m = re.search(r"(-?\d+(?:,\d{3})*(?:\.\d+)?)", working)
            if curr_num_m:
                val = float(curr_num_m.group(1).replace(",", ""))
                if is_negative and val > 0:
                    val = -val
                norm_val = int(val) if val.is_integer() else val
                return NormalizedCellValue(
                    raw_value=raw_str,
                    normalized_value=norm_val,
                    data_type="currency",
                    currency_code=currency_code,
                    unit=currency_code,
                    comparison_operator=comp_op,
                    min_inclusive=min_inc,
                    max_inclusive=max_inc,
                    is_approximate=is_approx,
                    is_negative=val < 0 or is_negative,
                    qualifiers=qualifiers,
                    formula=formula,
                    cached_value=cached_val,
                    is_inherited=inherited_flag,
                    is_original_blank=blank_flag,
                    footnote_markers=markers,
                )

        # Duration / Time period
        dur_m = re.search(
            r"(-?\d+(?:\.\d+)?)\s*(calendar\s+days?|business\s+days?|working\s+days?|days?|hours?|months?|years?|weeks?|minutes?)\b",
            working,
            re.IGNORECASE,
        )
        if dur_m:
            val = float(dur_m.group(1))
            norm_val = int(val) if val.is_integer() else val
            unit = re.sub(r"\s+", " ", dur_m.group(2).lower().strip())
            return NormalizedCellValue(
                raw_value=raw_str,
                normalized_value=norm_val,
                data_type="duration",
                unit=unit,
                comparison_operator=comp_op,
                min_inclusive=min_inc,
                max_inclusive=max_inc,
                is_approximate=is_approx,
                is_negative=val < 0 or is_negative,
                qualifiers=qualifiers,
                formula=formula,
                cached_value=cached_val,
                is_inherited=inherited_flag,
                is_original_blank=blank_flag,
                footnote_markers=markers,
            )

        # Plain numeric (possibly with header_unit)
        num_m = re.match(r"^(?:[<>~]=?|\s)*(-?\d+(?:,\d{3})*(?:\.\d+)?)\s*([a-zA-Z]+)?$", working)
        if num_m:
            val = float(num_m.group(1).replace(",", ""))
            if is_negative and val > 0:
                val = -val
            norm_val = int(val) if val.is_integer() else val
            unit = num_m.group(2).lower() if num_m.group(2) else header_unit
            return NormalizedCellValue(
                raw_value=raw_str,
                normalized_value=norm_val,
                data_type="numeric",
                unit=unit,
                comparison_operator=comp_op,
                min_inclusive=min_inc,
                max_inclusive=max_inc,
                is_approximate=is_approx,
                is_negative=val < 0 or is_negative,
                qualifiers=qualifiers,
                formula=formula,
                cached_value=cached_val,
                is_inherited=inherited_flag,
                is_original_blank=blank_flag,
                footnote_markers=markers,
            )

        # Boolean / eligibility words
        low = working.lower()
        if low in ("yes", "true", "eligible", "allowed", "permitted", "required", "mandatory"):
            return NormalizedCellValue(
                raw_value=raw_str,
                normalized_value=True,
                data_type="boolean",
                qualifiers=qualifiers,
                formula=formula,
                cached_value=cached_val,
                is_inherited=inherited_flag,
                is_original_blank=blank_flag,
                footnote_markers=markers,
            )
        if low in ("no", "false", "ineligible", "not eligible", "prohibited", "none", "n/a", "not applicable"):
            return NormalizedCellValue(
                raw_value=raw_str,
                normalized_value=False if low in ("no", "false", "ineligible", "not eligible", "prohibited") else None,
                data_type="boolean" if low in ("no", "false", "ineligible", "not eligible", "prohibited") else "text",
                qualifiers=qualifiers,
                formula=formula,
                cached_value=cached_val,
                is_inherited=inherited_flag,
                is_original_blank=blank_flag,
                footnote_markers=markers,
            )

        return NormalizedCellValue(
            raw_value=raw_str,
            normalized_value=clean_body,
            data_type="text",
            unit=header_unit,
            currency_code=currency_code,
            comparison_operator=comp_op,
            is_approximate=is_approx,
            is_negative=is_negative,
            qualifiers=qualifiers,
            formula=formula,
            cached_value=cached_val,
            is_inherited=inherited_flag,
            is_original_blank=blank_flag,
            footnote_markers=markers,
        )

