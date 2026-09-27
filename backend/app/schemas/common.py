from typing import Annotated, Any

from pydantic import AfterValidator, BaseModel, Field

from app.utils.text import normalize_email

_MAX_EMAIL_LENGTH = 320


def _validate_email(value: str) -> str:
    value = normalize_email(value)
    local, sep, domain = value.partition("@")
    # Deliberately permissive: LAN deployments use internal domains like
    # `user@client.local`, which strict validators reject.
    if (
        not sep
        or not local
        or not domain
        or "@" in domain
        or any(ch.isspace() for ch in value)
        or len(value) > _MAX_EMAIL_LENGTH
    ):
        raise ValueError("Enter a valid email address")
    return value


Email = Annotated[str, AfterValidator(_validate_email)]

# Min length is the main defence; max length stops huge inputs from
# making argon2 hashing an easy denial-of-service.
Password = Annotated[str, Field(min_length=12, max_length=128)]


class Page[ItemT](BaseModel):
    items: list[ItemT]
    total: int
    offset: int
    limit: int


class ErrorDetail(BaseModel):
    code: str
    message: str
    details: Any | None = None


class ErrorResponse(BaseModel):
    error: ErrorDetail
