"""
modules/auth/api/views.py — Module 2.0
========================================
POST /api/v1/auth/login  — Demo credential authentication → JWT
POST /api/v1/auth/refresh — Refresh JWT (stub for Phase 1)
GET  /api/v1/auth/me     — Current user from token

Phase 1: No DB user table — credentials validated against SEED_CREDENTIALS.md roles.
Phase 2 swap: Replace _validate_demo_credentials → real DB lookup.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from fastapi import APIRouter, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import Form, Depends
from pydantic import BaseModel

from shared_kernel.auth.jwt_utils import (
    TokenPayload,
    create_access_token,
    get_current_tenant_context,
)
from config.settings.base import JWT_ACCESS_TOKEN_EXPIRE_MINUTES

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])

# ── Demo credential store (Phase 1 — replace with DB lookup in Phase 2) ───────
_DEMO_USERS: dict[str, dict] = {
    "admin@demo.school": {
        "password": "Demo@1234!",
        "role": "admin",
        "full_name": "ERP Admin",
        "tenant_id": "greenwood-high-001",
    },
    "principal@demo.school": {
        "password": "Demo@1234!",
        "role": "admin",
        "full_name": "Dr. Anita Sharma",
        "tenant_id": "greenwood-high-001",
    },
    "teacher01@demo.school": {
        "password": "Demo@1234!",
        "role": "teacher",
        "full_name": "Mr. Rajesh Kumar",
        "tenant_id": "greenwood-high-001",
    },
    "teacher02@demo.school": {
        "password": "Demo@1234!",
        "role": "teacher",
        "full_name": "Ms. Priya Singh",
        "tenant_id": "greenwood-high-001",
    },
    "parent-of-student-01@demo.school": {
        "password": "Demo@1234!",
        "role": "parent",
        "full_name": "Parent User",
        "tenant_id": "greenwood-high-001",
    },
}


# ── Response Models ────────────────────────────────────────────────────────────
class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int = JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60
    role: str
    full_name: str
    tenant_id: str


class MeResponse(BaseModel):
    sub: str
    tenant_id: str
    role: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with demo credentials",
    description=(
        "Authenticate using demo credentials from SEED_CREDENTIALS.md. "
        "Returns a signed JWT Bearer token for all subsequent API calls."
    ),
)
async def login(
    username: str = Form(..., description="Email address"),
    password: str = Form(..., description="Password"),
) -> TokenResponse:
    """Module 2.0 — Auth login."""
    user = _DEMO_USERS.get(username)
    if not user or user["password"] != password:
        logger.warning("Failed login attempt for: %s", username)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        subject=username,
        tenant_id=user["tenant_id"],
        role=user["role"],
        expires_delta=timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    logger.info("Successful login: %s (role=%s)", username, user["role"])
    return TokenResponse(
        access_token=token,
        role=user["role"],
        full_name=user["full_name"],
        tenant_id=user["tenant_id"],
    )


@router.get(
    "/me",
    response_model=MeResponse,
    summary="Get current user from token",
)
async def me(
    token_payload: TokenPayload = Depends(get_current_tenant_context),
) -> MeResponse:
    return MeResponse(
        sub=token_payload.sub,
        tenant_id=token_payload.tenant_id,
        role=token_payload.role,
    )
