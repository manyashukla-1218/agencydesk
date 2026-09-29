from datetime import datetime, timedelta
from typing import Optional
import uuid

from jose import jwt, JWTError
from passlib.context import CryptContext

from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_session_token(
    *,
    user_id: uuid.UUID,
    agency_id: Optional[uuid.UUID],
    role: str,
    client_id: Optional[uuid.UUID] = None,
) -> str:
    """Encodes an *active context*, not just an identity.

    Because one User row can have several agency/role pairings (see
    models.py), the JWT is scoped to whichever one the person picked at
    login ("acting as Agency X, role agency_admin" — similar to a Slack
    workspace switch). Every request is then trivially tenant-scoped: the
    server trusts agency_id from the token, never from the request body or
    query string.
    """
    payload = {
        "sub": str(user_id),
        "agency_id": str(agency_id) if agency_id else None,
        "client_id": str(client_id) if client_id else None,
        "role": role,
        "exp": datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_session_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError("invalid or expired token") from exc
