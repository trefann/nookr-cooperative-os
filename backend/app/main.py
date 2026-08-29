"""Nookr API.

An operating system for labour cooperatives: demand understanding, fair
allocation, workforce planning and welfare, over one PostgreSQL-backed API.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import Any

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.errors import register_exception_handlers
from app.db.session import engine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-7s %(name)s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("nookr")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    for warning in settings.startup_warnings():
        logger.warning("CONFIG: %s", warning)
    if not settings.llm_enabled:
        logger.info(
            "AI_API_KEY is not set. Service understanding will use the built-in "
            "rule engine, which is fully functional."
        )
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("Database reachable: %s", settings.database_url.split("@")[-1])
    except Exception as exc:  # noqa: BLE001 - surfaced, not swallowed
        logger.error(
            "Database is not reachable (%s). Run the migration and seed steps "
            "in the README before using the API.",
            exc,
        )
    yield


app = FastAPI(
    title="Nookr API",
    description=__doc__,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

api = APIRouter(prefix="/api")

from app.api.routes import (  # noqa: E402  - routers import app.core.config
    auth,
    bookings,
    catalogue,
    customer,
    demo,
    intelligence,
    transactions,
    workers,
)

api.include_router(auth.router)
api.include_router(catalogue.router)
api.include_router(workers.router)
api.include_router(bookings.router)
api.include_router(customer.router)
api.include_router(intelligence.router)
api.include_router(transactions.router)
api.include_router(demo.router)


@api.get("/health", tags=["meta"])
def health() -> dict[str, Any]:
    """Liveness plus an honest report of how the system is configured."""
    database_ok = True
    database_error: str | None = None
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except Exception as exc:  # noqa: BLE001
        database_ok = False
        database_error = str(exc)

    return {
        "status": "ok" if database_ok else "degraded",
        "app": settings.app_name,
        "version": app.version,
        "environment": settings.environment,
        "database": {
            "connected": database_ok,
            "engine": "postgresql" if not settings.is_sqlite else "sqlite",
            "error": database_error,
        },
        "ai": {
            "llm_configured": settings.llm_enabled,
            "service_understanding": "llm_with_rule_fallback"
            if settings.llm_enabled
            else "rule_based",
            "matching": "weighted_explainable_scoring",
            "forecasting": "weighted_moving_average_with_damped_trend",
        },
        "warnings": settings.startup_warnings(),
    }


app.include_router(api)


@app.get("/", tags=["meta"])
def root() -> dict[str, str]:
    return {
        "name": settings.app_name,
        "tagline": "AI-powered intelligence for cooperative workforce management",
        "docs": "/docs",
        "health": "/api/health",
    }
