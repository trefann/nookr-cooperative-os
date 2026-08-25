"""Reusable FastAPI dependencies for authentication and authorisation."""

from __future__ import annotations

from collections.abc import Callable, Iterable

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.errors import PermissionDeniedError, UnauthorizedError
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models import User, UserRole, Worker

#: auto_error=False so a missing header raises our own 401 envelope.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or not credentials.credentials:
        raise UnauthorizedError("Sign in to continue.")

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise UnauthorizedError("Your session has expired. Please sign in again.")

    subject = payload.get("sub")
    if not subject or not str(subject).isdigit():
        raise UnauthorizedError("Malformed session token.")

    user = db.get(User, int(subject))
    if user is None:
        raise UnauthorizedError("This account no longer exists.")
    if not user.is_active:
        raise PermissionDeniedError("This account has been deactivated.")
    return user


def require_roles(*roles: UserRole) -> Callable[[User], User]:
    """Dependency factory restricting a route to specific roles."""

    allowed: Iterable[str] = {str(role) for role in roles}

    def _dependency(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed:
            raise PermissionDeniedError(
                "Your role does not have access to this resource."
            )
        return current_user

    return _dependency


require_admin = require_roles(UserRole.ADMIN)
require_customer = require_roles(UserRole.CUSTOMER)
require_worker_role = require_roles(UserRole.WORKER)
require_staff = require_roles(UserRole.ADMIN, UserRole.WORKER)


def get_current_worker(
    current_user: User = Depends(require_worker_role),
    db: Session = Depends(get_db),
) -> Worker:
    """The Worker profile attached to the signed-in WORKER account."""
    worker = db.query(Worker).filter(Worker.user_id == current_user.id).one_or_none()
    if worker is None:
        raise PermissionDeniedError("No worker profile is linked to this account.")
    return worker
