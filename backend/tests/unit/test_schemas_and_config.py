import pytest
from pydantic import ValidationError

from app.core.config import Settings
from app.schemas.auth import LoginRequest
from app.schemas.user import UserCreate, UserUpdate


class TestEmail:
    @pytest.mark.parametrize(
        "email", ["a@example.com", "admin@client.local", "first.last+tag@sub.example.org"]
    )
    def test_accepts_valid_including_lan_domains(self, email: str) -> None:
        assert LoginRequest(email=email, password="x").email == email

    def test_normalizes_case_and_whitespace(self) -> None:
        assert LoginRequest(email="  Admin@Example.COM ", password="x").email == "admin@example.com"

    @pytest.mark.parametrize("email", ["", "no-at-sign", "@example.com", "a@", "a@b@c", "a b@c.d"])
    def test_rejects_invalid(self, email: str) -> None:
        with pytest.raises(ValidationError):
            LoginRequest(email=email, password="x")


class TestUserSchemas:
    def test_password_minimum_length(self) -> None:
        with pytest.raises(ValidationError):
            UserCreate(email="a@b.c", full_name="A", password="short")

    def test_password_maximum_length(self) -> None:
        with pytest.raises(ValidationError):
            UserCreate(email="a@b.c", full_name="A", password="x" * 129)

    def test_update_rejects_unknown_fields(self) -> None:
        with pytest.raises(ValidationError):
            UserUpdate.model_validate({"password_hash": "x"})

    def test_update_tracks_only_sent_fields(self) -> None:
        assert UserUpdate(full_name="New").model_dump(exclude_unset=True) == {"full_name": "New"}


class TestSettings:
    def test_production_refuses_default_secret(self) -> None:
        with pytest.raises(ValidationError, match="JWT_SECRET_KEY"):
            Settings(environment="production", jwt_secret_key="change-me", _env_file=None)

    def test_production_refuses_insecure_cookies(self) -> None:
        with pytest.raises(ValidationError, match="COOKIE_SECURE"):
            Settings(
                environment="production",
                jwt_secret_key="k" * 64,
                cookie_secure=False,
                _env_file=None,
            )

    def test_cors_origins_parsed_from_comma_string(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("CORS_ORIGINS", "https://a.com, https://b.com")
        settings = Settings(_env_file=None)
        assert settings.cors_origins == ["https://a.com", "https://b.com"]
