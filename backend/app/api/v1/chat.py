import uuid
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.services.chat_service import ChatService

router = APIRouter(prefix="/chat", tags=["chat"])


class CreateSessionRequest(BaseModel):
    organization_id: uuid.UUID
    user_id: uuid.UUID | None = None
    user_name: str = "Anonymous"
    user_role: str = "developer"
    title: str = "New Conversation"
    workspace_id: str | None = "all"
    domain: str | None = "global"


class SendMessageRequest(BaseModel):
    organization_id: uuid.UUID
    content: str = Field(..., min_length=1)
    user_id: uuid.UUID | None = None
    user_name: str = "User"
    user_role: str = "developer"
    workspace_id: str | None = None
    domain: str | None = None
    requested_depth: str | None = None


@router.get("/sessions")
async def list_chat_sessions(
    organization_id: uuid.UUID = Query(...),
    user_id: uuid.UUID | None = Query(None),
    workspace_id: str | None = Query(None),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    """List chat sessions for a specific organization, user/persona, and departmental workspace."""
    try:
        service = ChatService(db)
        return await service.list_sessions(organization_id, user_id, workspace_id, limit)
    except Exception as e:
        import logging
        logging.getLogger("chat").warning(f"Error querying chat sessions: {e}")
        return []


@router.post("/sessions")
async def create_chat_session(
    req: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new conversational session tagged with active departmental workspace."""
    service = ChatService(db)
    return await service.create_session(
        organization_id=req.organization_id,
        user_id=req.user_id,
        user_name=req.user_name,
        user_role=req.user_role,
        title=req.title,
        workspace_id=req.workspace_id,
        domain=req.domain,
    )


@router.get("/sessions/{session_id}")
async def get_chat_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get conversation details with complete message history."""
    service = ChatService(db)
    session_data = await service.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return session_data


class UpdateSessionRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)


@router.patch("/sessions/{session_id}")
async def update_chat_session(
    session_id: uuid.UUID,
    req: UpdateSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Rename or update a conversation session title."""
    service = ChatService(db)
    updated = await service.update_session_title(session_id, req.title)
    if not updated:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return updated


@router.delete("/sessions/{session_id}")
async def delete_chat_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation session and all its messages."""
    service = ChatService(db)
    success = await service.delete_session(session_id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat session not found")
    return {"status": "deleted", "session_id": str(session_id)}


@router.post("/sessions/{session_id}/messages")
async def send_chat_message(
    session_id: uuid.UUID,
    req: SendMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    """Post a user message, run context trust retrieval, and generate grounded assistant response."""
    service = ChatService(db)
    # Ensure session exists
    session_data = await service.get_session(session_id)
    if not session_data:
        raise HTTPException(status_code=404, detail="Chat session not found")

    result = await service.process_user_message(
        session_id=session_id,
        organization_id=req.organization_id,
        content=req.content,
        user_id=req.user_id,
        user_name=req.user_name,
        user_role=req.user_role,
        workspace_id=req.workspace_id,
        domain=req.domain,
        requested_depth=req.requested_depth,
    )
    return result


from app.services.feedback_telemetry_service import (
    FeedbackSubmitRequest,
    FeedbackTelemetryService,
    PilotFeedbackRequest,
)


@router.post("/sessions/{session_id}/messages/{message_id}/feedback")
async def submit_message_feedback(
    session_id: uuid.UUID,
    message_id: str,
    req: FeedbackSubmitRequest,
):
    """Log structured feedback with failure taxonomy stage."""
    req.session_id = str(session_id)
    req.message_id = str(message_id)
    return FeedbackTelemetryService.record_feedback(req)


@router.post("/sessions/{session_id}/messages/{message_id}/pilot-feedback")
async def submit_pilot_feedback(
    session_id: uuid.UUID,
    message_id: str,
    req: PilotFeedbackRequest,
):
    """Log formal pilot evaluator review (verdict, category, 8-point checklist)."""
    req.session_id = str(session_id)
    req.message_id = str(message_id)
    return FeedbackTelemetryService.record_pilot_feedback(req)


@router.get("/telemetry/feedback")
async def get_feedback_telemetry():
    """Get aggregated failure taxonomy distribution and steward queue stats."""
    return FeedbackTelemetryService.get_stage_distribution()


@router.get("/telemetry/pilot-feedback")
async def get_pilot_feedback_telemetry(
    session_id: str | None = None,
):
    """Get all recorded pilot evaluations and summary compliance statistics."""
    evaluations = FeedbackTelemetryService.list_pilot_feedback(session_id=session_id)
    summary = FeedbackTelemetryService.get_pilot_summary()
    return {
        "evaluations": evaluations,
        "summary": summary,
    }
