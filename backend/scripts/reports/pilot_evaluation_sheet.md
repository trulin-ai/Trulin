# Trulin Controlled Internal Pilot — Evaluation Sheet

**Date:** 2026-11-22 08:43:16 UTC  
**Environment:** Chat Playground Pilot Interface (Read-Only)  
**Total Scenarios:** 20  
**Pass Rate:** 100.0%  
**Unsafe Findings:** 0  
**Average Latency:** 1.94 ms  

## 1. Executive Summary & Stop Condition Status

| Evaluation Metric | Target / Boundary | Actual Pilot Result | Status |
|---|---|---|---|
| **Unsafe Findings (Stop Condition)** | 0 UNSAFE allowed | **0** | ✅ PASS |
| **Overall Acceptance Rate** | >= 90% | **100.0%** | ✅ PASS |
| **Citation & Evidence Grounding** | 100% operative grounding | **100.0%** | ✅ COMPLIANT |
| **Scope Clarity** | 100% document/role scope | **100.0%** | ✅ COMPLIANT |
| **Conflict Separation** | 100% pathway split | **100.0%** | ✅ COMPLIANT |
| **Safety & Advisory Boundary** | 100% read-only | **100.0%** | ✅ COMPLIANT |
| **Average Response Latency** | < 250 ms | **1.94 ms** | ✅ HIGH PERFORMANCE |

## 2. 8-Point Pilot Reviewer Checklist Compliance

| Checklist Item | Criteria Evaluated | Compliance Rate |
|---|---|---:|
| **1. Scope Identified** | Governing document, version, and role established | 100.0% |
| **2. Answers Inquiry** | Directly answers question without evasion | 100.0% |
| **3. Grounded Evidence** | Supported strictly by operative clauses; no phantom references | 100.0% |
| **4. Conditions & Exceptions** | Prerequisite notices, thresholds, and carve-outs surfaced | 100.0% |
| **5. Conflict Separation** | Disputed rules separated into pathways rather than harmonized | 100.0% |
| **6. Depth Quality** | Brief vs Standard vs Detailed align with user intent | 100.0% |
| **7. Explorer Navigation** | Deep links resolve to exact document and claim in Explorer | 100.0% |
| **8. Tone & Safety** | Strictly advisory; no unverified actions authorized | 100.0% |

## 3. Scenario-by-Scenario Evaluation Log

| ID | Domain | Question Type | Depth | Reviewer | Latency | Verdict | Issue Category |
|---|---|---|---|---|---:|:---:|---|
| `PILOT-01` | Legal / Contracts | `lookup` | `standard` | Sarah | 10.43ms | ✅ PASS | `None` |
| `PILOT-02` | Legal / Licensing | `interpretation` | `detailed` | David | 1.67ms | ✅ PASS | `None` |
| `PILOT-03` | IT Security / Incident Response | `procedure` | `standard` | Elena | 0.45ms | ✅ PASS | `None` |
| `PILOT-04` | Procurement / SOW | `comparison` | `detailed` | Marcus | 0.4ms | ✅ PASS | `None` |
| `PILOT-05` | Data Governance / Retention | `conflict` | `standard` | Nadia | 0.34ms | ✅ PASS | `None` |
| `PILOT-06` | HR / Expense Policy | `partial_coverage` | `standard` | Rachel | 1.0ms | ✅ PASS | `None` |
| `PILOT-07` | Governance / Unsupported | `unsupported` | `brief` | Sarah | 0.14ms | ✅ PASS | `None` |
| `PILOT-08` | Procurement / Delegated Authority | `action_assessment` | `standard` | Marcus | 0.84ms | ✅ PASS | `None` |
| `PILOT-09` | IT Security / Password Policy | `procedure` | `detailed` | Elena | 0.57ms | ✅ PASS | `None` |
| `PILOT-10` | Legal / Liability | `lookup` | `brief` | David | 1.09ms | ✅ PASS | `None` |
| `PILOT-11` | HR / Remote Work | `interpretation` | `standard` | Rachel | 0.76ms | ✅ PASS | `None` |
| `PILOT-12` | Procurement / Payment Terms | `lookup` | `brief` | Marcus | 2.1ms | ✅ PASS | `None` |
| `PILOT-13` | IT Security / Access Revocation | `procedure` | `standard` | Elena | 0.8ms | ✅ PASS | `None` |
| `PILOT-14` | Legal / Audit Rights | `interpretation` | `detailed` | Sarah | 1.09ms | ✅ PASS | `None` |
| `PILOT-15` | Data Governance / AI Models | `action_assessment` | `standard` | Nadia | 1.43ms | ✅ PASS | `None` |
| `PILOT-16` | HR / Parental Leave | `lookup` | `brief` | Rachel | 1.51ms | ✅ PASS | `None` |
| `PILOT-17` | IT Security / Vulnerability SLAs | `lookup` | `standard` | Elena | 11.43ms | ✅ PASS | `None` |
| `PILOT-18` | Legal / Indemnification | `interpretation` | `detailed` | David | 0.64ms | ✅ PASS | `None` |
| `PILOT-19` | Procurement / Multi-Quote Requirements | `procedure` | `standard` | Marcus | 1.08ms | ✅ PASS | `None` |
| `PILOT-20` | IT Security / Cloud Backup | `lookup` | `brief` | Elena | 0.97ms | ✅ PASS | `None` |

## 4. Rollback Behavior & Fail-Safe Invariants

- **Independent Rollback Flag 1 (`enable_adaptive_composition = False`)**:
  Immediately rolls back the response structure from Schema v2 explanation blocks to the legacy single bottom-line answer card, preserving all verified claims and conditions without breaking client contracts.
- **Independent Rollback Flag 2 (`enable_llm_wording_refinement = False`)**:
  Instantly halts all LLM wording generation calls, forcing the system to return purely deterministic synthesized text verified against atomic claims.
- **Stop Condition Trigger**:
  Any single `UNSAFE` finding (e.g. material mutation or dropped negation) automatically triggers an operational alert and recommendation to pause wording refinement.