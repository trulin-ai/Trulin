import asyncio
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.extraction.unified_pipeline import UnifiedExtractionPipeline, UnifiedPipelineOptions

PDF_PATH = os.path.abspath(os.path.join(
    os.path.dirname(__file__),
    "../storage/uploads/18197bd3-3c9b-43cc-be12-0804174b1be6/Northwind_Refund_Policy_Handbook.pdf"
))

async def test():
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

    print(f"Total candidates: {len(res.candidates)}, evaluations: {len(res.evaluations)}")
    
    indices = [1, 8, 26, 73, 74, 92, 93, 105, 120, 130, 137, 181, 225]
    for idx in indices:
        if idx <= len(res.candidates):
            c = res.candidates[idx - 1]
            e = res.evaluations[idx - 1]
            print(f"=== Candidate #{idx} ===")
            print(f"  S: {c.subject} | P: {c.predicate} | O: {c.object}")
            print(f"  Conds: {c.conditions}")
            print(f"  ClaimType: {c.claim_type}")
            print(f"  Decision: {e.lifecycle_decision.value} | Code: {e.decision_code.value}")
            print(f"  Decision Reason: {e.decision_reason}")
            print(f"  SourceMatch: passed={e.source_match.passed}, score={e.source_match.score}, reason={e.source_match.reason}")
            print(f"  Meaning: passed={e.meaning.passed}, score={e.meaning.score}, reason={e.meaning.reason}")
            print(f"  Completeness: passed={e.completeness.passed}, score={e.completeness.score}, reason={e.completeness.reason}")
            print(f"  Scope: passed={e.scope_eval.passed}, score={e.scope_eval.score}, reason={e.scope_eval.reason}")
            print()

asyncio.run(test())

