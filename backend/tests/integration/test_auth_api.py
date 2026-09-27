from collections.abc import Callable

from fastapi.testclient import TestClient

from app.core.cookies import ACCESS_COOKIE, CSRF_COOKIE, REFRESH_COOKIE
from app.models.user import User
from tests.conftest import TEST_PASSWORD, csrf, login

API = "/api/v1/auth"


def _replay(client: TestClient, refresh_token: str, csrf_token: str) -> int:
    """Send a refresh request with a specific (possibly stolen) token.

    Failed refreshes clear every auth cookie, so both cookies are set again here.
    """
    client.cookies.clear()
    client.cookies.set(REFRESH_COOKIE, refresh_token, domain="testserver.local", path=API)
    client.cookies.set(CSRF_COOKIE, csrf_token, domain="testserver.local", path="/")
    return client.post(f"{API}/refresh", headers={"X-CSRF-Token": csrf_token}).status_code


class TestLogin:
    def test_success_sets_session_cookies(
        self, client: TestClient, make_user: Callable[..., User]
    ) -> None:
        user = make_user()
        response = login(client, user)

        assert response.json()["email"] == user.email
        assert "password_hash" not in response.json()
        set_cookie = response.headers.get_list("set-cookie")
        access = next(c for c in set_cookie if c.startswith(f"{ACCESS_COOKIE}="))
        refresh = next(c for c in set_cookie if c.startswith(f"{REFRESH_COOKIE}="))
        csrf_cookie = next(c for c in set_cookie if c.startswith(f"{CSRF_COOKIE}="))
        assert "HttpOnly" in access and "Secure" in access
        assert "HttpOnly" in refresh and f"Path={API}" in refresh
        assert "HttpOnly" not in csrf_cookie  # the frontend must be able to read it

    def test_wrong_password_and_unknown_email_look_identical(
        self, client: TestClient, make_user: Callable[..., User]
    ) -> None:
        user = make_user()
        wrong = client.post(f"{API}/login", json={"email": user.email, "password": "nope"})
        unknown = client.post(
            f"{API}/login", json={"email": "ghost@example.com", "password": "nope"}
        )
        assert wrong.status_code == unknown.status_code == 401
        assert wrong.json() == unknown.json()

    def test_account_locks_after_repeated_failures(
        self, client: TestClient, make_user: Callable[..., User]
    ) -> None:
        user = make_user()
        for _ in range(3):  # MAX_FAILED_LOGINS=3 in conftest
            client.post(f"{API}/login", json={"email": user.email, "password": "nope"})

        response = client.post(
            f"{API}/login", json={"email": user.email, "password": TEST_PASSWORD}
        )
        assert response.status_code == 401
        assert "Too many failed attempts" in response.json()["error"]["message"]

    def test_inactive_user_cannot_log_in(
        self, client: TestClient, make_user: Callable[..., User]
    ) -> None:
        user = make_user(is_active=False)
        response = client.post(
            f"{API}/login", json={"email": user.email, "password": TEST_PASSWORD}
        )
        assert response.status_code == 401

    def test_email_is_case_insensitive(
        self, client: TestClient, make_user: Callable[..., User]
    ) -> None:
        user = make_user(email="mixed@example.com")
        response = client.post(
            f"{API}/login", json={"email": "MIXED@Example.com", "password": TEST_PASSWORD}
        )
        assert response.status_code == 200
        assert response.json()["id"] == str(user.id)


class TestSession:
    def test_me_requires_login(self, client: TestClient) -> None:
        response = client.get(f"{API}/me")
        assert response.status_code == 401
        assert response.json()["error"]["code"] == "not_authenticated"

    def test_me_returns_current_user(
        self, client: TestClient, make_user: Callable[..., User]
    ) -> None:
        user = make_user()
        login(client, user)
        assert client.get(f"{API}/me").json()["id"] == str(user.id)

    def test_state_change_without_csrf_header_is_rejected(
        self, client: TestClient, make_user: Callable[..., User]
    ) -> None:
        login(client, make_user())
        response = client.post(f"{API}/logout")
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "csrf_failed"

    def test_logout_ends_session(self, client: TestClient, make_user: Callable[..., User]) -> None:
        login(client, make_user())
        old_refresh = client.cookies.get(REFRESH_COOKIE) or ""
        assert client.post(f"{API}/logout", headers=csrf(client)).status_code == 204

        assert client.get(f"{API}/me").status_code == 401
        # The refresh token is revoked server-side, not just deleted from the browser.
        assert _replay(client, old_refresh, "any-csrf") == 401


class TestRefresh:
    def test_refresh_rotates_the_token(
        self, client: TestClient, make_user: Callable[..., User]
    ) -> None:
        login(client, make_user())
        first = client.cookies.get(REFRESH_COOKIE)

        response = client.post(f"{API}/refresh", headers=csrf(client))

        assert response.status_code == 200
        assert client.cookies.get(REFRESH_COOKIE) not in (None, first)

    def test_reusing_an_old_refresh_token_revokes_the_whole_session(
        self, client: TestClient, make_user: Callable[..., User]
    ) -> None:
        login(client, make_user())
        stolen = client.cookies.get(REFRESH_COOKIE) or ""
        client.post(f"{API}/refresh", headers=csrf(client))
        current = client.cookies.get(REFRESH_COOKIE) or ""

        assert _replay(client, stolen, "any-csrf") == 401
        # The legitimate user's newer token is dead too: the attacker gets nothing.
        assert _replay(client, current, "any-csrf") == 401

    def test_refresh_without_cookie_fails(self, client: TestClient) -> None:
        client.cookies.set(CSRF_COOKIE, "x", domain="testserver.local", path="/")
        response = client.post(f"{API}/refresh", headers={"X-CSRF-Token": "x"})
        assert response.status_code == 401


class TestChangePassword:
    def test_change_password_logs_out_other_sessions(
        self, client: TestClient, make_user: Callable[..., User]
    ) -> None:
        user = make_user()
        login(client, user)
        other_device_access = client.cookies.get(ACCESS_COOKIE) or ""

        response = client.post(
            f"{API}/change-password",
            json={"current_password": TEST_PASSWORD, "new_password": "a-brand-new-password"},
            headers=csrf(client),
        )
        assert response.status_code == 200
        assert client.get(f"{API}/me").status_code == 200  # this device got a new session

        client.cookies.delete(ACCESS_COOKIE)
        client.cookies.set(ACCESS_COOKIE, other_device_access, domain="testserver.local", path="/")
        assert client.get(f"{API}/me").status_code == 401

    def test_wrong_current_password_is_rejected(
        self, client: TestClient, make_user: Callable[..., User]
    ) -> None:
        login(client, make_user())
        response = client.post(
            f"{API}/change-password",
            json={"current_password": "wrong", "new_password": "a-brand-new-password"},
            headers=csrf(client),
        )
        assert response.status_code == 401


class TestHardening:
    def test_security_headers_present(self, client: TestClient) -> None:
        response = client.get("/api/v1/health")
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        assert response.headers["X-Frame-Options"] == "DENY"
        assert "default-src 'none'" in response.headers["Content-Security-Policy"]
        assert response.headers["X-Request-ID"]

    def test_readiness_checks_database(self, client: TestClient) -> None:
        assert client.get("/api/v1/health/ready").json() == {"status": "ok"}

    def test_validation_errors_do_not_echo_input(self, client: TestClient) -> None:
        response = client.post(f"{API}/login", json={"email": "bad", "password": "secret-value"})
        assert response.status_code == 422
        assert "secret-value" not in response.text

    def test_malicious_request_id_is_replaced(self, client: TestClient) -> None:
        response = client.get("/api/v1/health", headers={"X-Request-ID": "evil\nlog-line"})
        assert "\n" not in response.headers["X-Request-ID"]
