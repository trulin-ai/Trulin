"""
Table Context Enrichment Engine — TCUSE (Sections 7, 8, 9, 10, 12).

Combines Table-level, Header-level, Row-level, Cell-level, and External
Footnote/Paragraph context to generate:
- Level 1: AtomicTableFact (explicit raw table fact)
- Level 2: Context-Enriched CandidateClaim (independently understandable SPO claim)
with complete evidence_refs and provenance.
"""

from __future__ import annotations

import re
import uuid
from typing import Any, Dict, List, Optional, Tuple

from app.extraction.deontic_classifier import DeonticClassifier
from app.extraction.models import (
    CandidateClaim,
    ExtractionStrategyType,
    FieldEvidenceBinding,
    TableGridBinding,
    TypedValue,
)
from app.extraction.table_context.models import (
    AtomicTableFact,
    CanonicalTable,
    CanonicalTableRow,
    HeaderNode,
    NormalizedCellValue,
    TableConfidenceBreakdown,
    TableSemanticInterpretation,
    TableType,
)
from app.ingestion.parsers.evidence_model import ContentRole


class TableContextEnrichmentEngine:
    """Central TCUSE enrichment and context-aware SPO claim generation engine."""

    # Specialized legacy/domain predicates from DeonticClassifier that should be
    # preserved when a column header directly matches an established domain rule
    SPECIALIZED_COLUMN_PREDICATES = {
        "has_probationary_notice_duration",
        "has_confirmed_notice_duration",
        "has_return_window",
        "has_return_deadline",
        "has_posting_duration",
        "has_posting_sla_estimate",
        "has_stage_duration",
        "has_refund_processing_duration",
        "has_cancellation_eligibility",
        "has_cancellation_refund_outcome",
        "has_cancellation_refund_timing",
        "has_post_shipment_resolution_path",
        "has_post_delivery_resolution_path",
        "has_refund_method",
        "has_warranty_period",
        "has_warranty_remedy",
        "has_return_shipping_rule",
        "has_duties_and_taxes_rule",
        "requires_approval_role",
        "has_internal_policy_reference",
        "has_contact_email",
        "has_contact_phone",
        "has_contact_address",
        "has_contact_hours",
        "has_service_level_target",
        "has_definition",
        "has_example_value",
        "is_required_for_refund_request",
    }

    @classmethod
    def _compose_entity_subject(
        cls,
        scope_dict: Dict[str, str],
        scope_nodes: List[HeaderNode],
        interp: TableSemanticInterpretation,
    ) -> str:
        """Composes a clean, natural subject entity combining row scope and primary entity."""
        parts: List[str] = []
        primary_ent = (interp.primary_entity or "").strip()

        for idx, (col_name, val) in enumerate(scope_dict.items()):
            clean_val = DeonticClassifier.strip_markdown(str(val or "")).strip()
            if not clean_val:
                continue
            col_low = col_name.lower()
            # Avoid duplicating primary_entity if already inside value
            if primary_ent and primary_ent.lower() not in clean_val.lower() and idx == 0:
                if any(k in col_low for k in ("grade", "tier", "level", "category", "type", "group")):
                    candidate_part = f"{clean_val} {primary_ent}"
                else:
                    candidate_part = clean_val
            else:
                candidate_part = clean_val
            if candidate_part not in parts:
                parts.append(candidate_part)

        if parts:
            return ", ".join(parts)
        return primary_ent or "Policy Entity"

    @classmethod
    def _format_value_with_unit(
        cls,
        norm_val: NormalizedCellValue,
        header_node: HeaderNode,
        interp: TableSemanticInterpretation,
    ) -> str:
        """Formats the claim object preserving original value and attaching header/table units when unambiguous."""
        raw = norm_val.raw_value.strip()
        clean_body = re.sub(r"\s*(?:\*+|†|‡|\[\d+\]|\(\d+\)|[¹²³⁴⁵⁶⁷⁸⁹]+)\s*$", "", raw).strip()
        if norm_val.is_formula_unavailable:
            return f"Formula ({norm_val.formula}, cached result unavailable)"

        unit = norm_val.unit or header_node.embedded_unit
        if unit and unit not in clean_body.lower() and norm_val.data_type in ("numeric", "range"):
            if unit == "%":
                return f"{clean_body}%"
            if norm_val.currency_code and norm_val.currency_code not in clean_body.upper():
                return f"{norm_val.currency_code} {clean_body}"
            return f"{clean_body} {unit}"
        return clean_body or raw

    @classmethod
    def _build_structured_conditions(
        cls,
        scope_dict: Dict[str, str],
        header_node: HeaderNode,
        norm_val: NormalizedCellValue,
        interp: TableSemanticInterpretation,
        matched_footnotes: List[str],
    ) -> List[Any]:
        """Builds structured condition objects & strings preserving header, scope, and temporal context."""
        conds: List[Any] = []

        # 1. Header-level conditions (e.g. "Within 7 days", "After 7 days", "Probationers")
        for hc in header_node.inferred_conditions:
            m_win = re.match(r"^(within|after)\s+(\d+)\s*(days?|hours?|months?|years?|weeks?)$", hc, re.IGNORECASE)
            if m_win:
                op = "less_than_or_equal_to" if m_win.group(1).lower() == "within" else "greater_than"
                conds.append({
                    "field": "timeframe",
                    "operator": op,
                    "value": int(m_win.group(2)),
                    "unit": m_win.group(3).lower(),
                    "raw": hc,
                })
            else:
                conds.append(hc)

        if header_node.parent_header and header_node.clean_header and not header_node.inferred_conditions:
            # e.g. Parent="Refund Amount (USD)" -> Child="Standard"
            if header_node.clean_header.lower() not in ("amount", "value", "days", "rate", "limit"):
                conds.append(f"{header_node.parent_header}: {header_node.clean_header}")

        # 2. Additional scope columns beyond primary entity
        if len(scope_dict) > 1:
            for k, v in list(scope_dict.items())[1:]:
                if str(v).strip():
                    conds.append({
                        "field": re.sub(r"[^a-z0-9]+", "_", k.lower()).strip("_"),
                        "operator": "equals",
                        "value": str(v).strip(),
                    })

        # 3. Footnote-derived non-exception conditions
        for fn in matched_footnotes:
            if not any(w in fn.lower() for w in ("except", "unless", "exclude", "excluding", "not eligible")):
                conds.append(fn)

        # 4. Temporal / Geographic applicability
        if interp.temporal_applicability:
            conds.append(f"Applicability: {interp.temporal_applicability}")
        if interp.geographic_applicability:
            conds.append(f"Region: {interp.geographic_applicability}")

        return conds

    @classmethod
    def _derive_context_aware_spo(
        cls,
        subject: str,
        scope_dict: Dict[str, str],
        header_node: HeaderNode,
        norm_val: NormalizedCellValue,
        formatted_obj: str,
        interp: TableSemanticInterpretation,
        conditions: List[Any],
        exceptions: List[str],
    ) -> Tuple[str, str, str, str, str]:
        """
        Derives (predicate, claim_text, modality, modal_op, claim_type) from full table context.
        Never merely appends the table title to a generic sentence.
        """
        hdr_clean = header_node.clean_header
        hdr_low = hdr_clean.lower()
        topic = (interp.business_topic or "").strip()
        topic_low = topic.lower()

        # Special handling for revision history & metadata/signatory/key-value tables
        if interp.table_type == TableType.REVISION_HISTORY:
            subj_ver = subject if subject.lower().startswith("policy") else f"Policy version {subject}"
            if "date" in hdr_low:
                return ("has_revision_date", f"{subj_ver} has revision date {formatted_obj}.", "POLICY_FACT", "specifies", "revision_history")
            if "author" in hdr_low or "revised by" in hdr_low:
                return ("revised_by", f"{subj_ver} was revised by {formatted_obj}.", "POLICY_FACT", "specifies", "revision_history")
            if "summary" in hdr_low or "change" in hdr_low:
                return ("has_change_summary", f"{subj_ver} has change summary: {formatted_obj.rstrip('.')}.", "POLICY_FACT", "specifies", "revision_history")
            hdr_slug = re.sub(r"[^a-z0-9]+", "_", hdr_low).strip("_") or "detail"
            return (f"has_{hdr_slug}", f"{subj_ver} has {hdr_clean.lower()} {formatted_obj}.", "POLICY_FACT", "specifies", "revision_history")

        if interp.table_type == TableType.METADATA_NAVIGATIONAL:
            scope_keys_low = [k.lower() for k in scope_dict.keys()]
            if any("role" in k for k in scope_keys_low):
                if hdr_low in ("name", "signatory", "approver"):
                    return ("has_signatory", f"{subject} has signatory {formatted_obj}.", "POLICY_FACT", "specifies", "metadata")
                if "date" in hdr_low:
                    return ("has_approval_date", f"{subject} has approval date {formatted_obj}.", "POLICY_FACT", "specifies", "metadata")
                if "signature" in hdr_low:
                    return ("has_signature", f"{subject} has signature {formatted_obj}.", "POLICY_FACT", "specifies", "metadata")

            kv_key_low = DeonticClassifier.strip_markdown(str(next(iter(scope_dict.values()), subject))).strip().lower()
            kv_map = {
                "policy title": ("has_title", "has title"),
                "document title": ("has_title", "has title"),
                "title": ("has_title", "has title"),
                "document number": ("has_document_number", "has document number"),
                "policy number": ("has_document_number", "has document number"),
                "version": ("has_version", "has version"),
                "status": ("has_status", "has status"),
                "effective date": ("has_effective_date", "has effective date"),
                "next review date": ("has_review_date", "has review date"),
                "review date": ("has_review_date", "has review date"),
                "policy owner": ("has_owner", "has owner"),
                "owner": ("has_owner", "has owner"),
                "approving body": ("approved_by", "is approved by"),
                "approved by": ("approved_by", "is approved by"),
                "applies to": ("applies_to", "applies to"),
                "classification": ("has_classification", "has classification"),
            }
            if kv_key_low in kv_map:
                kv_pred, kv_verb = kv_map[kv_key_low]
                return (kv_pred, f"Policy {kv_verb} {formatted_obj}.", "POLICY_FACT", "specifies", "metadata")

            return (
                "has_document_metadata",
                f"{subject} {hdr_clean}: {formatted_obj}.",
                "POLICY_FACT",
                "specifies",
                "metadata",
            )

        # Missing/ambiguous context without business topic -> preserve atomic fact without inventing meaning
        if not topic and interp.is_ambiguous:
            col_slug = re.sub(r"[^a-z0-9]+", "_", hdr_low).strip("_") or "value"
            pred = f"has_{col_slug}"
            return (
                pred,
                f"{subject} has {hdr_clean} of {formatted_obj}.",
                "POLICY_FACT",
                "specifies",
                "policy",
            )

        # Check DeonticClassifier only for highly specialized legacy domain headers when context matches
        # (so existing refund/notice-period benchmarks retain exact canonical predicates)
        legacy = DeonticClassifier.normalize_table_policy_claim(
            scope_dict=scope_dict,
            rule_key=hdr_clean,
            rule_value=norm_val.raw_value,
            conditions=[],
            qualifiers=list(norm_val.qualifiers),
        )
        legacy_pred = legacy.get("predicate", "")
        if legacy_pred in cls.SPECIALIZED_COLUMN_PREDICATES:
            # Ensure context topic doesn't conflict with the legacy predicate's domain
            if not topic_low or any(tok in legacy_pred for tok in re.findall(r"[a-z]{4,}", topic_low)):
                return (
                    legacy_pred,
                    legacy["claim_text"],
                    legacy.get("modality", "POLICY_FACT"),
                    legacy.get("modal_operator", "specifies"),
                    legacy.get("claim_type", "policy"),
                )

        # Dynamic context-aware predicate & natural language claim synthesis
        pred = interp.canonical_predicate_stem or f"has_{re.sub(r'[^a-z0-9]+', '_', topic_low).strip('_')}"
        # Specialize predicate if multi-column table has distinct metric columns beyond generic "Days"/"Value"/"Amount"
        generic_val_hdrs = {"days", "value", "amount", "limit", "rate", "percentage", "eligibility", "status", "duration", "period", "allowance"}
        if hdr_low not in generic_val_hdrs and not header_node.inferred_conditions:
            hdr_slug = re.sub(r"[^a-z0-9]+", "_", hdr_low).strip("_")
            # Avoid duplicating trailing token (e.g. pred='has_sub_limits_limit' + hdr='limit_inr')
            pred_tail = pred.rsplit("_", 1)[-1]
            if hdr_slug.startswith(pred_tail + "_"):
                hdr_slug = hdr_slug[len(pred_tail) + 1:]
            if hdr_slug and hdr_slug not in pred:
                pred = f"{pred}_{hdr_slug}"

        # Build condition suffix for independent understandability
        cond_phrases: List[str] = []
        for c in conditions:
            if isinstance(c, dict) and c.get("raw"):
                cond_phrases.append(str(c["raw"]).lower())
            elif isinstance(c, dict) and c.get("field") and c.get("value") is not None:
                cond_phrases.append(f"when {c['field'].replace('_', ' ')} is {c['value']}")
            elif isinstance(c, str) and not c.startswith(("Table Column:", "Applicability:")):
                cond_phrases.append(c)

        cond_suffix = f" ({', '.join(cond_phrases)})" if cond_phrases else ""
        exc_suffix = f" [Exception: {exceptions[0]}]" if exceptions else ""

        # Handle boolean negation / prohibition cleanly
        if norm_val.data_type == "boolean" and norm_val.normalized_value is False:
            modality = "PROHIBITED"
            modal_op = "is not eligible for"
            if pred.startswith("is_eligible_for_"):
                pred = pred.replace("is_eligible_for_", "is_not_eligible_for_", 1)
            elif pred.startswith("is_entitled_to_"):
                pred = pred.replace("is_entitled_to_", "is_not_entitled_to_", 1)
            claim_text = f"{subject} is not eligible for {topic_low}{cond_suffix}.{exc_suffix}"
        elif pred.startswith("is_entitled_to_") or (pred.startswith("has_") and pred.endswith("_entitlement")):
            modality = "POLICY_FACT"
            modal_op = "is entitled to"
            ent_phrase = topic_low if "entitlement" in topic_low else f"{topic_low} entitlement"
            claim_text = f"{subject} has {ent_phrase} of {formatted_obj}{cond_suffix}.{exc_suffix}"
        elif pred.startswith("is_eligible_for_"):
            modality = "PERMITTED"
            modal_op = "is eligible for"
            if norm_val.data_type == "boolean" and norm_val.normalized_value is True:
                claim_text = f"{subject} is eligible for {topic_low}{cond_suffix}.{exc_suffix}"
            else:
                claim_text = f"{subject} is eligible for {topic_low} of {formatted_obj}{cond_suffix}.{exc_suffix}"
        elif pred.startswith("is_responsible_for_"):
            modality = "REQUIRED"
            modal_op = "is responsible for"
            raci_map = {
                "R": "R (Responsible)",
                "A": "A (Accountable)",
                "C": "C (Consulted)",
                "I": "I (Informed)",
            }
            code = formatted_obj.strip().upper()
            if code in raci_map:
                claim_text = f"{subject}: {hdr_clean} must act as {raci_map[code]} ({topic_low}){cond_suffix}.{exc_suffix}"
            else:
                claim_text = f"{subject} is responsible for {topic_low} ({hdr_clean}: {formatted_obj}){cond_suffix}.{exc_suffix}"
        elif pred.startswith("calculates_"):
            modality = "POLICY_FACT"
            modal_op = "calculates"
            formula_note = f" via formula {norm_val.formula}" if norm_val.formula else ""
            claim_text = f"{subject} has {topic_low} calculated as {formatted_obj}{formula_note}{cond_suffix}.{exc_suffix}"
        elif interp.table_type == TableType.STATISTICAL:
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} reports {topic_low} ({hdr_clean}) of {formatted_obj}{cond_suffix}.{exc_suffix}"
        elif interp.table_type == TableType.SCHEDULE:
            modality = "POLICY_FACT"
            modal_op = "specifies"
            claim_text = f"{subject} has {topic_low} schedule ({hdr_clean}) of {formatted_obj}{cond_suffix}.{exc_suffix}"
        elif interp.table_type == TableType.THRESHOLD:
            modality = "POLICY_FACT"
            modal_op = "is limited to"
            claim_text = f"{subject} has {topic_low} threshold ({hdr_clean}) of {formatted_obj}{cond_suffix}.{exc_suffix}"
        else:
            modality = "POLICY_FACT"
            modal_op = "specifies"
            metric_part = f" ({hdr_clean})" if hdr_low not in topic_low else ""
            claim_text = f"{subject} specifies {topic_low}{metric_part} as {formatted_obj}{cond_suffix}.{exc_suffix}"

        is_pure_glossary = interp.table_type == TableType.REFERENCE and any(
            k in topic_low for k in ("glossary", "definition", "directory", "contact", "acronym", "abbreviation")
        )
        claim_type_str = {
            TableType.STATISTICAL: "metric",
            TableType.REVISION_HISTORY: "revision_history",
            TableType.METADATA_NAVIGATIONAL: "metadata",
        }.get(interp.table_type, "reference" if is_pure_glossary else "policy")

        return pred, claim_text.strip(), modality, modal_op, claim_type_str

    @classmethod
    def enrich_and_generate_claims(
        cls,
        table: CanonicalTable,
        interp: TableSemanticInterpretation,
        envelope_id: uuid.UUID,
        asset_id: str,
    ) -> Tuple[List[AtomicTableFact], List[CandidateClaim]]:
        """
        Generates paired Level 1 AtomicTableFacts and Level 2 Context-Enriched CandidateClaims
        for every row & rule cell in a CanonicalTable.
        """
        atomic_facts: List[AtomicTableFact] = []
        claims: List[CandidateClaim] = []

        ctx = table.context_bundle
        hdr_hierarchy = table.header_hierarchy
        scope_col_names = set(hdr_hierarchy.scope_columns)

        # Collect contextual evidence unit IDs
        ctx_evidence_refs: List[str] = []
        for item in ctx.all_items:
            if item.unit_id and item.unit_id not in ctx_evidence_refs:
                ctx_evidence_refs.append(item.unit_id)

        # Map footnotes by marker
        footnotes_by_marker: Dict[str, str] = {}
        table_wide_notes: List[str] = []
        for fn in ctx.footnotes + ctx.referenced_notes:
            if fn.marker:
                footnotes_by_marker[fn.marker] = fn.text
            else:
                table_wide_notes.append(fn.text)

        is_non_rule_table = interp.table_type in (TableType.REVISION_HISTORY, TableType.METADATA_NAVIGATIONAL)

        for row in table.rows:
            scope_dict = {h: row.cells.get(h, "") for h in hdr_hierarchy.scope_columns if h in row.cells}
            scope_nodes = [hn for hn in hdr_hierarchy.columns if hn.raw_header in scope_col_names]
            subject = cls._compose_entity_subject(scope_dict, scope_nodes, interp)
            raw_row_key = " | ".join(str(v).strip() for v in scope_dict.values() if str(v).strip()) or row.row_id
            if interp.table_type == TableType.REVISION_HISTORY and not subject.lower().startswith("policy"):
                subject = f"Policy version {subject}"
            elif (
                interp.table_type == TableType.METADATA_NAVIGATIONAL
                and len(scope_dict) == 1
                and next(iter(scope_dict.keys())).strip().lower() in {"key", "field", "attribute", "property", "parameter", "item", "label", "document number"}
            ):
                subject = "Policy"

            for h_node in hdr_hierarchy.columns:
                if h_node.raw_header in scope_col_names:
                    continue

                col_name = h_node.raw_header
                norm_val = row.normalized_cells.get(col_name)
                if not norm_val:
                    continue

                # Skip empty non-formula cells cleanly (still tracked in completeness audit)
                if norm_val.data_type == "empty" and not norm_val.formula:
                    continue

                # Skip purely decorative dashes/checkmarks unless explicit boolean
                if not re.sub(r"[\s•●❖\-_|*✓✔✗✘\.]+", "", norm_val.raw_value) and not norm_val.formula:
                    continue

                # 1. Level 1: Atomic Table Fact
                cell_id = f"{table.table_id}_row_{row.row_index}_col_{h_node.col_index}"
                formatted_obj = cls._format_value_with_unit(norm_val, h_node, interp)
                fact = AtomicTableFact(
                    fact_id=f"fact_{cell_id}",
                    subject=raw_row_key,
                    predicate="has_value",
                    object=formatted_obj,
                    table_id=table.table_id,
                    row_id=row.row_id,
                    row_index=row.row_index,
                    column_id=col_name,
                    col_index=h_node.col_index,
                    raw_value=norm_val.raw_value,
                    normalized_value=norm_val.normalized_value,
                    evidence_unit_id=row.unit_id,
                )
                atomic_facts.append(fact)

                # 2. Resolve matched footnotes & exceptions for this cell/header/row-scope
                scope_markers: List[str] = []
                for sn in scope_nodes:
                    s_norm = row.normalized_cells.get(sn.raw_header)
                    if s_norm:
                        scope_markers.extend(s_norm.footnote_markers)
                    scope_markers.extend(sn.footnote_markers)
                active_markers = list(dict.fromkeys(h_node.footnote_markers + norm_val.footnote_markers + scope_markers))
                matched_fn_texts: List[str] = []
                matched_fn_unit_ids: List[str] = []
                for mk in active_markers:
                    if mk in footnotes_by_marker:
                        matched_fn_texts.append(footnotes_by_marker[mk])
                # Also attach table-wide exception notes if applicable to row or whole table
                cell_exceptions: List[str] = []
                for fn in ctx.footnotes + ctx.referenced_notes:
                    if (fn.marker and fn.marker in active_markers) or (not fn.marker):
                        fn_low = fn.text.lower()
                        # Check if note mentions this specific row key or applies generally
                        row_tokens = [t for t in raw_row_key.lower().split() if len(t) > 2]
                        applies_to_row = bool(fn.marker and fn.marker in active_markers) or not row_tokens or any(rt in fn_low for rt in row_tokens) or "all " in fn_low
                        if applies_to_row:
                            if fn.unit_id and fn.unit_id not in matched_fn_unit_ids:
                                matched_fn_unit_ids.append(fn.unit_id)
                            if any(w in fn_low for w in ("except", "unless", "exclude", "excluding", "not eligible", "prohibited")):
                                if fn.text not in cell_exceptions:
                                    cell_exceptions.append(fn.text)
                            elif fn.text not in matched_fn_texts:
                                matched_fn_texts.append(fn.text)

                conditions = cls._build_structured_conditions(
                    scope_dict=scope_dict,
                    header_node=h_node,
                    norm_val=norm_val,
                    interp=interp,
                    matched_footnotes=matched_fn_texts,
                )

                # 3. Level 2: Context-Enriched SPO Claim
                pred, claim_text, modality, modal_op, claim_type_str = cls._derive_context_aware_spo(
                    subject=subject,
                    scope_dict=scope_dict,
                    header_node=h_node,
                    norm_val=norm_val,
                    formatted_obj=formatted_obj,
                    interp=interp,
                    conditions=conditions,
                    exceptions=cell_exceptions,
                )

                # Build complete evidence_refs (cell + row + scope cells + title/caption/footnotes)
                scope_cell_ids = [
                    f"{table.table_id}_row_{row.row_index}_col_{sn.col_index}"
                    for sn in scope_nodes
                ]
                all_ev_refs = list(dict.fromkeys(
                    scope_cell_ids + [cell_id, row.unit_id] + ctx_evidence_refs + matched_fn_unit_ids
                ))

                v_type_map = {
                    "duration": "DURATION",
                    "percentage": "PERCENTAGE",
                    "currency": "CURRENCY",
                    "date": "CALENDAR_DEADLINE",
                    "boolean": "BOOLEAN",
                }
                tv_type = v_type_map.get(norm_val.data_type, "TEXT_RULE")
                num_val = (
                    float(norm_val.normalized_value)
                    if isinstance(norm_val.normalized_value, (int, float)) and not isinstance(norm_val.normalized_value, bool)
                    else None
                )

                table_binding = TableGridBinding(
                    table_id=table.table_id,
                    row_key=raw_row_key,
                    column_header=col_name,
                    cell_value=norm_val.raw_value,
                    normalized_value=norm_val.normalized_value,
                    normalized_unit=norm_val.unit or h_node.embedded_unit,
                    row_index=row.row_index,
                    col_index=h_node.col_index,
                    is_merged_cell=norm_val.is_inherited,
                    is_inherited=norm_val.is_inherited,
                    is_original_blank=norm_val.is_original_blank,
                    formula=norm_val.formula,
                    header_hierarchy=h_node.header_path,
                    qualifiers=list(norm_val.qualifiers),
                    typed_value=TypedValue(
                        value_type=tv_type,
                        scalar_min=norm_val.range_min if norm_val.range_min is not None else num_val,
                        scalar_max=norm_val.range_max if norm_val.range_max is not None else num_val,
                        unit=norm_val.unit or h_node.embedded_unit or norm_val.currency_code,
                        qualifier=norm_val.qualifiers[0] if norm_val.qualifiers else None,
                        raw_text=norm_val.raw_value,
                    ),
                )

                field_bindings = [
                    FieldEvidenceBinding(field="subject", value=subject, evidence_span=raw_row_key),
                    FieldEvidenceBinding(field="object", value=formatted_obj, evidence_span=norm_val.raw_value),
                ]

                grid_coords = {
                    "table_type": interp.table_type.value,
                    "row_key": raw_row_key,
                    "row_scope": scope_dict,
                    "col_header": col_name,
                    "header_hierarchy": h_node.header_path,
                    "cell_value": norm_val.raw_value,
                    "unit": norm_val.unit or h_node.embedded_unit,
                    "qualifiers": norm_val.qualifiers,
                }

                merged_locator = dict(row.locator)
                merged_locator.update({
                    "table_id": table.table_id,
                    "table_title": ctx.table_title.text if ctx.table_title else None,
                    "table_caption": ctx.table_caption.text if ctx.table_caption else None,
                    "col_header": col_name,
                    "header_hierarchy": h_node.header_path,
                    "row_key": raw_row_key,
                    "cell_id": cell_id,
                    "table_grid": grid_coords,
                    "in_table": True,
                })

                sem_ctx_dict = {
                    "table_id": table.table_id,
                    "table_type": interp.table_type.value,
                    "business_domain": interp.business_domain,
                    "business_topic": interp.business_topic,
                    "table_purpose": interp.table_purpose,
                    "relationship_type": interp.relationship_type,
                    "value_interpretation": interp.value_interpretation,
                    "table_title": ctx.table_title.text if ctx.table_title else None,
                    "table_caption": ctx.table_caption.text if ctx.table_caption else None,
                    "header_hierarchy": h_node.header_path,
                    "is_ambiguous": interp.is_ambiguous,
                    "missing_context_reasons": interp.missing_context_reasons,
                }

                conf_breakdown = TableConfidenceBreakdown(
                    table_extraction=table.extraction_confidence,
                    table_reconstruction=table.reconstruction_confidence,
                    context_interpretation=interp.semantic_confidence,
                    claim_generation=0.95 if not interp.is_ambiguous else 0.55,
                    evidence_verification=0.95,
                )

                is_ambig = row.is_ambiguous or interp.is_ambiguous or ctx.has_inconsistency or norm_val.is_formula_unavailable
                ambig_reasons = []
                if row.ambiguity_reason:
                    ambig_reasons.append(row.ambiguity_reason)
                if ctx.has_inconsistency:
                    ambig_reasons.extend(ctx.inconsistency_reasons)
                if interp.is_ambiguous and interp.missing_context_reasons:
                    ambig_reasons.extend(interp.missing_context_reasons)
                if norm_val.is_formula_unavailable:
                    ambig_reasons.append(f"Formula '{norm_val.formula}' cached value unavailable.")

                cand = CandidateClaim.create(
                    envelope_id=envelope_id,
                    unit_id=row.unit_id,
                    asset_id=asset_id,
                    claim_text=claim_text,
                    subject=subject,
                    predicate=pred,
                    object_=formatted_obj,
                    value=norm_val.normalized_value,
                    unit=norm_val.unit or h_node.embedded_unit,
                    qualifiers=list(norm_val.qualifiers),
                    modal_operator=modal_op,
                    modality=modality,
                    conditions=conditions,
                    exceptions=cell_exceptions,
                    scope=scope_dict,
                    claim_type=claim_type_str,
                    is_canonical=not is_non_rule_table,
                    content_role=ContentRole.REVISION_HISTORY if is_non_rule_table else ContentRole.POLICY_RULE,
                    extraction_strategy=ExtractionStrategyType.TABLE_AWARE,
                    evidence_text_span=row.raw_text,
                    locator=merged_locator,
                    table_binding=table_binding,
                    typed_value=table_binding.typed_value,
                    evidence_bindings=field_bindings,
                    structured_values={
                        "row_scope": scope_dict,
                        "column": col_name,
                        "header_hierarchy": h_node.header_path,
                        "normalized_cell": norm_val.model_dump(),
                        "atomic_table_fact": fact.model_dump(),
                        "semantic_context": sem_ctx_dict,
                        "evidence_refs": all_ev_refs,
                        "confidence_breakdown": conf_breakdown.model_dump(),
                        "is_formula_unavailable": norm_val.is_formula_unavailable,
                    },
                    is_ambiguous=is_ambig,
                    ambiguity_reason="; ".join(ambig_reasons) if ambig_reasons else None,
                    confidence=round(min(table.extraction_confidence, interp.semantic_confidence, 0.96), 3),
                )
                cand.semantic_context = sem_ctx_dict
                cand.atomic_fact = fact.model_dump()
                cand.evidence_refs = all_ev_refs
                cand.confidence_breakdown = conf_breakdown.model_dump()
                claims.append(cand)

        return atomic_facts, claims

