"""Auth cookie names and helpers. The only place cookies are set or cleared.

- access_token:  httpOnly JWT, sent to every API call.
- refresh_token: httpOnly, only sent to the auth endpoints (narrow path).
- csrf_token:    readable by JS; the frontend echoes it in the X-CSRF-Token
                 header (double-submit pattern, checked in middleware).
"""

from datetime import datetime

from fastapi import Response

from app.core.config import get_settings

ACCESS_COOKIE = "access_token"
REFRESH_COOKIE = "refresh_token"
CSRF_COOKIE = "csrf_token"
CSRF_HEADER = "X-CSRF-Token"


def _refresh_path() -> str:
    return f"{get_settings().api_prefix}/auth"


def _set(
    response: Response, name: str, value: str, *, expires: datetime, path: str, httponly: bool
) -> None:
    settings = get_settings()
    response.set_cookie(
        name,
        value,
        expires=expires,
        path=path,
        httponly=httponly,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
    )


def _delete(response: Response, name: str, *, path: str, httponly: bool) -> None:
    settings = get_settings()
    response.delete_cookie(
        name,
        path=path,
        httponly=httponly,
        secure=settings.cookie_secure,
        samesite=settings.cookie_samesite,
        domain=settings.cookie_domain,
    )


def set_auth_cookies(
    response: Response,
    *,
    access_token: str,
    access_expires: datetime,
    refresh_token: str,
    refresh_expires: datetime,
    csrf_token: str,
) -> None:
    _set(response, ACCESS_COOKIE, access_token, expires=access_expires, path="/", httponly=True)
    _set(
        response,
        REFRESH_COOKIE,
        refresh_token,
        expires=refresh_expires,
        path=_refresh_path(),
        httponly=True,
    )
    _set(response, CSRF_COOKIE, csrf_token, expires=refresh_expires, path="/", httponly=False)


def clear_auth_cookies(response: Response) -> None:
    _delete(response, ACCESS_COOKIE, path="/", httponly=True)
    _delete(response, REFRESH_COOKIE, path=_refresh_path(), httponly=True)
    _delete(response, CSRF_COOKIE, path="/", httponly=False)
