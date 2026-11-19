# Corpus-Wide Universal Claim Certification Audit Report

**Audit Execution Timestamp**: 2026-11-14T05:39:39.735522+00:00  
**Target Directory**: `B:\Context_Layer_Ai\research\validation_50\raw_documents\Microsoft`  
**Architecture**: Universal 10-Gate Fail-Closed Evidence-First Engine  
**Total Documents Evaluated**: 40  
**Total Raw Candidates**: 3066  
**Execution Runtime**: 199.71 seconds  

---

## 1. Executive Summary & Core Invariant Metrics

All previous platform data was completely purged to guarantee a clean slate. Every document in the target directory was parsed directly into structured text, grounded with immutable SHA-256 evidence spans, and evaluated through the universal 10 gates without any hardcoded document assumptions or metadata synthesis.

| Certification Disposition | Count | Percentage | Operational Meaning |
|---|---|---|---|
| **Automated-Certified Canonical** | **359** | **11.7%** | Passed all 10 fail-closed gates; safe for autonomous agent retrieval |
| **Review Required** | **2122** | **69.2%** | Valid rules awaiting human confirmation or custom taxonomy binding |
| **Quarantined Compound** | **21** | **0.7%** | Multi-branch / mixed-polarity rules isolated from autonomous execution |
| **Non-Rule Reclassified** | **82** | **2.7%** | Definitions, descriptions, and references routed to citation-only tier |
| **Rejected Malformed** | **470** | **15.3%** | Page headers, postal addresses, or grammatical fragments rejected |
| **Collapsed Duplicates** | **12** | **0.4%** | Redundant propositions collapsed with `duplicate_of` back-pointer |

---

## 2. Performance Breakdown by Document Category

The universal architecture was tested across 6 distinct enterprise document archetypes:

| Document Type | Docs | Raw Candidates | Certified Canonical | Review Required | Quarantined | Non-Rules | Rejected | Duplicates |
|---|---|---|---|---|---|---|---|---|
| **Contract** | 12 | 2441 | 316 | 1662 | 21 | 64 | 367 | 11 |
| **Hr Policy** | 4 | 223 | 10 | 178 | 0 | 4 | 31 | 0 |
| **Invoice** | 9 | 133 | 7 | 107 | 0 | 4 | 15 | 0 |
| **Refund Policy** | 7 | 91 | 5 | 42 | 0 | 1 | 43 | 0 |
| **Regulatory Compliance** | 2 | 142 | 18 | 106 | 0 | 5 | 12 | 1 |
| **Technical Documentation** | 6 | 36 | 3 | 27 | 0 | 4 | 2 | 0 |

---

## 3. Universal 10-Gate Failure Pattern Analysis

Under the fail-closed policy, every candidate that does not strictly satisfy a gate is rejected or routed to review. The distribution of tripped gates across all candidates:

| Gate Evaluated | Tripped Count | Invariant Enforced |
|---|---|---|
| `predicate_valid` | **2456** | Controlled taxonomy vocabulary (fails closed on unapproved or banned catch-all generic predicates) |
| `text_integrity` | **432** | Authentic verbatim fidelity (blocks synthetic templates and injected slugs) |
| `clause_entails_claim` | **169** | Contextual entailment (rejects ungrounded assertions) |
| `subject_valid` | **139** | Actor/entity resolution (rejects fragments, page numbers, postal lines) |
| `evidence_located` | **117** | Exact byte/character offset alignment with source SHA-256 hash |
| `claim_type_allowed` | **82** | Operative rule requirement (reclassifies definitions, descriptions, references) |
| `atomicity_valid` | **21** | Atomic requirement (flags multi-branch disjunctions and mixed polarities) |
| `duplicate_valid` | **12** | Semantic uniqueness (collapses identical propositions to canonical) |
| `counterparty_resolved` | **4** | Obligor/obligee binding (rejects ungrounded dangling pronouns) |

---

## 4. Four-Tier Agent Retrieval Access Distribution

The risk policy service computes agent access permissions directly from certification state and predicate risk levels:

| Agent Access Tier | Count | Description |
|---|---|---|
| **HUMAN_CONFIRMATION_REQUIRED** | **2104** | High-risk actions (termination, indemnification) or unverified claims require human approval |
| **BLOCKED** | **522** | Quarantined, rejected, or duplicate claims strictly isolated from retrieval |
| **FULL_AUTONOMOUS** | **359** | Autonomous decision-making and constraint enforcement authorized |
| **CITATION_ONLY** | **81** | Available for background informational context and citations, not binding action |

---

## 5. Document-Level Certification Metrics (All 40 Documents)

| Document ID | Type | Pages | Raw Claims | Certified | Review | Quarantined | Non-Rules | Rej. | Dup. | Filename |
|---|---|---|---|---|---|---|---|---|---|---|
| `DOC-051` | contract | 6 | 84 | 4 | 68 | 4 | 2 | 6 | 0 | Agreement_for_leasing_or_renting_certain_Micr... |
| `DOC-052` | invoice | 6 | 10 | 1 | 9 | 0 | 0 | 0 | 0 | Checklist Microsoft Customer Agreement Billin... |
| `DOC-053` | contract | 5 | 46 | 6 | 28 | 0 | 2 | 10 | 0 | Enterprise Agreement.pdf |
| `DOC-054` | contract | 9 | 77 | 10 | 61 | 0 | 2 | 4 | 0 | Enterprise Subscription Enrollment (Indirect)... |
| `DOC-055` | contract | 294 | 1142 | 128 | 748 | 7 | 32 | 216 | 11 | mcaps-MSFT-GSA-Commercial-Supplier-Agreement-... |
| `DOC-056` | contract | 7 | 73 | 12 | 39 | 3 | 2 | 17 | 0 | Microsoft Business and Services Agreement.pdf |
| `DOC-057` | contract | 11 | 101 | 33 | 53 | 3 | 5 | 7 | 0 | Microsoft Customer Agreement.pdf |
| `DOC-058` | contract | 36 | 337 | 57 | 260 | 2 | 12 | 6 | 0 | Microsoft Partner Agreement (Direct).docx |
| `DOC-059` | contract | 30 | 274 | 45 | 213 | 2 | 7 | 7 | 0 | Microsoft Partner Agreement (Indirect).docx |
| `DOC-060` | contract | 11 | 143 | 20 | 114 | 0 | 0 | 9 | 0 | Migrate EA to Microsoft Customer Agreement AP... |
| `DOC-061` | contract | 11 | 154 | 0 | 70 | 0 | 0 | 84 | 0 | Modern-Work-Plan-Comparison-SMB.pdf |
| `DOC-062` | contract | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | Services Provider License Agreement (Indirect... |
| `DOC-063` | invoice | 24 | 40 | 5 | 31 | 0 | 3 | 1 | 0 | Set up billing for Microsoft Customer Agreeme... |
| `DOC-064` | contract | 5 | 10 | 1 | 8 | 0 | 0 | 1 | 0 | Software Licensing Terms - English _ Microsof... |
| `DOC-065` | invoice | 17 | 23 | 0 | 19 | 0 | 1 | 3 | 0 | Transfer Azure product billing ownership to a... |
| `DOC-066` | regulatory_compliance | 33 | 129 | 18 | 96 | 0 | 5 | 9 | 1 | MicrosoftProductandServicesDPA(WW)(English)(M... |
| `DOC-067` | regulatory_compliance | 4 | 13 | 0 | 10 | 0 | 0 | 3 | 0 | Supplier Security and Privacy Assurance Progr... |
| `DOC-068` | hr_policy | 2 | 15 | 0 | 14 | 0 | 0 | 1 | 0 | How-Microsoft-is-reinventing-HR-with-Microsof... |
| `DOC-069` | hr_policy | 40 | 103 | 1 | 86 | 0 | 0 | 16 | 0 | Human-Rights-Transparency-Report-2025.pdf |
| `DOC-070` | hr_policy | 41 | 92 | 9 | 67 | 0 | 2 | 14 | 0 | Privacy in Microsoft Cloud Services.pdf |
| `DOC-071` | hr_policy | 2 | 13 | 0 | 11 | 0 | 2 | 0 | 0 | SupplierComm Refresh July 2024 WebVersion.pdf |
| `DOC-072` | invoice | 7 | 14 | 0 | 14 | 0 | 0 | 0 | 0 | Download Azure billing invoice - Microsoft Co... |
| `DOC-073` | invoice | 9 | 12 | 0 | 10 | 0 | 0 | 2 | 0 | Microsoft volume licensing invoices _ Microso... |
| `DOC-074` | invoice | 4 | 26 | 0 | 17 | 0 | 0 | 9 | 0 | Understand IRS tax forms issued by Microsoft ... |
| `DOC-075` | invoice | 8 | 4 | 1 | 3 | 0 | 0 | 0 | 0 | Understand your invoice for your Microsoft MO... |
| `DOC-076` | invoice | 3 | 4 | 0 | 4 | 0 | 0 | 0 | 0 | View or download your invoice in the Microsof... |
| `DOC-077` | invoice | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | View your Microsoft Store order history _ Mic... |
| `DOC-078` | refund_policy | 2 | 13 | 0 | 2 | 0 | 0 | 11 | 0 | Can't get a refund on apps and games from Mic... |
| `DOC-079` | refund_policy | 4 | 5 | 0 | 2 | 0 | 1 | 2 | 0 | Cancel a Microsoft 365 subscription _ Microso... |
| `DOC-080` | refund_policy | 2 | 5 | 1 | 1 | 0 | 0 | 3 | 0 | Check the status of your Microsoft Store retu... |
| `DOC-081` | refund_policy | 2 | 13 | 0 | 4 | 0 | 0 | 9 | 0 | Get a refund for apps and games purchased fro... |
| `DOC-082` | refund_policy | 4 | 20 | 1 | 8 | 0 | 0 | 11 | 0 | Get an exchange or refund on devices bought f... |
| `DOC-083` | refund_policy | 5 | 11 | 0 | 7 | 0 | 0 | 4 | 0 | How to get a refund on a Microsoft subscripti... |
| `DOC-084` | refund_policy | 4 | 24 | 3 | 18 | 0 | 0 | 3 | 0 | Microsoft subscription refund policy _ Micros... |
| `DOC-085` | technical_documentation | 5 | 7 | 0 | 5 | 0 | 1 | 1 | 0 | Microsoft Entra deployment plans - Microsoft ... |
| `DOC-086` | technical_documentation | 2 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | Microsoft Entra operations reference guide - ... |
| `DOC-087` | technical_documentation | 8 | 8 | 1 | 4 | 0 | 2 | 1 | 0 | Microsoft Entra security operations guide - M... |
| `DOC-088` | technical_documentation | 7 | 10 | 1 | 9 | 0 | 0 | 0 | 0 | Protect APIs by using Azure Application Gatew... |
| `DOC-089` | technical_documentation | 4 | 2 | 0 | 2 | 0 | 0 | 0 | 0 | Security Copilot in Microsoft Entra _ Microso... |
| `DOC-090` | technical_documentation | 5 | 7 | 1 | 5 | 0 | 1 | 0 | 0 | What is Microsoft Entra_ - Microsoft Entra _ ... |

---

## 6. Verification and Audit Sign-Off

- **Clean Database State**: Verified all pre-existing platform data was cleanly wiped prior to ingestion.
- **Zero Document-Specific Hardcoding**: All 40 documents were processed through identical, document-agnostic gate pipelines.
- **Physical Evidence Grounding**: Every certified claim has verified `char_start`, `char_end`, and `source_hash`.
- **Relational Integrity**: `documents`, `document_versions`, `claims`, `claim_evidence`, `claim_trust_scores`, and `human_reviews` populated with referential integrity.

*Report automatically generated by Context Trust Layer Universal Certification Pipeline.*