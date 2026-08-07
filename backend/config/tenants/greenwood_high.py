"""
config/tenants/greenwood_high.py
=================================
Concrete tenant configuration for Greenwood High International School.
Source of truth: ARCHITECTURE.md §2.1 (example instance)

This file is a static Python config object — the Phase-1 in-memory registry
implementation. Phase 2 moves these to DB rows / S3 JSON without changing consumers.
"""
from decimal import Decimal
from config.tenants.schema import (
    TenantConfig, SchoolMetadata, ThemeTokens, FeatureFlags,
    AcademicCalendarConfig, GradingPolicy, AcademicTermStructure,
    PaymentGatewayProvider,
)

GREENWOOD_HIGH_CONFIG = TenantConfig(
    tenant_id="greenwood-high-001",

    school=SchoolMetadata(
        legal_name="Greenwood High International School",
        display_name="Greenwood High",
        tagline="Nurturing Minds, Building Futures",
        address_line1="12 Lakeview Road, Civil Lines",
        address_line2="Near Central Park",
        city="Kanpur",
        state="Uttar Pradesh",
        country_code="IN",
        postal_code="208001",
        contact_email="admin@greenwoodhigh.edu.in",
        contact_phone="+91-512-2601234",
        website_url="https://greenwoodhigh.edu.in",
        established_year=1998,
        accreditation_bodies=["CBSE", "ISO 9001:2015"],
    ),

    theme=ThemeTokens(
        primary_color="#0F4C81",        # Deep navy blue — institutional authority
        secondary_color="#F2A900",      # Amber gold — energy and optimism
        accent_color="#1CA9C9",         # Teal — modern tech accent
        success_color="#16A34A",
        warning_color="#D97706",
        error_color="#DC2626",
        font_family_heading="Inter",
        font_family_body="Inter",
        logo_url="https://placehold.co/240x60/0F4C81/FFFFFF?text=Greenwood+High",
        logo_dark_variant_url="https://placehold.co/240x60/FFFFFF/0F4C81?text=Greenwood+High",
        favicon_url="https://placehold.co/32x32/0F4C81/F2A900?text=G",
        login_background_url="https://images.unsplash.com/photo-1580582932707-520aed937b7b?w=1920",
        border_radius_scale="soft",
    ),

    features=FeatureFlags(
        ai_analytics_enabled=True,
        whatsapp_notifications_enabled=True,    # Greenwood has WhatsApp subscription
        biometric_attendance_enabled=False,     # Phase 2 CV/OCR — not yet
        online_fee_payment_enabled=True,
        parent_mobile_app_enabled=True,
        multi_campus_enabled=False,
        transport_module_enabled=True,          # Greenwood runs school buses
        library_module_enabled=False,
    ),

    academic_calendar=AcademicCalendarConfig(
        term_structure=AcademicTermStructure.SEMESTER,
        terms_per_year=2,
        academic_year_start_month=6,            # June start (Indian school year)
        working_days=["MON", "TUE", "WED", "THU", "FRI", "SAT"],
    ),

    grading_policy=GradingPolicy(
        scale_type="PERCENTAGE",
        passing_threshold=Decimal("33"),
        grade_bands={
            "A+": (Decimal("90"), Decimal("100")),
            "A":  (Decimal("80"), Decimal("89")),
            "B":  (Decimal("70"), Decimal("79")),
            "C":  (Decimal("60"), Decimal("69")),
            "D":  (Decimal("33"), Decimal("59")),
            "F":  (Decimal("0"),  Decimal("32")),
        },
    ),

    default_locale="en-IN",
    default_timezone="Asia/Kolkata",
    default_currency="INR",
    payment_gateway_provider=PaymentGatewayProvider.DUMMY,
    notification_providers={
        "sms": "dummy_channel",
        "email": "dummy_channel",
        "push": "dummy_channel",
        "whatsapp": "dummy_channel",
    },
)
