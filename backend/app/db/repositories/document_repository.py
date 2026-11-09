import uuid
from collections.abc import Sequence

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.enums import RecordStatus
from app.db.repositories.base import BaseRepository


class DocumentRepository(BaseRepository[Document]):
    def __init__(self, session: AsyncSession):
        super().__init__(Document, session)

    async def get_by_id_with_versions(
        self,
        document_id: uuid.UUID,
    ) -> Document | None:
        stmt = (
            select(Document)
            .where(Document.id == document_id)
            .options(selectinload(Document.versions))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_external_id(
        self,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        external_id: str,
    ) -> Document | None:
        stmt = select(Document).where(
            Document.organization_id == organization_id,
            Document.source_id == source_id,
            Document.external_id == external_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_organization(
        self,
        organization_id: uuid.UUID,
        source_id: uuid.UUID | None = None,
        limit: int = 50,
        offset: int = 0,
        include_archived: bool = False,
    ) -> Sequence[Document]:
        stmt = select(Document).where(Document.organization_id == organization_id)
        if not include_archived:
            stmt = stmt.where(
                Document.status.notin_([RecordStatus.INACTIVE, RecordStatus.DELETED])
            )
        if source_id and isinstance(source_id, uuid.UUID):
            stmt = stmt.where(Document.source_id == source_id)
        stmt = (
            stmt.offset(offset)
            .limit(limit)
            .options(selectinload(Document.versions))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_or_create_version_with_dedup(
        self,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        title: str,
        content_uri: str | None,
        content_hash: str | None,
        document_type: str | None = "policy",
        external_id: str | None = None,
        owner_id: uuid.UUID | None = None,
        folder_id: uuid.UUID | None = None,
    ) -> tuple[Document, DocumentVersion, bool]:
        """
        Idempotent document ingestion with SHA-256 deduplication.
        Returns:
            (document, version, is_changed: bool)
            - is_changed is True if this is a newly created document or a modified version.
            - is_changed is False if the document already exists with identical content_hash.
        """
        document = None
        # 1. Exact match by (organization_id, source_id, external_id)
        if external_id:
            document = await self.get_by_external_id(
                organization_id=organization_id,
                source_id=source_id,
                external_id=external_id,
            )

        # 2. Match by (organization_id, external_id) across sources
        if not document and external_id:
            stmt = (
                select(Document)
                .where(
                    Document.organization_id == organization_id,
                    Document.external_id == external_id,
                )
                .order_by(Document.created_at.asc())
                .limit(1)
            )
            res = await self.session.execute(stmt)
            document = res.scalar_one_or_none()

        # 3. Match within target folder by normalized title or content_hash
        if not document and folder_id:
            if title:
                stmt = (
                    select(Document)
                    .where(
                        Document.organization_id == organization_id,
                        Document.folder_id == folder_id,
                        func.lower(func.trim(Document.title)) == title.strip().lower(),
                    )
                    .order_by(Document.created_at.asc())
                    .limit(1)
                )
                res = await self.session.execute(stmt)
                document = res.scalar_one_or_none()

            if not document and content_hash:
                stmt = (
                    select(Document)
                    .where(
                        Document.organization_id == organization_id,
                        Document.folder_id == folder_id,
                        Document.content_hash == content_hash,
                    )
                    .order_by(Document.created_at.asc())
                    .limit(1)
                )
                res = await self.session.execute(stmt)
                document = res.scalar_one_or_none()

        # 4. Organization-wide match by title and content_hash
        if not document and title and content_hash:
            stmt = (
                select(Document)
                .where(
                    Document.organization_id == organization_id,
                    func.lower(func.trim(Document.title)) == title.strip().lower(),
                    Document.content_hash == content_hash,
                )
                .order_by(Document.created_at.asc())
                .limit(1)
            )
            res = await self.session.execute(stmt)
            document = res.scalar_one_or_none()

        # 5. Organization-wide match by content_hash alone
        if not document and content_hash:
            stmt = (
                select(Document)
                .where(
                    Document.organization_id == organization_id,
                    Document.content_hash == content_hash,
                )
                .order_by(Document.created_at.asc())
                .limit(1)
            )
            res = await self.session.execute(stmt)
            document = res.scalar_one_or_none()

        if not document:
            # Brand new document
            document = Document(
                organization_id=organization_id,
                source_id=source_id,
                folder_id=folder_id,
                owner_id=owner_id,
                title=title,
                document_type=document_type,
                external_id=external_id,
                content_uri=content_uri,
                content_hash=content_hash,
            )
            self.session.add(document)
            await self.session.flush()
            await self.session.refresh(document)

            version = DocumentVersion(
                document_id=document.id,
                version_number=1,
                content_uri=content_uri,
                content_hash=content_hash,
                is_current=True,
            )
            self.session.add(version)
            await self.session.flush()
            await self.session.refresh(version)
            return document, version, True

        # Existing document: Update owner_id if not present or passed
        if owner_id and not document.owner_id:
            document.owner_id = owner_id
            await self.session.flush()

        # Existing document: Assign or update folder_id if passed
        if folder_id and document.folder_id != folder_id:
            document.folder_id = folder_id
            await self.session.flush()

        # Existing document: Clean up title if previously contaminated by path
        if title and document.title != title:
            if "/" in document.title or "\\" in document.title:
                document.title = title
                await self.session.flush()

        # Existing document: Check current active version
        current_version = await self.get_current_version(document.id)
        if current_version and current_version.content_hash and content_hash:
            if current_version.content_hash.strip().lower() == content_hash.strip().lower():
                # Document is identical -> Deduplication match (UNCHANGED)
                return document, current_version, False

        # Content is new or modified -> Create new incremented version
        stmt = (
            select(DocumentVersion.version_number)
            .where(DocumentVersion.document_id == document.id)
            .order_by(DocumentVersion.version_number.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        latest_version = res.scalar_one_or_none() or 0
        next_version_num = latest_version + 1

        # Update document header
        document.title = title
        document.content_uri = content_uri
        document.content_hash = content_hash
        await self.session.flush()

        # Deactivate existing current versions
        await self.session.execute(
            update(DocumentVersion)
            .where(DocumentVersion.document_id == document.id)
            .values(is_current=False)
        )
        await self.session.flush()

        # Create new current version
        new_version = DocumentVersion(
            document_id=document.id,
            version_number=next_version_num,
            content_uri=content_uri,
            content_hash=content_hash,
            is_current=True,
        )
        self.session.add(new_version)
        await self.session.flush()
        await self.session.refresh(new_version)

        # Supersede claims from prior versions of this document
        from app.db.repositories.claim_repository import ClaimRepository
        claim_repo = ClaimRepository(self.session)
        await claim_repo.supersede_claims_for_document(document.id, new_version.id)

        return document, new_version, True

    async def create_document_with_version(
        self,
        organization_id: uuid.UUID,
        source_id: uuid.UUID,
        title: str,
        content_uri: str | None,
        content_hash: str | None,
        document_type: str | None = "policy",
        external_id: str | None = None,
    ) -> tuple[Document, DocumentVersion]:
        doc, ver, _ = await self.get_or_create_version_with_dedup(
            organization_id=organization_id,
            source_id=source_id,
            title=title,
            content_uri=content_uri,
            content_hash=content_hash,
            document_type=document_type,
            external_id=external_id,
        )
        return doc, ver

    async def get_current_version(
        self,
        document_id: uuid.UUID,
    ) -> DocumentVersion | None:
        stmt = select(DocumentVersion).where(
            DocumentVersion.document_id == document_id,
            DocumentVersion.is_current.is_(True),
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_folder_ids(
        self,
        organization_id: uuid.UUID,
        folder_ids: list[uuid.UUID],
        status_filter: str | None = None,
        include_archived: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> Sequence[Document]:
        stmt = select(Document).where(
            Document.organization_id == organization_id,
            Document.folder_id.in_(folder_ids),
        )
        if status_filter:
            stmt = stmt.where(Document.status == status_filter)
        elif not include_archived:
            stmt = stmt.where(
                Document.status.notin_([RecordStatus.INACTIVE, RecordStatus.DELETED])
            )
        stmt = (
            stmt.order_by(Document.updated_at.desc())
            .offset(offset)
            .limit(limit)
            .options(selectinload(Document.versions))
        )
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def count_by_folder_ids(
        self,
        organization_id: uuid.UUID,
        folder_ids: list[uuid.UUID],
        status_filter: str | None = None,
        include_archived: bool = False,
    ) -> int:
        from sqlalchemy import func
        stmt = select(func.count(Document.id)).where(
            Document.organization_id == organization_id,
            Document.folder_id.in_(folder_ids),
        )
        if status_filter:
            stmt = stmt.where(Document.status == status_filter)
        elif not include_archived:
            stmt = stmt.where(
                Document.status.notin_([RecordStatus.INACTIVE, RecordStatus.DELETED])
            )
        result = await self.session.execute(stmt)
        return result.scalar() or 0
