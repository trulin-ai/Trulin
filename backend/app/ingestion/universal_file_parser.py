import csv
import io
import json
import logging
import re
import uuid
import xml.etree.ElementTree as ET
import zipfile
from enum import Enum
from html.parser import HTMLParser
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.ingestion.parsers.evidence_model import ExtractionQualityReport, ExtractionStatus

logger = logging.getLogger(__name__)

# Patterns for identifiers, versions, dates, amounts, etc. that should NOT be split or mutated by OCR repair
PROTECTED_OCR_PATTERNS = [
    r'https?://[^\s]+',
    r'www\.[^\s]+',
    r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
    r'[\$€£¥]\s*\d+(?:,\d{3})*(?:\.\d+)?(?:k|m|b|t)?\b',
    r'\b\d+(?:,\d{3})*(?:\.\d+)?\s*(?:USD|EUR|GBP|k|m|b)\b',
    r'\b\d+(?:\.\d+)?%',
    r'\b\d{1,2}(?:st|nd|rd|th)\b',
    r'\b\d{4}-\d{2}-\d{2}\b',
    r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',
    r'\bv\d+(?:\.\d+)*\b',
    r'\b(?:AES|TLS|FIDO|SHA|RSA|IPV|HTTP|OAUTH|UTF|PDF|SQL|SOC|ISO|HIPAA|PCI|CVE|GDPR|NIST)[-_]?\d+(?:\.\d+)*\b',
    r'\b[A-Za-z]{2,}\d+(?:\.\d+)*\b',
    r'\b[A-Za-z]+[-_]\d+\b',
    r'\bP\d+\b',
]
_PROTECTED_REGEX = re.compile('|'.join(f'(?:{p})' for p in PROTECTED_OCR_PATTERNS), re.IGNORECASE)


def mask_protected_tokens(text: str) -> Tuple[str, Dict[str, str]]:
    tokens_map: Dict[str, str] = {}
    def repl(m):
        key = f"__PROT_TOK_{len(tokens_map)}__"
        tokens_map[key] = m.group(0)
        return key

    masked = _PROTECTED_REGEX.sub(repl, text)
    return masked, tokens_map


def unmask_protected_tokens(text: str, tokens_map: Dict[str, str]) -> str:
    for key, val in tokens_map.items():
        text = text.replace(key, val)
    return text


def repair_ocr_text(raw_text: str) -> str:
    """Repairs OCR-induced token concatenation, missing punctuation spacing, and run-together words.
    Protects dates, amounts, percentages, versions, IDs, and technical standards from unsafe corruption.
    """
    if not raw_text:
        return ""

    try:
        import wordsegment
        wordsegment.load()
    except Exception:
        wordsegment = None

    # Mask protected tokens prior to OCR repairs to prevent unsafe corruption (e.g., AES256, TLS1.3, v2.0, 15th, $100k)
    masked_text, tokens_map = mask_protected_tokens(raw_text)

    lines = masked_text.splitlines()
    repaired_lines = []
    for line in lines:
        if not line.strip():
            repaired_lines.append(line)
            continue

        # Clean special quote / bracket artifacts
        line = line.replace("《", " ").replace("》", " ").replace("“", '"').replace("”", '"').replace("’", "'")
        line = re.sub(r"([a-zA-Z])'s([a-zA-Z])", r"\1's \2", line)

        # 1. Punctuation spacing: comma, parens, colon, semicolon (guarded)
        line = re.sub(r'([a-zA-Z])\(', r'\1 (', line)
        line = re.sub(r'\)([a-zA-Z])', r') \1', line)
        line = re.sub(r',([a-zA-Z])', r', \1', line)
        line = re.sub(r';([a-zA-Z])', r'; \1', line)

        # 2. Letter to digit / digit to letter transitions (e.g. next30days -> next 30 days)
        # Note: Protected tokens (AES256, TLS1.3, 15th, etc.) are masked as __PROT_TOK_N__ and preserved
        line = re.sub(r'([a-zA-Z])(\d+)', r'\1 \2', line)
        line = re.sub(r'(\d+)([a-zA-Z])', r'\1 \2', line)

        tokens = line.split()
        repaired_tokens = []
        for token in tokens:
            if "@" in token or token.startswith(("http://", "https://", "www.", "__PROT_TOK_")):
                repaired_tokens.append(token)
                continue

            match = re.match(r"^([^\w]*)([\w]+)([^\w]*)$", token)
            if not match:
                repaired_tokens.append(token)
                continue

            prefix, word, suffix = match.groups()
            if len(word) <= 3 or word.isdigit() or word.startswith("__PROT_TOK_"):
                repaired_tokens.append(token)
                continue

            # Letter-to-digit and digit-to-letter transitions for words with 3+ letters
            # (e.g. within30days -> within 30 days)
            if re.search(r'[a-zA-Z]{3,}\d+', word):
                word = re.sub(r'([a-zA-Z]{3,})(\d+)', r'\1 \2', word)
            if re.search(r'\d+[a-zA-Z]{3,}', word):
                word = re.sub(r'(\d+)([a-zA-Z]{3,})', r'\1 \2', word)

            # CamelCase splitting (e.g. SafeDrinkingWaterAct -> Safe Drinking Water Act)
            camel_parts = re.findall(r'[A-Z]+(?=[A-Z][a-z]|\d|\W|$)|[A-Z]?[a-z]+|\d+', word)
            if len(camel_parts) > 1 and all(len(p) >= 2 for p in camel_parts):
                repaired_tokens.append(prefix + " ".join(camel_parts) + suffix)
            elif len(word) >= 7 and wordsegment is not None and not any(c.isdigit() for c in word):
                try:
                    segs = wordsegment.segment(word.lower())
                    if len(segs) > 1 and all(len(s) >= 3 for s in segs):
                        if word[0].isupper():
                            segs[0] = segs[0].capitalize()
                        repaired_tokens.append(prefix + " ".join(segs) + suffix)
                    else:
                        repaired_tokens.append(token)
                except Exception:
                    repaired_tokens.append(token)
            else:
                repaired_tokens.append(token)

        repaired_lines.append(" ".join(repaired_tokens))

    repaired_result = "\n".join(repaired_lines)
    return unmask_protected_tokens(repaired_result, tokens_map)

_OCR_ENGINE = None

def get_ocr_engine():
    global _OCR_ENGINE
    if _OCR_ENGINE is None:
        try:
            from rapidocr_onnxruntime import RapidOCR
            _OCR_ENGINE = RapidOCR()
            logger.info("RapidOCR engine initialized successfully")
        except Exception as e:
            logger.warning("RapidOCR could not be initialized: %s", e)
            _OCR_ENGINE = False
    return _OCR_ENGINE if _OCR_ENGINE is not False else None


class ContentBlockType(str, Enum):
    PARAGRAPH = "paragraph"
    HEADING = "heading"
    TABLE = "table"
    LIST_ITEM = "list_item"
    CAPTION = "caption"
    HEADER_FOOTER = "header_footer"
    IMAGE_OCR = "image_ocr"
    CODE_OR_CONFIG = "code_or_config"
    UNKNOWN = "unknown"


class ContentBlock(BaseModel):
    id: str = Field(default_factory=lambda: f"blk_{uuid.uuid4().hex[:12]}")
    block_type: ContentBlockType = ContentBlockType.PARAGRAPH
    text: str
    raw_text: str = ""
    text_source: str = "native"  # "native", "ocr", "repaired_ocr", "hybrid"
    ocr_confidence: Optional[float] = None
    bounding_box: Optional[Dict[str, Any]] = None
    page_number: Optional[int] = None
    section_heading: Optional[str] = None
    heading_path: List[str] = Field(default_factory=list)
    table_data: Optional[Dict[str, Any]] = None  # {"headers": [...], "rows": [[...]], "row_dicts": [...]}
    start_char_offset: int = 0
    end_char_offset: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentPage(BaseModel):
    page_number: int
    text: str
    native_text: str = ""
    ocr_text_raw: str = ""
    ocr_text_repaired: str = ""
    selected_text_source: str = "native"  # "native", "ocr", "hybrid"
    ocr_confidence: Optional[float] = None
    char_count: int = 0
    is_scanned_image: bool = False
    width: Optional[float] = None
    height: Optional[float] = None
    blocks: List[ContentBlock] = Field(default_factory=list)


class ParsedDocument(BaseModel):
    filename: str
    title: str
    file_type: str
    parser_name: str = "UniversalFileParser"
    parser_version: str = "2.0.0"
    content_hash: str = ""
    full_text: str
    raw_text: str
    pages: List[DocumentPage] = Field(default_factory=list)
    blocks: List[ContentBlock] = Field(default_factory=list)
    tables: List[Dict[str, Any]] = Field(default_factory=list)
    extraction_quality: float = 1.0  # 0.0 to 1.0
    extraction_status: ExtractionStatus = ExtractionStatus.SUCCESS
    quality_report: Optional[ExtractionQualityReport] = None
    is_scanned: bool = False
    warnings: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class _HTMLToTextExtractor(HTMLParser):
    """Converts HTML documents to clean markdown-formatted text."""

    def __init__(self):
        super().__init__()
        self.result = []
        self.current_tag = None
        self.ignore_tags = {"script", "style", "head", "meta", "link", "noscript"}
        self.in_ignore = False
        self.table_row = []
        self.in_table = False

    def handle_starttag(self, tag, attrs):
        self.current_tag = tag.lower()
        if self.current_tag in self.ignore_tags:
            self.in_ignore = True
            return

        if self.current_tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            level = int(self.current_tag[1])
            self.result.append("\n\n" + "#" * level + " ")
        elif self.current_tag == "p":
            self.result.append("\n\n")
        elif self.current_tag == "li":
            self.result.append("\n- ")
        elif self.current_tag == "tr":
            self.in_table = True
            self.table_row = []
        elif self.current_tag in {"td", "th"}:
            if self.in_table:
                self.current_cell_parts = []
        elif self.current_tag == "br":
            self.result.append("\n")

    def handle_endtag(self, tag):
        t = tag.lower()
        if t in self.ignore_tags:
            self.in_ignore = False
        elif t in {"td", "th"} and self.in_table:
            val = "".join(getattr(self, "current_cell_parts", [])).strip()
            self.table_row.append(val)
            self.current_cell_parts = []
        elif t == "tr" and self.table_row:
            self.result.append("\n| " + " | ".join(self.table_row) + " |")
            self.table_row = []
        elif t == "table":
            self.in_table = False
            self.result.append("\n\n")

    def handle_data(self, data):
        if self.in_ignore:
            return
        if self.in_table and self.current_tag in {"td", "th"}:
            if not hasattr(self, "current_cell_parts"):
                self.current_cell_parts = []
            self.current_cell_parts.append(data)
        else:
            self.result.append(data)

    def get_text(self) -> str:
        raw = "".join(self.result)
        return re.sub(r"\n{3,}", "\n\n", raw).strip()


class UniversalFileParser:
    PARSER_VERSION: str = "2.0.0"
    SCHEMA_VERSION: str = "2.0.0"

    @classmethod
    def _get_ocr_engine(cls):
        return get_ocr_engine()

    """Universal parser capable of extracting structured text and canonical blocks from any document format."""

    @classmethod
    def parse_file(cls, filename: str, raw_bytes: bytes, doc_title: Optional[str] = None) -> str:
        """Parses any input file and returns structured Markdown text (Backward compatible)."""
        parsed = cls.parse_structured(filename, raw_bytes, doc_title)
        return parsed.full_text

    @classmethod
    def parse_structured(cls, filename: str, raw_bytes: bytes, doc_title: Optional[str] = None) -> ParsedDocument:
        """Parses any input file and returns a rich ParsedDocument with page, block, and table fidelity."""
        import hashlib
        name = filename or "uploaded_document"
        title = doc_title or name.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title()
        title = title.replace("\x00", "").strip()
        lower_name = name.lower()
        content_hash = hashlib.sha256(raw_bytes).hexdigest()

        # Content-Addressed Pipeline Cache Lookup (Cryptographic Invariant Key)
        cache_key = None
        try:
            from app.caching.pipeline_cache import default_pipeline_cache
            config_hash = hashlib.sha256(b"ocr=true,table=true,headings=v2,mode=layout").hexdigest()[:16]
            cache_key = default_pipeline_cache.compute_pipeline_key(
                stage_name="universal_parser",
                source_sha256=content_hash,
                parser_version="v3.4",
                parser_config_hash=config_hash,
                normalizer_version="v1.3",
                ocr_version="v1.2",
                evidence_schema_version="v1.0",
            )
            cached_doc = default_pipeline_cache.get_model("universal_parser", cache_key, ParsedDocument)
            if cached_doc is not None:
                return cached_doc
        except Exception as cache_err:
            logger.warning("Pipeline cache lookup error for %s: %s", filename, cache_err)

        warnings: List[str] = []

        # Empty payload handling
        if len(raw_bytes) == 0:
            full_text = f"# {title}\n\n[Empty file '{filename}' contains no content]"
            q_report = ExtractionQualityReport(
                status=ExtractionStatus.EMPTY,
                completeness_score="NOT_MEASURED",
                warnings=["File is empty (0 bytes)."],
                parser_name="UniversalFileParser",
            )
            return ParsedDocument(
                filename=filename,
                title=title,
                file_type="plain_text",
                content_hash=content_hash,
                full_text=full_text,
                raw_text="",
                pages=[],
                blocks=[],
                tables=[],
                extraction_quality=0.0,
                extraction_status=ExtractionStatus.EMPTY,
                quality_report=q_report,
                is_scanned=False,
                warnings=["File is empty (0 bytes)."],
                metadata={"file_size": 0},
            )

        # Check for Legacy Compound File Binary Format (CFBF/OLE2) e.g. legacy .doc, .xls, .ppt
        is_cfbf = raw_bytes.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1")
        if is_cfbf and lower_name.endswith((".doc", ".xls", ".ppt")):
            legacy_warning = f"Legacy binary format ({filename}) detected (CFBF/OLE2). Modern OpenXML (.docx/.xlsx/.pptx) is required."
            warnings.append(legacy_warning)
            full_text = f"# {title}\n\n[Legacy binary file '{filename}' cannot be parsed as modern OpenXML. Please convert to modern format.]"
            blk = ContentBlock(
                id=f"blk_legacy_{uuid.uuid4().hex[:8]}",
                block_type=ContentBlockType.PARAGRAPH,
                text=full_text,
                raw_text=full_text,
            )
            q_report = ExtractionQualityReport(
                status=ExtractionStatus.UNSUPPORTED,
                completeness_score=0.0,
                warnings=warnings,
                parser_name="UniversalFileParser",
            )
            return ParsedDocument(
                filename=filename,
                title=title,
                file_type="plain_text",
                content_hash=content_hash,
                full_text=full_text,
                raw_text=full_text,
                pages=[],
                blocks=[blk],
                tables=[],
                extraction_quality=0.0,
                extraction_status=ExtractionStatus.UNSUPPORTED,
                quality_report=q_report,
                is_scanned=False,
                warnings=warnings,
                metadata={"file_size": len(raw_bytes), "legacy_binary": True},
            )

        file_type = "plain_text"
        if lower_name.endswith(".pdf"):
            file_type = "pdf"
        elif lower_name.endswith((".docx", ".doc")):
            file_type = "docx"
        elif lower_name.endswith((".xlsx", ".xls")):
            file_type = "xlsx"
        elif lower_name.endswith((".pptx", ".ppt")):
            file_type = "pptx"
        elif lower_name.endswith(".csv"):
            file_type = "csv"
        elif lower_name.endswith(".tsv"):
            file_type = "tsv"
        elif lower_name.endswith((".json", ".jsonl")):
            file_type = "json"
        elif lower_name.endswith((".html", ".htm", ".xhtml")):
            file_type = "html"
        elif lower_name.endswith(".xml"):
            file_type = "xml"
        elif lower_name.endswith(".rtf"):
            file_type = "rtf"
        elif lower_name.endswith((".md", ".markdown")):
            file_type = "markdown"
        elif lower_name.endswith((".yaml", ".yml", ".toml", ".ini", ".conf", ".sql", ".log", ".env")):
            file_type = "code_or_config"

        pages: List[DocumentPage] = []
        blocks: List[ContentBlock] = []
        tables: List[Dict[str, Any]] = []
        extraction_quality = 1.0
        is_scanned = False
        full_text = ""

        try:
            if file_type == "pdf":
                full_text, pages, blocks, tables, warnings, is_scanned, extraction_quality = cls._parse_pdf_structured(
                    raw_bytes, title, filename
                )
            elif file_type == "docx":
                full_text, pages, blocks, tables, warnings = cls._parse_docx_structured(
                    raw_bytes, title, filename
                )
            elif file_type == "xlsx":
                full_text, pages, blocks, tables, warnings = cls._parse_xlsx_structured(
                    raw_bytes, title, filename
                )
            elif file_type in ("csv", "tsv"):
                delimiter = "\t" if file_type == "tsv" else None
                full_text = cls._parse_csv(raw_bytes, title, delimiter=delimiter)
                blocks.append(ContentBlock(
                    id="blk_csv_1",
                    block_type=ContentBlockType.TABLE,
                    text=full_text,
                    raw_text=full_text,
                ))
            elif file_type == "json":
                full_text = cls._parse_json(raw_bytes, title, is_jsonl=lower_name.endswith(".jsonl"))
                blocks.append(ContentBlock(
                    id="blk_json_1",
                    block_type=ContentBlockType.CODE_OR_CONFIG,
                    text=full_text,
                    raw_text=full_text,
                ))
            elif file_type in ("html", "xhtml"):
                full_text = cls._parse_html(raw_bytes, title)
                blocks.append(ContentBlock(
                    id="blk_html_1",
                    block_type=ContentBlockType.PARAGRAPH,
                    text=full_text,
                    raw_text=full_text,
                ))
            elif file_type == "xml":
                full_text = cls._parse_xml(raw_bytes, title)
                blocks.append(ContentBlock(
                    id="blk_xml_1",
                    block_type=ContentBlockType.CODE_OR_CONFIG,
                    text=full_text,
                    raw_text=full_text,
                ))
            elif file_type == "rtf":
                full_text = cls._parse_rtf(raw_bytes, title)
                blocks.append(ContentBlock(
                    id="blk_rtf_1",
                    block_type=ContentBlockType.PARAGRAPH,
                    text=full_text,
                    raw_text=full_text,
                ))
            elif file_type == "markdown":
                full_text, pages, blocks = cls._parse_markdown_structured(raw_bytes, title, filename)
            elif file_type == "code_or_config":
                ext = lower_name.rsplit(".", 1)[-1]
                full_text = cls._parse_code_or_config(raw_bytes, title, ext)
                blocks.append(ContentBlock(
                    id="blk_code_1",
                    block_type=ContentBlockType.CODE_OR_CONFIG,
                    text=full_text,
                    raw_text=full_text,
                ))
            else:
                full_text = cls._parse_plain_text(raw_bytes, title, filename)
                blocks.append(ContentBlock(
                    id="blk_text_1",
                    block_type=ContentBlockType.PARAGRAPH,
                    text=full_text,
                    raw_text=full_text,
                ))

        except Exception as e:
            logger.warning("UniversalFileParser error for %s: %s", filename, e)
            warnings.append(f"Parsing error: {str(e)}")
            # Do NOT silently fall back from a failed binary parser to plain-text parsing
            if file_type in ("pdf", "docx", "xlsx", "pptx"):
                extraction_quality = 0.0
                full_text = f"# {title}\n\n[Parsing error for binary {file_type} file '{filename}': {str(e)}]"
                blocks.append(ContentBlock(
                    id=f"blk_error_{uuid.uuid4().hex[:8]}",
                    block_type=ContentBlockType.PARAGRAPH,
                    text=full_text,
                    raw_text=full_text,
                ))
            else:
                full_text = cls._parse_plain_text(raw_bytes, title, filename)
                blocks.append(ContentBlock(
                    id=f"blk_fallback_{uuid.uuid4().hex[:8]}",
                    block_type=ContentBlockType.PARAGRAPH,
                    text=full_text,
                    raw_text=full_text,
                ))

        full_text = full_text.replace("\x00", "").strip()
        if not full_text:
            full_text = f"# {title}\n\n[No extractable content found in {filename}]"

        # Resolve explicit ExtractionStatus
        if extraction_quality == 0.0 or not blocks or (file_type == "pdf" and any("no extractable text" in w.lower() for w in warnings)):
            if is_scanned or any("needs_ocr" in w.lower() or "scanned" in w.lower() for w in warnings):
                doc_status = ExtractionStatus.NEEDS_OCR
            elif not warnings:
                doc_status = ExtractionStatus.EMPTY
            else:
                doc_status = ExtractionStatus.FAILED
        elif warnings or extraction_quality < 1.0:
            doc_status = ExtractionStatus.PARTIAL
        else:
            doc_status = ExtractionStatus.SUCCESS

        quality_report = ExtractionQualityReport(
            status=doc_status,
            completeness_score=extraction_quality,
            expected_pages=len(pages) if pages else None,
            processed_pages=len(pages) if pages else None,
            expected_blocks=len(blocks),
            processed_blocks=len(blocks),
            detected_tables=len(tables),
            extracted_tables=len(tables),
            valid_evidence_units=len(blocks),
            valid_source_locators=sum(1 for b in blocks if b.page_number is not None),
            warnings=list(warnings),
            parser_name="UniversalFileParser",
        )

        result_doc = ParsedDocument(
            filename=filename,
            title=title,
            file_type=file_type,
            content_hash=content_hash,
            full_text=full_text,
            raw_text=full_text,
            pages=pages,
            blocks=blocks,
            tables=tables,
            extraction_quality=extraction_quality,
            extraction_status=doc_status,
            quality_report=quality_report,
            is_scanned=is_scanned,
            warnings=warnings,
            metadata={"file_size": len(raw_bytes), "block_count": len(blocks), "page_count": len(pages)},
        )
        if cache_key and doc_status not in (ExtractionStatus.FAILED, ExtractionStatus.EMPTY):
            try:
                from app.caching.pipeline_cache import default_pipeline_cache
                default_pipeline_cache.set("universal_parser", cache_key, result_doc, metadata={"filename": filename})
            except Exception as cache_store_err:
                logger.warning("Pipeline cache store error for %s: %s", filename, cache_store_err)
        return result_doc

    @classmethod
    def _parse_pdf_structured(
        cls, raw_bytes: bytes, title: str, filename: str
    ) -> Tuple[str, List[DocumentPage], List[ContentBlock], List[Dict[str, Any]], List[str], bool, float]:
        pages: List[DocumentPage] = []
        blocks: List[ContentBlock] = []
        tables: List[Dict[str, Any]] = []
        warnings: List[str] = []
        is_scanned_overall = False
        empty_pages = 0
        total_chars = 0
        pages_text: List[str] = []

        # 1. Try PyMuPDF (fitz) first for high-fidelity native text, tables, and spatial layout
        pymupdf_available = False
        try:
            import pymupdf
            pymupdf_available = True
        except ImportError:
            try:
                import fitz as pymupdf
                pymupdf_available = True
            except ImportError:
                pymupdf_available = False

        if pymupdf_available:
            try:
                doc = pymupdf.open(stream=raw_bytes, filetype="pdf")
                total_pages = len(doc)
                ocr_engine = cls._get_ocr_engine()

                for page_idx in range(total_pages):
                    page = doc[page_idx]
                    page_num = page_idx + 1
                    rect = page.rect
                    page_width = float(rect.width)
                    page_height = float(rect.height)
                    page_area = max(1.0, page_width * page_height)

                    native_text = (page.get_text() or "").strip()
                    native_len = len(native_text)
                    printable_chars = sum(1 for c in native_text if c.isprintable())
                    printable_ratio = (printable_chars / max(1, native_len)) if native_len > 0 else 0.0

                    # Table extraction using PyMuPDF find_tables
                    page_tables: List[Dict[str, Any]] = []
                    try:
                        tabs = page.find_tables()
                        for t_idx, tab in enumerate(tabs.tables, start=1):
                            extracted = tab.extract()
                            if extracted and len(extracted) > 0:
                                hdrs = [str(c or "").strip() for c in extracted[0]]
                                data_r = [[str(c or "").strip() for c in row] for row in extracted[1:]]
                                t_id = f"tbl_p{page_num}_{t_idx}"
                                t_meta = {
                                    "table_id": t_id,
                                    "page_number": page_num,
                                    "headers": hdrs,
                                    "rows": data_r,
                                    "bbox": list(tab.bbox) if hasattr(tab, "bbox") else None,
                                    "row_count": tab.row_count,
                                    "col_count": tab.col_count,
                                }
                                page_tables.append(t_meta)
                                tables.append(t_meta)
                    except Exception as tab_err:
                        logger.warning("PyMuPDF table extraction on page %d: %s", page_num, tab_err)

                    # Multi-signal scanned detection:
                    # Measure image coverage vs native text density
                    img_list = page.get_images()
                    total_img_area = 0.0
                    for img in img_list:
                        try:
                            for r in page.get_image_rects(img[0]):
                                total_img_area += r.width * r.height
                        except Exception:
                            pass
                    img_coverage = total_img_area / page_area
                    replacement_chars = native_text.count("\ufffd") + native_text.count("?")
                    replacement_ratio = replacement_chars / max(1, native_len)

                    # Page is scanned only if large image covers page AND text is sparse/absent,
                    # or if zero text and images exist, or high glyph corruption rate (> 5%).
                    # Legitimate short text pages without dominant image coverage are NOT scanned.
                    is_page_scanned = (
                        (img_coverage > 0.4 and native_len < 40)
                        or (len(img_list) > 0 and native_len < 15 and printable_ratio < 0.5)
                        or (len(img_list) > 0 and native_len > 0 and replacement_ratio > 0.05)
                        or (native_len == 0 and len(img_list) > 0)
                    )

                    ocr_raw = ""
                    ocr_repaired = ""
                    page_ocr_conf: Optional[float] = None
                    selected_source = "native"

                    # Run OCR only when page is scanned or native text is missing/corrupt and images exist
                    if (is_page_scanned or native_len == 0) and ocr_engine is not None and len(img_list) > 0:
                        try:
                            pix = page.get_pixmap(dpi=150)
                            img_bytes = pix.tobytes("png")
                            ocr_res, _ = ocr_engine(img_bytes)
                            if ocr_res:
                                ocr_lines = [line[1] for line in ocr_res if len(line) > 1 and line[1].strip()]
                                confs = [line[2] for line in ocr_res if len(line) > 2 and line[2] is not None]
                                if confs:
                                    page_ocr_conf = float(sum(confs) / len(confs))
                                ocr_raw = "\n".join(ocr_lines)
                                # OCR repair is ONLY applied to OCR-derived text
                                ocr_repaired = repair_ocr_text(ocr_raw).strip()
                        except Exception as ocr_err:
                            logger.warning("RapidOCR failed on page %d: %s", page_num, ocr_err)

                    # Selection strategy: Do NOT select OCR text simply because it has more characters!
                    # If native text exists and is readable, prefer native text.
                    if is_page_scanned and ocr_repaired:
                        if native_len < 20 or printable_ratio < 0.6:
                            clean_page_text = ocr_repaired
                            selected_source = "ocr"
                            is_scanned_overall = True
                            warnings.append(f"Page {page_num}: text recovered via OCR ({len(clean_page_text)} chars).")
                        else:
                            clean_page_text = native_text
                            selected_source = "native"
                    else:
                        clean_page_text = native_text
                        selected_source = "native"

                    char_count = len(clean_page_text)
                    total_chars += char_count
                    if char_count < 20:
                        empty_pages += 1

                    page_blocks: List[ContentBlock] = []
                    if clean_page_text:
                        from app.normalization.document_restructurer import DocumentSemanticRestructurer
                        from app.normalization.normalizer import DocumentNormalizer

                        page_with_tables = DocumentSemanticRestructurer.extract_tables_from_layout(clean_page_text)
                        reflowed_page = DocumentNormalizer.reflow_fragmented_lines(page_with_tables)
                        pages_text.append(f"## Page {page_num}\n{reflowed_page}")

                        chunks = reflowed_page.split("\n\n")
                        for b_idx, chunk in enumerate(chunks, start=1):
                            chk = chunk.strip()
                            if not chk:
                                continue
                            is_tbl = bool(chk.startswith("|") and "\n|" in chk)
                            is_hdg = bool(re.match(r"^(#+|Section\s+\d+|Chapter\s+\d+|Article\s+\d+|Rule\s+\d+)", chk, re.IGNORECASE))
                            if not is_hdg and re.match(r"^\d+\.\d*\s+[A-Z]", chk):
                                first_line = chk.split("\n")[0].strip()
                                if len(first_line.split()) <= 8 and not first_line.endswith((".", ";")) and not any(m in first_line.lower() for m in [" shall ", " must ", " should ", " will ", " may "]):
                                    is_hdg = True

                            b_type = ContentBlockType.TABLE if is_tbl else (ContentBlockType.HEADING if is_hdg else (ContentBlockType.IMAGE_OCR if selected_source == "ocr" else ContentBlockType.PARAGRAPH))

                            matched_table_data = None
                            if is_tbl:
                                tbl_lines = [l for l in chk.split("\n") if l.strip().startswith("|")]
                                if len(tbl_lines) >= 2:
                                    hdrs = [c.strip() for c in tbl_lines[0].split("|") if c.strip()]
                                    data_r = [[c.strip() for c in l.split("|") if c.strip()] for l in tbl_lines[2:]]
                                    matched_table_data = {"headers": hdrs, "rows": data_r, "page_number": page_num}

                            blk = ContentBlock(
                                id=f"blk_p{page_num}_{b_idx}",
                                block_type=b_type,
                                text=chk,
                                raw_text=chk,
                                page_number=page_num,
                                text_source=selected_source,
                                ocr_confidence=page_ocr_conf if selected_source == "ocr" else None,
                                table_data=matched_table_data,
                            )
                            page_blocks.append(blk)
                            blocks.append(blk)

                    pages.append(DocumentPage(
                        page_number=page_num,
                        text=clean_page_text,
                        native_text=native_text,
                        ocr_text_raw=ocr_raw,
                        ocr_text_repaired=ocr_repaired,
                        selected_text_source=selected_source,
                        ocr_confidence=page_ocr_conf,
                        char_count=char_count,
                        is_scanned_image=is_page_scanned,
                        width=page_width,
                        height=page_height,
                        blocks=page_blocks,
                    ))

                total_pages_count = max(1, len(pages))
                if empty_pages == total_pages_count or total_chars == 0:
                    extraction_quality = 0.0
                    warnings.append(f"PDF contains no extractable text or OCR failed ({filename}).")
                    full_text = f"# {title}\n\n[No extractable text found in {filename}]"
                    return full_text, pages, blocks, tables, warnings, is_scanned_overall, extraction_quality

                if is_scanned_overall:
                    extraction_quality = max(0.65, min(0.95, 1.0 - (empty_pages / total_pages_count) * 0.4))
                else:
                    extraction_quality = max(0.7, min(1.0, 1.0 - (empty_pages / total_pages_count) * 0.3))

                full_text = f"# {title}\n\n" + "\n\n".join(pages_text)
                try:
                    from app.normalization.document_restructurer import DocumentSemanticRestructurer
                    full_text = DocumentSemanticRestructurer.restructure(full_text)
                except Exception as restruct_err:
                    logger.warning("DocumentSemanticRestructurer failed: %s", restruct_err)

                return full_text, pages, blocks, tables, warnings, is_scanned_overall, extraction_quality

            except Exception as mupdf_err:
                logger.warning("PyMuPDF failed, attempting fallback to pypdf: %s", mupdf_err)
                warnings.append(f"PyMuPDF warning: {str(mupdf_err)}")

        # 2. Fallback using pypdf
        try:
            import pypdf
            reader = pypdf.PdfReader(io.BytesIO(raw_bytes))
            pages_text = []
            from app.normalization.normalizer import DocumentNormalizer

            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    # Prefer layout extraction mode to preserve multi-column tables and spatial geometry
                    page_text = page.extract_text(extraction_mode="layout") or ""
                    if not page_text.strip():
                        page_text = page.extract_text() or ""
                except Exception:
                    page_text = page.extract_text() or ""

                clean_page_text = page_text.strip()
                char_count = len(clean_page_text)
                total_chars += char_count
                raw_digital_text = clean_page_text

                # Multi-signal check
                images = getattr(page, "images", [])
                page_is_scanned = (char_count < 40 and len(images) > 0)
                ocr_raw = ""
                ocr_repaired = ""
                selected_source = "native"

                if page_is_scanned:
                    try:
                        ocr_engine = cls._get_ocr_engine()
                        if ocr_engine is not None:
                            page_ocr_lines = []
                            for img in images:
                                try:
                                    result, _ = ocr_engine(img.data)
                                    if result:
                                        lines = [line[1] for line in result if line[2] > 0.4]
                                        page_ocr_lines.extend(lines)
                                except Exception as img_err:
                                    logger.warning("OCR image extraction error on page %d: %s", page_num, img_err)

                            if page_ocr_lines:
                                ocr_raw = "\n".join(page_ocr_lines)
                                ocr_repaired = repair_ocr_text(ocr_raw).strip()
                                if len(ocr_repaired) > char_count:
                                    clean_page_text = ocr_repaired
                                    selected_source = "ocr"
                                    is_scanned_overall = True
                                    warnings.append(f"Page {page_num}: text recovered via OCR ({len(clean_page_text)} chars).")
                    except Exception as ocr_err:
                        logger.warning("OCR processing error on page %d: %s", page_num, ocr_err)
                        warnings.append(f"Page {page_num}: OCR attempt failed: {str(ocr_err)}")

                if char_count < 20:
                    empty_pages += 1

                page_blocks: List[ContentBlock] = []
                if clean_page_text:
                    from app.normalization.document_restructurer import DocumentSemanticRestructurer

                    page_with_tables = DocumentSemanticRestructurer.extract_tables_from_layout(clean_page_text)
                    reflowed_page = DocumentNormalizer.reflow_fragmented_lines(page_with_tables)
                    pages_text.append(f"## Page {page_num}\n{reflowed_page}")

                    lines = reflowed_page.split("\n\n")
                    for b_idx, chunk in enumerate(lines, start=1):
                        chk = chunk.strip()
                        if not chk:
                            continue

                        # Precise table detection
                        pipe_lines = [l.strip() for l in chk.split("\n") if l.strip().count("|") >= 2]
                        is_table = len(pipe_lines) >= 2 or (len(pipe_lines) >= 1 and any(re.search(r"\|:?-+:?\|", l) for l in chk.split("\n")))

                        is_hdg = bool(re.match(r"^(#+|Section\s+\d+|Chapter\s+\d+|Article\s+\d+|Rule\s+\d+)", chk, re.IGNORECASE))
                        b_type = ContentBlockType.TABLE if is_table else (ContentBlockType.HEADING if is_hdg else (ContentBlockType.IMAGE_OCR if selected_source == "ocr" else ContentBlockType.PARAGRAPH))

                        table_meta = None
                        if is_table:
                            tbl_lines = [l for l in chk.split("\n") if l.strip().count("|") >= 2]
                            if len(tbl_lines) >= 2:
                                hdrs = split_markdown_table_row(tbl_lines[0])
                                data_r = []
                                start_idx = 1
                                if len(tbl_lines) > 1:
                                    cand_sep = split_markdown_table_row(tbl_lines[1])
                                    if all(re.match(r"^:?-+:?$", c) for c in cand_sep if c):
                                        start_idx = 2
                                for l in tbl_lines[start_idx:]:
                                    row_c = split_markdown_table_row(l)
                                    if len(row_c) < len(hdrs):
                                        row_c.extend([""] * (len(hdrs) - len(row_c)))
                                    data_r.append(row_c[:len(hdrs)])
                                table_meta = {"headers": hdrs, "rows": data_r, "page_number": page_num}
                                tables.append(table_meta)

                        blk = ContentBlock(
                            id=f"blk_p{page_num}_{b_idx}",
                            block_type=b_type,
                            text=chk,
                            raw_text=chk,
                            page_number=page_num,
                            text_source=selected_source,
                            table_data=table_meta,
                        )
                        page_blocks.append(blk)
                        blocks.append(blk)

                pages.append(DocumentPage(
                    page_number=page_num,
                    text=clean_page_text,
                    native_text=page_text,
                    ocr_text_raw=ocr_raw,
                    ocr_text_repaired=ocr_repaired,
                    selected_text_source=selected_source,
                    char_count=char_count,
                    is_scanned_image=ocr_succeeded or (is_likely_scanned and char_count < 40),
                    is_likely_scanned=is_likely_scanned,
                    ocr_attempted=ocr_attempted,
                    ocr_succeeded=ocr_succeeded,
                    ocr_confidence=round(ocr_confidence, 3),
                    text_extraction_status=extraction_status,
                    raw_digital_text=raw_digital_text,
                    raw_ocr_text=raw_ocr_text,
                    blocks=page_blocks,
                ))

            total_pages = max(1, len(reader.pages))
            if empty_pages == total_pages or total_chars == 0:
                extraction_quality = 0.0
                warnings.append(f"PDF contains no extractable text ({filename}).")
                full_text = f"# {title}\n\n[No extractable text found in {filename}]"
            else:
                if is_scanned_overall:
                    extraction_quality = max(0.65, min(0.95, 1.0 - (empty_pages / total_pages) * 0.4))
                else:
                    extraction_quality = max(0.7, min(1.0, 1.0 - (empty_pages / total_pages) * 0.3))
                full_text = f"# {title}\n\n" + "\n\n".join(pages_text)

            return full_text, pages, blocks, tables, warnings, is_scanned_overall, extraction_quality

        except Exception as e:
            warnings.append(f"PDF extraction error: {str(e)}")
            return f"# {title}\n\n[Corrupt PDF: {str(e)}]", [], [], [], warnings, False, 0.0

    @classmethod
    def _parse_docx_structured(
        cls, raw_bytes: bytes, title: str, filename: str
    ) -> Tuple[str, List[DocumentPage], List[ContentBlock], List[Dict[str, Any]], List[str]]:
        blocks: List[ContentBlock] = []
        tables: List[Dict[str, Any]] = []
        warnings: List[str] = []
        ordered_elements_text: List[str] = []

        try:
            import docx
            from docx.oxml.text.paragraph import CT_P
            from docx.oxml.table import CT_Tbl
            from docx.text.paragraph import Paragraph
            from docx.table import Table

            doc = docx.Document(io.BytesIO(raw_bytes))
            current_hier: List[str] = [title]
            elem_idx = 1
            tbl_idx = 1

            # Traverse the document body in its original sequential order, interleaving paragraphs and tables
            for child in doc.element.body.iterchildren():
                if isinstance(child, CT_P):
                    p = Paragraph(child, doc)
                    txt = p.text.strip()
                    if not txt:
                        continue
                    style_name = (p.style.name if hasattr(p, "style") and p.style else "").lower()
                    is_heading = "heading" in style_name or bool(
                        re.match(r"^(Chapter\s+\d+|Page\s+\d+|Section\s+\d+|Control\s+rule|Policy\s+\d+)", txt, re.IGNORECASE)
                    )
                    level = 1
                    if "heading" in style_name:
                        m = re.search(r"\d+", style_name)
                        if m:
                            level = int(m.group(0))

                    if is_heading:
                        current_hier = current_hier[:level] + [txt]
                        formatted_text = f"## {txt}"
                        b_type = ContentBlockType.HEADING
                    else:
                        formatted_text = txt
                        b_type = ContentBlockType.PARAGRAPH

                    blocks.append(ContentBlock(
                        id=f"blk_docx_{elem_idx}",
                        block_type=b_type,
                        text=formatted_text,
                        raw_text=txt,
                        heading_path=list(current_hier),
                    ))
                    ordered_elements_text.append(formatted_text)
                    elem_idx += 1

                elif isinstance(child, CT_Tbl):
                    t = Table(child, doc)
                    table_rows = []
                    headers = []
                    has_merged_cells = False

                    for r_idx, row in enumerate(t.rows):
                        cells = []
                        prev_tc = None
                        for cell in row.cells:
                            # Detect merged cells by checking underlying XML element identity
                            if prev_tc is not None and cell._tc is prev_tc:
                                has_merged_cells = True
                            prev_tc = cell._tc
                            cells.append(cell.text.strip())

                        if r_idx == 0:
                            headers = cells
                        table_rows.append(cells)

                    if table_rows:
                        formatted_rows = ["| " + " | ".join(r) + " |" for r in table_rows]
                        t_text = "\n" + "\n".join(formatted_rows) + "\n"
                        ordered_elements_text.append(t_text)
                        t_data = {
                            "table_id": f"tbl_docx_{tbl_idx}",
                            "headers": headers,
                            "rows": table_rows,
                            "has_merged_cells": has_merged_cells,
                            "heading_path": list(current_hier),
                        }
                        tables.append(t_data)
                        blocks.append(ContentBlock(
                            id=f"blk_table_{tbl_idx}",
                            block_type=ContentBlockType.TABLE,
                            text=t_text,
                            raw_text=t_text,
                            table_data=t_data,
                            heading_path=list(current_hier),
                        ))
                        tbl_idx += 1
                        elem_idx += 1

            full_text = f"# {title}\n\n" + "\n\n".join(ordered_elements_text)
            return full_text, [], blocks, tables, warnings
        except Exception as e:
            warnings.append(f"DOCX parser error: {str(e)}")
            return "", [], [], [], warnings

    @classmethod
    def _parse_xlsx_structured(
        cls, raw_bytes: bytes, title: str, filename: str
    ) -> Tuple[str, List[DocumentPage], List[ContentBlock], List[Dict[str, Any]], List[str]]:
        blocks: List[ContentBlock] = []
        tables: List[Dict[str, Any]] = []
        warnings: List[str] = []
        sheets_markdown: List[str] = []

        try:
            import openpyxl
            wb_formulas = openpyxl.load_workbook(io.BytesIO(raw_bytes), data_only=False)
            try:
                wb_values = openpyxl.load_workbook(io.BytesIO(raw_bytes), data_only=True)
            except Exception:
                wb_values = None

            for s_idx, sheet_name in enumerate(wb_formulas.sheetnames, start=1):
                ws_form = wb_formulas[sheet_name]
                ws_val = wb_values[sheet_name] if wb_values and sheet_name in wb_values.sheetnames else None

                is_hidden = getattr(ws_form, "sheet_state", "visible") == "hidden"
                merged_ranges = [str(r) for r in ws_form.merged_cells.ranges]

                max_r = ws_form.max_row or 0
                max_c = ws_form.max_column or 0
                if max_r == 0 or max_c == 0:
                    continue

                table_rows: List[List[str]] = []
                headers: List[str] = []
                grid_metadata: List[List[Dict[str, Any]]] = []

                for r in range(1, max_r + 1):
                    row_cells: List[str] = []
                    row_meta: List[Dict[str, Any]] = []
                    for c in range(1, max_c + 1):
                        cell_f = ws_form.cell(row=r, column=c)
                        cell_v = ws_val.cell(row=r, column=c) if ws_val else None

                        val_f = cell_f.value
                        val_v = cell_v.value if cell_v else None

                        formula = None
                        if isinstance(val_f, str) and val_f.startswith("="):
                            formula = val_f
                            display_val = val_v if val_v is not None else val_f
                        else:
                            display_val = val_f

                        display_str = str(display_val) if display_val is not None else ""
                        row_cells.append(display_str)
                        row_meta.append({
                            "coordinate": cell_f.coordinate,
                            "row": r,
                            "col": c,
                            "value": display_val,
                            "formula": formula,
                            "data_type": cell_f.data_type,
                            "number_format": cell_f.number_format,
                        })

                    if r == 1:
                        headers = row_cells
                    table_rows.append(row_cells)
                    grid_metadata.append(row_meta)

                if table_rows:
                    formatted_rows = []
                    for idx, row in enumerate(table_rows):
                        clean_row = [c.replace("\n", " ").replace("|", "\\|") for c in row]
                        formatted_rows.append("| " + " | ".join(clean_row) + " |")
                        if idx == 0:
                            formatted_rows.append("| " + " | ".join(["---"] * len(clean_row)) + " |")

                    sheet_hdr = f"## Sheet: {sheet_name}" + (" (Hidden)" if is_hidden else "")
                    sheet_md = sheet_hdr + "\n\n" + "\n".join(formatted_rows)
                    sheets_markdown.append(sheet_md)

                    t_data = {
                        "sheet_name": sheet_name,
                        "table_id": f"tbl_sheet_{s_idx}",
                        "is_hidden": is_hidden,
                        "merged_ranges": merged_ranges,
                        "headers": headers,
                        "rows": table_rows[1:] if len(table_rows) > 1 else [],
                        "row_count": max_r,
                        "col_count": max_c,
                        "cell_metadata": grid_metadata,
                    }
                    tables.append(t_data)
                    blocks.append(ContentBlock(
                        id=f"blk_xlsx_{s_idx}",
                        block_type=ContentBlockType.TABLE,
                        text=sheet_md,
                        raw_text=sheet_md,
                        table_data=t_data,
                    ))

            full_text = f"# {title}\n\n" + "\n\n".join(sheets_markdown)
            return full_text, [], blocks, tables, warnings

        except Exception as e:
            logger.warning("openpyxl failed for %s, falling back: %s", filename, e)
            warnings.append(f"XLSX openpyxl error: {str(e)}")
            full_text = cls._parse_xlsx(raw_bytes, title, filename)
            blocks.append(ContentBlock(
                id="blk_xlsx_fallback",
                block_type=ContentBlockType.TABLE,
                text=full_text,
                raw_text=full_text,
            ))
            return full_text, [], blocks, tables, warnings

    @classmethod
    def _parse_pdf(cls, raw_bytes: bytes, title: str, filename: str) -> str:
        text, _, _, _, _, _, _ = cls._parse_pdf_structured(raw_bytes, title, filename)
        return text

    @classmethod
    def _parse_docx(cls, raw_bytes: bytes, title: str, filename: str) -> str:
        text, _, _, _, _ = cls._parse_docx_structured(raw_bytes, title, filename)
        return text

    @classmethod
    def _parse_xlsx(cls, raw_bytes: bytes, title: str, filename: str) -> str:
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                shared_strings = []
                if "xl/sharedStrings.xml" in zf.namelist():
                    ss_tree = ET.fromstring(zf.read("xl/sharedStrings.xml"))
                    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                    for si in ss_tree.findall(".//main:si", ns):
                        t_nodes = [t.text for t in si.findall(".//main:t", ns) if t.text]
                        shared_strings.append("".join(t_nodes))

                sheet_files = sorted([f for f in zf.namelist() if f.startswith("xl/worksheets/sheet") and f.endswith(".xml")])
                sheets_output = []

                for idx, sheet_file in enumerate(sheet_files, start=1):
                    sheet_tree = ET.fromstring(zf.read(sheet_file))
                    ns = {"main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
                    rows_data = []

                    for row in sheet_tree.findall(".//main:row", ns):
                        row_vals = []
                        for cell in row.findall(".//main:c", ns):
                            cell_type = cell.get("t")
                            v_node = cell.find("main:v", ns)
                            if v_node is not None and v_node.text:
                                val = v_node.text
                                if cell_type == "s" and val.isdigit():
                                    idx_val = int(val)
                                    val = shared_strings[idx_val] if idx_val < len(shared_strings) else val
                                row_vals.append(val.strip())
                            else:
                                t_node = cell.find("main:is/main:t", ns)
                                if t_node is not None and t_node.text:
                                    row_vals.append(t_node.text.strip())
                        if row_vals and any(row_vals):
                            rows_data.append("| " + " | ".join(row_vals) + " |")

                    if rows_data:
                        sheets_output.append(f"## Sheet {idx}\n\n" + "\n".join(rows_data))

                if sheets_output:
                    return f"# {title}\n\n" + "\n\n".join(sheets_output)
        except Exception:
            pass

        return cls._parse_plain_text(raw_bytes, title, filename)

    @classmethod
    def _parse_pptx(cls, raw_bytes: bytes, title: str, filename: str) -> str:
        try:
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                slide_files = sorted(
                    [f for f in zf.namelist() if f.startswith("ppt/slides/slide") and f.endswith(".xml")],
                    key=lambda x: int(re.search(r"\d+", x).group()) if re.search(r"\d+", x) else 0,
                )
                slides_output = []
                ns = {"a": "http://schemas.openxmlformats.org/drawingml/2006/main"}

                for idx, sfile in enumerate(slide_files, start=1):
                    tree = ET.fromstring(zf.read(sfile))
                    texts = [t.text.strip() for t in tree.findall(".//a:t", ns) if t.text and t.text.strip()]
                    if texts:
                        slides_output.append(f"## Slide {idx}\n" + "\n".join(texts))

                if slides_output:
                    return f"# {title}\n\n" + "\n\n".join(slides_output)
        except Exception:
            pass

        return cls._parse_plain_text(raw_bytes, title, filename)

    @classmethod
    def _parse_csv(cls, raw_bytes: bytes, title: str, delimiter: Optional[str] = None) -> str:
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                decoded = raw_bytes.decode(enc)
                f = io.StringIO(decoded)
                reader = csv.reader(f, delimiter=delimiter) if delimiter else csv.reader(f)
                rows = []
                headers = []
                for idx, row in enumerate(reader):
                    # Preserve all columns and empty cell positions without column shifting
                    clean_row = [c.strip().replace("\n", " ").replace("|", "\\|") for c in row]
                    if any(c for c in clean_row) or idx == 0:
                        rows.append("| " + " | ".join(clean_row) + " |")
                        rows.append("| " + " | ".join(["---"] * len(clean_row)) + " |")
                    else:
                        # Align row column count with header
                        if headers and len(clean_row) < len(headers):
                            clean_row.extend([""] * (len(headers) - len(clean_row)))
                        rows.append("| " + " | ".join(clean_row[:len(headers)] if headers else clean_row) + " |")
                if rows:
                    return f"# {title}\n\n" + "\n".join(rows)
            except UnicodeDecodeError:
                continue
        return ""

    @classmethod
    def _parse_json(cls, raw_bytes: bytes, title: str, is_jsonl: bool = False) -> str:
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                decoded = raw_bytes.decode(enc).strip()
                if is_jsonl:
                    lines = [json.loads(line) for line in decoded.splitlines() if line.strip()]
                    formatted = json.dumps(lines, indent=2)
                else:
                    data = json.loads(decoded)
                    formatted = json.dumps(data, indent=2)
                return f"# {title}\n\n```json\n{formatted}\n```"
            except Exception:
                continue
        return cls._parse_plain_text(raw_bytes, title, "data.json")

    @classmethod
    def _parse_html(cls, raw_bytes: bytes, title: str) -> str:
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                html_str = raw_bytes.decode(enc)
                # Try robust lxml.html DOM parser
                try:
                    import lxml.html
                    doc = lxml.html.fromstring(html_str)
                    # Strip style, script, noscript, and metadata tags
                    for el in doc.xpath('//script | //style | //noscript | //head | //meta | //link'):
                        el.drop_tree()

                    body = doc.xpath('//body')
                    root = body[0] if body else doc

                    rendered_parts: List[str] = []
                    for el in root.iter():
                        tag = el.tag
                        if not isinstance(tag, str):
                            continue
                        tag = tag.lower()
                        if tag in ('h1', 'h2', 'h3', 'h4', 'h5', 'h6'):
                            level = int(tag[1])
                            txt = el.text_content().strip()
                            if txt:
                                rendered_parts.append(f"\n\n{'#' * level} {txt}\n")
                        elif tag == 'p' and el.getparent() is not None and el.getparent().tag.lower() not in ('td', 'th', 'li'):
                            txt = el.text_content().strip()
                            if txt:
                                rendered_parts.append(f"\n\n{txt}\n")
                        elif tag in ('ul', 'ol') and el.getparent() is not None and el.getparent().tag.lower() not in ('li',):
                            items = [li.text_content().strip() for li in el.xpath('./li') if li.text_content().strip()]
                            if items:
                                list_md = "\n".join(f"- {it}" for it in items)
                                rendered_parts.append(f"\n\n{list_md}\n")
                        elif tag == 'table':
                            # Process only top-level tables to avoid double-processing nested tables
                            if not el.xpath('ancestor::table'):
                                headers = [th.text_content().strip() for th in el.xpath('.//tr[1]//th | .//thead//th')]
                                rows = []
                                for tr in el.xpath('.//tbody/tr | .//tr[position()>1]'):
                                    cells = [td.text_content().strip() for td in tr.xpath('./td | ./th')]
                                    if cells:
                                        rows.append(cells)
                                if headers or rows:
                                    t_lines = []
                                    if headers:
                                        t_lines.append("| " + " | ".join(headers) + " |")
                                        t_lines.append("| " + " | ".join(["---"] * len(headers)) + " |")
                                    for r in rows:
                                        t_lines.append("| " + " | ".join(r) + " |")
                                    rendered_parts.append("\n\n" + "\n".join(t_lines) + "\n")

                    extracted = re.sub(r"\n{3,}", "\n\n", "".join(rendered_parts)).strip()
                    if extracted:
                        return f"# {title}\n\n{extracted}"
                except Exception:
                    pass

                # Fallback to _HTMLToTextExtractor
                extractor = _HTMLToTextExtractor()
                extractor.feed(html_str)
                extracted = extractor.get_text()
                if extracted:
                    return f"# {title}\n\n{extracted}"
            except Exception:
                continue
        return cls._parse_plain_text(raw_bytes, title, "document.html")

    @classmethod
    def _parse_xml(cls, raw_bytes: bytes, title: str) -> str:
        for enc in ("utf-8", "utf-8-sig", "latin-1"):
            try:
                xml_str = raw_bytes.decode(enc)
                tree = ET.fromstring(xml_str)
                formatted_elements = []

                def _render_elem(elem: ET.Element, depth: int = 0):
                    tag = elem.tag.split("}")[-1] if "}" in elem.tag else elem.tag
                    attrs = " ".join(f'{k}="{v}"' for k, v in elem.attrib.items())
                    attr_str = f" ({attrs})" if attrs else ""
                    txt = (elem.text or "").strip()
                    indent = "  " * depth
                    if txt:
                        formatted_elements.append(f"{indent}- **<{tag}{attr_str}>**: {txt}")
                    elif attrs:
                        formatted_elements.append(f"{indent}- **<{tag}{attr_str}>**")
                    for child in elem:
                        _render_elem(child, depth + 1)

                _render_elem(tree)
                if formatted_elements:
                    return f"# {title}\n\n" + "\n".join(formatted_elements)
            except Exception:
                continue
        return cls._parse_plain_text(raw_bytes, title, "data.xml")

    @classmethod
    def _parse_rtf(cls, raw_bytes: bytes, title: str) -> str:
        text = raw_bytes.decode("latin-1", errors="ignore")
        # Strip header/font/color/stylesheet tables
        text = re.sub(r"\{\\\*(?:fonttbl|colortbl|stylesheet|info)[^}]*\}", " ", text)
        # Structural control words
        text = re.sub(r"\\par\b|\\line\b", "\n", text)
        text = re.sub(r"\\tab\b", "\t", text)
        text = re.sub(r"\\bullet\b", "• ", text)
        text = re.sub(r"\\endash\b", "–", text)
        text = re.sub(r"\\emdash\b", "—", text)
        text = re.sub(r"\\lquote\b|\\rquote\b", "'", text)
        text = re.sub(r"\\ldblquote\b|\\rdblquote\b", '"', text)

        # Hex escapes \'xx
        def _hex_repl(m):
            try:
                return chr(int(m.group(1), 16))
            except Exception:
                return ""
        text = re.sub(r"\\\'([0-9a-fA-F]{2})", _hex_repl, text)

        # Unicode escapes \uN?
        def _u_repl(m):
            try:
                code = int(m.group(1))
                if code < 0:
                    code += 65536
                return chr(code)
            except Exception:
                return ""
        text = re.sub(r"\\u(-?\d+)(?:\?)?", _u_repl, text)

        # Remove remaining control words and group braces
        clean_text = re.sub(r"\\[a-zA-Z0-9\-]+", " ", text)
        clean_text = re.sub(r"[{}\\]", " ", clean_text)
        clean_text = re.sub(r"[ \t]+", " ", clean_text)
        clean_text = re.sub(r"\n\s*\n+", "\n\n", clean_text).strip()
        return f"# {title}\n\n{clean_text}"

    @classmethod
    def _parse_markdown_structured(
        cls, raw_bytes: bytes, title: str, filename: str
    ) -> Tuple[str, List[DocumentPage], List[ContentBlock]]:
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                text = raw_bytes.decode(enc)
                break
            except UnicodeDecodeError:
                continue
        else:
            text = raw_bytes.decode("utf-8", errors="replace")

        lines = text.splitlines()
        blocks: List[ContentBlock] = []
        current_hier: List[str] = [title]
        current_para: List[str] = []
        b_idx = 1

        def flush_para():
            nonlocal b_idx
            if current_para:
                para_text = " ".join(current_para).strip()
                if para_text:
                    blocks.append(ContentBlock(
                        id=f"blk_md_{b_idx}",
                        block_type=ContentBlockType.PARAGRAPH,
                        text=para_text,
                        raw_text=para_text,
                        heading_path=list(current_hier),
                        page_number=1,
                    ))
                    b_idx += 1
                current_para.clear()

        in_yaml_frontmatter = False
        if lines and lines[0].strip() == "---":
            in_yaml_frontmatter = True
            lines = lines[1:]

        in_code_block = False
        code_block_lines: List[str] = []
        code_block_lang = ""

        in_table_block = False
        table_lines: List[str] = []

        def flush_table():
            nonlocal b_idx, in_table_block, table_lines
            if table_lines:
                tbl_text = "\n".join(table_lines)
                headers = []
                data_rows = []
                for idx, t_line in enumerate(table_lines):
                    cells = [c.strip() for c in t_line.split("|")[1:-1]] if t_line.startswith("|") else [c.strip() for c in t_line.split("|")]
                    if idx == 0:
                        headers = cells
                    elif idx == 1 and all(re.match(r"^:?-+:?$", c) for c in cells if c):
                        continue
                    else:
                        data_rows.append(cells)

                blocks.append(ContentBlock(
                    id=f"blk_md_{b_idx}",
                    block_type=ContentBlockType.TABLE,
                    text=tbl_text,
                    raw_text=tbl_text,
                    heading_path=list(current_hier),
                    page_number=1,
                    table_data={"headers": headers, "rows": data_rows},
                ))
                b_idx += 1
                table_lines = []
            in_table_block = False

        for line in lines:
            if in_yaml_frontmatter:
                if line.strip() == "---":
                    in_yaml_frontmatter = False
                continue

            stripped = line.strip()

            # Fenced code block handling
            if stripped.startswith("```"):
                flush_para()
                flush_table()
                if not in_code_block:
                    in_code_block = True
                    code_block_lang = stripped[3:].strip()
                    code_block_lines = [line]
                else:
                    code_block_lines.append(line)
                    code_text = "\n".join(code_block_lines)
                    blocks.append(ContentBlock(
                        id=f"blk_md_{b_idx}",
                        block_type=ContentBlockType.CODE_OR_CONFIG,
                        text=code_text,
                        raw_text=code_text,
                        heading_path=list(current_hier),
                        page_number=1,
                    ))
                    b_idx += 1
                    in_code_block = False
                    code_block_lines = []
                    code_block_lang = ""
                continue

            if in_code_block:
                code_block_lines.append(line)
                continue

            # Markdown Table handling
            if stripped.startswith("|") and ("|" in stripped[1:]):
                flush_para()
                in_table_block = True
                table_lines.append(line)
                continue
            elif in_table_block:
                flush_table()

            if not stripped:
                flush_para()
                continue

            # Heading check
            heading_m = re.match(r"^(#{1,6})\s+(.*)$", stripped)
            if heading_m:
                flush_para()
                level = len(heading_m.group(1))
                h_text = heading_m.group(2).strip()
                current_hier = current_hier[:level] + [h_text]
                blocks.append(ContentBlock(
                    id=f"blk_md_{b_idx}",
                    block_type=ContentBlockType.HEADING,
                    text=h_text,
                    raw_text=line,
                    heading_path=list(current_hier),
                    page_number=1,
                ))
                b_idx += 1
                continue

            # List items or quote notes
            if re.match(r"^(?:>\s*\[!NOTE\]|>\s*|(?:\d+[\.\)]|[a-z][\.\)]|\*|-)\s+)", stripped):
                flush_para()
                clean_item = re.sub(r"^(?:>\s*\[!NOTE\]\s*|>\s*)", "", stripped).strip()
                blocks.append(ContentBlock(
                    id=f"blk_md_{b_idx}",
                    block_type=ContentBlockType.LIST_ITEM if not stripped.startswith(">") else ContentBlockType.PARAGRAPH,
                    text=clean_item,
                    raw_text=line,
                    heading_path=list(current_hier),
                    page_number=1,
                ))
                b_idx += 1
                continue

            current_para.append(stripped)

        flush_para()
        flush_table()
        if in_code_block and code_block_lines:
            code_text = "\n".join(code_block_lines)
            blocks.append(ContentBlock(
                id=f"blk_md_{b_idx}",
                block_type=ContentBlockType.CODE_OR_CONFIG,
                text=code_text,
                raw_text=code_text,
                heading_path=list(current_hier),
                page_number=1,
            ))

        pages = [DocumentPage(page_number=1, text=text, width=612.0, height=792.0)]
        return text, pages, blocks

    @classmethod
    def _parse_code_or_config(cls, raw_bytes: bytes, title: str, lang: str) -> str:
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                decoded = raw_bytes.decode(enc)
                return f"# {title}\n\n```{lang}\n{decoded}\n```"
            except UnicodeDecodeError:
                continue
        return cls._parse_plain_text(raw_bytes, title, f"code.{lang}")

    @classmethod
    def _parse_plain_text(cls, raw_bytes: bytes, title: str, filename: str) -> str:
        for enc in ("utf-8", "utf-8-sig", "latin-1", "cp1252"):
            try:
                decoded = raw_bytes.decode(enc)
                if any(c for c in decoded if c.isprintable()):
                    return f"# {title}\n\n{decoded.strip()}"
            except UnicodeDecodeError:
                continue
        return f"# {title}\n\n[Binary file {filename} ({len(raw_bytes)} bytes) contains no extractable plain text]"
