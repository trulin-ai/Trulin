import asyncio
import sys
import os
import uuid
import json

sys.path.insert(0, os.path.abspath("backend"))
from app.db.database import AsyncSessionLocal
from sqlalchemy import text

NORTHWIND_DOC_ID = uuid.UUID("e3cdd194-1a9b-4f01-9031-13e6b027d3d2")

async def main():
    async with AsyncSessionLocal() as session:
        await session.execute(text("SET TRANSACTION READ ONLY;"))
        with open("backend/scripts/baseline/claim_id_deterministic_mapping.json") as f:
            mapping = json.load(f)["mappings"]
        with open("backend/scripts/baseline/phase2_5_repaired_extraction_v1.json") as f:
            extraction = json.load(f)
        
        map_by_audit = {m["audit_id"]: m["stable_claim_id"] for m in mapping}
        claims_with_uuid = []
        for c in extraction:
            aid = c.get("claim_id")
            uuid_val = map_by_audit.get(aid)
            claims_with_uuid.append((aid, uuid_val, c.get("predicate"), c.get("status")))
        
        print(f"Total extracted claims: {len(claims_with_uuid)}")
        print(f"First 3: {claims_with_uuid[:3]}")

if __name__ == "__main__":
    asyncio.run(main())
