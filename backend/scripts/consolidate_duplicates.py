import asyncio
import uuid
from sqlalchemy import select, update, delete, func
from app.db.database import AsyncSessionLocal
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.models.claim import Claim
from app.db.models.claim_evidence import ClaimEvidence
from app.db.models.folder import Folder

async def consolidate():
    async with AsyncSessionLocal() as session:
        print("--- Checking and consolidating duplicate documents in database ---")

        # 1. Clean path-contaminated titles (e.g. 'Hr Policies/How Microsoft...')
        stmt = select(Document).where(Document.title.like("%/%") | Document.title.like("%\\%"))
        res = await session.execute(stmt)
        contaminated_docs = res.scalars().all()
        for doc in contaminated_docs:
            clean_title = doc.title.replace("\\", "/").rsplit("/", 1)[-1].strip()
            print(f"Cleaning contaminated title: '{doc.title}' -> '{clean_title}'")
            doc.title = clean_title
        if contaminated_docs:
            await session.commit()

        # 2. Find duplicate documents by (organization_id, lower(trim(title)))
        stmt = select(Document).order_by(Document.created_at.asc())
        res = await session.execute(stmt)
        all_docs = res.scalars().all()

        # Group by (organization_id, normalized_title)
        groups = {}
        for d in all_docs:
            norm_title = (d.title or "").strip().lower()
            key = (str(d.organization_id), norm_title)
            groups.setdefault(key, []).append(d)

        duplicates_found = 0
        merged_count = 0

        for (org_id, title_key), docs in groups.items():
            if len(docs) <= 1:
                continue

            duplicates_found += 1
            primary = docs[0]
            print(f"\nDuplicate group for '{primary.title}' (Org: {org_id}): {len(docs)} documents found.")
            print(f"  Primary ID: {primary.id} (folder: {primary.folder_id}, created: {primary.created_at})")

            for dup in docs[1:]:
                print(f"  Merging duplicate ID: {dup.id} (folder: {dup.folder_id}, created: {dup.created_at}) -> primary {primary.id}")

                # Re-link ClaimEvidence pointing to dup
                await session.execute(
                    update(ClaimEvidence).where(ClaimEvidence.document_id == dup.id).values(document_id=primary.id)
                )

                # Re-link or merge versions
                v_res = await session.execute(select(DocumentVersion).where(DocumentVersion.document_id == dup.id))
                dup_versions = v_res.scalars().all()
                for v in dup_versions:
                    # Check if primary already has a version with same hash
                    p_v_res = await session.execute(
                        select(DocumentVersion).where(
                            DocumentVersion.document_id == primary.id,
                            DocumentVersion.content_hash == v.content_hash
                        )
                    )
                    existing_pv = p_v_res.scalar_one_or_none()
                    if existing_pv:
                        print(f"    Re-linking claims from version {v.id} to existing primary version {existing_pv.id}")
                        await session.execute(
                            update(Claim).where(Claim.document_version_id == v.id).values(document_version_id=existing_pv.id)
                        )
                        print(f"    Deleting redundant version {v.id}.")
                        await session.execute(delete(DocumentVersion).where(DocumentVersion.id == v.id))
                    else:
                        print(f"    Re-linking unique version {v.id} to primary document.")
                        v.document_id = primary.id

                # Delete duplicate document record
                await session.execute(delete(Document).where(Document.id == dup.id))
                merged_count += 1

        await session.commit()
        print(f"\n--- Consolidation completed! Merged {merged_count} duplicate documents across {duplicates_found} groups. ---")

if __name__ == "__main__":
    asyncio.run(consolidate())
