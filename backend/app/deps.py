"""
Everything that keeps Tenant A out of Tenant B's data, and clients out of
internal content, is funneled through this one file. Routers never write
their own `.filter(Agency.id == ...)` — they call `scope.tasks()`,
`scope.projects()`, etc., and get a pre-filtered query back. This is
deliberate: the assignment's #1 risk ("internal content leaking to clients
... check every code path") is best mitigated by having exactly one code
path, not by trusting every router author to remember the filter.
"""
from dataclasses import dataclass
from typing import Optional
import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session, Query

from app.database import get_db
from app import models
from app.security import decode_session_token

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


@dataclass
class ActiveContext:
    user_id: uuid.UUID
    role: str  # "agency_admin" | "agency_member" | "client_user"
    agency_id: Optional[uuid.UUID]
    client_id: Optional[uuid.UUID]  # only set for client_user

    @property
    def is_client(self) -> bool:
        return self.role == "client_user"

    @property
    def is_admin(self) -> bool:
        return self.role == "agency_admin"


def get_current_context(token: str = Depends(oauth2_scheme)) -> ActiveContext:
    try:
        payload = decode_session_token(token)
    except ValueError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")
    return ActiveContext(
        user_id=uuid.UUID(payload["sub"]),
        role=payload["role"],
        agency_id=uuid.UUID(payload["agency_id"]) if payload.get("agency_id") else None,
        client_id=uuid.UUID(payload["client_id"]) if payload.get("client_id") else None,
    )


def require_agency_staff(ctx: ActiveContext = Depends(get_current_context)) -> ActiveContext:
    if ctx.is_client:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Agency staff only")
    return ctx


def require_admin(ctx: ActiveContext = Depends(get_current_context)) -> ActiveContext:
    if not ctx.is_admin:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Agency admin only")
    return ctx


class TenantScope:
    """Bound to one request's ActiveContext. Every method below returns a
    Query that is *already* filtered — callers add ordering/pagination on
    top, nothing else.
    """

    def __init__(self, db: Session, ctx: ActiveContext):
        self.db = db
        self.ctx = ctx

    # ---- projects -------------------------------------------------
    def projects(self) -> Query:
        q = self.db.query(models.Project).filter(models.Project.agency_id == self.ctx.agency_id)
        if self.ctx.is_client:
            q = q.filter(models.Project.client_id == self.ctx.client_id)
        elif self.ctx.role == "agency_member":
            q = q.join(models.ProjectMember).filter(models.ProjectMember.user_id == self.ctx.user_id)
        return q

    def project_or_404(self, project_id: uuid.UUID) -> models.Project:
        project = self.projects().filter(models.Project.id == project_id).first()
        if not project:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
        return project

    # ---- tasks ------------------------------------------------------
    def tasks(self) -> Query:
        # Always start from agency_id — this is what stops cross-tenant
        # reads even if a project_id from another tenant gets guessed and
        # passed in a filter param upstream.
        q = self.db.query(models.Task).filter(models.Task.agency_id == self.ctx.agency_id)
        if self.ctx.is_client:
            q = (
                q.join(models.Project, models.Task.project_id == models.Project.id)
                .filter(models.Project.client_id == self.ctx.client_id)
                .filter(models.Task.is_client_visible.is_(True))
            )
        elif self.ctx.role == "agency_member":
            q = q.join(models.ProjectMember, models.ProjectMember.project_id == models.Task.project_id).filter(
                models.ProjectMember.user_id == self.ctx.user_id
            )
        return q

    def task_or_404(self, task_id: uuid.UUID) -> models.Task:
        task = self.tasks().filter(models.Task.id == task_id).first()
        if not task:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Task not found")
        return task

    # ---- comments -----------------------------------------------------
    def comments_for_task(self, task: models.Task) -> Query:
        q = self.db.query(models.Comment).filter(
            models.Comment.task_id == task.id, models.Comment.agency_id == self.ctx.agency_id
        )
        if self.ctx.is_client:
            q = q.filter(models.Comment.is_client_visible.is_(True))
        return q

    # ---- files ----------------------------------------------------------
    def files_for_task(self, task: models.Task) -> Query:
        q = self.db.query(models.FileAsset).filter(
            models.FileAsset.task_id == task.id, models.FileAsset.agency_id == self.ctx.agency_id
        )
        if self.ctx.is_client:
            q = q.filter(models.FileAsset.is_client_visible.is_(True))
        return q

    # ---- time entries (agency-only; clients never see raw time data) ----
    def time_entries_for_task(self, task: models.Task) -> Query:
        if self.ctx.is_client:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Clients cannot view time entries")
        return self.db.query(models.TimeEntry).filter(
            models.TimeEntry.task_id == task.id, models.TimeEntry.agency_id == self.ctx.agency_id
        )

    # ---- clients (agency-side listing of its own clients) ----------------
    def clients(self) -> Query:
        if self.ctx.is_client:
            return self.db.query(models.Client).filter(models.Client.id == self.ctx.client_id)
        return self.db.query(models.Client).filter(models.Client.agency_id == self.ctx.agency_id)


def get_scope(
    db: Session = Depends(get_db), ctx: ActiveContext = Depends(get_current_context)
) -> TenantScope:
    return TenantScope(db, ctx)
