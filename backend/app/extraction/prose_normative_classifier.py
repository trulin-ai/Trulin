"""
Layer 5: Prose Normative Classifier.
Applies Filters P1–P4 to classify prose document units (block_type != "table_row")
into normative policy rules vs non-normative context (promotional, capability, hedging)
and lexical definitions.
"""

from __future__ import annotations

import re
from typing import Optional

from app.ingestion.parsers.evidence_model import ContentRole


class ProseNormativeClassifier:
    """Classifies prose text into ContentRole (POLICY_RULE, NON_RULE_CONTEXT, DEFINITION)."""

    # Prose Filter P1: Hedging / promotional language → Non-Rule Context
    HEDGING_PATTERNS = [
        r"\bcan provide\b",
        r"\bincreasingly\b",
        r"\bthis approach\b",
        r"\bwe recommend\b",
        r"\bcan help\b",
        r"\bmay help\b",
    ]

    # Prose Filter P3: Capability descriptions → Non-Rule Context
    CAPABILITY_PATTERNS = [
        r"\byou can enable\b",
        r"\byou can create\b",
        r"\byou can manage\b",
        r"\byou can build\b",
    ]

    # Prose Filter P2: Definitional patterns → ContentRole.DEFINITION
    DEFINITIONAL_PATTERNS = [
        r"^([A-Z][\w\s\-]+?)\s+[-–—]\s+(.+)$",  # "X - Y" glossary style
        r"^(?!Where\b|When\b|If\b|Unless\b|While\b)([A-Z][\w\s]{1,40}?)\s+is\s+(defined as|a|an|the|any)\s+(.+)$",  # "X is Y" definitional
    ]

    # Prose Filter P4: Deontic/normative language → eligible for Verified
    NORMATIVE_PATTERNS = [
        r"\bmust\b",
        r"\bshall\b",
        r"\brequired\b",
        r"\bonly possible with\b",
        r"\bcan approve or deny\b",
        r"\bis required\b",
    ]

    @classmethod
    def classify(cls, text: str, default_role: ContentRole = ContentRole.POLICY_RULE) -> ContentRole:
        """
        Classifies prose text into a ContentRole.
        Strict precedence:
        1. P1: Hedging / promotional language -> NON_RULE_CONTEXT
        2. P3: Capability descriptions -> NON_RULE_CONTEXT
        3. P2: Definitional patterns -> DEFINITION
        4. P4: Deontic / normative obligations -> POLICY_RULE
        5. Default: default_role
        """
        if not text:
            return default_role

        clean_text = text.strip()

        # P1: Hedging / promotional language → Non-Rule Context
        if any(re.search(p, clean_text, re.IGNORECASE) for p in cls.HEDGING_PATTERNS):
            return ContentRole.NON_RULE_CONTEXT

        # P3: Capability descriptions → Non-Rule Context
        if any(re.search(p, clean_text, re.IGNORECASE) for p in cls.CAPABILITY_PATTERNS):
            return ContentRole.NON_RULE_CONTEXT

        # P2: Definitional patterns → DEFINITION
        if any(re.match(p, clean_text) for p in cls.DEFINITIONAL_PATTERNS):
            return ContentRole.DEFINITION

        # P4: Deontic/normative language → POLICY_RULE
        if any(re.search(p, clean_text, re.IGNORECASE) for p in cls.NORMATIVE_PATTERNS):
            return ContentRole.POLICY_RULE

        return default_role

    @classmethod
    def classify_unit(cls, text: str, default_role: ContentRole = ContentRole.POLICY_RULE) -> ContentRole:
        """
        Classifies a multi-sentence evidence unit.
        Preserves POLICY_RULE if any sentence contains operative policy obligations,
        ensuring candidate extractors process them without paragraph-level poisoning.
        """
        if not text:
            return default_role

        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
        if len(sentences) <= 1:
            return cls.classify(text, default_role=default_role)

        sentence_roles = [cls.classify(s, default_role=default_role) for s in sentences]
        if any(r == ContentRole.POLICY_RULE for r in sentence_roles):
            return ContentRole.POLICY_RULE
        if any(r == ContentRole.DEFINITION for r in sentence_roles):
            return ContentRole.DEFINITION
        if any(r == ContentRole.NON_RULE_CONTEXT for r in sentence_roles):
            return ContentRole.NON_RULE_CONTEXT
        return default_role
