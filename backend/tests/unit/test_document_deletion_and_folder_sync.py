import os
import tempfile
import uuid
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import AsyncSessionLocal
from app.db.models.data_source import DataSource
from app.db.models.document import Document, RecordStatus
from app.db.models.folder import Folder
from app.db.models.organization import Organization
from app.db.models.user import User
from app.db.repositories.document_repository import DocumentRepository
from app.services.folder_service import FolderService


@pytest.fixture
async def db():
    async with AsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def setup_org_and_folder(db: AsyncSession):
    org_id = uuid.uuid4()
    org = Organization(
        id=org_id,
        name=f"Org {str(org_id)[:8]}",
        slug=f"org-{str(org_id)[:8]}",
    )
    db.add(org)
    await db.flush()

    user = User(
        id=uuid.uuid4(),
        organization_id=org_id,
        email=f"user-{str(org_id)[:8]}@test.local",
        name="Tester",
        role="admin",
    )
    db.add(user)

    folder = Folder(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Legal Policies",
        depth=0,
        folder_type="custom",
    )
    db.add(folder)

    ds = DataSource(
        id=uuid.uuid4(),
        organization_id=org_id,
        name="Upload Source",
        source_type="file",
        external_id=f"src-{str(org_id)[:8]}",
        authority_level=80,
    )
    db.add(ds)
    await db.commit()
    return {"org_id": org_id, "folder_id": folder.id, "source_id": ds.id}


@pytest.mark.asyncio
async def test_soft_decommissioned_document_hidden_from_folder_and_tree(setup_org_and_folder, db: AsyncSession):
    org_id = setup_org_and_folder["org_id"]
    folder_id = setup_org_and_folder["folder_id"]
    source_id = setup_org_and_folder["source_id"]

    repo = DocumentRepository(db)
    service = FolderService(db)

    # 1. Create an active document in folder
    doc = Document(
        id=uuid.uuid4(),
        organization_id=org_id,
        source_id=source_id,
        folder_id=folder_id,
        title="test_policy.pdf",
        status=RecordStatus.ACTIVE,
        content_hash=uuid.uuid4().hex,
    )
    db.add(doc)
    await db.commit()

    # Verify active doc is listed
    docs = await repo.list_by_folder_ids(organization_id=org_id, folder_ids=[folder_id])
    assert len(docs) == 1
    assert docs[0].id == doc.id

    tree = await service.list_folders(org_id)
    target_folder = next(f for f in tree if f.id == folder_id)
    assert target_folder.direct_documents_count == 1

    # 2. Soft-decommission (archive) document
    doc.status = RecordStatus.INACTIVE
    await db.commit()

    # Verify document is omitted by default from folder listings
    docs_after = await repo.list_by_folder_ids(organization_id=org_id, folder_ids=[folder_id])
    assert len(docs_after) == 0

    # Verify document is omitted from organization listings
    org_docs = await repo.list_by_organization(org_id)
    assert len(org_docs) == 0

    # Verify folder tree counts update to 0
    tree_after = await service.list_folders(org_id)
    target_folder_after = next(f for f in tree_after if f.id == folder_id)
    assert target_folder_after.direct_documents_count == 0

    # Verify folder metrics update to 0
    metrics = await service.get_folder_metrics(org_id, folder_id)
    assert metrics.documents.total == 0


@pytest.mark.asyncio
async def test_permanent_deletion_removes_file_and_updates_folder(setup_org_and_folder, db: AsyncSession):
    org_id = setup_org_and_folder["org_id"]
    folder_id = setup_org_and_folder["folder_id"]
    source_id = setup_org_and_folder["source_id"]

    repo = DocumentRepository(db)
    service = FolderService(db)

    # Create temporary file to test disk cleanup
    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(b"content")
        temp_path = tf.name

    doc = Document(
        id=uuid.uuid4(),
        organization_id=org_id,
        source_id=source_id,
        folder_id=folder_id,
        title="to_delete.pdf",
        content_uri=temp_path,
        status=RecordStatus.ACTIVE,
        content_hash=uuid.uuid4().hex,
    )
    db.add(doc)
    await db.commit()

    assert os.path.exists(temp_path)

    # Delete permanently
    await db.delete(doc)
    await db.commit()
    if os.path.exists(temp_path):
        os.remove(temp_path)

    # Verify listings and counts are 0
    docs = await repo.list_by_folder_ids(organization_id=org_id, folder_ids=[folder_id])
    assert len(docs) == 0

    tree = await service.list_folders(org_id)
    target_folder = next(f for f in tree if f.id == folder_id)
    assert target_folder.direct_documents_count == 0
    assert not os.path.exists(temp_path)
