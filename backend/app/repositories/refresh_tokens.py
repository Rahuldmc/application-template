import uuid

from sqlalchemy import select, update

from app.database.repository import BaseRepository
from app.models.refresh_token import RefreshToken
from app.utils.time import utcnow


class RefreshTokenRepository(BaseRepository[RefreshToken]):
    model = RefreshToken

    def get_by_hash_for_update(self, token_hash: str) -> RefreshToken | None:
        # Row lock: two concurrent refreshes with the same token can't both succeed.
        return self.session.scalars(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash).with_for_update()
        ).first()

    def revoke_family(self, family_id: uuid.UUID) -> None:
        self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )

    def revoke_all_for_user(self, user_id: uuid.UUID) -> None:
        self.session.execute(
            update(RefreshToken)
            .where(RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None))
            .values(revoked_at=utcnow())
        )
