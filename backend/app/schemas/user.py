import uuid
from datetime import datetime
from typing import Any
from pydantic import BaseModel, ConfigDict

from app.db.enums import RecordStatus, UserRole


class UserBase(BaseModel):
    name: str
    email: str
    role: UserRole = UserRole.VIEWER
    title: str | None = None
    department: str | None = None
    avatar_url: str | None = None
    phone: str | None = None
    bio: str | None = None
    timezone: str | None = None
    user_preferences: dict[str, Any] | None = None


class UserCreate(UserBase):
    organization_id: uuid.UUID


class UserUpdate(BaseModel):
    name: str | None = None
    role: UserRole | None = None
    title: str | None = None
    department: str | None = None
    avatar_url: str | None = None
    phone: str | None = None
    bio: str | None = None
    timezone: str | None = None
    user_preferences: dict[str, Any] | None = None
    status: RecordStatus | None = None
    reason: str | None = None


class UserResponse(UserBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    status: RecordStatus
    last_active_device: str | None = None
    created_at: datetime
    updated_at: datetime


class ActivityLogCreate(BaseModel):
    organization_id: uuid.UUID
    action_type: str
    target_type: str
    target_id: str | None = None
    target_title: str | None = None
    domain: str = "General"
    details: dict[str, Any] | None = None
    user_id: uuid.UUID | None = None
    user_name: str = "System"
    user_role: str = "system"


class ActivityLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    organization_id: uuid.UUID
    user_id: uuid.UUID | None
    user_name: str
    user_role: str
    action_type: str
    target_type: str
    target_id: str | None
    target_title: str | None
    domain: str
    details: dict[str, Any] | None
    created_at: datetime
