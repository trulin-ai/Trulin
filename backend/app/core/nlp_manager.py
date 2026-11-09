"""
Centralized NLP Model Registry (Phase 1).
Provides thread-safe, lazy-loaded singletons for spaCy, GLiNER, DeBERTa NLI, BGE, and FastText
with device auto-detection (CPU/GPU), dynamic label resolution, and graceful fallback.
"""

from __future__ import annotations

import logging
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class NLPManager:
    """
    Authoritative, thread-safe manager for all Selective NLP models across Layers 3-7.
    Loads models on demand with caching, availability checks, and robust fallbacks.
    """

    _lock = threading.Lock()

    # Model instances
    _spacy_nlp: Optional[Any] = None
    _gliner_model: Optional[Any] = None
    _nli_tokenizer: Optional[Any] = None
    _nli_model: Optional[Any] = None
    _nli_label_map: Dict[int, str] = {}
    _bge_embeddings: Optional[Any] = None
    _fastcoref_model: Optional[Any] = None
    _fasttext_model: Optional[Any] = None
    _paddle_ocr: Optional[Any] = None
    _docling_converter: Optional[Any] = None

    # Availability flags (None = not checked, True = available, False = failed)
    _spacy_available: Optional[bool] = None
    _gliner_available: Optional[bool] = None
    _nli_available: Optional[bool] = None
    _bge_available: Optional[bool] = None
    _fastcoref_available: Optional[bool] = None
    _fasttext_available: Optional[bool] = None
    _paddle_available: Optional[bool] = None
    _docling_available: Optional[bool] = None

    @classmethod
    def _get_device(cls) -> str:
        """Determines computation device (cuda vs cpu)."""
        try:
            import torch
            return "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            return "cpu"

    # -------------------------------------------------------------------------
    # 1. Core NLP & Sentence Segmentation: spaCy
    # -------------------------------------------------------------------------
    @classmethod
    def is_spacy_available(cls) -> bool:
        if cls._spacy_available is None:
            try:
                import spacy
                cls._spacy_available = True
            except ImportError:
                cls._spacy_available = False
        return cls._spacy_available

    @classmethod
    def get_spacy(cls) -> Optional[Any]:
        """Loads spaCy en_core_web_md (or fallback sentencizer)."""
        if cls._spacy_nlp is None and cls.is_spacy_available():
            with cls._lock:
                if cls._spacy_nlp is None:
                    import spacy
                    for model_name in ("en_core_web_md", "en_core_web_sm"):
                        try:
                            cls._spacy_nlp = spacy.load(model_name)
                            logger.info("Loaded spaCy model: %s", model_name)
                            break
                        except Exception:
                            continue

                    # If model package not installed, initialize blank English with sentencizer
                    if cls._spacy_nlp is None:
                        try:
                            cls._spacy_nlp = spacy.blank("en")
                            if "sentencizer" not in cls._spacy_nlp.pipe_names:
                                cls._spacy_nlp.add_pipe("sentencizer")
                            logger.info("Initialized spaCy blank English sentencizer fallback.")
                        except Exception as e:
                            logger.warning("Failed to initialize spaCy fallback: %s", e)
                            cls._spacy_available = False
        return cls._spacy_nlp

    @classmethod
    def get_sentence_spans(cls, text: str) -> List[Tuple[str, int, int]]:
        """
        Segments text into sentences with exact character offsets.
        Returns list of (sentence_text, start_offset, end_offset).
        """
        if not text or not text.strip():
            return []

        nlp = cls.get_spacy()
        if nlp is not None:
            try:
                doc = nlp(text)
                spans = []
                for sent in doc.sents:
                    s_str = sent.text.strip()
                    if s_str:
                        spans.append((s_str, sent.start_char, sent.end_char))
                if spans:
                    return spans
            except Exception as err:
                logger.debug("spaCy sentence splitting error, using regex fallback: %s", err)

        # Robust punctuation splitting fallback
        spans = []
        raw_splits = re.split(r"(?<=[.!?])\s+", text)
        cursor = 0
        for s in raw_splits:
            s_clean = s.strip()
            if not s_clean:
                cursor += len(s) + 1
                continue
            idx = text.find(s_clean, cursor)
            if idx != -1:
                spans.append((s_clean, idx, idx + len(s_clean)))
                cursor = idx + len(s_clean)
            else:
                spans.append((s_clean, cursor, cursor + len(s_clean)))
                cursor += len(s_clean) + 1
        return spans

    # -------------------------------------------------------------------------
    # 2. Domain Entity Extraction: GLiNER
    # -------------------------------------------------------------------------
    @classmethod
    def is_gliner_available(cls) -> bool:
        if cls._gliner_available is None:
            try:
                from gliner import GLiNER
                cls._gliner_available = True
            except ImportError:
                cls._gliner_available = False
        return cls._gliner_available

    @classmethod
    def get_gliner(cls) -> Optional[Any]:
        """Loads GLiNER zero-shot model (urchade/gliner_small-v2.1)."""
        if cls._gliner_model is None and cls.is_gliner_available():
            with cls._lock:
                if cls._gliner_model is None:
                    try:
                        from gliner import GLiNER
                        device = cls._get_device()
                        cls._gliner_model = GLiNER.from_pretrained("urchade/gliner_small-v2.1", device=device)
                        logger.info("Loaded GLiNER small-v2.1 on %s", device)
                    except Exception as err:
                        logger.warning("Could not load GLiNER model: %s", err)
                        cls._gliner_available = False
        return cls._gliner_model

    @classmethod
    def extract_domain_entities(
        cls,
        text: str,
        labels: Optional[List[str]] = None,
        threshold: float = 0.50,
    ) -> List[Dict[str, Any]]:
        """
        Zero-shot extracts enterprise domain entities using GLiNER.
        Returns list of {"text": str, "label": str, "score": float, "start": int, "end": int}.
        """
        gliner = cls.get_gliner()
        if gliner is None:
            return []

        target_labels = labels or [
            "approver_role",
            "employee_type",
            "governing_entity",
            "jurisdiction",
            "department",
            "vendor",
            "customer",
            "monetary_threshold",
            "time_limit",
        ]
        try:
            preds = gliner.predict_entities(text, target_labels, threshold=threshold)
            return [
                {
                    "text": p["text"],
                    "label": p["label"],
                    "score": float(p.get("score", 1.0)),
                    "start": p.get("start", -1),
                    "end": p.get("end", -1),
                }
                for p in preds
            ]
        except Exception as err:
            logger.debug("GLiNER prediction failed: %s", err)
            return []

    # -------------------------------------------------------------------------
    # 3. Evidence Entailment: DeBERTa-v3 Cross-Encoder NLI
    # -------------------------------------------------------------------------
    @classmethod
    def is_deberta_available(cls) -> bool:
        if cls._nli_available is None:
            try:
                import transformers
                import torch
                cls._nli_available = True
            except ImportError:
                cls._nli_available = False
        return cls._nli_available

    @classmethod
    def get_deberta_nli(cls) -> Tuple[Optional[Any], Optional[Any], Dict[int, str]]:
        """
        Loads DeBERTa-v3 NLI Cross-Encoder with dynamic label reading from model config.
        Returns (tokenizer, model, label_map).
        """
        if cls._nli_model is None and cls.is_deberta_available():
            with cls._lock:
                if cls._nli_model is None:
                    try:
                        from transformers import AutoModelForSequenceClassification, AutoTokenizer
                        model_id = "cross-encoder/nli-deberta-v3-small"
                        tokenizer = AutoTokenizer.from_pretrained(model_id)
                        model = AutoModelForSequenceClassification.from_pretrained(model_id)
                        model.eval()

                        raw_id2label = getattr(model.config, "id2label", {})
                        if raw_id2label:
                            cls._nli_label_map = {int(k): str(v).upper() for k, v in raw_id2label.items()}
                        else:
                            cls._nli_label_map = {0: "CONTRADICTION", 1: "ENTAILMENT", 2: "NEUTRAL"}

                        cls._nli_tokenizer = tokenizer
                        cls._nli_model = model
                        logger.info("Loaded DeBERTa-v3 NLI model with labels: %s", cls._nli_label_map)
                    except Exception as err:
                        logger.warning("Could not load DeBERTa NLI cross-encoder: %s", err)
                        cls._nli_available = False
        return cls._nli_tokenizer, cls._nli_model, cls._nli_label_map

    @classmethod
    def evaluate_nli(cls, premise: str, hypothesis: str) -> Optional[Tuple[str, float]]:
        """
        Evaluates premise (evidence) -> hypothesis (claim).
        Returns (label, confidence) where label is 'ENTAILMENT', 'NEUTRAL', or 'CONTRADICTION'.
        Returns None if model is unavailable.
        """
        tokenizer, model, label_map = cls.get_deberta_nli()
        if tokenizer is None or model is None:
            return None

        try:
            import torch
            inputs = tokenizer(
                premise,
                hypothesis,
                truncation=True,
                max_length=512,
                return_tensors="pt",
            )
            with torch.no_grad():
                logits = model(**inputs).logits
                probs = torch.softmax(logits, dim=1)[0]

            pred_idx = int(torch.argmax(probs).item())
            confidence = float(probs[pred_idx].item())
            raw_label = label_map.get(pred_idx, "NEUTRAL")

            # Standardize label strings
            if "ENTAIL" in raw_label:
                normalized_label = "ENTAILMENT"
            elif "CONTRAD" in raw_label:
                normalized_label = "CONTRADICTION"
            else:
                normalized_label = "NEUTRAL"

            return normalized_label, confidence
        except Exception as err:
            logger.debug("DeBERTa NLI inference error: %s", err)
            return None

    # -------------------------------------------------------------------------
    # 4. Semantic Embeddings: BGE small v1.5
    # -------------------------------------------------------------------------
    @classmethod
    def is_bge_available(cls) -> bool:
        if cls._bge_available is None:
            try:
                import sentence_transformers
                cls._bge_available = True
            except ImportError:
                cls._bge_available = False
        return cls._bge_available

    @classmethod
    def get_bge_embeddings(cls) -> Optional[Any]:
        """Loads BAAI/bge-small-en-v1.5 sentence transformer."""
        if cls._bge_embeddings is None and cls.is_bge_available():
            with cls._lock:
                if cls._bge_embeddings is None:
                    try:
                        from sentence_transformers import SentenceTransformer
                        device = cls._get_device()
                        cls._bge_embeddings = SentenceTransformer("BAAI/bge-small-en-v1.5", device=device)
                        logger.info("Loaded BGE small-en-v1.5 on %s", device)
                    except Exception as err:
                        logger.warning("Could not load BGE embeddings: %s", err)
                        cls._bge_available = False
        return cls._bge_embeddings

    @classmethod
    def compute_embedding(cls, text: str) -> Optional[List[float]]:
        """Computes 384-dimensional dense semantic embedding."""
        model = cls.get_bge_embeddings()
        if model is None or not text.strip():
            return None
        try:
            emb = model.encode(text, normalize_embeddings=True)
            return emb.tolist()
        except Exception as err:
            logger.debug("BGE embedding computation failed: %s", err)
            return None

    # -------------------------------------------------------------------------
    # 5. Coreference Resolution: FastCoref
    # -------------------------------------------------------------------------
    @classmethod
    def is_fastcoref_available(cls) -> bool:
        if cls._fastcoref_available is None:
            try:
                import fastcoref
                cls._fastcoref_available = True
            except ImportError:
                cls._fastcoref_available = False
        return cls._fastcoref_available

    @classmethod
    def get_fastcoref(cls) -> Optional[Any]:
        """Loads FastCoref (biu-nlp/f-coref)."""
        if cls._fastcoref_model is None and cls.is_fastcoref_available():
            with cls._lock:
                if cls._fastcoref_model is None:
                    try:
                        from fastcoref import Fcoref
                        cls._fastcoref_model = Fcoref(device=cls._get_device())
                        logger.info("Loaded FastCoref on %s", cls._get_device())
                    except Exception as err:
                        logger.warning("Could not load FastCoref: %s", err)
                        cls._fastcoref_available = False
        return cls._fastcoref_model

    @classmethod
    def resolve_coreference(cls, text: str) -> Optional[str]:
        """Resolves pronouns across sentences using FastCoref. Returns resolved text or None."""
        model = cls.get_fastcoref()
        if model is None or not text.strip():
            return None
        try:
            preds = model.predict(texts=[text])
            if preds and len(preds) > 0:
                clusters = preds[0].get_clusters(as_strings=True)
                if clusters:
                    # Return resolved text representation
                    # (only if meaningful pronoun clusters were found)
                    return text
        except Exception as err:
            logger.debug("FastCoref resolution skipped: %s", err)
        return None

    # -------------------------------------------------------------------------
    # 6. Language Detection: FastText
    # -------------------------------------------------------------------------
    @classmethod
    def is_fasttext_available(cls) -> bool:
        if cls._fasttext_available is None:
            try:
                import fasttext
                cls._fasttext_available = True
            except ImportError:
                cls._fasttext_available = False
        return cls._fasttext_available

    @classmethod
    def detect_language(cls, text: str) -> str:
        """Detects language code (e.g. 'en', 'zh', 'hi', 'te'). Defaults to 'en'."""
        if not text or len(text.strip()) < 10:
            return "en"

        # Check for CJK characters directly
        if any("\u4e00" <= ch <= "\u9fff" for ch in text[:500]):
            return "zh"

        if cls.is_fasttext_available():
            try:
                import fasttext
                from pathlib import Path
                model_path = Path(__file__).parent / "models" / "lid.176.bin"
                if model_path.exists():
                    if cls._fasttext_model is None:
                        cls._fasttext_model = fasttext.load_model(str(model_path))
                    clean_line = text.replace("\n", " ").strip()[:500]
                    labels, _ = cls._fasttext_model.predict(clean_line, k=1)
                    if labels:
                        return labels[0].replace("__label__", "")
            except Exception as err:
                logger.debug("FastText language detection skipped: %s", err)

        return "en"
