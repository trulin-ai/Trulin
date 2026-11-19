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
from app.ingestion.parsers.document_parser import DocumentParser
from app.extraction.pipeline import Layer5ExtractionPipeline
from app.validation_gate import Layer6ValidationGatePipeline
from app.ingestion.universal_file_parser import UniversalFileParser

SEARCH_PATHS = [
    REPO_ROOT / "backend/storage/uploads/18197bd3-3c9b-43cc-be12-0804174b1be6/Northwind_Refund_Policy_Handbook.pdf",
    REPO_ROOT / "docs/Northwind_Refund_Policy_Handbook.pdf",
]

for p in (REPO_ROOT / "backend/storage/uploads").glob("*/Northwind_Refund_Policy_Handbook.pdf"):
    SEARCH_PATHS.append(p)

async def run():
    target_path = None
    for p in SEARCH_PATHS:
        if p.exists():
            target_path = p
            break

    if not target_path:
        raise FileNotFoundError(f"Northwind PDF not found in search paths: {SEARCH_PATHS}")

    print(f"Loading Northwind PDF from: {target_path}")
    content = target_path.read_bytes()

    parsed_structured = UniversalFileParser.parse_structured(
        filename=target_path.name,
        raw_bytes=content,
    )
    envelope = EnvelopeFactory.create_from_file_upload(
        filename=target_path.name,
        raw_bytes=parsed_structured.full_text.encode("utf-8"),
        parsed_content=parsed_structured.full_text,
        organization_id=uuid.uuid4(),
        source_id=uuid.uuid4(),
    )

    parsed_res = await DocumentParser.parse(envelope)
    l5_res = await Layer5ExtractionPipeline().process_envelope(envelope, parsed_res)
    l6_res = await Layer6ValidationGatePipeline(persist_to_db=False).process_extraction_result(envelope, l5_res)

    print("\n" + "=" * 70)
    print("NORTHWIND REFUND POLICY HANDBOOK EXTRACTION & GOVERNANCE REPORT")
    print("=" * 70)
    print(f"Total evaluated candidates:    {len(l5_res.candidates)} (Expected: 191)")
    print(f"Certified / Approved:         {l6_res.claims_approved} (Expected: 160)")
    print(f"Queued for Review:            {l6_res.claims_queued_for_review} (Expected: 20)")
    print(f"Hard Rejected:                {l6_res.claims_rejected} (Expected: 11)")
    print(f"Certification Rate:           {l6_res.claims_approved / len(l5_res.candidates) * 100:.1f}% (Expected: ~83.8%)")
    print("-" * 70)

    assert len(l5_res.candidates) == 191, f"Expected 191 candidates, got {len(l5_res.candidates)}"
    assert l6_res.claims_approved == 160, f"Expected 160 approved, got {l6_res.claims_approved}"
    assert l6_res.claims_queued_for_review == 20, f"Expected 20 review, got {l6_res.claims_queued_for_review}"
    assert l6_res.claims_rejected == 11, f"Expected 11 rejected, got {l6_res.claims_rejected}"
    print("ALL NORTHWIND BASELINE ACCEPTANCE CRITERIA PASSED!")

if __name__ == "__main__":
    asyncio.run(run())

