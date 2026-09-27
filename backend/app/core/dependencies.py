"""FastAPI dependencies shared by all routers: DB session, current user, roles.

Usage in a router:

    @router.get("/things")
    def list_things(db: DbSession, user: CurrentUser) -> ...

    @router.delete("/things/{id}", dependencies=[Depends(require_roles(Role.ADMIN))])
"""

from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.core.cookies import ACCESS_COOKIE
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.core.security import decode_access_token
from app.database.session import SessionLocal
from app.models.user import Role, User
from app.repositories.users import UserRepository


def get_db() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


DbSession = Annotated[Session, Depends(get_db)]


def get_current_user(request: Request, db: DbSession) -> User:
    token = request.cookies.get(ACCESS_COOKIE)
    if not token:
        raise AuthenticationError()
    claims = decode_access_token(token)

    # Load the user on every request so deactivation, role changes and
    # "log out everywhere" take effect immediately, not at token expiry.
    user = UserRepository(db).get(claims.user_id)
    if user is None or not user.is_active or user.token_version != claims.token_version:
        raise AuthenticationError()
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_roles(*roles: Role) -> Callable[[User], User]:
    allowed = {str(role) for role in roles}

    def _check(user: CurrentUser) -> User:
        if user.role not in allowed:
            raise PermissionDeniedError()
        return user

    return _check


AdminUser = Annotated[User, Depends(require_roles(Role.ADMIN))]
