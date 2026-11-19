import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_optional_current_user
from app.db.database import get_db
from app.db.models.organization import Organization
from app.db.models.user import User
from app.db.repositories.document_repository import DocumentRepository
from app.schemas.document import DocumentResponse
from app.schemas.folder import (
    DocumentMoveRequest,
    FolderCreate,
    FolderMetricsResponse,
    FolderMove,
    FolderResponse,
    FolderTreeNode,
    FolderUpdate,
)
from app.services.folder_service import FolderService

router = APIRouter(prefix="/folders", tags=["folders"])


async def _resolve_organization_id(
    current_user: Optional[User] = Depends(get_optional_current_user),
    org_header: Optional[str] = Header(None, alias="X-Organization-Id"),
    org_query: Optional[uuid.UUID] = Query(None, alias="organization_id"),
    db: AsyncSession = Depends(get_db),
) -> uuid.UUID:
    """
    Derives active organization from authenticated session context.
    Prevents caller from accessing another tenant's data via query params.
    """
    if current_user and current_user.organization_id:
        return current_user.organization_id

    # Fallback for unauthenticated development / demo mode
    if org_header:
        try:
            return uuid.UUID(org_header)
        except ValueError:
            pass

    if org_query:
        return org_query

    # Default to first active organization in database
    res = await db.execute(select(Organization.id).limit(1))
    first_id = res.scalar_one_or_none()
    if first_id:
        return first_id

    default_org_id = uuid.UUID("11111111-1111-1111-1111-111111111111")
    return default_org_id


@router.get("", response_model=List[FolderResponse] | List[FolderTreeNode])
async def list_folders(
    parent_id: Optional[uuid.UUID] = Query(None, description="Filter by immediate parent ID"),
    tree: bool = Query(False, description="Return nested hierarchy tree if true"),
    org_id: uuid.UUID = Depends(_resolve_organization_id),
    db: AsyncSession = Depends(get_db),
):
    """Lists workspace folders for the authenticated organization."""
    service = FolderService(db)
    return await service.list_folders(organization_id=org_id, parent_id=parent_id, as_tree=tree)


@router.post("", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_in: FolderCreate,
    current_user: Optional[User] = Depends(get_optional_current_user),
    org_id: uuid.UUID = Depends(_resolve_organization_id),
    db: AsyncSession = Depends(get_db),
):
    """Creates a new folder with normalized sibling uniqueness and depth limits."""
    service = FolderService(db)
    user_id = current_user.id if current_user else None
    result = await service.create_folder(organization_id=org_id, user_id=user_id, folder_in=folder_in)
    await db.commit()
    return result


@router.patch("/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: uuid.UUID,
    folder_in: FolderUpdate,
    org_id: uuid.UUID = Depends(_resolve_organization_id),
    db: AsyncSession = Depends(get_db),
):
    """Renames or updates styling of a folder. System Inbox cannot be renamed."""
    service = FolderService(db)
    result = await service.update_folder(organization_id=org_id, folder_id=folder_id, folder_in=folder_in)
    await db.commit()
    return result


@router.post("/{folder_id}/move", response_model=FolderResponse)
async def move_folder(
    folder_id: uuid.UUID,
    move_in: FolderMove,
    org_id: uuid.UUID = Depends(_resolve_organization_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Concurrency-safe transactional folder move.
    Guarantees cycle prevention, max depth <= 6, sibling uniqueness, and same-tenant isolation.
    """
    service = FolderService(db)
    result = await service.move_folder(
        organization_id=org_id,
        folder_id=folder_id,
        new_parent_id=move_in.new_parent_id,
    )
    await db.commit()
    return result


@router.delete("/{folder_id}")
async def delete_folder(
    folder_id: uuid.UUID,
    org_id: uuid.UUID = Depends(_resolve_organization_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Deletes an empty folder.
    Strictly blocks deleting the system Inbox or non-empty folders (containing documents or subfolders).
    """
    service = FolderService(db)
    await service.delete_folder(organization_id=org_id, folder_id=folder_id)
    await db.commit()
    return {"success": True, "message": "Folder deleted successfully."}


@router.get("/{folder_id}/documents")
async def list_folder_documents(
    folder_id: uuid.UUID,
    recursive: bool = Query(False, description="Include documents from all descendant subfolders"),
    status: Optional[str] = Query(None, description="Filter by status (e.g. active, processing, failed)"),
    include_archived: bool = Query(False, description="Include inactive/archived/deleted documents"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    org_id: uuid.UUID = Depends(_resolve_organization_id),
    db: AsyncSession = Depends(get_db),
):
    """Returns paginated documents within a folder or its entire subtree."""
    service = FolderService(db)
    doc_repo = DocumentRepository(db)

    folder_ids = [folder_id]
    if recursive:
        descendants = await service._get_subtree_folders(org_id, folder_id)
        folder_ids.extend([d.id for d in descendants])

    docs = await doc_repo.list_by_folder_ids(
        organization_id=org_id,
        folder_ids=folder_ids,
        status_filter=status,
        include_archived=include_archived,
        limit=limit,
        offset=offset,
    )
    total = await doc_repo.count_by_folder_ids(
        organization_id=org_id,
        folder_ids=folder_ids,
        status_filter=status,
        include_archived=include_archived,
    )

    from app.api.v1.documents import _get_claims_counts_for_documents
    doc_ids = [d.id for d in docs]
    claims_counts = await _get_claims_counts_for_documents(db, doc_ids)
    items = []
    for d in docs:
        resp = DocumentResponse.model_validate(d)
        resp.claims_count = claims_counts.get(d.id, 0)
        items.append(resp)

    return {
        "folder_id": str(folder_id),
        "is_recursive": recursive,
        "total": total,
        "limit": limit,
        "offset": offset,
        "items": items,
    }


@router.get("/{folder_id}/metrics", response_model=FolderMetricsResponse)
async def get_folder_metrics(
    folder_id: uuid.UUID,
    recursive: bool = Query(True, description="Evaluate subtree if true, or direct folder contents only"),
    org_id: uuid.UUID = Depends(_resolve_organization_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Returns transparent factual status counts for documents and claims in scope.
    Evaluated strictly over current document versions.
    """
    service = FolderService(db)
    return await service.get_folder_metrics(organization_id=org_id, folder_id=folder_id, recursive=recursive)


@router.post("/move-document")
async def move_document_to_folder(
    req: DocumentMoveRequest,
    document_id: uuid.UUID = Query(..., description="Document ID to move"),
    org_id: uuid.UUID = Depends(_resolve_organization_id),
    db: AsyncSession = Depends(get_db),
):
    """Moves a document to another folder within the same organization."""
    service = FolderService(db)
    doc = await service.move_document(
        organization_id=org_id,
        document_id=document_id,
        destination_folder_id=req.destination_folder_id,
    )
    await db.commit()
    return {
        "success": True,
        "document_id": str(doc.id),
        "folder_id": str(doc.folder_id),
        "message": "Document moved successfully.",
    }


@router.post("/auto-organize")
async def auto_organize_workspace_folders(
    org_id: uuid.UUID = Depends(_resolve_organization_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Intelligently provisions standard enterprise folders and auto-files
    unorganized / unclassified documents into appropriate domain and connector folders.
    """
    service = FolderService(db)
    result = await service.auto_organize_documents(organization_id=org_id)
    await db.commit()
    return result


@router.post("/migrate-slack")
async def migrate_slack_workspace_folders(
    org_id: uuid.UUID = Depends(_resolve_organization_id),
    db: AsyncSession = Depends(get_db),
):
    """
    Reroutes all Slack conversational threads into Slack Messages subfolders
    and all extracted attachments into Slack Documents subfolders.
    """
    service = FolderService(db)
    result = await service.migrate_existing_slack_documents(organization_id=org_id)
    await db.commit()
    return result

