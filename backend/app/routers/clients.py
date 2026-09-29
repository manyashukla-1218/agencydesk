from typing import List

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models
from app.deps import get_scope, TenantScope, require_admin, ActiveContext
from pydantic import BaseModel
import uuid


class ClientOut(BaseModel):
    id: uuid.UUID
    name: str

    class Config:
        from_attributes = True


class ClientCreate(BaseModel):
    name: str


router = APIRouter(prefix="/clients", tags=["clients"])


@router.get("", response_model=List[ClientOut])
def list_clients(scope: TenantScope = Depends(get_scope)):
    return scope.clients().all()


@router.post("", response_model=ClientOut, status_code=status.HTTP_201_CREATED)
def create_client(
    payload: ClientCreate, db: Session = Depends(get_db), ctx: ActiveContext = Depends(require_admin)
):
    client = models.Client(agency_id=ctx.agency_id, name=payload.name)
    db.add(client)
    db.commit()
    db.refresh(client)
    return client
