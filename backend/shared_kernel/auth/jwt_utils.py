"""
shared_kernel/auth/jwt_utils.py
================================
Stateless HS256 JWT helpers shared by all modules that need auth.
No DB access — tokens are self-contained.

Rule: Business logic never imports from here directly.
It imports the FastAPI Depends-injectable `get_current_tenant_context`.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass
from typing import Any

from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer

from config.settings.base import (
    SECRET_KEY,
    JWT_ALGORITHM,
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES,
)

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


@dataclass(frozen=True)
class TokenPayload:
    sub: str           # user email / identifier
    tenant_id: str
    role: str          # "admin" | "teacher" | "parent" | "student"
    exp: datetime


def create_access_token(
    subject: str,
    tenant_id: str,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Sign a JWT access token."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "tenant_id": tenant_id,
        "role": role,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> TokenPayload:
    """Decode and validate a JWT. Raises HTTPException on failure."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[JWT_ALGORITHM])
        sub: str = payload.get("sub", "")
        tenant_id: str = payload.get("tenant_id", "")
        role: str = payload.get("role", "guest")
        exp_ts = payload.get("exp", 0)
        if not sub or not tenant_id:
            raise credentials_exception
        exp_dt = datetime.fromtimestamp(exp_ts, tz=timezone.utc)
        return TokenPayload(sub=sub, tenant_id=tenant_id, role=role, exp=exp_dt)
    except JWTError:
        raise credentials_exception


async def get_current_token_payload(
    token: str = Depends(oauth2_scheme),
) -> TokenPayload:
    """FastAPI dependency: extract + validate Bearer token."""
    return decode_access_token(token)


async def get_current_tenant_context(
    payload: TokenPayload = Depends(get_current_token_payload),
) -> TokenPayload:
    """
    FastAPI dependency for routes requiring authenticated tenant context.
    Usage: `tenant: TokenPayload = Depends(get_current_tenant_context)`
    """
    return payload
