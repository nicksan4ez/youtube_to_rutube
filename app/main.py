from __future__ import annotations

from contextlib import asynccontextmanager
from fastapi import FastAPI

from app import __version__
from app.config import get_settings
from app.db.base import Base, get_engine
from app.routes import admin, webhook
from app.utils.logging import configure_logging, get_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    configure_logging(settings.log_level)
    Base.metadata.create_all(bind=get_engine())
    logger = get_logger("startup")
    logger.info("application_started", version=settings.application_version)
    try:
        yield
    finally:
        logger.info("application_stopping")


def create_app() -> FastAPI:
    settings = get_settings()
    fastapi_app = FastAPI(
        title="YouTube to RuTube",
        version=settings.application_version or __version__,
        lifespan=lifespan,
    )
    fastapi_app.include_router(
        webhook.router,
        prefix="",
    )
    fastapi_app.include_router(admin.router, prefix="/api")
    return fastapi_app


app = create_app()
