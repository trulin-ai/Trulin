import uuid
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db.database import get_db
from app.db.models.user import User
from app.services.lineage_service import LineageService

router = APIRouter(prefix="/lineage", tags=["lineage"])


def _resolve_authorized_org(current_user: User, requested_org_id: Optional[uuid.UUID]) -> uuid.UUID:
    """Derives organization scope from the authenticated user and blocks cross-tenant queries."""
    if requested_org_id is not None and requested_org_id != current_user.organization_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Cross-organization lineage access denied.",
        )
    return current_user.organization_id


@router.get("/graph")
async def get_lineage_graph(
    organization_id: Optional[uuid.UUID] = Query(None, description="Optional org verification (must match authenticated user)"),
    workspace_id: Optional[str] = Query(None, description="Optional workspace folder subtree filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves scoped multi-tiered DAG lineage graph across sources, documents, claims, conflicts, and decisions."""
    org_id = _resolve_authorized_org(current_user, organization_id)
    service = LineageService(db)
    return await service.get_lineage_graph(org_id, workspace_id=workspace_id)


@router.get("/investigate")
async def investigate_subgraph(
    organization_id: Optional[uuid.UUID] = Query(None, description="Optional org verification (must match authenticated user)"),
    workspace_id: Optional[str] = Query(None, description="Optional workspace folder subtree filter"),
    mode: str = Query("risk", description="Investigation Lens: risk | evidence | impact | hierarchy | decision"),
    root_id: Optional[str] = Query(None, description="Optional root focus node ID"),
    max_depth: int = Query(2, ge=1, le=4, description="Maximum traversal depth hops"),
    limit: int = Query(45, ge=5, le=120, description="Hard node ceiling limit"),
    cursor: Optional[str] = Query(None, description="Opaque pagination cursor"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retrieves a bounded, ranked, investigation-centric lineage subgraph."""
    org_id = _resolve_authorized_org(current_user, organization_id)
    service = LineageService(db)
    return await service.investigate_lineage_subgraph(
        organization_id=org_id,
        workspace_id=workspace_id,
        mode=mode,
        root_id=root_id,
        max_depth=max_depth,
        limit=limit,
        cursor=cursor,
    )


@router.get("/blast-radius/{claim_id}")
async def get_claim_blast_radius(
    claim_id: uuid.UUID,
    workspace_id: Optional[str] = Query(None, description="Optional workspace folder subtree filter"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Calculates downstream blast radius of deprecating, altering, or conflicting on an authorized claim."""
    service = LineageService(db)
    result = await service.get_blast_radius(
        claim_id,
        organization_id=current_user.organization_id,
        workspace_id=workspace_id,
    )
    if "error" in result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=result["error"],
        )
    return result


class EdgeMutationRequest(BaseModel):
    organization_id: Optional[uuid.UUID] = None
    added_edges: List[Dict[str, Any]] = []
    severed_edge_ids: List[str] = []
    reason: Optional[str] = None


@router.post("/edges/mutate")
async def mutate_lineage_edges(
    payload: EdgeMutationRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Disabled until persisted, audited edge overrides are implemented (historical provenance is read-only)."""
    _resolve_authorized_org(current_user, payload.organization_id)
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Lineage edge mutation is disabled: extraction provenance is read-only until persisted audit overrides are enabled.",
    )
