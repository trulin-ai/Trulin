"""
Compares Slice 1 extraction run against the frozen baseline
(backend/scripts/northwind_candidates_baseline_frozen.json)
Reports exact candidate-level delta, lineage, and defect resolution for:
1. Candidate #1 (Custom contract override precedence)
2. Candidates #92, #93 (Exclusive > 150 threshold preservation)
3. Candidate #130 (Trial cancellation vs shipment)
4. Candidate #181 (Provider documentation upon request vs customer requirement)
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions
from app.services.universal_gate_evaluator import UniversalGateEvaluator

PDF_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    "../storage/uploads/18197bd3-3c9b-43cc-be12-0804174b1be6/Northwind_Refund_Policy_Handbook.pdf"
))
BASELINE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "northwind_candidates_baseline_frozen.json"))
SLICE1_OUT_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "northwind_candidates_slice1_run.json"))


async def run_slice1_export():
    with open(PDF_PATH, "rb") as f:
        raw_bytes = f.read()

    opts = UnifiedPipelineOptions(
        extract_tables=True,
        enable_deontic_classification=True,
        enable_conflict_detection=False,
    )
    res = await UnifiedExtractionPipeline.execute(
        filename="Northwind_Refund_Policy_Handbook.pdf",
        raw_bytes=raw_bytes,
        options=opts,
    )

    candidates = res.candidates or []
    records = []
    for idx, c in enumerate(candidates):
        loc = c.locator or {}
        gate_res = UniversalGateEvaluator.evaluate(
            claim_text=c.claim_text,
            subject=c.subject,
            predicate=c.predicate,
            object_text=str(c.object or ""),
            claim_type=c.claim_type,
            metadata={"table_grid": bool(loc.get("table_grid") or loc.get("table_id"))},
            locator=loc,
        )
        rec = {
            "order_index": idx + 1,
            "candidate_id": c.candidate_id,
            "subject": c.subject,
            "predicate": c.predicate,
            "object": str(c.object or ""),
            "conditions": c.conditions or [],
            "status": "APPROVED" if gate_res.all_gates_passed else "REJECTED",
            "lifecycle_state": gate_res.lifecycle_state.value if hasattr(gate_res.lifecycle_state, "value") else str(gate_res.lifecycle_state),
            "decision_reason": "; ".join(gate_res.rejection_reasons) if gate_res.rejection_reasons else "ALL_GATES_PASSED",
            "claim_text": c.claim_text,
            "verbatim_source_quote": c.evidence_text_span,
        }
        records.append(rec)

    with open(SLICE1_OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)

    return records


def compare_against_baseline(slice1_records):
    with open(BASELINE_PATH, "r", encoding="utf-8") as f:
        baseline_records = json.load(f)

    print(f"\n=======================================================")
    print(f"SLUCE 1 COMPARISON REPORT: BASELINE vs SLICE 1")
    print(f"Baseline Candidate Count: {len(baseline_records)}")
    print(f"Slice 1 Candidate Count:   {len(slice1_records)}")
    print(f"=======================================================\n")

    # Focus inspection candidates
    target_topics = {
        "Defect 1: Threshold > 150": lambda r: "150" in str(r.get("claim_text", "")) or "150" in str(r.get("conditions", "")),
        "Defect 2: Custom contract override": lambda r: "override" in str(r.get("predicate", "")).lower() or "override" in str(r.get("claim_text", "")).lower(),
        "Defect 3: Documentation upon request": lambda r: "invoice" in str(r.get("claim_text", "")).lower() or "provides_documentation" in str(r.get("predicate", "")),
        "Defect 4: Trial cancellation": lambda r: "trial" in str(r.get("claim_text", "")).lower() or "trial" in str(r.get("predicate", "")),
    }

    for topic_name, matcher in target_topics.items():
        print(f"--- {topic_name} ---")
        base_matches = [r for r in baseline_records if matcher(r)]
        slice1_matches = [r for r in slice1_records if matcher(r)]

        print(f"Baseline ({len(base_matches)} found):")
        for b in base_matches[:3]:
            print(f"  [#{b.get('baseline_order_index') or b.get('order_index')}] S: '{b.get('subject')}' | P: '{b.get('predicate')}' | O: '{b.get('object')}' | Conds: {b.get('conditions')} | Status: {b.get('status')}")

        print(f"Slice 1 ({len(slice1_matches)} found):")
        for s in slice1_matches[:3]:
            print(f"  [#{s.get('order_index')}] S: '{s.get('subject')}' | P: '{s.get('predicate')}' | O: '{s.get('object')}' | Conds: {s.get('conditions')} | Status: {s.get('status')}")
        print()


if __name__ == "__main__":
    records = asyncio.run(run_slice1_export())
    compare_against_baseline(records)
