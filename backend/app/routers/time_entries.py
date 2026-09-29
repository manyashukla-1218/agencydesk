import uuid
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.deps import get_scope, TenantScope, require_agency_staff, ActiveContext

router = APIRouter(tags=["time-entries"])


@router.get("/tasks/{task_id}/time-entries", response_model=List[schemas.TimeEntryOut])
def list_time_entries(task_id: uuid.UUID, scope: TenantScope = Depends(get_scope)):
    task = scope.task_or_404(task_id)  # raises 403/404 before we even reach the client-block below
    return scope.time_entries_for_task(task).all()


@router.post(
    "/tasks/{task_id}/time-entries", response_model=schemas.TimeEntryOut, status_code=status.HTTP_201_CREATED
)
def log_time(
    task_id: uuid.UUID,
    payload: schemas.TimeEntryCreate,
    db: Session = Depends(get_db),
    ctx: ActiveContext = Depends(require_agency_staff),
    scope: TenantScope = Depends(get_scope),
):
    task = scope.task_or_404(task_id)
    entry = models.TimeEntry(
        task_id=task.id,
        agency_id=task.agency_id,
        user_id=ctx.user_id,
        duration_minutes=payload.duration_minutes,
        note=payload.note,
        entry_date=payload.entry_date or datetime.utcnow(),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry
