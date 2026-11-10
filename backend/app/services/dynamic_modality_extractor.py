"""
Dynamic Modality Extractor and Consistency Validator.

Derives modality from clause syntax and validates that normative claim text
faithfully retains the corresponding permission, obligation, or prohibition polarity.
"""

import re
from dataclasses import dataclass
from typing import Optional

from app.schemas.universal_claim import ModalityType


@dataclass
class ModalityExtractionResult:
    modality: ModalityType
    is_consistent: bool
    detected_phrase: str
    error_reason: Optional[str] = None


class DynamicModalityExtractor:
    """Extracts modality from clause text and checks polarity consistency."""

    PROHIBITION_PATTERNS = [
        r"\b(?:may\s+not|must\s+not|shall\s+not|will\s+not|cannot|prohibited\s+from|is\s+not\s+permitted\s+to|is\s+not\s+licensed\s+to|neither\s+party\s+will|neither\s+party\s+shall)\b",
        r"\b(?:no\s+party\s+may|in\s+no\s+event\s+will)\b",
        r"\b(?:cannot\s+claim|shall\s+not\s+be\s+entitled|shall\s+not\s+have\s+any\s+right|are\s+barred\s+from|disqualified\s+from|ineligible\s+for|no\s+claim\s+shall\s+lie)\b",
    ]

    ENTITLEMENT_PATTERNS = [
        r"\b(?:is\s+entitled\s+to|are\s+entitled\s+to|has\s+the\s+right\s+to|have\s+the\s+right\s+to|reserves\s+the\s+right\s+to|reserve\s+the\s+right\s+to)\b",
        r"\b(?:shall\s+be\s+entitled\s+to|shall\s+be\s+eligible\s+for|is\s+eligible\s+to|are\s+eligible\s+to|is\s+entitled\s+to\s+receive|shall\s+have\s+the\s+right\s+to)\b",
    ]

    PERMISSION_PATTERNS = [
        r"\b(?:may|can|authorizes?|grants?|is\s+permitted\s+to|are\s+permitted\s+to)\b",
        r"\b(?:may\s+at\s+its\s+option|shall\s+have\s+discretion\s+to|is\s+authorized\s+to|has\s+the\s+option\s+to)\b",
    ]

    OBLIGATION_PATTERNS = [
        r"\b(?:must|shall|is\s+required\s+to|are\s+required\s+to|agrees\s+to|agree\s+to|is\s+obligated\s+to|are\s+obligated\s+to)\b",
        r"\b(?:will|warrants?|retains?|remains\s+responsible\s+for|is\s+responsible\s+for)\b",
        r"\b(?:payment\s+is\s+due|due\s+and\s+payable|due\s+within|shall\s+pay|must\s+remit|shall\s+indemnify|shall\s+hold\s+harmless|shall\s+give\s+notice|must\s+provide\s+notice)\b",
    ]

    @classmethod
    def extract_modality(cls, text: str) -> ModalityType:
        t_low = (text or "").lower()

        for pat in cls.PROHIBITION_PATTERNS:
            if re.search(pat, t_low):
                return ModalityType.MUST_NOT

        for pat in cls.ENTITLEMENT_PATTERNS:
            if re.search(pat, t_low):
                return ModalityType.ENTITLED_TO

        for pat in cls.PERMISSION_PATTERNS:
            if re.search(pat, t_low):
                return ModalityType.MAY

        for pat in cls.OBLIGATION_PATTERNS:
            if re.search(pat, t_low):
                return ModalityType.MUST

        return ModalityType.CONDITIONAL

    @classmethod
    def validate_consistency(
        cls,
        claim_text: str,
        declared_modality: ModalityType,
        predicate_name: Optional[str] = None,
    ) -> ModalityExtractionResult:
        """
        Validates consistency between claim text, declared modality, and predicate.
        Fails if text lost negation or modal meaning was reversed.
        """
        t_low = (claim_text or "").lower()
        extracted = cls.extract_modality(t_low)

        # Check MUST_NOT: must retain explicit negative polarity
        if declared_modality == ModalityType.MUST_NOT:
            has_negation = any(n in t_low for n in ["not", "n't", "never", "neither", "no ", "without", "prohibit"])
            if not has_negation:
                return ModalityExtractionResult(
                    modality=extracted,
                    is_consistent=False,
                    detected_phrase="affirmative_text",
                    error_reason=f"Modality consistency failure: Declared MUST_NOT prohibition lacks negative polarity in text: '{claim_text[:60]}'.",
                )

        # Check Predicate vs Text Polarity
        if predicate_name:
            pred_low = predicate_name.lower()
            is_prohib_pred = any(
                pred_low == p or pred_low.startswith(f"{p}_") or f"_{p}_" in pred_low
                for p in ["must_not", "prohibited", "shall_not", "may_not"]
            )
            # If prohibition predicate targets a specific object (e.g. agreement) absent from the text,
            # this is an object mismatch evaluated by Gate 4 semantic entailment, not a text integrity failure.
            is_agreement_pred = "agreement" in pred_low or "contract" in pred_low
            has_agreement_in_text = any(w in t_low for w in ["agreement", "contract", "terms", "amendment"])
            if is_prohib_pred and is_agreement_pred and not has_agreement_in_text:
                pass
            else:
                has_negation = any(n in t_low for n in [" not ", "n't ", "never", "neither", "no ", "without", "prohibit"])
                if is_prohib_pred and not has_negation:
                    return ModalityExtractionResult(
                        modality=extracted,
                        is_consistent=False,
                        detected_phrase="missing_negation",
                        error_reason=f"Modality consistency failure: Prohibition predicate '{predicate_name}' contradicts affirmative claim text lacking negation.",
                    )

        return ModalityExtractionResult(
            modality=extracted,
            is_consistent=True,
            detected_phrase=str(extracted.value),
            error_reason=None,
        )
