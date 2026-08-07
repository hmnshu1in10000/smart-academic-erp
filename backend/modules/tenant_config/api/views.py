"""
modules/tenant_config/api/views.py — Module 1.0
=================================================
GET /api/v1/core/tenant-config
Returns the full TenantConfig for a given tenant_id.
Clients (Web + Mobile) call this on startup to get theme tokens and feature flags.
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from config.di.container import get_container
from config.tenants.schema import TenantConfig

router = APIRouter(prefix="/core", tags=["Tenant Config"])


class TenantConfigResponse(BaseModel):
    """API response shape for tenant configuration."""
    tenant_id: str
    school_name: str
    tagline: Optional[str]
    city: str
    country: str
    board: str
    academic_year: str
    currency_symbol: str
    timezone: str
    theme: dict
    features: dict

    model_config = {"from_attributes": True}


@router.get(
    "/tenant-config",
    response_model=TenantConfigResponse,
    summary="Get tenant configuration",
    description=(
        "Returns the full TenantConfig including theme tokens and feature flags. "
        "Called by web/mobile clients on application startup."
    ),
)
async def get_tenant_config(
    tenant_id: str = Query(default="greenwood-high-001", description="Tenant identifier"),
) -> TenantConfigResponse:
    """Module 1.0 — Tenant Config endpoint."""
    container = get_container()
    try:
        config: TenantConfig = container.tenant_config_provider.get_config(tenant_id)
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

    return TenantConfigResponse(
        tenant_id=config.tenant_id,
        school_name=config.school.display_name,
        tagline=config.school.tagline,
        city=config.school.city,
        country=config.school.country_code,
        board="CBSE",
        academic_year="2024-25",
        currency_symbol="₹",
        timezone=config.default_timezone,
        theme={
            "primary": config.theme.primary_color,
            "secondary": config.theme.secondary_color,
            "accent": config.theme.accent_color,
            "success": config.theme.success_color,
            "warning": config.theme.warning_color,
            "error": config.theme.error_color,
            "font_family_heading": config.theme.font_family_heading,
            "font_family_body": config.theme.font_family_body,
            "logo_url": config.theme.logo_url,
            "favicon_url": config.theme.favicon_url,
        },
        features={
            "biometric_attendance_enabled": config.features.biometric_attendance_enabled,
            "ai_analytics_enabled": config.features.ai_analytics_enabled,
            "parent_mobile_app_enabled": config.features.parent_mobile_app_enabled,
            "online_fee_payment_enabled": config.features.online_fee_payment_enabled,
            "library_module_enabled": config.features.library_module_enabled,
        },
    )
