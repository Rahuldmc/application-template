"""Import every model here so Alembic autogenerate can see all tables."""

from app.models.refresh_token import RefreshToken
from app.models.user import Role, User

__all__ = ["RefreshToken", "Role", "User"]
