"""
backend/main.py — FastAPI Application Entry Point
===================================================
Registers all module routers under /api/v1 and configures
CORS, lifespan, and global exception handlers.

Source of truth: ARCHITECTURE.md §2.0 (API Layer Convention)
"""
from __future__ import annotations

import logging
import sys
import os
import time

sys.path.insert(0, os.path.dirname(__file__))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from config.settings.base import (
    ALLOWED_ORIGINS,
    API_V1_PREFIX,
    PROJECT_NAME,
    PROJECT_VERSION,
    DEBUG,
)

# ── Module Routers ─────────────────────────────────────────────────────────────
from modules.tenant_config.api.views import router as tenant_router
from modules.auth.api.views import router as auth_router
from modules.students.api.views import router as students_router
from modules.attendance.api.views import router as attendance_router
from modules.fees.api.views import router as fees_router
from modules.ai_analytics.api.views import router as ai_analytics_router
from modules.notification_engine.api.views import router as notification_router
from modules.parent.api.views import router as parent_router
from modules.student.api.views import router as student_router

logger = logging.getLogger(__name__)


# ── Lifespan ───────────────────────────────────────────────────────────────────
from contextlib import asynccontextmanager
from modules.dummy_data_engine.infrastructure.db.session import create_all_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: ensure DB tables exist. Shutdown: log graceful stop."""
    logger.info("=== Smart Academic ERP API starting up ===")
    create_all_tables()
    logger.info("DB tables verified.")
    yield
    logger.info("=== Smart Academic ERP API shutting down ===")


# ── App ────────────────────────────────────────────────────────────────────────
app = FastAPI(
    title=PROJECT_NAME,
    version=PROJECT_VERSION,
    description=(
        "AI-Powered Smart Academic ERP — Phase 2 REST API + Conversational Analytics Engine"
    ),
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── CORS ───────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request timing middleware ──────────────────────────────────────────────────
@app.middleware("http")
async def add_process_time(request: Request, call_next):
    start = time.monotonic()
    response = await call_next(request)
    duration = time.monotonic() - start
    response.headers["X-Process-Time"] = f"{duration:.4f}s"
    return response


# ── Global exception handler ───────────────────────────────────────────────────
from shared_kernel.exceptions.domain_exceptions import (
    DomainException,
    EntityNotFoundError,
    TenantNotFoundError,
)


@app.exception_handler(EntityNotFoundError)
async def not_found_handler(request: Request, exc: EntityNotFoundError):
    return JSONResponse(status_code=404, content={"error": exc.error_code, "detail": str(exc)})


@app.exception_handler(TenantNotFoundError)
async def tenant_not_found_handler(request: Request, exc: TenantNotFoundError):
    return JSONResponse(status_code=404, content={"error": exc.error_code, "detail": str(exc)})


@app.exception_handler(DomainException)
async def domain_exception_handler(request: Request, exc: DomainException):
    return JSONResponse(status_code=400, content={"error": exc.error_code, "detail": str(exc)})


# ── Health check ───────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok", "version": PROJECT_VERSION}


# ── Mount Routers ──────────────────────────────────────────────────────────────
app.include_router(tenant_router,     prefix=API_V1_PREFIX)
app.include_router(auth_router,       prefix=API_V1_PREFIX)
app.include_router(students_router,   prefix=API_V1_PREFIX)
app.include_router(attendance_router, prefix=API_V1_PREFIX)
app.include_router(fees_router,       prefix=API_V1_PREFIX)
app.include_router(ai_analytics_router, prefix=API_V1_PREFIX)
app.include_router(notification_router, prefix=API_V1_PREFIX)
app.include_router(parent_router,     prefix=API_V1_PREFIX)
app.include_router(student_router,    prefix=API_V1_PREFIX)
