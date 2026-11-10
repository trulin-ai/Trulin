import uuid
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.db.enums import RecordStatus


class DocumentVersionResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    version_number: int
    content_uri: str | None = None
    content_hash: str | None = None
    modified_at: datetime | None = None
    is_current: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentCreate(BaseModel):
    organization_id: uuid.UUID
    source_id: uuid.UUID | None = None
    folder_id: uuid.UUID | None = None
    title: str
    content: str
    document_type: str | None = "policy"
    external_id: str | None = None
    metadata: dict | None = None
    owner_id: uuid.UUID | None = None


class DocumentResponse(BaseModel):
    id: uuid.UUID
    organization_id: uuid.UUID
    source_id: uuid.UUID | None = None
    folder_id: uuid.UUID | None = None
    owner_id: uuid.UUID | None = None
    external_id: str | None = None
    title: str
    document_type: str | None = None
    content_uri: str | None = None
    content_hash: str | None = None
    status: RecordStatus
    created_at: datetime
    updated_at: datetime
    versions: list[DocumentVersionResponse] = Field(default_factory=list)
    claims_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class DocumentIngestionResult(BaseModel):
    document: DocumentResponse
    current_version: DocumentVersionResponse
    normalized: bool = False
    message: str = "Document successfully ingested"
