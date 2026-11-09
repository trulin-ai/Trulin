# 🧠 Context Trust Layer: Final Authoritative Selective NLP Implementation Plan
## Claims & Evidence Extraction Engine (Layers 3–7)

> **Document Status**: Final Authoritative Engineering Specification & Implementation Blueprint  
> **Scope**: Layers 3, 4, 5, 6, and 7 (with supporting scoping in Layers 1 & 2)  
> **Strictly Untouched**: Layers 8, 9, 10, and 11 (Trust Scoring, Conflict Engine, HITL Queue, MCP Decision Gate)  
> **Target Acceptance Metrics**: Claim Precision $\ge 95\%$, Evidence Grounding $\ge 99\%$, Condition Preservation $\ge 98\%$, Unsupported Claim Rate $\approx 0\%$

---

## 1. Executive Summary & Architectural Scope

The **Context Trust Layer (CTL)** extracts atomic, machine-readable claims with tamper-proof evidence provenance from heterogeneous enterprise assets (PDFs, DOCX, Markdown, Slack threads, Jira tickets, CSV/Excel spreadsheets, databases, and JSON/XML records).

This plan operationalizes the **Selective NLP Architecture** across the existing 11-layer design:
1. **Zero Architecture Changes**: Preserves the 11 authoritative layers without introducing intermediate or auxiliary layers.
2. **Selective Execution Cascade**: Fast deterministic rules run first. Deep transformers (`Docling`, `GLiNER`, `DeBERTa-v3`, `FastCoref`) execute conditionally only when required by formatting, domain ambiguity, or relational complexity.
3. **Decoupled Claim & Evidence Invariant**: Verbatim source evidence (`ImmutableEvidenceUnit`) and semantic structured propositions (`CanonicalClaim`) remain independently modeled and linked via stable UUID foreign keys.
4. **Condition & Threshold Preservation**: A claim is invalid if it drops qualifying conditions (e.g., "12 months continuous service"), alters numerical thresholds (e.g., ₹10,000), or reverses deontic force.
5. **Conflict Engine Strictly Untouched**: No changes to cross-document conflict detection, version contradiction, or HITL resolution in this phase.

---

## 2. Comprehensive Layer-by-Layer NLP Mapping

```
┌──────────────────────────────────────────────────────────────────────────────────────────────────┐
│ LAYER                                   │ NLP MODELS & IMPLEMENTATION RESPONSIBILITY             │
├─────────────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Layer 1: Data Source Governance         │ FastText (lid.176.bin) language detection, Pydantic v2 │
│ Layer 2: Native Connector Discovery     │ Connector SDKs, SHA-256 byte hashing, schema validation│
│ Layer 3: Canonical Source Envelope      │ Multi-format envelope preservation, byte offsets       │
│ Layer 4: Specialized Source Parsing     │ Docling, PyMuPDF, Per-Page PaddleOCR, Table AST Parser │
│ Layer 5: Candidate Extraction & Deontic │ spaCy (en_core_web_md), GLiNER, Regex, BGE, FastCoref │
│ Layer 6: Multi-Dimensional Validation   │ DeBERTa-v3 NLI, Condition Preserver, Numeric Gates     │
│ Layer 7: TEVV Enterprise Benchmark      │ Automated test suite, scikit-learn, precision/grounding│
│ Layer 8: Dynamic Trust Scoring          │ [FROZEN] Existing multi-factor exponential decay       │
│ Layer 9: Cross-Corpus Conflict Detection│ [FROZEN] Existing cross-claim contradiction engine     │
│ Layer 10: HITL Adjudication Queue       │ [FROZEN] Existing human review adjudication queue      │
│ Layer 11: Real-Time Decision Gate       │ [FROZEN] Existing sub-150ms MCP interception engine    │
└──────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Phase 0: Repository Audit & Baseline Findings

### 3.1 Existing Functionality Reused
* **`backend/app/ingestion/envelope.py`**: Sealed `CanonicalSourceEnvelope` model with deterministic SHA-256 hashing.
* **`backend/app/ingestion/parsers/evidence_model.py`**: `ParsedEvidenceUnit`, `ContentRole`, and `ExtractionQualityReport`.
* **`backend/app/schemas/canonical_claim_v3.py`**: Certified 9-gate schema (`SubjectPayload`, `PredicatePayload`, `ConditionV3`, `GatesV3`).
* **`backend/app/extraction/models.py`**: `CandidateClaim`, `Layer5ExtractionResult`, and `CompletenessLedger`.
* **`backend/app/llm/`**: Existing OpenAI and Ollama provider factories (used strictly as fallback).

### 3.2 Gaps & Deficiencies Identified
1. **Lack of Central Model Management**: NLP components were instantiated ad-hoc or approximated with regex.
2. **Whole-Document OCR Trigger**: `UniversalFileParser` evaluated OCR across entire files rather than per page, causing unnecessary overhead or missed scanned pages.
3. **Compound Paragraph Claims**: Lack of spaCy sentence segmentation caused entire multi-rule paragraphs to be extracted as a single entangled claim.
4. **Heuristic NLI Approximations**: `clause_entailment_evaluator.py` approximated entailment using 450 lines of regex keyword rules, causing false positives on negation and dropped conditions.
5. **Dropped Restrictive Conditions**: When extracting primary values (e.g., "24 days leave"), qualifying conditions ("completed 12 months continuous service") were frequently discarded.

---

## 4. Phase 1: Centralized NLP Model Registry & Dependencies

### 4.1 Centralized Model Manager
**File:** `backend/app/core/nlp_manager.py` *(New Component)*

Provides thread-safe, lazy-loaded singletons with device auto-detection (`cuda` / `cpu`), dynamic model configuration, and graceful degradation:

```python
"""
Centralized NLP Model Registry.
Thread-safe lazy initialization for spaCy, GLiNER, DeBERTa NLI, BGE, and FastText.
"""
from __future__ import annotations
import logging
import threading
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

class NLPManager:
    _lock = threading.Lock()
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

    @classmethod
    def get_spacy(cls):
        """Loads spaCy en_core_web_md with sentencizer and parser."""
        if cls._spacy_nlp is None:
            with cls._lock:
                if cls._spacy_nlp is None:
                    import spacy
                    try:
                        cls._spacy_nlp = spacy.load("en_core_web_md")
                    except OSError:
                        logger.warning("Downloading en_core_web_md...")
                        from spacy.cli import download
                        download("en_core_web_md")
                        cls._spacy_nlp = spacy.load("en_core_web_md")
        return cls._spacy_nlp

    @classmethod
    def get_gliner(cls):
        """Loads GLiNER zero-shot entity extractor (urchade/gliner_small-v2.1)."""
        if cls._gliner_model is None:
            with cls._lock:
                if cls._gliner_model is None:
                    from gliner import GLiNER
                    cls._gliner_model = GLiNER.from_pretrained("urchade/gliner_small-v2.1")
        return cls._gliner_model

    @classmethod
    def get_deberta_nli(cls) -> Tuple[Any, Any, Dict[int, str]]:
        """
        Loads DeBERTa-v3 NLI Cross-Encoder and dynamically extracts model label mapping.
        """
        if cls._nli_model is None or cls._nli_tokenizer is None:
            with cls._lock:
                if cls._nli_model is None:
                    from transformers import AutoModelForSequenceClassification, AutoTokenizer
                    model_id = "cross-encoder/nli-deberta-v3-small"
                    cls._nli_tokenizer = AutoTokenizer.from_pretrained(model_id)
                    cls._nli_model = AutoModelForSequenceClassification.from_pretrained(model_id)
                    cls._nli_model.eval()
                    
                    # Dynamically read label mapping from model config
                    raw_id2label = getattr(cls._nli_model.config, "id2label", {})
                    cls._nli_label_map = {
                        int(k): v.upper() for k, v in raw_id2label.items()
                    } if raw_id2label else {0: "CONTRADICTION", 1: "ENTAILMENT", 2: "NEUTRAL"}
        return cls._nli_tokenizer, cls._nli_model, cls._nli_label_map

    @classmethod
    def get_bge_embeddings(cls):
        """Loads BAAI/bge-small-en-v1.5 SentenceTransformer."""
        if cls._bge_embeddings is None:
            with cls._lock:
                if cls._bge_embeddings is None:
                    from sentence_transformers import SentenceTransformer
                    cls._bge_embeddings = SentenceTransformer("BAAI/bge-small-en-v1.5")
        return cls._bge_embeddings

    @classmethod
    def get_fastcoref(cls):
        """Loads FastCoref (biu-nlp/f-coref) for conditional pronoun resolution."""
        if cls._fastcoref_model is None:
            with cls._lock:
                if cls._fastcoref_model is None:
                    from fastcoref import Fcoref
                    cls._fastcoref_model = Fcoref(device="cpu")
        return cls._fastcoref_model
```

### 4.2 Updated Dependency Specification
**File:** `backend/requirements.txt`

```txt
# Fast API & Core
fastapi>=0.110.0
uvicorn[standard]>=0.28.0
pydantic>=2.7.0
pydantic-settings>=2.2.0

# Database & Vectors
sqlalchemy>=2.0.28
asyncpg>=0.29.0
alembic>=1.13.1
pgvector>=0.2.5
psycopg[binary]>=3.1.18

# Core NLP & Tokenization
spacy>=3.7.4
fasttext-wheel>=0.9.2

# Document Layout & OCR
pymupdf>=1.24.0
pymupdf4llm>=0.0.17
docling>=2.0.0
paddleocr>=2.7.3

# Zero-Shot NER & Coreference
gliner>=0.2.0
fastcoref>=2.1.6

# NLI & Embeddings (PyTorch CPU optimized)
torch>=2.2.0 --extra-index-url https://download.pytorch.org/whl/cpu
transformers>=4.40.0
sentence-transformers>=3.0.0

# Document Parsers
python-docx>=1.1.0
openpyxl>=3.1.2
beautifulsoup4>=4.12.3
lxml>=5.1.0
pypdf>=4.1.0
```

---

## 5. Phase 2: Layer 3 Canonical Source & Evidence Foundation

**File:** `backend/app/ingestion/universal_file_parser.py` & `backend/app/ingestion/envelope.py`

1. **Dual Content Representation**:
   * Store `raw_content` (original file byte string) and `normalized_content` (NFKC normalized, cleaned line endings) side by side. Text normalization must never overwrite raw evidence text.
2. **Deterministic Evidence Locator**:
   * Every evidence block retains:
     * `document_uri`: Uniform resource name `urn:doc:{asset_id}`.
     * `source_byte_hash`: SHA-256 of raw document bytes.
     * `page_number`: 1-based physical page index.
     * `char_start` / `char_end`: Exact character offsets in normalized content.
     * `table_locator`: `{"table_id": str, "row_idx": int, "col_idx": int, "header": str}`.
     * `bounding_box`: `[ymin, xmin, ymax, xmax]` for OCR and visually rendered PDFs.

---

## 6. Phase 3: Layer 4 Specialized Document & Table Parsing

### 6.1 Per-Page OCR Decision Heuristic
**File:** `backend/app/ingestion/universal_file_parser.py`

Instead of document-wide heuristics, evaluate OCR necessity per page:

```python
def should_run_page_ocr(page_text: str, page_images: list, page_rect) -> bool:
    """Evaluates whether an individual page requires PaddleOCR."""
    text_len = len(page_text.strip())
    # 1. Native text is completely empty but images exist
    if text_len == 0 and len(page_images) > 0:
        return True
    
    # 2. Corrupted glyph replacement rate (> 5% replacement characters)
    replacement_chars = page_text.count("\ufffd") + page_text.count("?")
    if text_len > 0 and (replacement_chars / text_len) > 0.05:
        return True
        
    # 3. Dense visual scan check: high image coverage with low character density
    if text_len < 40 and len(page_images) >= 1:
        return True
        
    return False
```

### 6.2 Multi-Level Evidence Segmentation
**File:** `backend/app/ingestion/parsers/document_parser.py`

Preserve hierarchical structure during evidence unit segmentation:
* **Sentences**: Using `NLPManager.get_spacy().sents`, segment narrative prose while attaching parent clause and heading titles to `hierarchical_context`.
* **Tables**: Convert rows into structured `ParsedEvidenceUnit` instances where each cell is bound to its column header:
  ```json
  {
    "block_type": "table_row",
    "structured_data": {
      "table_id": "tbl_notice_periods",
      "row_idx": 3,
      "columns": {"Employee Grade": "M4+", "Probation Notice": "30 Days", "Confirmed Notice": "90 Days"}
    }
  }
  ```

---

## 7. Phase 4: Layer 5 Candidate Discovery & Claim Extraction

### 7.1 Sentence-Level Candidate Discovery
**File:** `backend/app/extraction/candidate_discovery.py`

1. **Suppress Non-Claim Content**:
   * Filter out document control tables, revision history, copyright notices, and framing preambles ("The purpose of this document is to outline...").
   * Filter pure FAQ questions while preserving FAQ answers.
2. **Multifactor Candidate Signal Detection**:
   * Modal verbs: `must`, `shall`, `may`, `entitled to`, `prohibited from`, `cannot`.
   * Numerical/temporal boundaries: `\d+\s*(days|months|years|hours|INR|USD|%)`.
   * Action & governance predicates: `approves`, `reimburses`, `authorizes`, `terminates`.
   * Structured record invariants: SQL constraints, database fields.

### 7.2 Semantic Discovery & Passage Matching with BGE
**File:** `backend/app/extraction/candidate_discovery.py`

* Compute batched embeddings using `NLPManager.get_bge_embeddings()`.
* Retrieve semantically related adjacent paragraphs when a sentence contains anaphoric references or partial conditions.

### 7.3 Three-Tier Entity Extraction Cascade
**File:** `backend/app/extraction/subject_normalizer.py`

```python
def extract_entities_cascaded(text: str) -> Dict[str, Any]:
    entities = {}
    
    # Tier 1: Deterministic regex for structured numbers, currencies, durations
    entities["values"] = match_regex_quantities(text)
    
    # Tier 2: spaCy NER for general named entities
    nlp = NLPManager.get_spacy()
    doc = nlp(text)
    for ent in doc.ents:
        entities[ent.label_] = ent.text
        
    # Tier 3: Conditional GLiNER for enterprise domain entities
    # Activated when standard roles (approver, claimant, jurisdiction) are unresolved
    if "ROLE" not in entities or "ORGANIZATION" not in entities:
        gliner = NLPManager.get_gliner()
        domain_labels = [
            "approver_role", "employee_type", "governing_entity", 
            "jurisdiction", "department", "vendor", "customer"
        ]
        gliner_preds = gliner.predict_entities(text, domain_labels, threshold=0.55)
        for pred in gliner_preds:
            entities[pred["label"]] = pred["text"]
            
    return entities
```

### 7.4 Structured S-P-O & Condition Extraction
**File:** `backend/app/extraction/extractors/domain_rule_extractor.py`

Parse dependency syntax trees:
* **Actor (Subject)**: Trace `nsubj`, `nsubjpass`, or prepositional agents (`agent`).
* **Action (Predicate)**: Identify root verbs (`ROOT`) + auxiliary verbs (`aux`, `auxpass`).
* **Object**: Trace direct objects (`dobj`), attribute nouns (`attr`), and prepositional objects (`pobj`).
* **Conditions & Exceptions**: Identify adverbial clauses (`advcl`) introduced by subordinating markers: `if`, `unless`, `provided that`, `subject to`, `except where`.
* **LLM Fallback**: If dependency parsing confidence $< 0.60$ or compound disjunctions are detected, pass the single clause to `LLMSemanticExtractor` enforcing strict Pydantic JSON output.

---

## 8. Phase 5: Claim Normalization & Sentence Framing

**File:** `backend/app/extraction/claim_quality_normalizer.py`

Maintain strict separation between **Original Evidence** and **Normalized Claim**:

### 8.1 Nine Standardized Claim Types
Map every claim to its primary operational category:
1. `ENTITLEMENT`: Right or eligibility granted to a subject.
2. `OBLIGATION`: Mandatory requirement or affirmative duty.
3. `PROHIBITION`: Forbidden action or negative duty.
4. `CONDITION`: Prerequisite qualifier for another claim.
5. `EXCEPTION`: Explicit carve-out or exemption.
6. `THRESHOLD`: Numerical limit or operational boundary.
7. `PROCESS`: Ordered sequence of operational steps.
8. `EVENT`: Verified factual occurrence or status update.
9. `INFORMATION`: Informative factual assertion without normative force.

### 8.2 Canonical Sentence Generation
Synthesize human-readable sentences from structured fields without inventing unverified context:
* **Template**: `{Subject} {Modal Phrase} {Normalized Action} {Object} [provided that {Conditions}] [except {Exceptions}].`
* **Invariant**: Never inject terms (e.g., "per calendar year") unless explicitly present in evidence or verified document metadata.

---

## 9. Phase 6: Layer 6 Multi-Dimensional Evidence Validation

**File:** `backend/app/extraction/clause_entailment_evaluator.py` & `backend/app/validation_gate/evaluators.py`

### 9.1 DeBERTa-v3 NLI Cross-Encoder Gate
Evaluate directional entailment:
$$\text{Premise: } \text{verbatim\_quote} \quad \longrightarrow \quad \text{Hypothesis: } \text{canonical\_claim\_sentence}$$

```python
def evaluate_deberta_nli(premise: str, hypothesis: str) -> Tuple[str, float]:
    tokenizer, model, label_map = NLPManager.get_deberta_nli()
    inputs = tokenizer(premise, hypothesis, truncation=True, max_length=512, return_tensors="pt")
    with torch.no_grad():
        logits = model(**inputs).logits
        probs = torch.softmax(logits, dim=1)[0]
    
    pred_idx = torch.argmax(probs).item()
    label = label_map.get(pred_idx, "NEUTRAL")
    confidence = probs[pred_idx].item()
    return label, confidence
```

### 9.2 Twelve Multi-Dimensional Validation Checks
Every claim must pass through the following invariant checks before persistence:
1. **Span Grounding**: Verbatim quote exists in original source text.
2. **Subject Match**: Subject entity is supported by evidence.
3. **Predicate Match**: Normalized action reflects evidence verb.
4. **Object Match**: Target object/value is grounded in evidence.
5. **Modality Invariant**: Modal force (`MUST`, `MAY`, `MUST_NOT`) matches source polarity.
6. **Negation Check**: Negative particles (`not`, `never`, `prohibited`) are preserved.
7. **Numeric Equivalence**: All numerical values, currencies, and percentages match.
8. **Temporal Equivalence**: Deadlines and durations match.
9. **Condition Preservation**: Restrictive qualifiers in evidence are captured in structured conditions.
10. **Exception Preservation**: Carve-outs and exemptions are explicitly listed.
11. **Context Resolution**: Coreference and pronoun bindings are verified.
12. **Directional Entailment**: DeBERTa NLI outputs `ENTAILMENT` (or passes deterministic high-confidence check).

*Routing*:
* `CONTRADICTION` $\to$ **REJECT**.
* `NEUTRAL` (or missing condition) $\to$ **REVIEW** (Human Review Queue).
* `ENTAILMENT` + all checks passed $\to$ **APPROVE** (Verified Truth Store).

---

## 10. Phase 7: Layer 7 TEVV Benchmarking Suite

**File:** `research/validation_50/run_validation.py`

Benchmark against manually annotated corporate documents across:
* Employment Agreements, HR Handbooks, and Leave Policies.
* Invoices, Purchase Orders, and SOC-2 Audit Reports.
* Scanned PDFs, Markdown technical specifications, and Slack threads.

### Target Benchmark Thresholds
* **Claim Precision**: $\ge 95\%$ (Certified claims represent genuine enterprise rules).
* **Evidence Grounding**: $\ge 99\%$ (Exact verbatim match and character offset alignment).
* **Condition Preservation**: $\ge 98\%$ (Conditions in source clauses retained in claims).
* **Unsupported Claim Rate**: $\approx 0\%$ (Un-grounded assertions blocked by NLI gate).
* **LLM Token Reduction**: $\ge 85\%$ drop in LLM calls via deterministic & small-model preprocessing.

---

## 11. Concrete Engineering Execution Sequence

```
1. ENVIRONMENT SETUP
   ├── Update backend/requirements.txt
   ├── Run pip install inside .venv
   └── Download spaCy 'en_core_web_md' model artifact

2. FOUNDATION SERVICES
   ├── Create backend/app/core/nlp_manager.py
   └── Update backend/app/core/config.py with model enablement flags

3. INGESTION & PARSING (LAYERS 3 & 4)
   ├── Implement should_run_page_ocr() in universal_file_parser.py
   ├── Upgrade table parsing to preserve row-header associations
   └── Implement sentence-level ParsedEvidenceUnit splitting in document_parser.py

4. EXTRACTION PIPELINE (LAYER 5)
   ├── Refactor candidate_discovery.py to suppress metadata/framing
   ├── Implement 3-tier cascaded NER in subject_normalizer.py
   ├── Implement dependency-guided S-P-O in domain_rule_extractor.py
   └── Upgrade claim_quality_normalizer.py for canonical sentence framing

5. VALIDATION GATES (LAYER 6)
   ├── Integrate DeBERTa-v3 NLI in clause_entailment_evaluator.py
   └── Add ConditionPreservationEvaluator in validation_gate/evaluators.py

6. BENCHMARK & REGRESSION (LAYER 7)
   ├── Execute unit test regression suite (backend/tests/)
   └── Run research/validation_50/run_validation.py and report measured metrics
```

---

## 12. Strict Scope Confirmation

* **Layers 8–11 Untouched**: `app/trust_engine/`, `app/conflict_engine/`, `app/services/conflict_service.py`, and `app/retrieval/` remain completely unchanged.
* **No Database Migrations Required**: The canonical claim schema maps directly to existing JSON fields (`conditions_data`, `exceptions_data`, `evidence_relationships`, `validation_status`).
* **Zero Disruption to Existing Connectors**: Ingestion envelopes and downstream API contracts remain strictly backward-compatible.

