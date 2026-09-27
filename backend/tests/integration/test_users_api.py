"""Reference tests for a feature module: authorization matrix + behaviour.

For every endpoint, test: anonymous, wrong role, other user's record,
own record / allowed role, and invalid input.
"""

from collections.abc import Callable
from typing import ClassVar

import pytest
from fastapi.testclient import TestClient

from app.models.user import Role, User
from tests.conftest import TEST_PASSWORD, csrf, login

API = "/api/v1/users"

UserFactory = Callable[..., User]


@pytest.fixture
def admin(make_user: UserFactory) -> User:
    return make_user(role=Role.ADMIN)


class TestListUsers:
    def test_anonymous_gets_401(self, client: TestClient) -> None:
        assert client.get(API).status_code == 401

    def test_regular_user_gets_403(self, client: TestClient, make_user: UserFactory) -> None:
        login(client, make_user())
        assert client.get(API).status_code == 403

    def test_admin_gets_paginated_list(
        self, client: TestClient, admin: User, make_user: UserFactory
    ) -> None:
        for _ in range(3):
            make_user()
        login(client, admin)

        body = client.get(API, params={"limit": 2}).json()

        assert body["total"] == 4
        assert len(body["items"]) == 2
        assert body["limit"] == 2

    def test_limit_is_capped(self, client: TestClient, admin: User) -> None:
        login(client, admin)
        assert client.get(API, params={"limit": 1000}).status_code == 422


class TestCreateUser:
    payload: ClassVar[dict[str, str]] = {
        "email": "new@example.com",
        "full_name": "New",
        "password": "long-enough-pass",
    }

    def test_admin_can_create(self, client: TestClient, admin: User) -> None:
        login(client, admin)
        response = client.post(API, json=self.payload, headers=csrf(client))
        assert response.status_code == 201
        assert response.json()["role"] == "user"

    def test_created_user_can_log_in(self, client: TestClient, admin: User) -> None:
        login(client, admin)
        client.post(API, json=self.payload, headers=csrf(client))
        response = client.post(
            "/api/v1/auth/login",
            json={"email": self.payload["email"], "password": self.payload["password"]},
        )
        assert response.status_code == 200

    def test_duplicate_email_conflicts(self, client: TestClient, admin: User) -> None:
        login(client, admin)
        client.post(API, json=self.payload, headers=csrf(client))
        duplicate = {**self.payload, "email": "NEW@example.com"}
        assert client.post(API, json=duplicate, headers=csrf(client)).status_code == 409

    def test_regular_user_cannot_create(self, client: TestClient, make_user: UserFactory) -> None:
        login(client, make_user())
        assert client.post(API, json=self.payload, headers=csrf(client)).status_code == 403


class TestGetUser:
    def test_user_can_read_self(self, client: TestClient, make_user: UserFactory) -> None:
        user = make_user()
        login(client, user)
        assert client.get(f"{API}/{user.id}").status_code == 200

    def test_user_cannot_read_others_and_gets_404(
        self, client: TestClient, make_user: UserFactory
    ) -> None:
        user, other = make_user(), make_user()
        login(client, user)
        # 404, not 403: don't confirm the id exists.
        assert client.get(f"{API}/{other.id}").status_code == 404

    def test_admin_can_read_anyone(
        self, client: TestClient, admin: User, make_user: UserFactory
    ) -> None:
        login(client, admin)
        assert client.get(f"{API}/{make_user().id}").status_code == 200

    def test_invalid_id_is_422(self, client: TestClient, admin: User) -> None:
        login(client, admin)
        assert client.get(f"{API}/not-a-uuid").status_code == 422


class TestUpdateUser:
    def test_user_can_rename_self(self, client: TestClient, make_user: UserFactory) -> None:
        user = make_user()
        login(client, user)
        response = client.patch(
            f"{API}/{user.id}", json={"full_name": "Renamed"}, headers=csrf(client)
        )
        assert response.status_code == 200
        assert response.json()["full_name"] == "Renamed"

    def test_user_cannot_promote_self(self, client: TestClient, make_user: UserFactory) -> None:
        user = make_user()
        login(client, user)
        response = client.patch(f"{API}/{user.id}", json={"role": "admin"}, headers=csrf(client))
        assert response.status_code == 403

    def test_unknown_fields_rejected(self, client: TestClient, make_user: UserFactory) -> None:
        user = make_user()
        login(client, user)
        response = client.patch(
            f"{API}/{user.id}", json={"token_version": 99}, headers=csrf(client)
        )
        assert response.status_code == 422

    def test_admin_cannot_demote_self(self, client: TestClient, admin: User) -> None:
        login(client, admin)
        response = client.patch(f"{API}/{admin.id}", json={"role": "user"}, headers=csrf(client))
        assert response.status_code == 422

    def test_deactivating_a_user_kills_their_session_immediately(
        self, db_client_pair: tuple[TestClient, TestClient], admin: User, make_user: UserFactory
    ) -> None:
        admin_client, user_client = db_client_pair
        target = make_user()
        login(user_client, target)
        login(admin_client, admin)

        response = admin_client.patch(
            f"{API}/{target.id}", json={"is_active": False}, headers=csrf(admin_client)
        )
        assert response.status_code == 200
        assert user_client.get("/api/v1/auth/me").status_code == 401
        assert (
            user_client.post(
                "/api/v1/auth/login", json={"email": target.email, "password": TEST_PASSWORD}
            ).status_code
            == 401
        )


@pytest.fixture
def db_client_pair(client: TestClient) -> tuple[TestClient, TestClient]:
    """Two browsers (separate cookie jars) against the same test database."""
    second = TestClient(client.app, base_url="https://testserver")
    return client, second
