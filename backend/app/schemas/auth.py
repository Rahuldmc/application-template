from pydantic import BaseModel, ConfigDict, Field

from app.schemas.common import Email, Password


class LoginRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    email: Email
    # No min length on login: policy is enforced when a password is set.
    password: str = Field(min_length=1, max_length=128)


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    current_password: str = Field(min_length=1, max_length=128)
    new_password: Password
