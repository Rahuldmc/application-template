"""Generic repository with the CRUD helpers every table needs.

Subclass it per model (see app/repositories/users.py) and add
model-specific queries there. Repositories only talk to the database:
they `flush()` but never `commit()`. Services own the transaction.
"""

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from app.database.base import Base

MAX_PAGE_SIZE = 100


class BaseRepository[ModelT: Base]:
    model: type[ModelT]

    def __init__(self, session: Session) -> None:
        self.session = session

    def get(self, id_: uuid.UUID) -> ModelT | None:
        return self.session.get(self.model, id_)

    def get_by(self, **filters: Any) -> ModelT | None:
        return self.session.scalars(select(self.model).filter_by(**filters)).first()

    def list(
        self,
        *,
        offset: int = 0,
        limit: int = 50,
        query: Select[ModelT] | None = None,
    ) -> Sequence[ModelT]:
        stmt = query if query is not None else select(self.model)
        limit = max(1, min(limit, MAX_PAGE_SIZE))
        return self.session.scalars(stmt.offset(max(0, offset)).limit(limit)).all()

    def count(self, query: Select[ModelT] | None = None) -> int:
        stmt = query if query is not None else select(self.model)
        return self.session.scalar(select(func.count()).select_from(stmt.subquery())) or 0

    def add(self, instance: ModelT) -> ModelT:
        self.session.add(instance)
        self.session.flush()  # assigns defaults/ids and surfaces constraint errors early
        return instance

    def update(self, instance: ModelT, values: dict[str, Any]) -> ModelT:
        for field, value in values.items():
            if not hasattr(instance, field):
                raise AttributeError(f"{self.model.__name__} has no field {field!r}")
            setattr(instance, field, value)
        self.session.flush()
        return instance

    def delete(self, instance: ModelT) -> None:
        self.session.delete(instance)
        self.session.flush()
