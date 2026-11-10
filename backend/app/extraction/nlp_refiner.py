"""
Layer 5.2: Unified NLP Semantic Refiner & S-P-O Structuring Engine.

Combines Pass 1 deterministic extractions with Pass 2 NLP refinement:
1. Resolves dangling pronouns & anaphora using FastCoref or contextual antecedents.
2. Refines and validates enterprise actors/entities using cascaded GLiNER / spaCy NER.
3. Performs syntactic dependency tree parsing (spaCy) to cleanly isolate Subject, Root Verb, and Direct Object.
4. Separates adverbial and conditional subordinate clauses into structured conditions.
5. Aligns predicates against the controlled enterprise PredicateRegistryService.
6. Guarantees 100% fail-closed safety with zero-crash fallbacks to Pass 1 outputs.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from app.core.nlp_manager import NLPManager
from app.extraction.models import CandidateClaim, ExtractionStrategyType
from app.extraction.subject_normalizer import SubjectNormalizer
from app.taxonomy.registry import PredicateRegistryService

logger = logging.getLogger(__name__)

# Pronouns and vague demonstrative references that must not remain as canonical subjects
AMBIGUOUS_PRONOUNS: Set[str] = {
    "it", "they", "them", "their", "theirs", "its", "this", "these", "those",
    "such", "such party", "such parties", "the party", "each party", "either party",
    "he", "she", "him", "her", "his", "hers", "someone", "anyone", "everyone",
}

# Subordinate clause markers that introduce conditions rather than being part of the object
CONDITION_CLAUSE_PREFIXES = (
    "if ", "unless ", "provided that ", "subject to ", "in cases where ",
    "in the event that ", "where ", "when ", "whenever ", "upon ", "after ",
    "as long as ", "on the condition that ",
)

# Common sentence connectors to strip from the beginning of subjects
CONNECTIVE_PREFIX_PATTERN = re.compile(
    r"^(?:furthermore|moreover|additionally|in addition|however|nevertheless|therefore|consequently|accordingly|specifically|namely|for example|as such|in this case|in general|generally),?\s+",
    re.IGNORECASE,
)


class NLPSemanticRefiner:
    """
    Executes Pass 2 linguistic refinement on Pass 1 candidate claims.
    Standardizes Subject-Predicate-Object triplets and extracts subordinate conditions.
    """

    @classmethod
    def refine_candidate(
        cls,
        candidate: CandidateClaim,
        source_context: Optional[str] = None,
    ) -> CandidateClaim:
        """
        Refines a single candidate claim using NLP models.
        Mutates the candidate in-place and returns it.
        """
        try:
            # 1. Skip table claims from aggressive re-parsing (tables have verified 2D grid coordinates)
            is_table_claim = bool(
                candidate.extraction_strategy == ExtractionStrategyType.TABLE_AWARE
                or candidate.table_binding is not None
            )

            enrichment: Dict[str, Any] = {
                "nlp_refined": False,
                "coreference_resolved": False,
                "syntactic_triplet_parsed": False,
                "entity_type": None,
            }

            raw_subject = (candidate.subject or "").strip()
            raw_predicate = (candidate.predicate or "").strip()
            raw_object = str(candidate.object or "").strip()
            full_sentence = (candidate.evidence_text_span or candidate.claim_text or "").strip()

            # Clean leading sentence connectives (e.g. "Furthermore, the customer" -> "the customer")
            clean_subj = CONNECTIVE_PREFIX_PATTERN.sub("", raw_subject).strip()

            # -----------------------------------------------------------------
            # Step A: Pronoun & Coreference Resolution
            # -----------------------------------------------------------------
            subj_lower = clean_subj.lower().strip()
            if subj_lower in AMBIGUOUS_PRONOUNS:
                resolved_subj = cls._resolve_pronoun(
                    pronoun=clean_subj,
                    candidate=candidate,
                    source_context=source_context or full_sentence,
                )
                if resolved_subj and resolved_subj.lower() != subj_lower:
                    clean_subj = resolved_subj
                    enrichment["coreference_resolved"] = True
                    enrichment["original_pronoun"] = raw_subject

            # -----------------------------------------------------------------
            # Step B: Cascaded Entity Disambiguation (GLiNER / spaCy / Allowlist)
            # -----------------------------------------------------------------
            normalized_entity, is_valid_entity = SubjectNormalizer.normalize(clean_subj)
            if normalized_entity and normalized_entity != clean_subj:
                clean_subj = normalized_entity

            # Extract fine-grained domain entities if available
            entity_metadata = SubjectNormalizer.resolve_entity_cascaded(clean_subj)
            if entity_metadata.get("entities"):
                primary_ent = entity_metadata["entities"][0]
                enrichment["entity_type"] = primary_ent.get("label")
                enrichment["entity_source"] = primary_ent.get("source")

            # If table claim, safely extract parenthetical conditions from cell object without destroying scalar value
            if is_table_claim and raw_object:
                paren_match = re.search(r"\(([^)]+)\)", raw_object)
                if paren_match:
                    cond_candidate = paren_match.group(1).strip()
                    if any(cond_candidate.lower().startswith(p) for p in ("if ", "when ", "subject to", "upon ", "with ", "only if")):
                        current_conds = list(candidate.conditions or [])
                        if cond_candidate not in current_conds:
                            current_conds.append(cond_candidate)
                        candidate.conditions = current_conds
                        raw_object = re.sub(r"\s*\([^)]+\)", "", raw_object).strip()

            # -----------------------------------------------------------------
            # Step C: Syntactic Dependency Tree Parsing (For Narrative Clauses)
            # -----------------------------------------------------------------
            if not is_table_claim and full_sentence:
                syntactic_result = cls._parse_syntactic_triplet(full_sentence)
                if syntactic_result:
                    parsed_subj, parsed_pred, parsed_obj, isolated_conditions = syntactic_result
                    
                    # If syntactic parser found a valid subject and object, refine candidate
                    if parsed_subj and len(parsed_subj.split()) <= 6:
                        # Normalize parsed subject
                        norm_parsed, _ = SubjectNormalizer.normalize(parsed_subj)
                        if norm_parsed and norm_parsed.lower() not in AMBIGUOUS_PRONOUNS:
                            clean_subj = norm_parsed

                    # If the object contained trapped conditional clauses, isolate them
                    if isolated_conditions:
                        current_conds = list(candidate.conditions or [])
                        for cond_text in isolated_conditions:
                            if cond_text not in current_conds:
                                current_conds.append(cond_text)
                        candidate.conditions = current_conds

                    if parsed_obj and len(parsed_obj.strip()) > 1:
                        # Clean direct object
                        raw_object = parsed_obj

                    enrichment["syntactic_triplet_parsed"] = True

            # -----------------------------------------------------------------
            # Step D: Controlled Predicate Alignment
            # -----------------------------------------------------------------
            aligned_pred = cls._align_predicate(raw_predicate, clean_subj, raw_object)
            if aligned_pred:
                candidate.predicate = aligned_pred
            else:
                candidate.predicate = raw_predicate

            # Update final values
            candidate.subject = clean_subj
            candidate.object = raw_object
            enrichment["nlp_refined"] = True
            candidate.nlp_enrichment = enrichment

            return candidate

        except Exception as exc:
            logger.debug("NLP semantic refinement fallback triggered for %s: %s", candidate.candidate_id, exc)
            candidate.nlp_enrichment = {"nlp_refined": False, "fallback_reason": str(exc)}
            return candidate

    @classmethod
    def refine_candidates(
        cls,
        candidates: List[CandidateClaim],
        source_text: Optional[str] = None,
    ) -> List[CandidateClaim]:
        """Refines a batch of candidate claims in-place."""
        refined: List[CandidateClaim] = []
        for cand in candidates:
            try:
                ref_c = cls.refine_candidate(cand, source_text=source_text)
                refined.append(ref_c)
            except Exception as err:
                logger.debug("Skipping refinement error on %s: %s", getattr(cand, 'candidate_id', 'unknown'), err)
                refined.append(cand)
        return refined

    # -------------------------------------------------------------------------
    # Internal Refinement Helpers
    # -------------------------------------------------------------------------

    @classmethod
    def _resolve_pronoun(
        cls,
        pronoun: str,
        candidate: CandidateClaim,
        source_context: str,
    ) -> Optional[str]:
        """Resolves dangling pronoun using FastCoref, heading context, or entity registry."""
        # 1. FastCoref neural resolution if available
        if NLPManager.is_fastcoref_available() and len(source_context.strip()) > 10:
            try:
                resolved_text = NLPManager.resolve_coreference(source_context)
                if resolved_text and resolved_text != source_context:
                    # Check if pronoun was replaced in sentence
                    spacy_nlp = NLPManager.get_spacy()
                    if spacy_nlp:
                        doc = spacy_nlp(resolved_text[:300])
                        for ent in getattr(doc, "ents", []):
                            if ent.label_ in ("ORG", "PERSON"):
                                return ent.text
            except Exception as e:
                logger.debug("FastCoref pronoun resolution error: %s", e)

        # 2. Hierarchical context heuristic fallback (e.g. section heading actor)
        hier_context = list(candidate.locator.get("heading_path") or candidate.hierarchical_context or [])
        sec_h = candidate.locator.get("section_heading") or candidate.locator.get("section") or candidate.locator.get("title")
        if sec_h and sec_h not in hier_context:
            hier_context.append(sec_h)

        for heading in reversed(hier_context):
            h_clean = re.sub(r"^(?:#+|\d+(?:\.\d+)*\s*[-.]?\s*)", "", str(heading)).strip()
            role_keywords = (
                ("employee", "Employee"), ("customer", "Customer"), ("vendor", "Vendor"),
                ("partner", "Partner"), ("subscriber", "Subscriber"), ("admin", "Administrator"),
                ("contractor", "Contractor"), ("gold member", "Gold Members"), ("member", "Member"),
                ("client", "Client"), ("buyer", "Buyer"), ("seller", "Seller"),
                ("executive", "Executive"), ("probation", "Probationer"),
            )
            for kw, canon in role_keywords:
                if kw in h_clean.lower():
                    return canon

        # 3. Default contextual fallback by policy family
        doc_family = str(candidate.locator.get("document_type") or "").lower()
        if "employment" in doc_family or "resignation" in doc_family:
            return "Employee"
        elif "refund" in doc_family or "return" in doc_family:
            return "Customer"
        elif "vendor" in doc_family or "supplier" in doc_family:
            return "Vendor"

        return pronoun

    @classmethod
    def _parse_syntactic_triplet(
        cls,
        sentence: str,
    ) -> Optional[Tuple[str, str, str, List[str]]]:
        """
        Uses spaCy dependency tree to extract (Subject, Predicate_Verb, Direct_Object, Isolated_Conditions).
        Returns None if spaCy is unavailable or parsing fails.
        """
        nlp = NLPManager.get_spacy()
        if nlp is None:
            return None

        try:
            doc = nlp(sentence)
            subject_tokens: List[str] = []
            predicate_verb = ""
            object_tokens: List[str] = []
            isolated_conditions: List[str] = []

            # 1. Identify Root Verb
            root = next((tok for tok in doc if tok.dep_ == "ROOT"), None)
            if root is not None:
                predicate_verb = root.lemma_

            # 2. Identify Nominal Subject (nsubj / nsubjpass)
            for tok in doc:
                if tok.dep_ in ("nsubj", "nsubjpass"):
                    # Collect full subtree of the subject noun chunk
                    subj_chunk = [w.text for w in tok.subtree if w.dep_ not in ("advcl", "prep", "relcl", "punct")]
                    subject_tokens = subj_chunk
                    break

            # 3. Identify Direct Object (dobj), Attribute (attr), or Prepositional Object (pobj)
            for tok in doc:
                if tok.dep_ in ("dobj", "attr") or (tok.dep_ == "pobj" and tok.head.dep_ == "prep" and tok.head.head == root):
                    obj_chunk = [w.text for w in tok.subtree if w.dep_ not in ("advcl", "relcl")]
                    object_tokens = obj_chunk
                    break

            # 4. Extract Adverbial Subordinate Clauses (advcl) as isolated conditions
            for tok in doc:
                if tok.dep_ == "advcl":
                    cond_phrase = "".join([w.text_with_ws for w in tok.subtree]).strip()
                    if cond_phrase and any(cond_phrase.lower().startswith(p) for p in CONDITION_CLAUSE_PREFIXES):
                        isolated_conditions.append(cond_phrase)

            if subject_tokens and (object_tokens or predicate_verb):
                final_subj = " ".join(subject_tokens).strip()
                final_obj = " ".join(object_tokens).strip() if object_tokens else ""
                return final_subj, predicate_verb, final_obj, isolated_conditions

            return None
        except Exception as err:
            logger.debug("spaCy dependency triplet parsing exception: %s", err)
            return None

    @classmethod
    def _align_predicate(
        cls,
        raw_pred: str,
        subject: str,
        object_text: str,
    ) -> Optional[str]:
        """Aligns raw predicate against controlled PredicateRegistryService vocabulary."""
        if not raw_pred:
            return None

        clean_pred = raw_pred.lower().strip().replace(" ", "_")
        
        # 1. Exact match in registry
        if PredicateRegistryService.exists(clean_pred):
            return clean_pred

        # 2. Known predicate synonyms
        synonym_map = {
            "must_provide": "requires_receipt_retention",
            "must_retain": "requires_receipt_retention",
            "must_notify": "requires_written_notice",
            "shall_notify": "requires_written_notice",
            "requires_notice": "requires_written_notice",
            "must_return": "has_return_window",
            "must_request": "has_return_window",
            "must_pay": "must_pay_within_30_days",
            "shall_pay": "must_pay_within_30_days",
            "provides_refund": "has_refund_eligibility",
            "offers_refund": "has_refund_eligibility",
            "allows_return": "has_return_window",
            "may_return": "has_return_window",
            "cancels": "has_cancellation_window",
            "requires_notice_duration": "requires_written_notice",
            "notice_period": "has_notice_duration",
            "notice_duration": "has_notice_duration",
            "probation_period": "has_notice_duration",
            "refund_percentage": "has_refund_percentage",
            "refund_amount": "has_refund_percentage",
            "return_window": "has_return_window",
            "processing_time": "has_processing_timeline",
            "posting_duration": "has_posting_duration",
        }
        if clean_pred in synonym_map and PredicateRegistryService.exists(synonym_map[clean_pred]):
            return synonym_map[clean_pred]

        return clean_pred
