import secrets
import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app import models, schemas
from app.deps import require_admin, ActiveContext
from app.security import hash_password, create_session_token

router = APIRouter(prefix="/invites", tags=["invites"])


@router.post("", status_code=status.HTTP_201_CREATED)
def create_or_resend_invite(
    payload: schemas.InviteCreate,
    db: Session = Depends(get_db),
    ctx: ActiveContext = Depends(require_admin),
):
    """Resending an invite must not duplicate it. We look for an existing
    *pending* row for this (agency, email, client) first and just return its
    token again — the DB migration also backs this with a partial unique
    index so a race between two "resend" clicks can't slip through even
    under concurrent requests (see DESIGN.md, "invite races").
    """
    existing = (
        db.query(models.Invite)
        .filter(
            models.Invite.agency_id == ctx.agency_id,
            models.Invite.email == payload.email,
            models.Invite.client_id == payload.client_id,
            models.Invite.status == models.InviteStatus.pending,
        )
        .first()
    )
    if existing:
        return {"token": existing.token, "resent": True}

    invite = models.Invite(
        agency_id=ctx.agency_id,
        email=payload.email,
        role=models.InviteRole(payload.role),
        client_id=payload.client_id,
        token=secrets.token_urlsafe(24),
        expires_at=datetime.utcnow() + timedelta(days=7),
    )
    db.add(invite)
    try:
        db.commit()
    except IntegrityError:
        # Lost a race against a concurrent resend — fetch and return theirs
        # instead of erroring, which is what "shouldn't duplicate it" means
        # in practice under concurrency.
        db.rollback()
        existing = (
            db.query(models.Invite)
            .filter(
                models.Invite.agency_id == ctx.agency_id,
                models.Invite.email == payload.email,
                models.Invite.client_id == payload.client_id,
                models.Invite.status == models.InviteStatus.pending,
            )
            .first()
        )
        return {"token": existing.token, "resent": True}

    db.refresh(invite)
    return {"token": invite.token, "resent": False}


@router.post("/accept")
def accept_invite(payload: schemas.InviteAccept, db: Session = Depends(get_db)):
    invite = db.query(models.Invite).filter(models.Invite.token == payload.token).first()
    if not invite or invite.status != models.InviteStatus.pending:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invite is invalid or already used")
    if invite.expires_at and invite.expires_at < datetime.utcnow():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invite has expired")

    # "Accepting the same invite twice shouldn't create two accounts" — find
    # the user by email (global identity) and reuse it if it already exists,
    # instead of always inserting a new User row.
    user = db.query(models.User).filter(models.User.email == invite.email).first()
    if not user:
        user = models.User(
            email=invite.email, full_name=payload.full_name, hashed_password=hash_password(payload.password)
        )
        db.add(user)
        db.flush()

    if invite.role == models.InviteRole.client_user:
        already = (
            db.query(models.ClientUser)
            .filter(models.ClientUser.user_id == user.id, models.ClientUser.client_id == invite.client_id)
            .first()
        )
        if not already:
            db.add(models.ClientUser(user_id=user.id, client_id=invite.client_id, agency_id=invite.agency_id))
        role_str, agency_id, client_id = "client_user", invite.agency_id, invite.client_id
    else:
        already = (
            db.query(models.AgencyMembership)
            .filter(
                models.AgencyMembership.user_id == user.id, models.AgencyMembership.agency_id == invite.agency_id
            )
            .first()
        )
        if not already:
            db.add(
                models.AgencyMembership(
                    user_id=user.id, agency_id=invite.agency_id, role=models.AgencyRole(invite.role.value)
                )
            )
        role_str, agency_id, client_id = invite.role.value, invite.agency_id, None

    invite.status = models.InviteStatus.accepted
    db.commit()

    token = create_session_token(user_id=user.id, agency_id=agency_id, role=role_str, client_id=client_id)
    return {"token": token}


@router.post("/{invite_id}/revoke")
def revoke_invite(invite_id: uuid.UUID, db: Session = Depends(get_db), ctx: ActiveContext = Depends(require_admin)):
    invite = (
        db.query(models.Invite)
        .filter(models.Invite.id == invite_id, models.Invite.agency_id == ctx.agency_id)
        .first()
    )
    if not invite:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Invite not found")
    invite.status = models.InviteStatus.revoked
    db.commit()
    return {"ok": True}
