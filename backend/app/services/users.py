"""User management. This is the reference module: copy its shape for new features.

Pattern:
- The service receives the acting user (`actor`) and enforces ownership
  and role rules itself. Router-level role checks are a first gate only.
- Records the actor may not see raise NotFoundError, not PermissionDenied,
  so the API doesn't reveal which ids exist.
- The service commits; repositories only flush.
"""

import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import (
    BusinessRuleError,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)
from app.core.security import hash_password
from app.models.user import Role, User
from app.repositories.refresh_tokens import RefreshTokenRepository
from app.repositories.users import UserRepository
from app.schemas.common import Page
from app.schemas.user import UserCreate, UserRead, UserUpdate


class UserService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.tokens = RefreshTokenRepository(db)

    def list_users(self, *, offset: int, limit: int) -> Page[UserRead]:
        items, total = self.users.list_ordered(offset=offset, limit=limit)
        return Page[UserRead](
            items=[UserRead.model_validate(u) for u in items],
            total=total,
            offset=offset,
            limit=limit,
        )

    def get_user(self, actor: User, user_id: uuid.UUID) -> User:
        if actor.role != Role.ADMIN and actor.id != user_id:
            raise NotFoundError("User not found")
        user = self.users.get(user_id)
        if user is None:
            raise NotFoundError("User not found")
        return user

    def create_user(self, data: UserCreate) -> User:
        if self.users.get_by_email(data.email) is not None:
            raise ConflictError("A user with this email already exists")
        user = self.users.add(
            User(
                email=data.email,
                full_name=data.full_name,
                password_hash=hash_password(data.password),
                role=data.role,
            )
        )
        self.db.commit()
        return user

    def update_user(self, actor: User, user_id: uuid.UUID, data: UserUpdate) -> User:
        user = self.get_user(actor, user_id)
        changes = data.model_dump(exclude_unset=True)

        is_admin = actor.role == Role.ADMIN
        if not is_admin and {"role", "is_active"} & changes.keys():
            raise PermissionDeniedError("Only admins can change roles or account status")
        if is_admin and actor.id == user.id:
            demoting = changes.get("role", Role.ADMIN) != Role.ADMIN
            if demoting or changes.get("is_active") is False:
                # Prevents an admin from locking everyone out by accident.
                raise BusinessRuleError("Admins cannot deactivate or demote themselves")

        access_changed = ("role" in changes and changes["role"] != user.role) or (
            changes.get("is_active") is False and user.is_active
        )
        self.users.update(user, changes)
        if access_changed:
            # Force re-login so the new role/status applies everywhere immediately.
            user.token_version += 1
            self.tokens.revoke_all_for_user(user.id)
        self.db.commit()
        return user
