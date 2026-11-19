import sys, os
sys.path.insert(0, os.path.abspath('backend'))
import asyncio
import json
from app.db.database import AsyncSessionLocal
from app.db.models.claim import Claim
from app.db.models.claim_evidence import ClaimEvidence
from app.db.models.claim_validity import ClaimValidity
from sqlalchemy import select

async def dump_claims():
    async with AsyncSessionLocal() as session:
        c_res = await session.execute(select(Claim).order_by(Claim.created_at.asc()))
        claims = c_res.scalars().all()
        
        e_res = await session.execute(select(ClaimEvidence))
        evidence_list = e_res.scalars().all()
        ev_by_claim = {}
        for ev in evidence_list:
            ev_by_claim.setdefault(ev.claim_id, []).append(ev)

        v_res = await session.execute(select(ClaimValidity))
        validity_list = v_res.scalars().all()
        val_by_claim = {v.claim_id: v for v in validity_list}

        records = []
        for idx, c in enumerate(claims):
            evs = ev_by_claim.get(c.id, [])
            val = val_by_claim.get(c.id)
            ev_quotes = [e.text_span for e in evs]
            ev_locs = [{"page": e.page_number, "section": e.section, "start": e.start_offset, "end": e.end_offset} for e in evs]
            records.append({
                "number": idx + 1,
                "id": str(c.id),
                "subject": c.subject,
                "predicate": c.predicate,
                "object": c.object,
                "claim_text": c.claim_text,
                "claim_type": c.claim_type,
                "status": c.status.value if hasattr(c.status, "value") else str(c.status),
                "extraction_method": c.extraction_method,
                "extraction_model": c.extraction_model,
                "created_at": c.created_at.isoformat() if c.created_at else None,
                "evidence_quotes": ev_quotes,
                "locators": ev_locs,
                "validity_status": val.validity_status.value if val and hasattr(val.validity_status, "value") else (str(val.validity_status) if val else None)
            })

        with open("backend/scripts/baseline/db_224_claims_frozen.json", "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2)

        print(f"Dumped {len(records)} DB claims to backend/scripts/baseline/db_224_claims_frozen.json")

asyncio.run(dump_claims())
