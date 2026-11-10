# Universal Parser and Claim Extraction — Testing Checklist

This document is the official, reusable testing and validation checklist for the **Context Trust Layer Universal Document Parser and Claim Extraction Engine**. 

> **Core Principle**: Extracting text successfully does **not** mean extracting claims correctly. A parser can extract every word from a PDF or Slack dump and still fail to identify table rows, heading relationships, exception clauses, actor direction, or atomic claims.

---

## 1. File Format Detection and Universal Parser

**Objective**: Verify whether the system identifies and processes different types of enterprise data through the appropriate parser without forcing everything through plain-text extraction.

| ID | Testing question | Expected behavior |
| :--- | :--- | :--- |
| **UP-001** | Does the system identify the uploaded file format correctly? | Identify PDF, DOCX, DOC, XLSX, XLS, PPTX, PPT, TXT, MD, HTML, CSV, JSON, XML, EML, etc. |
| **UP-002** | Does it select the correct parser based on the file type? | Route each format to the appropriate parser without treating all files as plain text. |
| **UP-003** | Does it support normal PDFs? | Extract text, layout, paragraphs, headings, tables, and metadata. |
| **UP-004** | Does it support scanned PDFs? | Detect scanned pages and apply OCR. |
| **UP-005** | Does it support image-based documents? | Extract text from images using OCR. |
| **UP-006** | Does it support DOCX and DOC files? | Preserve paragraphs, headings, tables, lists, headers, footers, and document structure. |
| **UP-007** | Does it support XLSX and XLS files? | Preserve worksheets, cell values, formulas where relevant, headers, rows, columns, and merged cells. |
| **UP-008** | Does it support Markdown files? | Identify headings, subheadings, paragraphs, lists, tables, code blocks, links, and blockquotes. |
| **UP-009** | Does it support HTML files? | Identify titles, headings, sections, tables, lists, links, and paragraph structure. |
| **UP-010** | Does it support JSON files? | Preserve keys, values, arrays, nested objects, and relationships between fields. |
| **UP-011** | Does it support XML files? | Preserve tags, attributes, hierarchy, and nested elements. |
| **UP-012** | Does it support CSV files? | Identify column headers, records, cell values, and row relationships. |
| **UP-013** | Does it support PowerPoint files? | Extract slide titles, text boxes, tables, bullet points, notes, and relevant image text. |
| **UP-014** | Does it support email formats? | Preserve sender, recipient, subject, timestamp, body, attachments, and thread relationships. |
| **UP-015** | Does it support Slack messages? | Preserve workspace, channel, sender, timestamp, message text, thread replies, attachments, and message relationships. |
| **UP-016** | Does it support Microsoft Teams messages? | Preserve team, channel, sender, timestamps, replies, attachments, and conversation context. |
| **UP-017** | Does it support database exports? | Identify database type and process supported SQL, SQLite, JSON, CSV, or other structured exports. |
| **UP-018** | Does it support SQL files? | Identify tables, columns, data types, constraints, INSERT statements, and relevant relationships. |
| **UP-019** | Does it support log files? | Preserve timestamps, severity, components, events, and structured message content. |
| **UP-020** | Does it support files without extensions? | Identify format using content signatures where possible, or report an unsupported/unknown format. |
| **UP-021** | Does it handle corrupted or partially readable files? | Report extraction failures without silently discarding content. |
| **UP-022** | Does it handle password-protected or encrypted files? | Report that content is inaccessible instead of claiming successful extraction. |
| **UP-023** | Does it handle large files? | Process in manageable sections without losing content or document order. |
| **UP-024** | Does it identify unsupported formats? | Clearly report unsupported formats rather than generating fabricated extracted content. |

> **Crucial Rule**: The universal parser must have format-specific extraction adapters behind a common evidence representation contract. It must never force disparate file types into generic lossy text blobs.

---

## 2. Document Metadata Detection

**Objective**: Verify whether the system identifies the source identity, file information, and version information correctly.

| ID | Testing question | Expected behavior |
| :--- | :--- | :--- |
| **META-001** | Does it identify the original file name? | Preserve the exact original file name. |
| **META-002** | Does it identify the file extension and MIME type? | Record the detected format and actual file type. |
| **META-003** | Does it identify the document title? | Extract the title separately from the file name. |
| **META-004** | Does it identify the document version? | Extract explicit version numbers, such as v1.0, v2.1, or Revision 3. |
| **META-005** | Does it identify the document creation date? | Extract available creation metadata. |
| **META-006** | Does it identify the last modified date? | Preserve the available modification timestamp. |
| **META-007** | Does it identify the effective date? | Identify when a policy or document becomes effective. |
| **META-008** | Does it identify the publication date? | Extract the date when the document was published. |
| **META-009** | Does it identify the expiration date? | Extract an explicit expiration date when present. |
| **META-010** | Does it identify the author or owner? | Preserve the document author, publisher, or responsible department when available. |
| **META-011** | Does it identify the company or organization? | Extract the organization associated with the document. |
| **META-012** | Does it identify the document category? | Identify policy, handbook, agreement, announcement, report, email, procedure, etc. |
| **META-013** | Does it distinguish file modification date from policy effective date? | Keep these as separate metadata fields. |
| **META-014** | Does it handle missing metadata? | Mark unavailable fields as unknown instead of inventing values. |
| **META-015** | Does it preserve source identity across re-ingestion? | Track the same source and its different versions separately. |
| **META-016** | Does it detect duplicate documents? | Identify duplicates using appropriate source identity and content fingerprints. |
| **META-017** | Does it preserve the original source location? | Record file path, connector ID, source ID, and native locator where available. |

> **Critical Guardrail**: If a policy was created in January, modified in March, and became effective in April, the system must **not** treat all three dates as the same date.

---

## 3. Heading, Subheading, and Paragraph Identification

**Objective**: Verify whether the system understands document hierarchy rather than extracting all text as one continuous paragraph.

| ID | Testing question | Expected behavior |
| :--- | :--- | :--- |
| **STR-001** | Does it identify the main document title? | Store the title as document-level information. |
| **STR-002** | Does it identify main headings? | Recognize section headings separately from body text. |
| **STR-003** | Does it identify subheadings? | Identify nested heading levels correctly. |
| **STR-004** | Does it preserve heading hierarchy? | Preserve relationships such as H1 → H2 → H3. |
| **STR-005** | Does it identify normal paragraphs separately? | Keep body paragraphs as separate structural units. |
| **STR-006** | Does it identify paragraphs belonging to a particular heading? | Associate each paragraph with its correct parent section. |
| **STR-007** | Does it identify paragraph boundaries correctly? | Avoid merging unrelated paragraphs. |
| **STR-008** | Does it identify numbered sections? | Preserve numbering such as 1, 1.1, 1.1.1. |
| **STR-009** | Does it identify section introductions? | Preserve introductory text that applies to subsequent rules. |
| **STR-010** | Does it identify definitions sections? | Recognize defined terms and their meanings. |
| **STR-011** | Does it identify footnotes and endnotes? | Preserve their content and association with relevant text. |
| **STR-012** | Does it identify headers and footers? | Distinguish them from ordinary paragraph content. |
| **STR-013** | Does it identify page breaks? | Preserve page-level evidence locations. |
| **STR-014** | Does it identify repeated headings? | Avoid treating every repeated header as a new policy section. |
| **STR-015** | Does it preserve the original reading order? | Keep document sections in their original order. |

---

## 4. Table Detection and Table Claim Extraction

**Objective**: Verify whether the system extracts claims from tables without losing relationships between headers, rows, columns, and cells.

| ID | Testing question | Expected behavior |
| :--- | :--- | :--- |
| **TBL-001** | Does it detect tables in PDFs? | Identify table boundaries and structure. |
| **TBL-002** | Does it detect tables in scanned PDFs? | Use OCR and table structure recognition where required. |
| **TBL-003** | Does it detect tables in DOCX and DOC? | Extract actual table structures rather than flattened text. |
| **TBL-004** | Does it detect tables in XLSX and XLS? | Preserve worksheets, rows, columns, and cell relationships. |
| **TBL-005** | Does it detect Markdown tables? | Identify header rows, separators, and data rows. |
| **TBL-006** | Does it detect HTML tables? | Preserve table, row, header, and cell relationships. |
| **TBL-007** | Does it detect CSV tables? | Correctly identify column headers and record values. |
| **TBL-008** | Does it identify table headers? | Identify column names and their semantic meaning. |
| **TBL-009** | Does it identify row headers? | Recognize labels that apply to an entire row. |
| **TBL-010** | Does it associate each cell with its correct header? | Preserve header-to-cell relationships. |
| **TBL-011** | Does it identify individual rows as separate evidence units? | Avoid combining unrelated rows. |
| **TBL-012** | Does it detect merged cells? | Preserve merged-cell relationships and inherited labels. |
| **TBL-013** | Does it detect multi-level headers? | Preserve parent-child column header relationships. |
| **TBL-014** | Does it detect tables spanning multiple pages? | Reconstruct table continuity when supported by evidence. |
| **TBL-015** | Does it preserve table captions and titles? | Associate captions with the correct table. |
| **TBL-016** | Does it preserve notes and footnotes associated with tables? | Retain relevant qualifications and exceptions. |
| **TBL-017** | Does it identify units and currencies? | Preserve values such as USD, INR, %, days, hours, and kilograms. |
| **TBL-018** | Does it extract claims from table rows? | Convert meaningful row relationships into claims. |
| **TBL-019** | Does it extract claims from individual cells when appropriate? | Identify standalone cell-based facts without inventing relationships. |
| **TBL-020** | Does it distinguish blank cells from zero values? | Preserve missing values and numeric zero separately. |
| **TBL-021** | Does it preserve the parent heading of a table? | Include section context when interpreting table values. |
| **TBL-022** | Does it avoid combining values from different rows? | Prevent incorrect cross-row claim creation. |
| **TBL-023** | Does it detect table contradictions? | Preserve conflicting rows as separate claims for downstream evaluation. |
| **TBL-024** | Does it preserve the original table location? | Record page, table ID, row ID, column ID, and cell coordinates where available. |

---

## 5. Image Detection and OCR Extraction

**Objective**: Verify whether the system detects images embedded in documents and extracts relevant text from them.

| ID | Testing question | Expected behavior |
| :--- | :--- | :--- |
| **IMG-001** | Does it detect embedded images in PDFs? | Identify image objects and their locations. |
| **IMG-002** | Does it detect scanned pages? | Identify pages containing image-based text. |
| **IMG-003** | Does it detect images in DOCX and DOC? | Extract embedded image content where supported. |
| **IMG-004** | Does it detect images in PowerPoint? | Identify slide images and image text. |
| **IMG-005** | Does it detect image-based tables? | Apply OCR and table recognition. |
| **IMG-006** | Does it detect screenshots containing text? | Extract readable text from screenshots. |
| **IMG-007** | Does it extract text from diagrams? | Identify text labels and preserve spatial context. |
| **IMG-008** | Does it detect flowcharts? | Preserve labels and relationships where supported. |
| **IMG-009** | Does it detect charts containing text and values? | Extract titles, legends, labels, and values where readable. |
| **IMG-010** | Does it detect handwritten text? | Apply handwriting recognition when supported, or flag uncertain content. |
| **IMG-011** | Does it handle low-resolution images? | Use quality checks and flag unreliable OCR. |
| **IMG-012** | Does it handle rotated images? | Correct orientation when possible. |
| **IMG-013** | Does it handle multiple images on one page? | Extract each image separately. |
| **IMG-014** | Does it avoid duplicate extraction? | Prevent the same image text from being extracted repeatedly through different paths. |
| **IMG-015** | Does it preserve OCR confidence and status? | Record OCR engine, confidence, and processing result. |
| **IMG-016** | Does it preserve image evidence locations? | Record page, image ID, bounding box, and source locator where available. |
| **IMG-017** | Does it identify image extraction failures? | Report unreadable images rather than silently ignoring them. |

---

## 6. Bullet Point and List Extraction

**Objective**: Verify whether the system correctly identifies bullet points, numbered lists, nested lists, and list relationships.

| ID | Testing question | Expected behavior |
| :--- | :--- | :--- |
| **LIST-001** | Does it detect unordered bullet points? | Identify each bullet as a separate structural unit. |
| **LIST-002** | Does it detect numbered lists? | Preserve numbering and order. |
| **LIST-003** | Does it detect alphabetic lists? | Preserve a), b), c), etc. |
| **LIST-004** | Does it detect Roman numeral lists? | Preserve i), ii), iii), etc. |
| **LIST-005** | Does it detect nested bullet points? | Preserve parent-child list relationships. |
| **LIST-006** | Does it detect nested numbered lists? | Preserve list hierarchy. |
| **LIST-007** | Does it associate a list with its introductory sentence? | Preserve lead-in context. |
| **LIST-008** | Does it identify whether each bullet is a separate rule? | Extract independent claims where appropriate. |
| **LIST-009** | Does it identify bullets that depend on the previous bullet? | Preserve shared context and dependencies. |
| **LIST-010** | Does it identify exceptions within bullets? | Preserve exception relationships. |
| **LIST-011** | Does it identify continuation bullets across pages? | Preserve continuity where supported. |
| **LIST-012** | Does it preserve bullet order? | Maintain original sequence. |
| **LIST-013** | Does it avoid combining unrelated bullets? | Keep separate rules separate. |
| **LIST-014** | Does it avoid splitting one logically dependent bullet incorrectly? | Preserve the complete meaning of the rule. |
| **LIST-015** | Does it extract claims from list items? | Produce atomic claims while retaining their parent context. |

---

## 7. Paragraph Splitting and Atomic Claim Extraction

*(Highest priority for claim quality and Trust Layer grounding)*

**Objective**: Verify whether the system converts meaningful statements into individual claims instead of treating an entire paragraph as one claim.

The canonical semantic claim model is structured around:
- **Subject**: Who or what the statement concerns.
- **Predicate**: Action, relation, rule, or property.
- **Object / Detail**: Target or entity affected.
- **Modality**: MUST / SHOULD / CAN / PERMITTED / PROHIBITED.
- **Polarity**: POSITIVE / NEGATIVE.
- **Conditions**: Pre-requisites or triggers.
- **Exceptions**: Explicit carve-outs.
- **Scope**: Department, geography, role, or applicability boundary.
- **Temporal Constraints**: Effective dates, durations, waiting periods.
- **Quantities & Units**: Numbers, currency, thresholds.
- **Evidence Bindings**: Link back to specific source units and exact character spans.

| ID | Testing question | Expected behavior |
| :--- | :--- | :--- |
| **CLM-001** | Does it identify individual statements inside a paragraph? | Split independent statements into separate claims. |
| **CLM-002** | Does it avoid treating an entire paragraph as one claim? | Avoid paragraph-sized claim objects when multiple claims exist. |
| **CLM-003** | Does it identify the subject of each claim? | Identify who or what the statement concerns. |
| **CLM-004** | Does it identify the predicate or action? | Identify the actual action, rule, relationship, or property. |
| **CLM-005** | Does it identify the object? | Identify the entity or thing affected by the action. |
| **CLM-006** | Does it preserve actor direction? | Distinguish who performs an action and who receives it. |
| **CLM-007** | Does it identify positive and negative statements? | Preserve polarity correctly. |
| **CLM-008** | Does it identify mandatory statements? | Detect must, shall, required to, and equivalent expressions. |
| **CLM-009** | Does it identify permissions? | Detect may, can, permitted to, and equivalent expressions. |
| **CLM-010** | Does it identify prohibitions? | Detect must not, cannot, prohibited from, etc. |
| **CLM-011** | Does it identify entitlements? | Identify what an actor is entitled to receive or do. |
| **CLM-012** | Does it identify conditions? | Preserve if, when, unless, provided that, subject to, etc. |
| **CLM-013** | Does it identify exceptions? | Preserve except, excluding, notwithstanding, unless, etc. |
| **CLM-014** | Does it identify limitations? | Preserve restrictions, caps, thresholds, and boundaries. |
| **CLM-015** | Does it identify numerical values? | Preserve numbers and their associated units. |
| **CLM-016** | Does it identify temporal conditions? | Distinguish deadlines, durations, effective dates, and waiting periods. |
| **CLM-017** | Does it identify geographical or organizational scope? | Preserve region, department, employee category, or jurisdiction. |
| **CLM-018** | Does it identify compound sentences containing multiple claims? | Split independent claims without changing their meaning. |
| **CLM-019** | Does it preserve dependent clauses? | Keep conditions and qualifications attached to the correct claim. |
| **CLM-020** | Does it distinguish examples from actual rules? | Avoid treating illustrative examples as governing requirements. |
| **CLM-021** | Does it distinguish definitions from claims? | Preserve definitions without incorrectly converting every definition into a policy rule. |
| **CLM-022** | Does it identify factual statements separately from instructions? | Preserve the content type and semantic role. |
| **CLM-023** | Does it identify questions separately from assertions? | Avoid converting questions into factual claims. |
| **CLM-024** | Does it identify references to other sections? | Preserve references for later contextual resolution. |
| **CLM-025** | Does it avoid creating claims from incomplete fragments? | Mark incomplete or unresolved statements appropriately. |
| **CLM-026** | Does it preserve the original sentence and evidence span? | Maintain a direct link to source text. |
| **CLM-027** | Does it distinguish extracted claims from normalized claims? | Preserve the original extracted meaning and any canonical representation separately. |
| **CLM-028** | Does it avoid inventing missing subjects or objects? | Mark missing or unresolved fields explicitly. |
| **CLM-029** | Does it identify multiple subjects or objects correctly? | Preserve relationships without merging different actors. |
| **CLM-030** | Does it preserve negation scope? | Ensure that "not required to approve" is not interpreted as "required to approve." |

---

## 8. Language Identification and Multilingual Extraction

**Objective**: Verify whether the system handles documents written in different languages, mixed languages, and non-English characters.

| ID | Testing question | Expected behavior |
| :--- | :--- | :--- |
| **LNG-001** | Does it identify the primary document language? | Detect the dominant language. |
| **LNG-002** | Does it identify multiple languages in one document? | Detect language changes across sections or paragraphs. |
| **LNG-003** | Does it identify languages within one sentence? | Handle code-switching and mixed-language statements. |
| **LNG-004** | Does it preserve the original language? | Store original text without unintended translation. |
| **LNG-005** | Does it support English? | Extract and preserve English claims. |
| **LNG-006** | Does it support Indian languages? | Test supported languages such as Hindi, Telugu, Tamil, Kannada, Malayalam, and Bengali. |
| **LNG-007** | Does it support other international languages? | Test supported languages such as French, German, Spanish, Japanese, Chinese, and Arabic. |
| **LNG-008** | Does it preserve accented characters? | Correctly handle é, ñ, ü, ç, and similar characters. |
| **LNG-009** | Does it preserve Unicode characters? | Avoid character corruption during parsing and storage. |
| **LNG-010** | Does it preserve non-Latin scripts? | Avoid replacing characters with question marks or empty symbols. |
| **LNG-011** | Does it handle right-to-left languages? | Preserve Arabic, Hebrew, and other RTL reading order. |
| **LNG-012** | Does it preserve mathematical symbols? | Handle ≤, ≥, ≠, ±, and similar characters. |
| **LNG-013** | Does it preserve currency symbols? | Handle ₹, $, €, £, ¥, etc. |
| **LNG-014** | Does it preserve special punctuation? | Handle typographic quotes, dashes, bullets, and ellipses. |
| **LNG-015** | Does it preserve dates and localized numbers? | Handle regional date and decimal conventions. |
| **LNG-016** | Does it identify extraction failures caused by encoding? | Report encoding problems explicitly. |
| **LNG-017** | Does it distinguish translation from extraction? | Never silently replace original content with translated content. |
| **LNG-018** | Does it preserve the language of each extracted claim? | Store claim-level language metadata. |

---

## 9. Cross-Reference and Contextual Understanding

**Objective**: Verify whether the system understands references between paragraphs, headings, lists, and other sections.

| ID | Testing question | Expected behavior |
| :--- | :--- | :--- |
| **REF-001** | Does it identify phrases such as "this policy"? | Preserve the reference and its context. |
| **REF-002** | Does it identify phrases such as "the above conditions"? | Identify the referenced conditions when resolvable. |
| **REF-003** | Does it identify "subject to Section 4"? | Preserve the section reference. |
| **REF-004** | Does it identify references to previous paragraphs? | Resolve only when the reference is sufficiently clear. |
| **REF-005** | Does it identify references to future paragraphs? | Preserve forward references. |
| **REF-006** | Does it resolve pronouns such as he, she, they, it, and their? | Resolve antecedents when sufficiently supported. |
| **REF-007** | Does it resolve terms such as "such employees" and "these requests"? | Preserve their relationship to the relevant earlier context. |
| **REF-008** | Does it handle ambiguous references? | Mark them unresolved or ambiguous. |
| **REF-009** | Does it preserve list-level context? | Attach shared introductory conditions to the correct list items. |
| **REF-010** | Does it preserve table-level context? | Attach table headings and captions to the correct table claims. |
| **REF-011** | Does it identify definitions referenced elsewhere? | Preserve definition-to-claim relationships. |
| **REF-012** | Does it avoid using unrelated nearby text as evidence? | Bind claims only to evidence that supports their meaning. |

---

## 10. Slack, Teams, Email, and Conversational Data

**Objective**: Verify whether the system handles conversational information without losing message-level and thread-level relationships.

| ID | Testing question | Expected behavior |
| :--- | :--- | :--- |
| **MSG-001** | Does it identify individual messages? | Treat each message as a separate evidence unit. |
| **MSG-002** | Does it identify the sender? | Preserve sender identity and source ID. |
| **MSG-003** | Does it identify the timestamp? | Preserve the original message timestamp and timezone where available. |
| **MSG-004** | Does it identify channels and conversations? | Preserve channel, conversation, and workspace context. |
| **MSG-005** | Does it identify Slack threads? | Preserve parent message and reply relationships. |
| **MSG-006** | Does it identify Teams replies? | Preserve conversation and reply hierarchy. |
| **MSG-007** | Does it distinguish messages from attachments? | Preserve attachment references and their separate content. |
| **MSG-008** | Does it extract claims from short messages? | Extract meaningful claims even from brief messages. |
| **MSG-009** | Does it extract claims from multiple sentences in one message? | Split independent claims. |
| **MSG-010** | Does it preserve context across messages? | Resolve references only when supported by the conversation. |
| **MSG-011** | Does it distinguish questions from answers? | Do not treat questions as confirmed facts. |
| **MSG-012** | Does it distinguish proposals from approved decisions? | Preserve proposal, approval, and decision status. |
| **MSG-013** | Does it identify corrections and retractions? | Preserve their relationships to earlier messages. |
| **MSG-014** | Does it identify agreement or disagreement? | Preserve conversational stance without treating agreement alone as authoritative approval. |
| **MSG-015** | Does it identify quoted messages? | Distinguish quoted content from the current sender's statement. |
| **MSG-016** | Does it identify edited or deleted messages? | Preserve available edit/deletion metadata and source lifecycle status. |
| **MSG-017** | Does it identify duplicate messages after re-sync? | Avoid duplicate evidence records. |
| **MSG-018** | Does it preserve message ordering? | Maintain the conversation sequence. |
| **MSG-019** | Does it extract claims from email attachments? | Process attachments through their respective parsers. |
| **MSG-020** | Does it distinguish informal discussion from official policy? | Preserve source type and authority context rather than treating all messages as governing policy. |

---

## 11. Evidence and Source Traceability

**Objective**: Verify whether every extracted claim can be traced back to the exact original source.

| ID | Testing question | Expected behavior |
| :--- | :--- | :--- |
| **EVD-001** | Does every claim have an evidence reference? | Every claim should link to its supporting source material or an explicit missing-evidence status. |
| **EVD-002** | Does it preserve the original text span? | Retain the exact source text. |
| **EVD-003** | Does it preserve page numbers? | Record page numbers for paginated documents. |
| **EVD-004** | Does it preserve paragraph IDs? | Maintain paragraph-level source references. |
| **EVD-005** | Does it preserve heading paths? | Record the claim's parent heading and section hierarchy. |
| **EVD-006** | Does it preserve table IDs and row IDs? | Identify the originating table row. |
| **EVD-007** | Does it preserve cell-level references? | Identify the relevant cell and its header. |
| **EVD-008** | Does it preserve image references? | Link OCR text to its original image and location. |
| **EVD-009** | Does it preserve Slack message IDs? | Link claims to their original messages. |
| **EVD-010** | Does it preserve email IDs and thread IDs? | Maintain email source traceability. |
| **EVD-011** | Does it preserve source version information? | Identify which document version produced the claim. |
| **EVD-012** | Does it preserve extraction-run information? | Identify which ingestion and extraction run generated the claim. |
| **EVD-013** | Does it detect evidence offset mismatches? | Verify source offsets against the correct text representation. |
| **EVD-014** | Does it preserve OCR and extraction status? | Distinguish native text, OCR-derived text, and partially extracted content. |
| **EVD-015** | Does it prevent claims from losing their original evidence after normalization? | Maintain immutable original evidence and auditable transformations. |

---

## 12. Data Quality, Completeness, and Extraction Reliability

**Objective**: Verify that the parser does not silently lose information or create fabricated content.

| ID | Testing question | Expected behavior |
| :--- | :--- | :--- |
| **QLT-001** | Does it report the total number of pages, slides, sheets, messages, or records? | Record source-specific processing totals. |
| **QLT-002** | Does it report how many units were successfully processed? | Provide processed and failed counts. |
| **QLT-003** | Does it detect missing pages? | Identify gaps in page processing. |
| **QLT-004** | Does it detect missing table rows? | Identify incomplete table extraction. |
| **QLT-005** | Does it detect missing images? | Report unprocessed or unreadable images. |
| **QLT-006** | Does it detect empty or partially extracted sections? | Preserve failure status and reasons. |
| **QLT-007** | Does it detect duplicate content? | Identify duplicates without incorrectly deleting legitimate repeated statements. |
| **QLT-008** | Does it preserve original text when normalization fails? | Avoid destructive transformations. |
| **QLT-009** | Does it identify unsupported characters or encoding problems? | Report them instead of silently corrupting text. |
| **QLT-010** | Does it detect malformed structured data? | Report invalid JSON, XML, CSV, or SQL structures. |
| **QLT-011** | Does it prevent hallucinated text? | Extract only source-supported content. |
| **QLT-012** | Does it distinguish missing information from zero or false? | Preserve the difference between missing, null, zero, and false. |
| **QLT-013** | Does it handle partial processing? | Mark the document PARTIAL rather than claiming full success. |
| **QLT-014** | Does it produce a processing summary? | Report extracted, skipped, failed, and pending units. |
| **QLT-015** | Does it preserve all potentially claimable content? | Avoid silently discarding content because it does not match a predefined rule pattern. |

---

## 13. Claim Classification and Semantic Correctness

**Objective**: Verify whether the extracted statements are correctly represented and classified.

| ID | Testing question | Expected behavior |
| :--- | :--- | :--- |
| **SEM-001** | Does it distinguish policies from informational statements? | Preserve semantic content type. |
| **SEM-002** | Does it distinguish rules from examples? | Avoid classifying illustrative text as a governing rule. |
| **SEM-003** | Does it distinguish requirements from permissions? | Preserve modality. |
| **SEM-004** | Does it distinguish prohibitions from permissions? | Preserve polarity and modality. |
| **SEM-005** | Does it distinguish obligations from entitlements? | Preserve the direction of the relationship. |
| **SEM-006** | Does it distinguish conditions from outcomes? | Preserve conditional logic. |
| **SEM-007** | Does it distinguish exceptions from normal rules? | Keep exceptions attached to the appropriate claims. |
| **SEM-008** | Does it distinguish numerical limits from general descriptions? | Preserve thresholds, units, and comparators. |
| **SEM-009** | Does it distinguish temporal rules from other numeric rules? | Avoid confusing a posting duration with a return window, for example. |
| **SEM-010** | Does it distinguish actors correctly? | Avoid assigning a merchant's action to a customer or vice versa. |
| **SEM-011** | Does it distinguish similar but different actions? | Avoid treating refunds, credits, price adjustments, and subscription pauses as equivalent. |
| **SEM-012** | Does it distinguish source statements from inferred conclusions? | Label inference explicitly and do not present it as direct extraction. |
| **SEM-013** | Does it preserve unresolved claims? | Keep valid but unmapped claims instead of dropping them. |
| **SEM-014** | Does it identify ambiguous claims? | Mark ambiguity rather than forcing a classification. |
| **SEM-015** | Does it preserve claims with unknown predicates? | Avoid rejecting meaningful claims merely because the verb is unfamiliar. |

---

## 14. Normalization and Canonicalization

**Objective**: Verify whether extracted claims are mapped to a standard representation without changing their original meaning.

| ID | Testing question | Expected behavior |
| :--- | :--- | :--- |
| **NRM-001** | Does it preserve the original extracted claim? | Never overwrite the source-derived representation. |
| **NRM-002** | Does it create a separate normalized representation? | Keep original and canonical values distinct. |
| **NRM-003** | Does it map equivalent terms correctly? | Map genuine semantic equivalents. |
| **NRM-004** | Does it avoid mapping similar but different terms? | Prevent false semantic equivalence. |
| **NRM-005** | Does it preserve actor direction during normalization? | Do not reverse subject and object. |
| **NRM-006** | Does it preserve polarity? | Do not change positive to negative or vice versa. |
| **NRM-007** | Does it preserve modality? | Do not change may into must, for example. |
| **NRM-008** | Does it preserve conditions and exceptions? | Do not remove qualifying language. |
| **NRM-009** | Does it preserve units and thresholds? | Avoid changing numeric meaning. |
| **NRM-010** | Does it preserve temporal meaning? | Do not merge different time-related concepts. |
| **NRM-011** | Does it record mapping confidence and rationale? | Maintain auditable mapping metadata. |
| **NRM-012** | Does it preserve unmapped predicates? | Retain the original predicate with an unmapped status. |
| **NRM-013** | Does it record normalizer version? | Track which transformation produced the normalized claim. |
| **NRM-014** | Does it prevent embeddings from deciding mappings alone? | Use semantic similarity for candidate retrieval, followed by compatibility validation. |

---

## 15. Performance, Scale, and Re-ingestion

**Objective**: Verify that the universal parser remains reliable across large enterprise datasets and repeated ingestion.

| ID | Testing question | Expected behavior |
| :--- | :--- | :--- |
| **PERF-001** | Does it process multiple files in one ingestion run? | Support batch processing. |
| **PERF-002** | Does it process large PDFs without memory failures? | Use appropriate streaming or chunking. |
| **PERF-003** | Does it process large spreadsheets? | Avoid losing rows or sheets. |
| **PERF-004** | Does it process large Slack or Teams exports? | Preserve message ordering and relationships. |
| **PERF-005** | Does it handle multiple languages in a batch? | Maintain correct language identification. |
| **PERF-006** | Does it support concurrent processing? | Prevent cross-file evidence contamination. |
| **PERF-007** | Does it avoid duplicate claims during re-ingestion? | Use source and version identity appropriately. |
| **PERF-008** | Does it detect changed documents? | Identify changed content and versions. |
| **PERF-009** | Does it identify deleted or revoked source content? | Propagate source lifecycle changes. |
| **PERF-010** | Does it preserve old versions? | Keep historical source provenance when required. |
| **PERF-011** | Does it handle extraction retries? | Retry failed units without duplicating successful output. |
| **PERF-012** | Does it report processing time and resource usage? | Track latency, memory, and relevant processing metrics. |
| **PERF-013** | Does it isolate tenants? | Prevent one company's data from entering another company's extraction context. |
| **PERF-014** | Does it enforce source permissions? | Do not extract or expose content beyond authorized access. |

---

## 16. End-to-End Testing: Realistic Enterprise Document Scenarios

| ID | Test scenario | Expected behavior |
| :--- | :--- | :--- |
| **E2E-001** | PDF with headings, paragraphs, tables, and bullet points | Detect and process all structures separately. |
| **E2E-002** | Scanned PDF with images and table text | Apply OCR and recover readable content and table structure. |
| **E2E-003** | DOCX with nested headings, tables, and numbered lists | Preserve document hierarchy and extract claims. |
| **E2E-004** | Excel workbook with multiple sheets and merged headers | Preserve sheet, row, column, and header relationships. |
| **E2E-005** | Markdown document with code blocks and tables | Extract claimable content without interpreting code as policy statements. |
| **E2E-006** | Slack channel with parent messages and replies | Preserve conversation context and extract message-level claims. |
| **E2E-007** | Email with multiple replies and attachments | Preserve sender, time, thread, and attachment context. |
| **E2E-008** | Database export with nested JSON and relational records | Preserve entity relationships and source field provenance. |
| **E2E-009** | Document with multiple languages | Identify language and extract each section correctly. |
| **E2E-010** | Document with special symbols, currencies, and Unicode | Preserve the original characters and semantic meaning. |
| **E2E-011** | Document with exceptions and conditions | Preserve every qualification in the relevant claim. |
| **E2E-012** | Document with references to other sections | Preserve and resolve supported references. |
| **E2E-013** | Document containing contradictory policies | Extract both claims independently without silently reconciling them. |
| **E2E-014** | Document containing old and new versions | Preserve separate versions and their effective dates. |
| **E2E-015** | Document with unreadable images and missing pages | Report incomplete extraction rather than false success. |
| **E2E-016** | Document containing paragraphs, tables, lists, and screenshots of the same rule | Avoid duplicate claims while retaining all relevant evidence sources. |
| **E2E-017** | Large company data export with mixed file types | Process each source through the appropriate parser and common evidence contract. |
| **E2E-018** | Re-ingestion of the same Slack messages and files | Avoid duplicate records while preserving updates and source versions. |

---

## 17. Target Output Schema Contract

```json
{
  "source_metadata": {
    "file_name": "Employee_Leave_Policy.pdf",
    "file_type": "application/pdf",
    "document_title": "Employee Leave Policy",
    "document_version": "2.0",
    "creation_date": null,
    "modified_date": "2026-03-10",
    "effective_date": "2026-04-01",
    "language": "en",
    "source_id": "source_123",
    "source_sha256": "example_hash",
    "extraction_run_id": "run_456"
  },
  "processing_status": {
    "status": "COMPLETED",
    "total_pages": 10,
    "processed_pages": 10,
    "failed_pages": 0,
    "detected_tables": 2,
    "detected_images": 3,
    "ocr_pages": 1
  },
  "evidence_units": [
    {
      "evidence_id": "ev_001",
      "unit_type": "PARAGRAPH",
      "heading_path": [
        "Employee Leave Policy",
        "Annual Leave",
        "Eligibility"
      ],
      "original_text": "Employees can request annual leave after completing six months of service.",
      "page_number": 2,
      "language": "en",
      "extraction_method": "NATIVE_TEXT"
    },
    {
      "evidence_id": "ev_002",
      "unit_type": "TABLE_ROW",
      "table_id": "table_001",
      "row_id": "row_002",
      "headers": [
        "Employee Type",
        "Annual Leave"
      ],
      "cells": {
        "Employee Type": "Permanent",
        "Annual Leave": "20 days"
      },
      "page_number": 3,
      "extraction_method": "TABLE_EXTRACTION"
    }
  ],
  "claims": [
    {
      "claim_id": "claim_001",
      "evidence_ids": ["ev_001"],
      "subject": "Employees",
      "predicate": "request",
      "object": "annual leave",
      "modality": "PERMISSION",
      "polarity": "POSITIVE",
      "conditions": [
        "completion of six months of service"
      ],
      "exceptions": [],
      "scope": null,
      "temporal_constraints": [],
      "original_claim_text": "Employees can request annual leave after completing six months of service.",
      "extraction_status": "EXTRACTED",
      "mapping_status": "UNMAPPED",
      "verification_status": "PENDING"
    }
  ]
}
```

---

## 18. Mandatory Execution Rules for Antigravity

Whenever implementing, inspecting, or debugging the parser or claim extraction pipeline:

1. **Test all supported formats**: Do not test only PDF and DOCX.
2. **Test structure before claims**: Verify headings, tables, paragraphs, images, and lists before judging claim extraction.
3. **Test claims against original evidence**: Every extracted field must be traceable to the source.
4. **Test atomicity**: Multiple independent statements must not become one paragraph-sized claim.
5. **Test completeness**: Report missing pages, tables, images, rows, messages, and other failed units.
6. **Test semantic preservation**: Subject, predicate, object, modality, polarity, conditions, and exceptions must retain their original meaning.
7. **Test unknown patterns**: Do not reject a statement simply because it contains an unfamiliar verb, format, or expression.
8. **Test multilingual content**: Do not assume all company documents are English.
9. **Test version handling**: Do not confuse document dates, modification dates, and effective dates.
10. **Test re-ingestion**: Repeated synchronization must not create duplicate evidence or duplicate claims.
11. **Test failures explicitly**: Unsupported or unreadable content must be marked as failed, partial, or unresolved.
12. **Do not modify the implementation just to make tests pass**: First report actual behavior, evidence, failures, and responsible layers.

