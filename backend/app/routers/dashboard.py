import uuid
from sqlalchemy import func

from fastapi import APIRouter, Depends

from app import models, schemas
from app.deps import get_scope, TenantScope

router = APIRouter(tags=["dashboard"])


@router.get("/projects/{project_id}/dashboard", response_model=schemas.DashboardOut)
def project_dashboard(project_id: uuid.UUID, scope: TenantScope = Depends(get_scope)):
    scope.project_or_404(project_id)  # tenant + visibility check, same as every other endpoint

    # Reuse scope.tasks() rather than a raw query — this is what guarantees
    # the dashboard can't leak internal task counts to a client_user even
    # though it's a completely different code path (an aggregate, not a
    # list) from the board view.
    rows = (
        scope.tasks()
        .filter(models.Task.project_id == project_id)
        .with_entities(models.Task.status, func.count(models.Task.id))
        .group_by(models.Task.status)
        .all()
    )
    counts = {status.value: count for status, count in rows}

    total_hours = None
    if not scope.ctx.is_client:
        minutes = (
            scope.db.query(func.coalesce(func.sum(models.TimeEntry.duration_minutes), 0))
            .join(models.Task, models.TimeEntry.task_id == models.Task.id)
            .filter(models.Task.project_id == project_id, models.TimeEntry.agency_id == scope.ctx.agency_id)
            .scalar()
        )
        total_hours = round((minutes or 0) / 60, 2)

    return schemas.DashboardOut(project_id=project_id, task_counts_by_status=counts, total_hours_logged=total_hours)
