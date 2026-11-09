"""
Generates verifiable machine-generated evidence for Slice 1 and Slice 2.
"""

import asyncio
import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions

PDF_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    "../storage/uploads/18197bd3-3c9b-43cc-be12-0804174b1be6/Northwind_Refund_Policy_Handbook.pdf"
))

OUT_JSON = os.path.abspath(os.path.join(os.path.dirname(__file__), "machine_generated_verification_evidence.json"))

async def generate():
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

    records = {}
    for idx, (cand, ev) in enumerate(zip(res.candidates, res.evaluations)):
        order_idx = idx + 1
        rec = {
            "order_index": order_idx,
            "candidate_id": cand.candidate_id,
            "subject": cand.subject,
            "predicate": cand.predicate,
            "object": cand.object,
            "conditions": cand.conditions,
            "claim_type": cand.claim_type,
            "content_role": getattr(cand.content_role, "value", str(cand.content_role)),
            "status": cand.status,
            "is_canonical": cand.is_canonical,
            "claim_text": cand.claim_text,
            "verbatim_source_quote": cand.evidence_text_span,
            "lifecycle_decision": ev.lifecycle_decision.value,
            "decision_code": ev.decision_code.value,
            "decision_reason": ev.decision_reason,
            "composite_trust_score": ev.composite_trust_score,
            "gates": {
                "source_match": ev.source_match.passed,
                "meaning": ev.meaning.passed,
                "completeness": ev.completeness.passed,
                "scope": ev.scope_eval.passed,
            }
        }
        records[order_idx] = rec

    target_keys = [1, 8, 26, 92, 93, 105, 120, 130, 181, 225]
    extracted_evidence = {k: records.get(k) for k in target_keys if k in records}

    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(extracted_evidence, f, indent=2)

    print(json.dumps(extracted_evidence, indent=2))

if __name__ == "__main__":
    asyncio.run(generate())

