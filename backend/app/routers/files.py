import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.config import settings
from app.deps import get_scope, TenantScope, require_agency_staff, ActiveContext

router = APIRouter(tags=["files"])


@router.get("/tasks/{task_id}/files", response_model=List[schemas.FileOut])
def list_files(task_id: uuid.UUID, scope: TenantScope = Depends(get_scope)):
    task = scope.task_or_404(task_id)
    return scope.files_for_task(task).all()


@router.post("/tasks/{task_id}/files", response_model=schemas.FileOut, status_code=status.HTTP_201_CREATED)
def upload_file(
    task_id: uuid.UUID,
    is_client_visible: bool = Form(False),
    upload: UploadFile = File(...),
    db: Session = Depends(get_db),
    ctx: ActiveContext = Depends(require_agency_staff),
    scope: TenantScope = Depends(get_scope),
):
    task = scope.task_or_404(task_id)
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    storage_key = f"{task.agency_id}/{task.id}/{uuid.uuid4()}_{upload.filename}"
    dest = os.path.join(settings.UPLOAD_DIR, storage_key.replace("/", "_"))
    with open(dest, "wb") as f:
        f.write(upload.file.read())

    file_row = models.FileAsset(
        task_id=task.id,
        agency_id=task.agency_id,
        uploaded_by=ctx.user_id,
        filename=upload.filename,
        storage_key=storage_key,
        is_client_visible=is_client_visible,
    )
    db.add(file_row)
    db.commit()
    db.refresh(file_row)
    return file_row


@router.post("/files/{file_id}/approve", response_model=schemas.FileOut)
def set_file_approval(
    file_id: uuid.UUID,
    approved: bool,
    scope: TenantScope = Depends(get_scope),
):
    file_row = (
        scope.db.query(models.FileAsset)
        .filter(models.FileAsset.id == file_id, models.FileAsset.agency_id == scope.ctx.agency_id)
        .first()
    )
    if not file_row:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found")
    if not file_row.is_client_visible:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "File is not client-visible")
    if not scope.ctx.is_client:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the client can approve/request changes")

    # Confirm the file belongs to *this* client's own project — is_client_visible
    # alone isn't tenant/ownership scoping, so re-check via the task's project.
    task = scope.task_or_404(file_row.task_id)
    file_row.approval_status = (
        models.FileApprovalStatus.approved if approved else models.FileApprovalStatus.changes_requested
    )
    file_row.approved_by = scope.ctx.user_id
    scope.db.commit()
    scope.db.refresh(file_row)
    return file_row
