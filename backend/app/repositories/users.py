from sqlalchemy import select

from app.database.repository import BaseRepository
from app.models.user import User
from app.utils.text import normalize_email


class UserRepository(BaseRepository[User]):
    model = User

    def get_by_email(self, email: str) -> User | None:
        return self.session.scalars(
            select(User).where(User.email == normalize_email(email))
        ).first()

    def list_ordered(self, *, offset: int, limit: int) -> tuple[list[User], int]:
        query = select(User).order_by(User.created_at, User.id)
        return list(self.list(offset=offset, limit=limit, query=query)), self.count()
