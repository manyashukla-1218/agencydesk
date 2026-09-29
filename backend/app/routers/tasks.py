import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.deps import get_scope, TenantScope, require_agency_staff, ActiveContext

router = APIRouter(tags=["tasks"])


@router.get("/projects/{project_id}/tasks", response_model=List[schemas.TaskOut])
def list_tasks(
    project_id: uuid.UUID,
    status_filter: Optional[str] = None,
    q: Optional[str] = None,
    scope: TenantScope = Depends(get_scope),
):
    scope.project_or_404(project_id)  # 404s if this project isn't in-tenant / in-scope
    query = scope.tasks().filter(models.Task.project_id == project_id)
    # NB: status/search filters are applied *after* scope.tasks() has already
    # narrowed by tenant + client-visibility, precisely so a filter or search
    # param can never be used to route around the visibility check (this is
    # the exact edge case the assignment calls out: "search, filters ... are
    # easy to miss").
    if status_filter:
        query = query.filter(models.Task.status == status_filter)
    if q:
        query = query.filter(models.Task.title.ilike(f"%{q}%"))
    return query.all()


@router.post("/projects/{project_id}/tasks", response_model=schemas.TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(
    project_id: uuid.UUID,
    payload: schemas.TaskCreate,
    db: Session = Depends(get_db),
    ctx: ActiveContext = Depends(require_agency_staff),
    scope: TenantScope = Depends(get_scope),
):
    project = scope.project_or_404(project_id)
    task = models.Task(
        project_id=project.id,
        agency_id=ctx.agency_id,
        title=payload.title,
        description=payload.description,
        priority=payload.priority,
        due_date=payload.due_date,
        is_client_visible=payload.is_client_visible,
        assignee_id=payload.assignee_id,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/tasks/{task_id}", response_model=schemas.TaskOut)
def get_task(task_id: uuid.UUID, scope: TenantScope = Depends(get_scope)):
    return scope.task_or_404(task_id)


@router.patch("/tasks/{task_id}", response_model=schemas.TaskOut)
def update_task(
    task_id: uuid.UUID,
    payload: schemas.TaskUpdate,
    db: Session = Depends(get_db),
    ctx: ActiveContext = Depends(require_agency_staff),
    scope: TenantScope = Depends(get_scope),
):
    task = scope.task_or_404(task_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(task, field, value)
    db.commit()
    db.refresh(task)
    return task


@router.get("/tasks/{task_id}/comments", response_model=List[schemas.CommentOut])
def list_comments(task_id: uuid.UUID, scope: TenantScope = Depends(get_scope)):
    task = scope.task_or_404(task_id)
    return scope.comments_for_task(task).all()


@router.post("/tasks/{task_id}/comments", response_model=schemas.CommentOut, status_code=status.HTTP_201_CREATED)
def add_comment(
    task_id: uuid.UUID,
    payload: schemas.CommentCreate,
    db: Session = Depends(get_db),
    scope: TenantScope = Depends(get_scope),
):
    task = scope.task_or_404(task_id)
    ctx = scope.ctx
    is_visible = payload.is_client_visible
    if ctx.is_client:
        # Clients "can comment on tasks" per spec, but never set the flag
        # themselves — their comments are client-visible by definition
        # (they wrote it, they can see it) and never silently promoted to
        # internal-only, which would hide their own words from them.
        is_visible = True
    comment = models.Comment(
        task_id=task.id,
        agency_id=task.agency_id,
        author_id=ctx.user_id,
        body=payload.body,
        is_client_visible=is_visible,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment
