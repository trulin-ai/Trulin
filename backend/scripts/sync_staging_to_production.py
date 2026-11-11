import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import asyncio
from app.db.database import AsyncSessionLocal
from sqlalchemy import text

DOC_ID = 'e3cdd194-1a9b-4f01-9031-13e6b027d3d2'
VER_ID = 'bcf72c99-7909-4898-af98-56f261b7d24b'

async def sync():
    async with AsyncSessionLocal() as session:
        print("1. Syncing documents...")
        await session.execute(text("""
            INSERT INTO public.documents (id, organization_id, source_id, title, document_type, external_id, content_uri, content_hash, status, domain, owner_id, created_at, updated_at, folder_id)
            SELECT id, organization_id, source_id, title, document_type, external_id, content_uri, content_hash, status, domain, owner_id, created_at, updated_at, folder_id
            FROM staging.documents
            ON CONFLICT (id) DO NOTHING;
        """))

        print("2. Syncing document_versions...")
        await session.execute(text("""
            INSERT INTO public.document_versions (id, document_id, version_number, content_uri, content_hash, modified_at, is_current, created_at, updated_at)
            SELECT id, document_id, version_number, content_uri, content_hash, modified_at, is_current, created_at, updated_at
            FROM staging.document_versions
            ON CONFLICT (id) DO NOTHING;
        """))

        print("3. Syncing claims...")
        await session.execute(text("""
            INSERT INTO public.claims (id, organization_id, document_version_id, claim_text, subject, predicate, object, claim_type, extraction_method, extraction_model, status, created_at, updated_at)
            SELECT id, organization_id, document_version_id, claim_text, subject, predicate, object, claim_type, extraction_method, extraction_model, status, created_at, updated_at
            FROM staging.claims
            ON CONFLICT (id) DO UPDATE SET
                claim_text = EXCLUDED.claim_text,
                subject = EXCLUDED.subject,
                predicate = EXCLUDED.predicate,
                object = EXCLUDED.object,
                status = EXCLUDED.status,
                updated_at = EXCLUDED.updated_at;
        """))

        print("4. Syncing claim_evidence...")
        await session.execute(text("""
            INSERT INTO public.claim_evidence (id, claim_id, document_id, evidence_type, page_number, section, text_span, start_offset, end_offset, evidence_hash, created_at)
            SELECT id, claim_id, document_id, evidence_type, page_number, section, text_span, start_offset, end_offset, evidence_hash, created_at
            FROM staging.claim_evidence
            ON CONFLICT (id) DO NOTHING;
        """))

        print("5. Syncing claim_conflicts...")
        await session.execute(text("""
            INSERT INTO public.claim_conflicts (id, claim_a_id, claim_b_id, conflict_type, severity, confidence, resolution_status, resolved_claim_id, resolved_by, resolved_at, created_at)
            SELECT id, claim_a_id, claim_b_id, conflict_type, severity, confidence, resolution_status, resolved_claim_id, resolved_by, resolved_at, created_at
            FROM staging.claim_conflicts
            ON CONFLICT (id) DO UPDATE SET
                conflict_type = EXCLUDED.conflict_type,
                severity = EXCLUDED.severity,
                confidence = EXCLUDED.confidence,
                resolution_status = EXCLUDED.resolution_status;
        """))

        await session.commit()

        # Check verification
        pub_claims_cnt = (await session.execute(text(f"SELECT count(*) FROM public.claims WHERE document_version_id = '{VER_ID}'"))).scalar()
        print(f"Public claims for Northwind: {pub_claims_cnt}")
        pub_ev_cnt = (await session.execute(text(f"SELECT count(*) FROM public.claim_evidence WHERE document_id = '{DOC_ID}'"))).scalar()
        print(f"Public evidence for Northwind: {pub_ev_cnt}")
        pub_conf_cnt = (await session.execute(text("SELECT count(*) FROM public.claim_conflicts"))).scalar()
        print(f"Public conflicts: {pub_conf_cnt}")

if __name__ == "__main__":
    asyncio.run(sync())
