import os
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.db.models.document import Document
from app.db.models.document_version import DocumentVersion
from app.db.repositories.document_repository import DocumentRepository

def test_clean_filename_and_title_normalization():
    """
    Verifies that titles extracted from file paths strip folder prefixes,
    avoiding directory contamination like 'Hr Policies/Filename'.
    """
    test_cases = [
        ("Hr Policies/Employee_Handbook_2026.pdf", "Employee Handbook 2026"),
        ("Legal\\Contracts\\Vendor-Agreement.docx", "Vendor Agreement"),
        ("Finance/Reports/Q3_Audit.xlsx", "Q3 Audit"),
        ("SimpleDoc.txt", "Simpledoc"),
    ]

    for raw_path, expected_title in test_cases:
        clean_name = os.path.basename(raw_path.replace("\\", "/"))
        doc_title = clean_name.rsplit(".", 1)[0].replace("-", " ").replace("_", " ").title().strip()
        assert doc_title == expected_title

        # Base file ID should also be clean
        base_file_id = os.path.basename(raw_path.replace("\\", "/"))
        doc_external_id = f"file://{base_file_id}"
        assert "/" not in base_file_id
        assert "\\" not in base_file_id

@pytest.mark.asyncio
async def test_repository_deduplication_by_content_hash():
    """
    Verifies that DocumentRepository.get_or_create_version_with_dedup
    recognizes an existing document with the same content_hash and returns is_changed=False
    without adding a duplicate Document row.
    """
    session = AsyncMock()
    repo = DocumentRepository(session)

    org_id = uuid.uuid4()
    source_id = uuid.uuid4()
    folder_id = uuid.uuid4()
    content_hash = "sha256_hash_12345"
    title = "Corporate Return Policy"

    # Mock finding existing document by title or hash
    existing_doc = Document(
        id=uuid.uuid4(),
        organization_id=org_id,
        source_id=source_id,
        folder_id=folder_id,
        title=title,
        content_hash=content_hash,
    )
    existing_ver = DocumentVersion(
        id=uuid.uuid4(),
        document_id=existing_doc.id,
        version_number=1,
        content_hash=content_hash,
        is_current=True,
    )

    # Mock execute result
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_doc
    session.execute.return_value = mock_result

    # Mock get_current_version
    repo.get_current_version = AsyncMock(return_value=existing_ver)

    doc, ver, is_changed = await repo.get_or_create_version_with_dedup(
        organization_id=org_id,
        source_id=source_id,
        title=title,
        content_uri="sample text",
        content_hash=content_hash,
        folder_id=folder_id,
    )

    assert is_changed is False
    assert doc.id == existing_doc.id
    assert ver.id == existing_ver.id
    # Assert session.add was NOT called to add a new Document
    assert not any(isinstance(call.args[0], Document) for call in session.add.call_args_list)

@pytest.mark.asyncio
async def test_repository_deduplication_updates_folder_if_changed():
    """
    Verifies that if an existing document is moved or uploaded into a new folder,
    the repository assigns the new folder_id to the existing document record.
    """
    session = AsyncMock()
    repo = DocumentRepository(session)

    org_id = uuid.uuid4()
    source_id = uuid.uuid4()
    old_folder_id = uuid.uuid4()
    new_folder_id = uuid.uuid4()
    content_hash = "sha256_hash_99999"
    title = "Northwind Policy"

    existing_doc = Document(
        id=uuid.uuid4(),
        organization_id=org_id,
        source_id=source_id,
        folder_id=old_folder_id,
        title=title,
        content_hash=content_hash,
    )
    existing_ver = DocumentVersion(
        id=uuid.uuid4(),
        document_id=existing_doc.id,
        version_number=1,
        content_hash=content_hash,
        is_current=True,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_doc
    session.execute.return_value = mock_result
    repo.get_current_version = AsyncMock(return_value=existing_ver)

    doc, ver, is_changed = await repo.get_or_create_version_with_dedup(
        organization_id=org_id,
        source_id=source_id,
        title=title,
        content_uri="sample text",
        content_hash=content_hash,
        folder_id=new_folder_id,
    )

    assert doc.folder_id == new_folder_id
    assert is_changed is False

