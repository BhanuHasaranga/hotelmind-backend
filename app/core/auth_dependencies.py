import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_error = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = decode_access_token(token)
    except ValueError:
        raise credentials_error

    try:
        user_id = uuid.UUID(payload.sub)
    except ValueError:
        raise credentials_error

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise credentials_error

    return user


def require_roles(*roles: str):
    async def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action",
            )
        return user

    return dependency


def scope_branch(user: User, requested_branch_id: uuid.UUID | None) -> uuid.UUID | None:
    """Resolve which branch a request may operate on.

    OWNER may view any branch (or all, if requested_branch_id is None).
    Every other role is pinned to their own branch_id - any mismatched
    request is rejected rather than silently narrowed, since silently
    narrowing could mask a client-side bug that leaks cross-branch data.
    """
    if user.role == "OWNER":
        return requested_branch_id

    if requested_branch_id is not None and requested_branch_id != user.branch_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this branch",
        )
    return user.branch_id
