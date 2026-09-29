from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.security import verify_password, create_session_token

router = APIRouter(prefix="/auth", tags=["auth"])


def _memberships_for(db: Session, user: models.User):
    """Every (agency, role) OR (client, client_user) pairing this email can
    act as. This is where 'one person, two agencies' becomes concrete: we
    just union two membership tables keyed by the same user_id.
    """
    out = []
    for m in db.query(models.AgencyMembership).filter(models.AgencyMembership.user_id == user.id):
        out.append(
            schemas.Membership(
                agency_id=m.agency_id,
                agency_name=m.agency.name,
                client_id=None,
                client_name=None,
                role=m.role.value,
            )
        )
    for cu in db.query(models.ClientUser).filter(models.ClientUser.user_id == user.id):
        out.append(
            schemas.Membership(
                agency_id=cu.agency_id,
                agency_name=cu.client.agency.name,
                client_id=cu.client_id,
                client_name=cu.client.name,
                role="client_user",
            )
        )
    return out


@router.post("/login", response_model=schemas.LoginResponse)
def login(payload: schemas.LoginRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    contexts = _memberships_for(db, user)
    if not contexts:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No memberships for this account")

    if len(contexts) == 1:
        ctx = contexts[0]
        token = create_session_token(
            user_id=user.id, agency_id=ctx.agency_id, role=ctx.role, client_id=ctx.client_id
        )
        return schemas.LoginResponse(token=token, contexts=contexts)

    # Ambiguous: same email, several agency/role or client pairings.
    # Frontend shows a picker and calls /auth/select-context next.
    return schemas.LoginResponse(token=None, contexts=contexts)


@router.post("/select-context", response_model=schemas.LoginResponse)
def select_context(payload: schemas.SelectContextRequest, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == payload.email).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    if payload.client_id:
        membership = (
            db.query(models.ClientUser)
            .filter(models.ClientUser.user_id == user.id, models.ClientUser.client_id == payload.client_id)
            .first()
        )
        if not membership:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No such client membership")
        token = create_session_token(
            user_id=user.id, agency_id=membership.agency_id, role="client_user", client_id=membership.client_id
        )
        return schemas.LoginResponse(token=token)

    membership = (
        db.query(models.AgencyMembership)
        .filter(models.AgencyMembership.user_id == user.id, models.AgencyMembership.agency_id == payload.agency_id)
        .first()
    )
    if not membership:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No such agency membership")
    token = create_session_token(user_id=user.id, agency_id=membership.agency_id, role=membership.role.value)
    return schemas.LoginResponse(token=token)
