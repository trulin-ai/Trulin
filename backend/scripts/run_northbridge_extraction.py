import asyncio
import os
import sys
import uuid
from pathlib import Path

# Add backend directory to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent if (Path(__file__).resolve().parent.name == "scripts" and Path(__file__).resolve().parent.parent.name == "backend") else Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.ingestion.envelope import EnvelopeFactory
from app.ingestion.parsers.docx_parser import DocxAdapter
from app.extraction.pipeline import Layer5ExtractionPipeline
from app.validation_gate import Layer6ValidationGatePipeline

SEARCH_PATHS = [
    REPO_ROOT / "backend/storage/uploads/803da6db-66a8-4103-9353-792f353cf67f/Northbridge_Benefits_Leave_Claims_Policy.docx",
]

for p in (REPO_ROOT / "backend/storage/uploads").glob("*/Northbridge_Benefits_Leave_Claims_Policy.docx"):
    SEARCH_PATHS.append(p)

async def run():
    target_path = None
    for p in SEARCH_PATHS:
        if p.exists():
            target_path = p
            break

    if not target_path:
        raise FileNotFoundError(f"Northbridge DOCX not found in search paths: {SEARCH_PATHS}")

    print(f"Loading Northbridge DOCX from: {target_path}")
    raw_bytes = target_path.read_bytes()

    envelope = EnvelopeFactory.create_from_file_upload(
        filename=target_path.name,
        raw_bytes=raw_bytes,
        parsed_content="",
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
    )

    parsed_res = await DocxAdapter().parse_to_evidence(envelope)
    l5_res = await Layer5ExtractionPipeline().process_envelope(envelope, parsed_res)
    l6_res = await Layer6ValidationGatePipeline(persist_to_db=False).process_extraction_result(envelope, l5_res)

    print("\n" + "=" * 70)
    print("NORTHBRIDGE 30-TABLE POLICY EXTRACTION & GOVERNANCE REPORT")
    print("=" * 70)
    print(f"Total evaluated candidates:    {l6_res.total_candidates_evaluated} (Expected: 406)")
    print(f"Certified / Approved:         {l6_res.claims_approved} (Expected: 333)")
    print(f"Queued for Review:            {l6_res.claims_queued_for_review} (Expected: 17)")
    print(f"Hard Rejected:                {l6_res.claims_rejected} (Expected: 56)")
    print("-" * 70)

    assert l6_res.total_candidates_evaluated == 406, f"Expected 406 candidates, got {l6_res.total_candidates_evaluated}"
    assert l6_res.claims_approved == 333, f"Expected 333 approved, got {l6_res.claims_approved}"
    assert l6_res.claims_queued_for_review == 17, f"Expected 17 review, got {l6_res.claims_queued_for_review}"
    assert l6_res.claims_rejected == 56, f"Expected 56 rejected, got {l6_res.claims_rejected}"
    print("ALL NORTHBRIDGE BASELINE ACCEPTANCE CRITERIA PASSED!")

if __name__ == "__main__":
    asyncio.run(run())

