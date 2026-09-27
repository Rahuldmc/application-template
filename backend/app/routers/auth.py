"""Auth endpoints. Thin: validate input, call AuthService, set cookies."""

from fastapi import APIRouter, Request, Response, status
from fastapi.responses import JSONResponse

from app.core.cookies import REFRESH_COOKIE, clear_auth_cookies, set_auth_cookies
from app.core.dependencies import CurrentUser, DbSession
from app.core.exceptions import AuthenticationError, error_body
from app.schemas.auth import ChangePasswordRequest, LoginRequest
from app.schemas.user import UserRead
from app.services.auth import AuthService, ClientInfo, IssuedSession

router = APIRouter(prefix="/auth", tags=["auth"])


def _client(request: Request) -> ClientInfo:
    return ClientInfo(
        user_agent=request.headers.get("user-agent"),
        ip_address=request.client.host if request.client else None,
    )


def _apply(response: Response, session: IssuedSession) -> UserRead:
    set_auth_cookies(
        response,
        access_token=session.access_token,
        access_expires=session.access_expires,
        refresh_token=session.refresh_token,
        refresh_expires=session.refresh_expires,
        csrf_token=session.csrf_token,
    )
    return UserRead.model_validate(session.user)


@router.post("/login")
def login(body: LoginRequest, request: Request, response: Response, db: DbSession) -> UserRead:
    session = AuthService(db).login(body.email, body.password, _client(request))
    return _apply(response, session)


@router.post("/refresh", response_model=UserRead)
def refresh(request: Request, response: Response, db: DbSession) -> UserRead | JSONResponse:
    try:
        session = AuthService(db).refresh(request.cookies.get(REFRESH_COOKIE), _client(request))
    except AuthenticationError as exc:
        # Clear the stale cookies so the browser stops retrying with them.
        failed = JSONResponse(
            error_body(exc.code, exc.message), status_code=status.HTTP_401_UNAUTHORIZED
        )
        clear_auth_cookies(failed)
        return failed
    return _apply(response, session)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(request: Request, response: Response, db: DbSession) -> None:
    AuthService(db).logout(request.cookies.get(REFRESH_COOKIE))
    clear_auth_cookies(response)


@router.get("/me")
def me(user: CurrentUser) -> UserRead:
    return UserRead.model_validate(user)


@router.post("/change-password")
def change_password(
    body: ChangePasswordRequest,
    request: Request,
    response: Response,
    user: CurrentUser,
    db: DbSession,
) -> UserRead:
    session = AuthService(db).change_password(
        user, body.current_password, body.new_password, _client(request)
    )
    return _apply(response, session)
