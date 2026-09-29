import uuid
from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel


class Membership(BaseModel):
    agency_id: Optional[uuid.UUID]
    agency_name: Optional[str]
    client_id: Optional[uuid.UUID]
    client_name: Optional[str]
    role: str


class LoginRequest(BaseModel):
    email: str
    password: str


class LoginResponse(BaseModel):
    # If the email has more than one membership, `token` is omitted and the
    # caller must hit /auth/select-context with one of `contexts`.
    token: Optional[str] = None
    contexts: List[Membership] = []


class SelectContextRequest(BaseModel):
    email: str
    password: str
    agency_id: Optional[uuid.UUID] = None
    client_id: Optional[uuid.UUID] = None


class ProjectOut(BaseModel):
    id: uuid.UUID
    name: str
    status: str
    client_id: uuid.UUID

    class Config:
        from_attributes = True


class ProjectCreate(BaseModel):
    name: str
    client_id: uuid.UUID


class TaskOut(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    title: str
    description: str
    status: str
    priority: str
    assignee_id: Optional[uuid.UUID]
    due_date: Optional[datetime]
    is_client_visible: bool

    class Config:
        from_attributes = True


class TaskCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    due_date: Optional[datetime] = None
    is_client_visible: bool = False
    assignee_id: Optional[uuid.UUID] = None


class TaskUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = None
    priority: Optional[str] = None
    due_date: Optional[datetime] = None
    is_client_visible: Optional[bool] = None
    assignee_id: Optional[uuid.UUID] = None


class CommentOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    author_id: uuid.UUID
    body: str
    is_client_visible: bool
    created_at: datetime

    class Config:
        from_attributes = True


class CommentCreate(BaseModel):
    body: str
    is_client_visible: bool = False


class TimeEntryCreate(BaseModel):
    duration_minutes: int
    note: str = ""
    entry_date: Optional[datetime] = None


class TimeEntryOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    user_id: uuid.UUID
    duration_minutes: int
    note: str
    entry_date: datetime

    class Config:
        from_attributes = True


class FileOut(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    filename: str
    is_client_visible: bool
    approval_status: str

    class Config:
        from_attributes = True


class InviteCreate(BaseModel):
    email: str
    role: str  # agency_admin | agency_member | client_user
    client_id: Optional[uuid.UUID] = None


class InviteAccept(BaseModel):
    token: str
    full_name: str
    password: str


class DashboardOut(BaseModel):
    project_id: uuid.UUID
    task_counts_by_status: dict
    total_hours_logged: Optional[float] = None  # None when viewer is a client
