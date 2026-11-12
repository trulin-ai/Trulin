"""
Table Semantic Interpreter (Sections 5, 10, 11, 18).

Determines the table-level semantic meaning (domain, topic, purpose, entity,
relationship, conditions, actors, units, exceptions) prior to row-level claim
generation using a hybrid deterministic + NLP + cached optional LLM pipeline.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from app.caching.pipeline_cache import default_pipeline_cache
from app.extraction.table_context.models import (
    CanonicalTable,
    TableSemanticInterpretation,
    TableType,
)

logger = logging.getLogger(__name__)


class TableSemanticInterpreter:
    """Interprets the semantic meaning of a complete canonical table."""

    VERSION = "tcuse_interp_v3"

    GENERIC_HEADERS = {
        "col", "col_1", "col_2", "col1", "col2", "column_1", "column_2",
        "item", "items", "value", "values", "data", "amount", "count",
        "number", "days", "rate", "percentage", "status", "type", "name",
        "description", "notes", "note", "details", "category", "tier", "grade",
    }

    STRUCTURAL_TITLE_NOISE = {
        "table", "matrix", "schedule", "summary", "chart", "overview",
        "list", "entitlement", "entitlements", "policy", "rules", "guidelines",
        "criteria", "standards", "parameters", "specifications", "details",
    }

    DOMAIN_SIGNATURES: List[Tuple[str, Tuple[str, ...]]] = [
        ("HR", ("employee", "leave", "vacation", "sick", "probation", "notice period", "salary", "payroll", "benefits", "training", "onboarding", "offboarding", "grade")),
        ("Finance", ("refund", "reimbursement", "invoice", "billing", "payment", "chargeback", "tax", "duty", "fee", "price", "currency", "usd", "eur", "discount")),
        ("Security & Compliance", ("access", "password", "authentication", "encryption", "mfa", "security", "audit", "retention", "gdpr", "hipaa", "soc", "dpo", "pii", "compliance")),
        ("Operations & SLA", ("sla", "uptime", "response time", "escalation", "incident", "severity", "shipping", "delivery", "transit", "warehouse", "rma", "warranty")),
        ("Legal & Contracting", ("liability", "indemnity", "termination", "breach", "intellectual property", "governing law", "confidential", "license", "warranty")),
    ]

    @classmethod
    def classify_table_type(cls, table: CanonicalTable) -> TableType:
        """Deterministically classifies the table into one of the 12 semantic table types."""
        hdrs_low = " ".join(h.lower() for h in table.headers)
        ctx = table.context_bundle
        ctx_text = " ".join([
            ctx.table_title.text if ctx.table_title else "",
            ctx.table_caption.text if ctx.table_caption else "",
            ctx.table_description.text if ctx.table_description else "",
            ctx.subsection_heading.text if ctx.subsection_heading else "",
            ctx.parent_section_heading.text if ctx.parent_section_heading else "",
        ]).lower()
        combined = f"{hdrs_low} {ctx_text}".strip()

        # 1. Revision history
        if (
            any(k in hdrs_low for k in ("version", "rev", "revision"))
            and any(k in hdrs_low for k in ("date", "author", "approved", "description", "changes"))
        ) or "revision history" in ctx_text or "change log" in ctx_text:
            return TableType.REVISION_HISTORY

        # 2. Metadata / Navigational (TOC, Signoff, Sitemap, Document-Control Key-Value)
        is_kv_doc_control = (
            len(table.headers) == 2
            and table.headers[0].strip().lower() in {"key", "field", "attribute", "property", "parameter", "item", "label", "document number"}
            and (
                any(k in ctx_text for k in ("document control", "policy control", "document metadata", "key-value"))
                or sum(
                    1
                    for r in table.rows
                    if str(r.cells.get(table.headers[0], "")).strip().lower()
                    in {
                        "policy title", "document title", "document number", "policy number",
                        "version", "status", "effective date", "next review date", "review date",
                        "policy owner", "owner", "approving body", "applies to", "classification",
                    }
                ) >= 3
            )
        )
        if (
            is_kv_doc_control
            or ("section" in hdrs_low and ("title" in hdrs_low or "page" in hdrs_low))
            or ("role" in hdrs_low and ("signature" in hdrs_low or "signatory" in hdrs_low))
            or "table of contents" in ctx_text
            or ("approver" in ctx_text and "sign" in hdrs_low)
        ):
            return TableType.METADATA_NAVIGATIONAL

        # 3. Calculation table (contains formulas)
        has_formulas = any(
            nc.formula is not None
            for row in table.rows
            for nc in row.normalized_cells.values()
        )
        if has_formulas or "formula" in hdrs_low or "calculation" in combined:
            return TableType.CALCULATION

        # 4. Exception table
        if any(k in combined for k in ("exception", "exemption", "exclusion", "carve-out", "waiver")):
            return TableType.EXCEPTION

        # 5. Schedule / Timeline table (check before responsibility so calendars with an owner column stay schedules)
        if any(k in combined for k in ("schedule", "calendar", "timeline", "deadline", "milestone", "window", "turnaround", "duration", "notice period", "cutoff", "quarterly review")):
            return TableType.SCHEDULE

        # 6. Eligibility table
        if any(k in combined for k in ("eligible", "eligibility", "entitle", "entitlement", "qualify", "qualification", "can it be")):
            return TableType.ELIGIBILITY

        # 7. Threshold / Tier limit table
        if any(k in combined for k in ("threshold", "limit", "cap", "maximum", "minimum", "tier", "allowance", "quota")):
            return TableType.THRESHOLD

        # 8. Responsibility matrix (RACI / Owner / Approver) - require explicit matrix/governance markers
        if re.search(r"\b(raci|responsibility\s+matrix|decision\s+maker|authorized\s+by|approver|accountable)\b", combined):
            return TableType.RESPONSIBILITY

        # 9. Comparison table
        if any(k in combined for k in ("comparison", "vs", "versus", "plan comparison", "feature matrix")):
            return TableType.COMPARISON

        # 10. Statistical table
        if any(k in combined for k in ("statistics", "statistical", "survey", "metrics", "benchmark", "average", "median", "distribution", "count")):
            return TableType.STATISTICAL

        # 11. Reference / Glossary / Lookup table
        if any(k in combined for k in ("reference", "glossary", "definition", "meaning", "code", "lookup", "directory", "contact")):
            return TableType.REFERENCE

        return TableType.POLICY_RULE

    @classmethod
    def _infer_business_domain(cls, text: str) -> Optional[str]:
        low = (text or "").lower()
        best_domain: Optional[str] = None
        best_hits = 0
        for domain, kws in cls.DOMAIN_SIGNATURES:
            hits = sum(1 for kw in kws if kw in low)
            if hits > best_hits:
                best_hits = hits
                best_domain = domain
        return best_domain

    @classmethod
    def _extract_primary_entity(cls, table: CanonicalTable, context_text: str) -> Optional[str]:
        scope_cols = table.header_hierarchy.scope_columns
        if scope_cols:
            first_scope = scope_cols[0]
            clean_scope = re.sub(r"\([^)]*\)", "", first_scope).strip()
            # e.g. "Employee Grade" -> "Employee"; "Customer Tier" -> "Customer"
            parts = clean_scope.split()
            if len(parts) >= 2 and parts[-1].lower() in ("grade", "tier", "level", "type", "category", "role", "group", "status"):
                return parts[0].title() if len(parts) == 2 else " ".join(parts[:-1]).title()
            if clean_scope.lower() not in cls.GENERIC_HEADERS:
                return clean_scope
        # Check context text for actor nouns
        actor_m = re.search(r"\b(employees?|customers?|users?|vendors?|suppliers?|contractors?|administrators?|students?|members?|patients?)\b", context_text, re.IGNORECASE)
        if actor_m:
            word = actor_m.group(1).lower()
            return word[:-1].title() if word.endswith("s") and not word.endswith("ss") else word.title()
        return None

    @classmethod
    def _extract_topic_and_predicate(
        cls,
        table: CanonicalTable,
        table_type: TableType,
    ) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str], List[str]]:
        """
        Dynamically extracts (business_topic, table_purpose, relationship_type, predicate_stem, missing_reasons)
        from title, caption, description, section headings, and headers without hardcoding specific topics.
        """
        ctx = table.context_bundle
        primary_sources: List[str] = []
        if ctx.table_title:
            primary_sources.append(ctx.table_title.text)
        if ctx.table_caption:
            primary_sources.append(ctx.table_caption.text)
        if ctx.table_description:
            primary_sources.append(ctx.table_description.text)
        if ctx.subsection_heading:
            primary_sources.append(ctx.subsection_heading.text)
        if ctx.preceding_paragraph and not ctx.table_description:
            primary_sources.append(ctx.preceding_paragraph.text)
        if ctx.parent_section_heading and not primary_sources:
            primary_sources.append(ctx.parent_section_heading.text)

        missing_reasons: List[str] = []
        non_generic_hdrs = [
            h.clean_header for h in table.header_hierarchy.columns
            if h.clean_header.lower() not in cls.GENERIC_HEADERS and len(h.clean_header) > 2
        ]

        if not primary_sources and not non_generic_hdrs:
            missing_reasons.append("No table title, caption, description, or domain-specific column headers found.")
            return None, None, None, None, missing_reasons

        # Choose the most specific informative text phrase (prefer title -> caption -> substantive description -> subsection)
        def _is_structural_meta_prose(text: str) -> bool:
            low = text.strip().lower()
            meta_markers = ("grouped header", "parent header", "merged cell", "next table", "distinguish between", "table formatting", "multi-page", "spanned across")
            return any(m in low for m in meta_markers)

        anchor_phrase = ""
        if ctx.table_title:
            anchor_phrase = ctx.table_title.text
        elif ctx.table_caption:
            anchor_phrase = ctx.table_caption.text
        elif ctx.table_description and not _is_structural_meta_prose(ctx.table_description.text):
            anchor_phrase = ctx.table_description.text
        elif ctx.subsection_heading:
            anchor_phrase = ctx.subsection_heading.text
        elif ctx.table_description:
            anchor_phrase = ctx.table_description.text
        elif ctx.preceding_paragraph and not _is_structural_meta_prose(ctx.preceding_paragraph.text):
            anchor_phrase = ctx.preceding_paragraph.text
        elif ctx.parent_section_heading:
            anchor_phrase = ctx.parent_section_heading.text

        # If title is very generic (e.g., "Employee Entitlement Schedule" or "Policy Table") while caption/description is more specific, enrich anchor
        generic_title_words = cls.STRUCTURAL_TITLE_NOISE | {"employee", "staff", "company", "policy", "standard", "general"}
        title_specific_words = [
            w for w in re.findall(r"[a-z]{3,}", anchor_phrase.lower())
            if w not in generic_title_words
        ]
        if ctx.table_title and (ctx.table_caption or ctx.table_description) and len(title_specific_words) <= 1:
            supp = ctx.table_caption.text if ctx.table_caption else ctx.table_description.text
            t_words = set(re.findall(r"[a-z]{3,}", anchor_phrase.lower()))
            s_words = set(re.findall(r"[a-z]{3,}", supp.lower()))
            # Use description/caption to specialize generic titles (Test 2: same title, different descriptions)
            if len(s_words - t_words) >= 2:
                # Extract core topic from description/caption sentence
                m_spec = re.search(
                    r"\b(?:covers?|defines?|specifies|governs?|applies to|for|regarding|outlines?)\s+([A-Za-z0-9\s\-/]{4,55}?)(?:[.,;:]|\bfor\b|\bby\b|\bbased\b|$)",
                    supp,
                    re.IGNORECASE,
                )
                if m_spec:
                    spec_phrase = m_spec.group(1).strip()
                    if spec_phrase.lower() not in anchor_phrase.lower():
                        anchor_phrase = f"{anchor_phrase} ({spec_phrase})"
                else:
                    anchor_phrase = f"{anchor_phrase} — {supp[:80]}"

        # Extract clean topic tokens from anchor_phrase (strip Table N:, Figure N:, Slide N:, doc IDs, versions)
        clean_anchor = re.sub(r"^\s*(?:Table|Figure|Slide)\s+\d+(?:\.\d+)*\s*[:.\-—–|]?\s*", "", anchor_phrase, flags=re.IGNORECASE).strip()
        clean_anchor = re.sub(r"^\s*\d+(?:\.\d+)*\s+", "", clean_anchor).strip()
        clean_anchor = re.sub(r"\b[A-Z]{2,}(?:-[A-Z0-9]+){2,}\b", "", clean_anchor).strip()
        clean_anchor = re.sub(r"\(([^)]*)\)", lambda m: " " + m.group(1) + " ", clean_anchor)
        anchor_low = clean_anchor.lower()

        # Remove leading entity noun if it duplicates the primary scope column (e.g. "Employee Annual Leave Entitlement" -> "Annual Leave")
        topic_str = clean_anchor
        scope_first = (table.header_hierarchy.scope_columns[0].split()[0].lower() if table.header_hierarchy.scope_columns else "")
        if scope_first and topic_str.lower().startswith(scope_first + " "):
            topic_str = topic_str[len(scope_first):].strip()

        # Strip structural trailing/leading filler words and meta-prose verbs for clean topic name
        _STOP_OR_META = cls.STRUCTURAL_TITLE_NOISE | {
            "the", "a", "an", "of", "for", "and", "to", "in", "on", "this", "that",
            "next", "following", "below", "above", "between", "among", "by", "from", "with", "per",
            "distinguish", "distinguishes", "uses", "use", "shows", "show", "contains", "contain",
            "applies", "apply", "summarizes", "summarize", "outlines", "outline", "lists", "list",
            "grouped", "headers", "header", "parent", "child", "across", "different",
            "short", "column", "columns", "holding", "rows", "row", "are", "is",
        }
        topic_tokens = [
            w for w in re.split(r"[\s\-_/—.,:;]+", topic_str)
            if w and w.lower() not in _STOP_OR_META
        ]
        # Deduplicate adjacent repeated words
        dedup_tokens: List[str] = []
        for t in topic_tokens:
            if not dedup_tokens or dedup_tokens[-1].lower() != t.lower():
                dedup_tokens.append(t)

        # If anchor_phrase yielded no specific topic tokens, fall back to non-generic rule column headers
        if not dedup_tokens and non_generic_hdrs:
            dedup_tokens = [w for h in non_generic_hdrs[:2] for w in h.split() if len(w) > 2]

        if not dedup_tokens:
            missing_reasons.append("Insufficient semantic context to identify business topic.")
            return None, None, None, None, missing_reasons

        # Keep concise topic (up to 3 core words so predicates remain short and readable)
        topic_words = dedup_tokens[:3]
        business_topic = " ".join(topic_words).strip()
        topic_slug = re.sub(r"[^a-z0-9]+", "_", business_topic.lower()).strip("_")

        # Determine semantic relationship type & concise predicate stem from context + table_type
        combined_ctx = " ".join(primary_sources + [h.raw_header for h in table.header_hierarchy.columns]).lower()
        title_or_sub = " ".join(
            s.text.lower() for s in (ctx.table_title, ctx.subsection_heading) if s and s.text
        )
        if table_type == TableType.CALCULATION or any(w in combined_ctx for w in ("budget", "variance", "forecast", "worked example")):
            rel_type = f"{business_topic} Calculation"
            pred_stem = f"calculates_{topic_slug}"
        elif table_type == TableType.REFERENCE or any(w in title_or_sub for w in ("regulatory", "statutory", "acronym", "abbreviation", "glossary", "contact")):
            rel_type = f"{business_topic} Reference"
            pred_stem = f"has_{topic_slug}"
        elif "entitle" in combined_ctx:
            rel_type = f"{business_topic} Entitlement"
            pred_stem = f"has_{topic_slug}_entitlement" if not topic_slug.endswith("_entitlement") else f"has_{topic_slug}"
        elif "eligib" in combined_ctx:
            rel_type = f"{business_topic} Eligibility"
            pred_stem = f"is_eligible_for_{topic_slug}"
        elif "allowance" in combined_ctx or "benefit" in combined_ctx or "reimburse" in combined_ctx:
            rel_type = f"{business_topic} Allowance"
            pred_stem = f"is_eligible_for_{topic_slug}"
        elif table_type == TableType.SCHEDULE or any(w in combined_ctx for w in ("schedule", "calendar", "timeline", "duration", "period", "window", "deadline", "cutoff")):
            rel_type = f"{business_topic} Schedule"
            pred_stem = f"has_{topic_slug}_schedule" if not topic_slug.endswith("_schedule") else f"has_{topic_slug}"
        elif table_type == TableType.THRESHOLD or any(w in combined_ctx for w in ("limit", "cap", "threshold", "maximum", "minimum")):
            rel_type = f"{business_topic} Threshold"
            pred_stem = f"has_{topic_slug}_limit" if not topic_slug.endswith(("_limit", "_cap", "_threshold")) else f"has_{topic_slug}"
        elif table_type == TableType.RESPONSIBILITY or re.search(r"\b(raci|responsibility\s+matrix|decision\s+maker|authorized\s+by|approver|accountable)\b", combined_ctx):
            rel_type = f"{business_topic} Responsibility"
            pred_stem = f"is_responsible_for_{topic_slug}"
        elif table_type == TableType.STATISTICAL:
            rel_type = f"{business_topic} Metric"
            pred_stem = f"has_{topic_slug}_metric"
        elif table_type == TableType.CALCULATION:
            rel_type = f"{business_topic} Calculation"
            pred_stem = f"calculates_{topic_slug}"
        elif table_type == TableType.EXCEPTION:
            rel_type = f"{business_topic} Exception"
            pred_stem = f"has_{topic_slug}_exception"
        else:
            rel_type = f"{business_topic} Rule"
            pred_stem = f"has_{topic_slug}"

        purpose = f"Define {business_topic.lower()} rules"
        if table_type == TableType.THRESHOLD:
            purpose = f"Define {business_topic.lower()} thresholds and limits"
        elif table_type == TableType.ELIGIBILITY:
            purpose = f"Define {business_topic.lower()} eligibility"
        elif table_type == TableType.SCHEDULE:
            purpose = f"Define {business_topic.lower()} timelines and schedules"
        elif table_type == TableType.STATISTICAL:
            purpose = f"Report {business_topic.lower()} statistics"
        elif table_type == TableType.CALCULATION:
            purpose = f"Compute {business_topic.lower()} derived values"

        return business_topic, purpose, rel_type, pred_stem, missing_reasons

    @classmethod
    def interpret(
        cls,
        table: CanonicalTable,
        use_cache: bool = True,
    ) -> TableSemanticInterpretation:
        """
        Produces a complete TableSemanticInterpretation for a CanonicalTable.
        Uses content-addressed caching keyed on table + context fingerprint.
        """
        cache_key = None
        if use_cache:
            cache_key = default_pipeline_cache.compute_key(
                stage_name="table_semantic_interpretation",
                code_version=cls.VERSION,
                input_data={
                    "table_id": table.table_id,
                    "context_fp": table.context_bundle.context_fingerprint,
                },
            )
            cached = default_pipeline_cache.get("table_semantic_interpretation", cache_key)
            if cached:
                try:
                    return TableSemanticInterpretation(**cached)
                except Exception:
                    pass

        ctx = table.context_bundle
        table_type = cls.classify_table_type(table)

        all_ctx_text = " ".join(
            [ctx.document_title or ""]
            + [it.text for it in ctx.all_items]
            + [h.raw_header for h in table.header_hierarchy.columns]
        )

        domain = cls._infer_business_domain(all_ctx_text)
        primary_entity = cls._extract_primary_entity(table, all_ctx_text)
        business_topic, purpose, rel_type, pred_stem, missing_reasons = cls._extract_topic_and_predicate(table, table_type)

        units = sorted({
            u for u in (
                [h.embedded_unit for h in table.header_hierarchy.columns if h.embedded_unit]
                + [
                    nc.unit
                    for row in table.rows
                    for nc in row.normalized_cells.values()
                    if nc.unit
                ]
            ) if u
        })

        # Collect footnote qualifications
        fn_quals: Dict[str, str] = {}
        exceptions: List[str] = []
        for fn in ctx.footnotes + ctx.referenced_notes:
            key = fn.marker or "table_note"
            fn_quals[key] = fn.text
            if any(w in fn.text.lower() for w in ("except", "unless", "exclude", "excluding", "not eligible", "only if")):
                exceptions.append(fn.text)

        # Temporal & Geographic applicability cues from context
        temporal_app: Optional[str] = None
        m_temp = re.search(r"\b(effective\s+(?:from\s+)?[A-Za-z0-9,\s\-]+?\d{4}|FY\s*\d{2,4}|Q[1-4]\s+\d{4}|per\s+(?:year|month|annum|quarter)|annual(?:ly)?)\b", all_ctx_text, re.IGNORECASE)
        if m_temp:
            temporal_app = m_temp.group(0).strip()

        geo_app: Optional[str] = None
        m_geo = re.search(r"\b(United States|USA|US|UK|EU|EEA|EMEA|APAC|India|Canada|Global|North America)\b", all_ctx_text)
        if m_geo:
            geo_app = m_geo.group(0).strip()

        # Ambiguity & confidence calibration
        is_ambiguous = bool(missing_reasons) or ctx.has_inconsistency
        if ctx.has_inconsistency:
            missing_reasons.extend(ctx.inconsistency_reasons)

        if table_type in (TableType.REVISION_HISTORY, TableType.METADATA_NAVIGATIONAL):
            sem_conf = 0.95
            is_ambiguous = False
        elif is_ambiguous:
            sem_conf = 0.45 if ctx.has_inconsistency else 0.40
        elif ctx.table_title or ctx.table_caption:
            sem_conf = 0.94
        elif ctx.table_description or ctx.subsection_heading:
            sem_conf = 0.88
        else:
            sem_conf = 0.78

        # Header-derived conditions
        rule_conds = []
        for hn in table.header_hierarchy.columns:
            rule_conds.extend(hn.inferred_conditions)
            if hn.parent_header:
                rule_conds.append(f"{hn.parent_header}: {hn.clean_header}")

        val_interp = None
        if business_topic and units:
            val_interp = f"{business_topic} value in {units[0]}"
        elif business_topic:
            val_interp = f"{business_topic} specification"

        interp = TableSemanticInterpretation(
            table_id=table.table_id,
            table_type=table_type,
            business_domain=domain,
            business_topic=business_topic,
            table_purpose=purpose,
            primary_entity=primary_entity,
            secondary_entities=[h.clean_header for h in table.header_hierarchy.columns if h.role == "scope"][1:],
            entity_attributes=[h.clean_header for h in table.header_hierarchy.columns if h.role != "scope"],
            relationship_type=rel_type,
            canonical_predicate_stem=pred_stem,
            value_interpretation=val_interp,
            scope_conditions=table.header_hierarchy.scope_columns,
            rule_conditions=rule_conds,
            actors=[primary_entity] if primary_entity else [],
            units=units,
            temporal_applicability=temporal_app,
            geographic_applicability=geo_app,
            exceptions=exceptions,
            footnote_qualifications=fn_quals,
            is_ambiguous=is_ambiguous,
            missing_context_reasons=missing_reasons,
            semantic_confidence=sem_conf,
            interpretation_method="hybrid_deterministic_nlp",
        )

        if use_cache and cache_key:
            try:
                default_pipeline_cache.set("table_semantic_interpretation", cache_key, interp)
            except Exception:
                pass

        return interp

