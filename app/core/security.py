import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# passlib's bcrypt backend probes `bcrypt.__about__`, which was removed in
# bcrypt 4.x - that raises inside passlib before hashing even runs. Calling
# the `bcrypt` package directly sidesteps the broken shim entirely.


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))


def create_access_token(
    subject: str | uuid.UUID,
    role: str,
    branch_id: str | uuid.UUID | None,
    expires_delta: timedelta | None = None,
) -> str:
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.JWT_EXPIRES_MINUTES)
    )
    payload = {
        "sub": str(subject),
        "role": role,
        "branch_id": str(branch_id) if branch_id is not None else None,
        "exp": expire,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


class TokenPayload:
    def __init__(self, sub: str, role: str, branch_id: str | None):
        self.sub = sub
        self.role = role
        self.branch_id = branch_id


def decode_access_token(token: str) -> TokenPayload:
    try:
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc

    sub = payload.get("sub")
    role = payload.get("role")
    if sub is None or role is None:
        raise ValueError("Malformed token payload")

    return TokenPayload(sub=sub, role=role, branch_id=payload.get("branch_id"))
