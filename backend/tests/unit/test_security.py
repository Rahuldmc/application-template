import uuid
from datetime import timedelta

import jwt
import pytest

from app.core.config import get_settings
from app.core.exceptions import AuthenticationError
from app.core.security import (
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_token,
    password_needs_rehash,
    verify_password,
)
from app.utils.time import utcnow


class TestPasswords:
    def test_hash_is_not_plaintext_and_verifies(self) -> None:
        hashed = hash_password("a-long-password")
        assert hashed != "a-long-password"
        assert hashed.startswith("$argon2id$")
        assert verify_password("a-long-password", hashed)

    def test_wrong_password_fails(self) -> None:
        assert not verify_password("wrong", hash_password("a-long-password"))

    def test_garbage_hash_fails_without_raising(self) -> None:
        assert not verify_password("anything", "not-a-hash")

    def test_same_password_hashes_differently(self) -> None:
        assert hash_password("same") != hash_password("same")  # random salt

    def test_fresh_hash_does_not_need_rehash(self) -> None:
        assert not password_needs_rehash(hash_password("a-long-password"))


def _payload(**overrides: object) -> dict[str, object]:
    settings = get_settings()
    now = utcnow()
    payload: dict[str, object] = {
        "sub": str(uuid.uuid4()),
        "role": "user",
        "ver": 0,
        "type": "access",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    payload.update(overrides)
    return payload


def _encode(payload: dict[str, object], key: str | None = None, alg: str = "HS256") -> str:
    return jwt.encode(payload, key or get_settings().jwt_secret_key, algorithm=alg)


class TestAccessTokens:
    def test_round_trip(self) -> None:
        user_id = uuid.uuid4()
        token, expires_at = create_access_token(user_id, "admin", 3)
        claims = decode_access_token(token)
        assert claims.user_id == user_id
        assert claims.role == "admin"
        assert claims.token_version == 3
        assert expires_at > utcnow()

    def test_expired_token_rejected(self) -> None:
        past = utcnow() - timedelta(hours=1)
        token = _encode(_payload(iat=past, exp=past + timedelta(minutes=1)))
        with pytest.raises(AuthenticationError):
            decode_access_token(token)

    def test_wrong_signing_key_rejected(self) -> None:
        with pytest.raises(AuthenticationError):
            decode_access_token(_encode(_payload(), key="x" * 64))

    def test_alg_none_rejected(self) -> None:
        token = jwt.encode(_payload(), key=None, algorithm="none")
        with pytest.raises(AuthenticationError):
            decode_access_token(token)

    def test_wrong_audience_rejected(self) -> None:
        with pytest.raises(AuthenticationError):
            decode_access_token(_encode(_payload(aud="another-app")))

    def test_non_access_token_type_rejected(self) -> None:
        with pytest.raises(AuthenticationError):
            decode_access_token(_encode(_payload(type="refresh")))

    def test_missing_version_rejected(self) -> None:
        payload = _payload()
        del payload["ver"]
        with pytest.raises(AuthenticationError):
            decode_access_token(_encode(payload))

    def test_malformed_token_rejected(self) -> None:
        with pytest.raises(AuthenticationError):
            decode_access_token("not.a.jwt")


class TestOpaqueTokens:
    def test_refresh_tokens_are_unique_and_long(self) -> None:
        tokens = {generate_refresh_token() for _ in range(100)}
        assert len(tokens) == 100
        assert all(len(t) >= 64 for t in tokens)

    def test_hash_token_is_stable_sha256(self) -> None:
        assert hash_token("abc") == hash_token("abc")
        assert len(hash_token("abc")) == 64
        assert hash_token("abc") != hash_token("abd")
