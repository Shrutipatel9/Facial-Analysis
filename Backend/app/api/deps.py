"""Shared FastAPI dependencies: DB session, current-user guard, CSRF."""

import uuid

import jwt
from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.csrf import assert_cookie_request_allowed
from app.core.security import decode_access_token
from app.db.session import get_db
from app.exceptions import UnauthorizedError
from app.models.user import User
from app.services import user_service

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise UnauthorizedError()

    try:
        payload = decode_access_token(credentials.credentials)
    except jwt.InvalidTokenError as exc:
        # Covers expired signatures, bad signatures, and malformed tokens
        # alike -- see UnauthorizedError's docstring for why this doesn't
        # need finer-grained codes at this layer.
        raise UnauthorizedError() from exc

    try:
        user_id = uuid.UUID(payload.get("sub", ""))
    except ValueError as exc:
        raise UnauthorizedError() from exc

    user = await user_service.get_by_id(db, user_id)
    if user is None:
        raise UnauthorizedError()

    return user


def require_cookie_csrf(request: Request) -> None:
    """Dependency for endpoints that authenticate via the refresh cookie."""
    assert_cookie_request_allowed(request)
