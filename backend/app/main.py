"""FastAPI entry point.

Run locally:  uv run uvicorn app.main:app --reload
"""

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import register_middleware
from app.routers import api_router


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)

    docs = settings.enable_docs
    app = FastAPI(
        title=settings.app_name,
        docs_url="/docs" if docs else None,
        redoc_url=None,
        openapi_url="/openapi.json" if docs else None,
    )
    register_middleware(app, settings)
    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.api_prefix)
    return app


app = create_app()
