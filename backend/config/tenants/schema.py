"""
config/tenants/schema.py
========================
Pydantic v2 contract every tenant config file must satisfy.
Source of truth: ARCHITECTURE.md §2.1

Rule: This schema is the ONLY dependency Web/Mobile configuration is
contractually pinned to (via OpenAPI generation). Change here → regenerate
contracts/openapi.yaml → regenerate TypeScript DTOs.
"""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Enumerations ───────────────────────────────────────────────────────────────

class AcademicTermStructure(str, Enum):
    SEMESTER = "SEMESTER"
    TRIMESTER = "TRIMESTER"
    ANNUAL = "ANNUAL"


class PaymentGatewayProvider(str, Enum):
    DUMMY = "dummy_gateway"
    RAZORPAY = "razorpay"
    STRIPE = "stripe"
    PAYU = "payu"


# ── Sub-Models ─────────────────────────────────────────────────────────────────

class ThemeTokens(BaseModel):
    """
    All visual design tokens for the tenant.
    Rule (§2.4): Web/Mobile fetch these at runtime — NEVER bundle hex values at build time.
    """
    primary_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    accent_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    success_color: str = Field(default="#16A34A", pattern=r"^#[0-9A-Fa-f]{6}$")
    warning_color: str = Field(default="#D97706", pattern=r"^#[0-9A-Fa-f]{6}$")
    error_color: str = Field(default="#DC2626", pattern=r"^#[0-9A-Fa-f]{6}$")
    font_family_heading: str = "Inter"
    font_family_body: str = "Inter"
    logo_url: str
    logo_dark_variant_url: str | None = None
    favicon_url: str
    login_background_url: str | None = None
    border_radius_scale: str = "soft"   # "sharp" | "soft" | "round"


class FeatureFlags(BaseModel):
    """
    Runtime feature toggles.
    Rule (§1.3): Business logic uses FeatureFlagService.is_enabled(),
    never inlines tenant-name checks.
    """
    ai_analytics_enabled: bool = True
    whatsapp_notifications_enabled: bool = False
    biometric_attendance_enabled: bool = False   # Phase-2 CV/OCR hook — keep False in Phase 1
    online_fee_payment_enabled: bool = True
    parent_mobile_app_enabled: bool = True
    multi_campus_enabled: bool = False
    transport_module_enabled: bool = False
    library_module_enabled: bool = False


class GradeBand(BaseModel):
    label: str
    min_score: Decimal
    max_score: Decimal


class GradingPolicy(BaseModel):
    scale_type: str = "PERCENTAGE"     # "PERCENTAGE" | "GPA_4" | "GPA_10" | "LETTER"
    passing_threshold: Decimal = Decimal("33")
    grade_bands: dict[str, tuple[Decimal, Decimal]] = Field(
        default_factory=lambda: {
            "A+": (Decimal("90"), Decimal("100")),
            "A":  (Decimal("80"), Decimal("89")),
            "B":  (Decimal("70"), Decimal("79")),
            "C":  (Decimal("60"), Decimal("69")),
            "D":  (Decimal("33"), Decimal("59")),
            "F":  (Decimal("0"),  Decimal("32")),
        }
    )


class AcademicCalendarConfig(BaseModel):
    term_structure: AcademicTermStructure = AcademicTermStructure.SEMESTER
    terms_per_year: int = 2
    academic_year_start_month: int = Field(ge=1, le=12, default=6)
    working_days: list[str] = ["MON", "TUE", "WED", "THU", "FRI"]


class SchoolMetadata(BaseModel):
    legal_name: str
    display_name: str
    tagline: str | None = None
    address_line1: str
    address_line2: str | None = None
    city: str
    state: str | None = None
    country_code: str = "IN"
    postal_code: str | None = None
    contact_email: str
    contact_phone: str
    website_url: str | None = None
    established_year: int | None = None
    accreditation_bodies: list[str] = []


# ── Root Tenant Config ─────────────────────────────────────────────────────────

class TenantConfig(BaseModel):
    """
    Root tenant configuration. Every concrete tenant file (e.g. greenwood_high.py)
    must instantiate this class. Validated by Pydantic at import time — misconfigured
    tenant files fail fast, not silently.
    """
    tenant_id: str = Field(min_length=3, max_length=64)
    school: SchoolMetadata
    theme: ThemeTokens
    features: FeatureFlags = Field(default_factory=FeatureFlags)
    academic_calendar: AcademicCalendarConfig = Field(default_factory=AcademicCalendarConfig)
    grading_policy: GradingPolicy = Field(default_factory=GradingPolicy)
    default_locale: str = "en-IN"
    default_timezone: str = "Asia/Kolkata"
    default_currency: str = "INR"
    payment_gateway_provider: PaymentGatewayProvider = PaymentGatewayProvider.DUMMY
    notification_providers: dict[str, str] = Field(default_factory=dict)

    model_config = {"frozen": True}   # immutable after construction (matches DTO contract)
