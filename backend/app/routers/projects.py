import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.deps import get_scope, TenantScope, require_agency_staff, ActiveContext

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=List[schemas.ProjectOut])
def list_projects(scope: TenantScope = Depends(get_scope)):
    return scope.projects().all()


@router.post("", response_model=schemas.ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: schemas.ProjectCreate,
    db: Session = Depends(get_db),
    ctx: ActiveContext = Depends(require_agency_staff),
):
    if ctx.role != "agency_admin":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only agency_admin can create projects")

    client = (
        db.query(models.Client)
        .filter(models.Client.id == payload.client_id, models.Client.agency_id == ctx.agency_id)
        .first()
    )
    if not client:
        # Deliberately the same 404 a cross-tenant guess would get — never
        # confirm that a client_id exists in someone else's tenant.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Client not found")

    project = models.Project(agency_id=ctx.agency_id, client_id=client.id, name=payload.name)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.get("/{project_id}", response_model=schemas.ProjectOut)
def get_project(project_id: uuid.UUID, scope: TenantScope = Depends(get_scope)):
    return scope.project_or_404(project_id)
