"""User endpoints: the reference router. Copy this shape for new modules.

Routers stay thin: declare inputs/outputs, apply auth dependencies, call
the service, return a schema. No queries and no business rules here.
"""

import uuid

from fastapi import APIRouter, Query, status

from app.core.dependencies import AdminUser, CurrentUser, DbSession
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserRead, UserUpdate
from app.services.users import UserService

router = APIRouter(prefix="/users", tags=["users"])


@router.get("")
def list_users(
    _: AdminUser,
    db: DbSession,
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
) -> Page[UserRead]:
    return UserService(db).list_users(offset=offset, limit=limit)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_user(body: UserCreate, _: AdminUser, db: DbSession) -> UserRead:
    return UserRead.model_validate(UserService(db).create_user(body))


@router.get("/{user_id}")
def get_user(user_id: uuid.UUID, actor: CurrentUser, db: DbSession) -> UserRead:
    return UserRead.model_validate(UserService(db).get_user(actor, user_id))


@router.patch("/{user_id}")
def update_user(
    user_id: uuid.UUID, body: UserUpdate, actor: CurrentUser, db: DbSession
) -> UserRead:
    return UserRead.model_validate(UserService(db).update_user(actor, user_id, body))
