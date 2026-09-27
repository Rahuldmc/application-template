"""Password hashing, JWT access tokens, and opaque refresh/CSRF tokens.

Pure functions only: no database or HTTP access, so all of it is unit-testable.
"""

import hashlib
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.utils.time import utcnow

_hasher = PasswordHasher()  # argon2id with library-recommended parameters

# Verified against when the user doesn't exist, so a login for an unknown
# email takes as long as one for a real account (no timing-based enumeration).
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(32))


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False


def password_needs_rehash(password_hash: str) -> bool:
    return _hasher.check_needs_rehash(password_hash)


def burn_password_check(password: str) -> None:
    verify_password(password, _DUMMY_HASH)


@dataclass(frozen=True)
class AccessTokenClaims:
    user_id: uuid.UUID
    role: str
    token_version: int


def create_access_token(user_id: uuid.UUID, role: str, token_version: int) -> tuple[str, datetime]:
    settings = get_settings()
    now = utcnow()
    expires_at = now + timedelta(minutes=settings.access_token_ttl_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "ver": token_version,
        "type": "access",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "nbf": now,
        "exp": expires_at,
        "jti": secrets.token_hex(16),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, expires_at


def decode_access_token(token: str) -> AccessTokenClaims:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],  # pinned: never trust the token's own "alg"
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            leeway=30,  # tolerate small clock drift between machines
            options={"require": ["sub", "exp", "iat", "type", "ver"]},
        )
        if payload["type"] != "access":
            raise AuthenticationError()
        return AccessTokenClaims(
            user_id=uuid.UUID(payload["sub"]),
            role=str(payload.get("role", "")),
            token_version=int(payload["ver"]),
        )
    except (jwt.PyJWTError, ValueError, KeyError) as exc:
        raise AuthenticationError() from exc


def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    """SHA-256 is right here (not argon2): refresh tokens are long random
    values, so they can't be brute-forced, and lookups must be fast."""
    return hashlib.sha256(token.encode()).hexdigest()
