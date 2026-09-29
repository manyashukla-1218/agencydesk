import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.deps import require_admin, ActiveContext

router = APIRouter(tags=["members"])


@router.post("/projects/{project_id}/members/{user_id}")
def add_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: ActiveContext = Depends(require_admin),
):
    project = db.query(models.Project).filter(
        models.Project.id == project_id, models.Project.agency_id == ctx.agency_id
    ).first()
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")
    exists = (
        db.query(models.ProjectMember)
        .filter(models.ProjectMember.project_id == project_id, models.ProjectMember.user_id == user_id)
        .first()
    )
    if not exists:
        db.add(models.ProjectMember(project_id=project_id, user_id=user_id))
        db.commit()
    return {"ok": True}


@router.delete("/projects/{project_id}/members/{user_id}")
def remove_project_member(
    project_id: uuid.UUID,
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    ctx: ActiveContext = Depends(require_admin),
):
    """Decision (documented in DESIGN.md): removing someone from a project
    does NOT delete their past work (time entries, comments, uploaded
    files stay attributed to them for the audit trail). It DOES:
      1. drop their project_members row, so they immediately lose read/write
         access to the project's tasks (enforced automatically next request
         by TenantScope.tasks(), no extra cleanup needed there), and
      2. unassign them from any task in that project still pointing at them,
         so nothing is left silently assigned to someone who can no longer
         see it.
    """
    membership = (
        db.query(models.ProjectMember)
        .filter(models.ProjectMember.project_id == project_id, models.ProjectMember.user_id == user_id)
        .first()
    )
    if not membership:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Not a member of this project")

    project = db.query(models.Project).filter(
        models.Project.id == project_id, models.Project.agency_id == ctx.agency_id
    ).first()
    if not project:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Project not found")

    db.query(models.Task).filter(
        models.Task.project_id == project_id, models.Task.assignee_id == user_id
    ).update({"assignee_id": None})

    db.delete(membership)
    db.commit()
    return {"ok": True, "tasks_unassigned": True}
