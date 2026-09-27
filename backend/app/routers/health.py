from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.core.dependencies import DbSession

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def liveness() -> dict[str, str]:
    """The process is up. Used by process managers / container restarts."""
    return {"status": "ok"}


@router.get("/ready", response_model=None)
def readiness(db: DbSession) -> dict[str, str] | JSONResponse:
    """The app can serve traffic: the database is reachable."""
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse({"status": "unavailable"}, status_code=503)
    return {"status": "ok"}
