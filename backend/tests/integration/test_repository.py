from collections.abc import Callable

import pytest
from sqlalchemy.orm import Session

from app.database.repository import MAX_PAGE_SIZE
from app.models.user import User
from app.repositories.users import UserRepository


def test_get_by_email_is_case_insensitive(db: Session, make_user: Callable[..., User]) -> None:
    user = make_user(email="case@example.com")
    assert UserRepository(db).get_by_email("CASE@example.com") == user


def test_list_clamps_limit_and_count_matches(db: Session, make_user: Callable[..., User]) -> None:
    for _ in range(3):
        make_user()
    repo = UserRepository(db)
    assert len(repo.list(limit=MAX_PAGE_SIZE * 10)) == 3
    assert len(repo.list(limit=0)) == 1  # clamped up to 1
    assert repo.count() == 3


def test_update_rejects_unknown_field(db: Session, make_user: Callable[..., User]) -> None:
    with pytest.raises(AttributeError):
        UserRepository(db).update(make_user(), {"not_a_column": 1})


def test_delete_removes_row(db: Session, make_user: Callable[..., User]) -> None:
    repo = UserRepository(db)
    user = make_user()
    repo.delete(user)
    assert repo.get(user.id) is None
