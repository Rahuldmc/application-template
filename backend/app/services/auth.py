"""Authentication: login, token refresh with rotation, logout, password change.

Services hold business logic and own the transaction (they call commit).
They know nothing about HTTP: routers translate results into cookies.
"""

import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    burn_password_check,
    create_access_token,
    generate_csrf_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    password_needs_rehash,
    verify_password,
)
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories.refresh_tokens import RefreshTokenRepository
from app.repositories.users import UserRepository
from app.utils.time import utcnow

logger = logging.getLogger(__name__)

INVALID_CREDENTIALS = "Invalid email or password"
ACCOUNT_LOCKED = "Too many failed attempts. Try again later."
SESSION_EXPIRED = "Session expired. Please log in again."


@dataclass(frozen=True)
class ClientInfo:
    user_agent: str | None
    ip_address: str | None


@dataclass(frozen=True)
class IssuedSession:
    user: User
    access_token: str
    access_expires: datetime
    refresh_token: str
    refresh_expires: datetime
    csrf_token: str


class AuthService:
    def __init__(self, db: Session) -> None:
        self.db = db
        self.users = UserRepository(db)
        self.tokens = RefreshTokenRepository(db)
        self.settings = get_settings()

    def login(self, email: str, password: str, client: ClientInfo) -> IssuedSession:
        user = self.users.get_by_email(email)
        if user is None:
            burn_password_check(password)  # same timing as a real account
            raise AuthenticationError(INVALID_CREDENTIALS)

        now = utcnow()
        if user.locked_until and user.locked_until > now:
            raise AuthenticationError(ACCOUNT_LOCKED)

        if not verify_password(password, user.password_hash):
            self._record_failed_login(user)
            raise AuthenticationError(INVALID_CREDENTIALS)

        if not user.is_active:
            raise AuthenticationError(INVALID_CREDENTIALS)

        user.failed_login_attempts = 0
        user.locked_until = None
        if password_needs_rehash(user.password_hash):
            user.password_hash = hash_password(password)

        session = self._issue_session(user, family_id=uuid.uuid4(), client=client)
        self.db.commit()
        logger.info("User %s logged in", user.id)
        return session

    def refresh(self, raw_refresh_token: str | None, client: ClientInfo) -> IssuedSession:
        if not raw_refresh_token:
            raise AuthenticationError(SESSION_EXPIRED)

        stored = self.tokens.get_by_hash_for_update(hash_token(raw_refresh_token))
        if stored is None:
            raise AuthenticationError(SESSION_EXPIRED)

        if stored.used_at is not None or stored.revoked_at is not None:
            # A rotated-out token was presented again: it was copied by someone.
            # Kill every session in this login's family.
            self.tokens.revoke_family(stored.family_id)
            self.db.commit()
            logger.warning("Refresh token reuse detected for user %s", stored.user_id)
            raise AuthenticationError(SESSION_EXPIRED)

        user = self.users.get(stored.user_id)
        if stored.expires_at <= utcnow() or user is None or not user.is_active:
            self.tokens.revoke_family(stored.family_id)
            self.db.commit()
            raise AuthenticationError(SESSION_EXPIRED)

        stored.used_at = utcnow()
        session = self._issue_session(user, family_id=stored.family_id, client=client)
        self.db.commit()
        return session

    def logout(self, raw_refresh_token: str | None) -> None:
        if not raw_refresh_token:
            return
        stored = self.tokens.get_by_hash_for_update(hash_token(raw_refresh_token))
        if stored is not None:
            self.tokens.revoke_family(stored.family_id)
            self.db.commit()

    def change_password(
        self, user: User, current_password: str, new_password: str, client: ClientInfo
    ) -> IssuedSession:
        if not verify_password(current_password, user.password_hash):
            raise AuthenticationError("Current password is incorrect")

        user.password_hash = hash_password(new_password)
        # Log out every other device: old access tokens fail the version
        # check, old refresh tokens are revoked.
        user.token_version += 1
        self.tokens.revoke_all_for_user(user.id)
        session = self._issue_session(user, family_id=uuid.uuid4(), client=client)
        self.db.commit()
        logger.info("User %s changed password", user.id)
        return session

    def _record_failed_login(self, user: User) -> None:
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= self.settings.max_failed_logins:
            user.locked_until = utcnow() + timedelta(minutes=self.settings.lockout_minutes)
            user.failed_login_attempts = 0
            logger.warning("User %s locked after repeated failed logins", user.id)
        self.db.commit()

    def _issue_session(
        self, user: User, *, family_id: uuid.UUID, client: ClientInfo
    ) -> IssuedSession:
        access_token, access_expires = create_access_token(user.id, user.role, user.token_version)
        raw_refresh = generate_refresh_token()
        refresh_expires = utcnow() + timedelta(days=self.settings.refresh_token_ttl_days)
        self.tokens.add(
            RefreshToken(
                user_id=user.id,
                family_id=family_id,
                token_hash=hash_token(raw_refresh),
                expires_at=refresh_expires,
                user_agent=(client.user_agent or "")[:500] or None,
                ip_address=client.ip_address,
            )
        )
        return IssuedSession(
            user=user,
            access_token=access_token,
            access_expires=access_expires,
            refresh_token=raw_refresh,
            refresh_expires=refresh_expires,
            csrf_token=generate_csrf_token(),
        )
