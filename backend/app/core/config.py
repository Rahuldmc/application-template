"""Application settings, loaded from environment variables (and backend/.env).

All configuration lives here. Never read os.environ elsewhere in the app.
"""

from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_INSECURE_SECRETS = {"", "change-me", "change-me-generate-a-long-random-value"}


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    environment: Literal["development", "test", "production"] = "development"
    app_name: str = "application-template"
    api_prefix: str = "/api/v1"

    database_url: str = "postgresql+psycopg://app:app@localhost:5432/app"
    # Used only by the test suite, which wipes it. Must end in "_test".
    test_database_url: str | None = None
    database_pool_size: int = 5
    database_max_overflow: int = 10

    jwt_secret_key: str = Field(default="change-me", repr=False)
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_issuer: str = "application-template"
    jwt_audience: str = "application-template"
    access_token_ttl_minutes: int = 15
    refresh_token_ttl_days: int = 7

    cookie_secure: bool = True
    cookie_samesite: Literal["lax", "strict"] = "lax"
    cookie_domain: str | None = None

    cors_origins: Annotated[list[str], NoDecode] = []

    max_failed_logins: int = 5
    lockout_minutes: int = 15

    enable_docs: bool = True
    log_level: str = "INFO"

    @field_validator("cors_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("cookie_domain", mode="before")
    @classmethod
    def _empty_domain_is_none(cls, value: object) -> object:
        return value or None

    @model_validator(mode="after")
    def _refuse_insecure_production(self) -> "Settings":
        if self.environment == "production":
            if self.jwt_secret_key in _INSECURE_SECRETS or len(self.jwt_secret_key) < 32:
                raise ValueError("JWT_SECRET_KEY must be a random value of 32+ characters")
            if not self.cookie_secure:
                raise ValueError("COOKIE_SECURE must be true in production")
        return self

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
