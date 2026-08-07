# AI-Powered Academic ERP — System Architecture Specification

**Document Type:** Engineering Reference / System Design Contract
**Architecture Style:** Clean Architecture + Domain-Driven Design (DDD) + Vertical Slice Modularity
**Stack:** Django REST Framework (or FastAPI) · PostgreSQL · React.js/Tailwind · React Native (Expo) · Vanna.ai/LangChain (Text-to-SQL)
**Scope:** Phase 1 — Dummy Data Simulation (CV/OCR pipeline excluded, interface-reserved for Phase 2)

---

## Guiding Principles (enforced throughout this document)

1. **Functional Cohesion** — every module/sub-module/function does exactly one thing. A sub-module that both "calculates fee dues" and "sends SMS" is a cohesion violation and is split.
2. **Dependency Inversion** — modules depend on abstractions (`Protocol` / `ABC` in Python, `interface` in TS) never on another module's concrete class or ORM model.
3. **No Cross-Module ORM Reach-Through** — Module A never imports Module B's Django model or Prisma/TypeORM entity directly. All cross-module reads go through a **Service Facade** returning a DTO.
4. **Config/Theme Isolation** — zero hardcoded tenant strings, colors, business constants inside UI components or business logic. Every such value is resolved via a `TenantConfigProvider` / `ThemeProvider` at runtime.
5. **Replaceability** — any module can be deleted and its consumers keep compiling (they'll fail at the interface boundary, not scattered throughout the codebase), because consumers only hold interface references.

---

# SECTION 1: ARCHITECTURAL BOUNDARIES & COUPLING CONTRACTS

## 1.1 Layering Model (per module, Backend)

```
┌─────────────────────────────────────────────┐
│  Presentation Layer (DRF Views / FastAPI     │
│  Routers) — serializes DTOs, no business      │
│  logic                                        │
├─────────────────────────────────────────────┤
│  Application Layer (Use Cases / Services)     │
│  — orchestrates domain logic, talks to        │
│  interfaces only                              │
├─────────────────────────────────────────────┤
│  Domain Layer (Entities, Value Objects,       │
│  Domain Services) — pure Python, zero         │
│  framework imports                            │
├─────────────────────────────────────────────┤
│  Infrastructure Layer (ORM Repositories,      │
│  External Gateway Adapters, Dummy Data        │
│  Adapters) — implements the interfaces        │
│  declared in Application layer                │
└─────────────────────────────────────────────┘
```

Rule: **dependencies point inward only.** Domain layer never imports Django/DRF. Infrastructure implements interfaces defined by the Application layer (Dependency Inversion — the "port" is owned by the inner layer, the "adapter" lives outside).

## 1.2 Cross-Module Communication Contract

All inter-module communication uses one of three mechanisms — **never direct model imports**:

| Mechanism | When Used | Example |
|---|---|---|
| **Service Facade + DTO** | Synchronous read/query across modules | `AttendanceModule` asks `StudentModule.get_student_profile(student_id) -> StudentProfileDTO` |
| **Domain Event (async, pub/sub)** | Fire-and-forget cross-module side effects | `FeePaymentReceivedEvent` → consumed by `NotificationModule`, `AnalyticsModule` |
| **Strategy Interface (pluggable provider)** | Swappable external integrations | `IPaymentGatewayStrategy`, `INotificationProvider`, `IThemeProvider` |

### 1.2.1 Base DTO Contract (Python — `shared_kernel/contracts/base_dto.py`)

```python
from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

T = TypeVar("T")

@dataclass(frozen=True, slots=True)
class BaseDTO:
    """All cross-module DTOs are immutable, frameworks-agnostic dataclasses.
    Never expose an ORM model instance across a module boundary."""
    pass

@dataclass(frozen=True, slots=True)
class ResultDTO(Generic[T]):
    success: bool
    data: T | None
    error_code: str | None = None
    error_message: str | None = None
    trace_id: str | None = None

@dataclass(frozen=True, slots=True)
class PaginatedDTO(Generic[T]):
    items: list[T]
    total_count: int
    page: int
    page_size: int
    has_next: bool
```

### 1.2.2 Domain Event Contract (`shared_kernel/events/base_event.py`)

```python
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

@dataclass(frozen=True, slots=True)
class DomainEvent:
    event_id: UUID = field(default_factory=uuid4)
    tenant_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    event_type: str = ""
    payload: dict = field(default_factory=dict)
    correlation_id: str | None = None

# Example concrete event
@dataclass(frozen=True, slots=True)
class FeePaymentReceivedEvent(DomainEvent):
    event_type: str = "fee.payment.received"
    # payload keys (typed via a companion TypedDict, enforced at publish time):
    # student_id: UUID, amount: Decimal, invoice_id: UUID, payment_method: str
```

Event bus is an interface (`IEventBus`) — Phase 1 implementation is an in-process synchronous dispatcher (Django signals or a simple observer registry); Phase 2 can swap in Celery + Redis / Kafka **without touching any publisher or subscriber code**, because both only depend on `IEventBus`.

```python
from typing import Protocol, Callable

class IEventBus(Protocol):
    def publish(self, event: DomainEvent) -> None: ...
    def subscribe(self, event_type: str, handler: Callable[[DomainEvent], None]) -> None: ...
```

## 1.3 Strategy Pattern Interfaces (the swappable "ports")

### 1.3.1 Payment Gateway Strategy

```python
# modules/fee_management/application/interfaces/payment_gateway.py
from typing import Protocol
from dataclasses import dataclass
from decimal import Decimal
from uuid import UUID

@dataclass(frozen=True, slots=True)
class PaymentInitiationRequestDTO:
    invoice_id: UUID
    student_id: UUID
    amount: Decimal
    currency: str
    payer_email: str
    payer_phone: str
    callback_url: str
    metadata: dict

@dataclass(frozen=True, slots=True)
class PaymentInitiationResponseDTO:
    provider_reference_id: str
    redirect_url: str | None
    status: str  # "PENDING" | "REQUIRES_ACTION" | "FAILED"

@dataclass(frozen=True, slots=True)
class PaymentVerificationResponseDTO:
    provider_reference_id: str
    status: str  # "SUCCESS" | "FAILED" | "PENDING" | "REFUNDED"
    amount_captured: Decimal
    raw_provider_payload: dict

class IPaymentGatewayStrategy(Protocol):
    provider_name: str  # "razorpay" | "stripe" | "payu" | "dummy_gateway"

    def initiate_payment(self, request: PaymentInitiationRequestDTO) -> PaymentInitiationResponseDTO: ...
    def verify_payment(self, provider_reference_id: str) -> PaymentVerificationResponseDTO: ...
    def process_refund(self, provider_reference_id: str, amount: Decimal) -> PaymentVerificationResponseDTO: ...
    def handle_webhook(self, raw_payload: bytes, signature_header: str) -> PaymentVerificationResponseDTO: ...
```

Concrete implementations (`RazorpayGatewayAdapter`, `StripeGatewayAdapter`, `DummyGatewayAdapter`) are registered in a factory resolved by tenant config — see §2.3. The Fee Management application service depends **only** on `IPaymentGatewayStrategy`.

### 1.3.2 Notification Provider Strategy

```python
# modules/notification_engine/application/interfaces/notification_provider.py
from typing import Protocol
from dataclasses import dataclass
from enum import Enum

class NotificationChannel(str, Enum):
    SMS = "sms"
    EMAIL = "email"
    PUSH = "push"
    WHATSAPP = "whatsapp"
    IN_APP = "in_app"

@dataclass(frozen=True, slots=True)
class NotificationRequestDTO:
    recipient_id: str
    channel: NotificationChannel
    template_key: str          # never raw hardcoded strings — resolved via Template Registry
    template_variables: dict
    priority: str               # "LOW" | "NORMAL" | "HIGH" | "CRITICAL"

@dataclass(frozen=True, slots=True)
class NotificationDispatchResultDTO:
    dispatch_id: str
    channel: NotificationChannel
    status: str   # "QUEUED" | "SENT" | "FAILED" | "SUPPRESSED"
    provider_message_id: str | None

class INotificationProvider(Protocol):
    channel: NotificationChannel

    def send(self, request: NotificationRequestDTO) -> NotificationDispatchResultDTO: ...
    def get_delivery_status(self, dispatch_id: str) -> str: ...
```

Each channel has its own strategy implementation (`TwilioSmsProvider`, `SendgridEmailProvider`, `FcmPushProvider`, `WhatsappCloudApiProvider`, `DummyChannelProvider`). A `NotificationRouter` (application service) selects the provider via a `IProviderResolver` keyed off tenant feature flags — so a school without WhatsApp budget simply has that flag off, with zero code change.

### 1.3.3 School Theme / Tenant Config Provider

```python
# modules/core_infrastructure/application/interfaces/theme_provider.py
from typing import Protocol
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class ThemeTokensDTO:
    primary_color: str
    secondary_color: str
    accent_color: str
    font_family_heading: str
    font_family_body: str
    logo_url: str
    favicon_url: str
    school_display_name: str

@dataclass(frozen=True, slots=True)
class TenantConfigDTO:
    tenant_id: str
    school_legal_name: str
    academic_term_structure: str   # "SEMESTER" | "TRIMESTER" | "ANNUAL"
    feature_flags: dict[str, bool]
    theme: ThemeTokensDTO
    locale: str
    timezone: str
    currency_code: str

class ITenantConfigProvider(Protocol):
    def get_config(self, tenant_id: str) -> TenantConfigDTO: ...
    def get_theme(self, tenant_id: str) -> ThemeTokensDTO: ...
    def is_feature_enabled(self, tenant_id: str, feature_key: str) -> bool: ...
```

This is the **single dependency** every UI component, API view, and business-rule branch is allowed to consult for anything tenant-specific. No module may read `settings.py` constants for school-specific data — `settings.py` only holds infra concerns (DB URL, secret keys).

## 1.4 Dependency Injection Convention

Backend uses **constructor injection** via a lightweight DI container (`dependency-injector` library or FastAPI's native `Depends`). Every Application Service declares its dependencies as interface types in `__init__`:

```python
class FeeInvoiceService:
    def __init__(
        self,
        payment_gateway: IPaymentGatewayStrategy,
        invoice_repo: IFeeInvoiceRepository,
        event_bus: IEventBus,
        tenant_config: ITenantConfigProvider,
    ) -> None:
        self._gateway = payment_gateway
        self._repo = invoice_repo
        self._event_bus = event_bus
        self._tenant_config = tenant_config
```

Wiring (which concrete class satisfies which interface, including Dummy vs. Real adapters) happens **only** in a per-module `container.py` / `di_config.py` — never inline in business logic.

---

# SECTION 2: DECOUPLED THEME & TENANT CONFIGURATION SCHEMA

Single source of truth per platform. All three schemas below are **structurally aligned** (same keys, different syntax) so a tenant onboarding pipeline can generate all three from one master JSON.

## 2.1 Backend — `config/tenants/school_config.py` (per-tenant, loaded at request time via middleware)

```python
# config/tenants/schema.py — the Pydantic contract every tenant config file must satisfy
from pydantic import BaseModel, Field
from enum import Enum
from decimal import Decimal

class AcademicTermStructure(str, Enum):
    SEMESTER = "SEMESTER"
    TRIMESTER = "TRIMESTER"
    ANNUAL = "ANNUAL"

class ThemeTokens(BaseModel):
    primary_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    secondary_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    accent_color: str = Field(pattern=r"^#[0-9A-Fa-f]{6}$")
    success_color: str = "#16A34A"
    warning_color: str = "#D97706"
    error_color: str = "#DC2626"
    font_family_heading: str = "Inter"
    font_family_body: str = "Inter"
    logo_url: str
    logo_dark_variant_url: str | None = None
    favicon_url: str
    login_background_url: str | None = None

class FeatureFlags(BaseModel):
    ai_analytics_enabled: bool = True
    whatsapp_notifications_enabled: bool = False
    biometric_attendance_enabled: bool = False   # reserved — Phase 2 CV/OCR hook
    online_fee_payment_enabled: bool = True
    parent_mobile_app_enabled: bool = True
    multi_campus_enabled: bool = False
    transport_module_enabled: bool = False
    library_module_enabled: bool = False

class GradingPolicy(BaseModel):
    scale_type: str            # "PERCENTAGE" | "GPA_4" | "GPA_10" | "LETTER"
    passing_threshold: Decimal
    grade_bands: dict[str, tuple[Decimal, Decimal]]

class AcademicCalendarConfig(BaseModel):
    term_structure: AcademicTermStructure
    terms_per_year: int
    academic_year_start_month: int  # 1-12
    working_days: list[str]         # ["MON","TUE","WED","THU","FRI"]

class SchoolMetadata(BaseModel):
    legal_name: str
    display_name: str
    tagline: str | None = None
    address_line1: str
    address_line2: str | None = None
    city: str
    country_code: str
    contact_email: str
    contact_phone: str
    established_year: int | None = None
    accreditation_bodies: list[str] = []

class TenantConfig(BaseModel):
    tenant_id: str
    school: SchoolMetadata
    theme: ThemeTokens
    features: FeatureFlags
    academic_calendar: AcademicCalendarConfig
    grading_policy: GradingPolicy
    default_locale: str = "en-IN"
    default_timezone: str = "Asia/Kolkata"
    default_currency: str = "INR"
    payment_gateway_provider: str = "dummy_gateway"  # resolves IPaymentGatewayStrategy impl
    notification_providers: dict[str, str] = {}       # channel -> provider key
```

Example concrete instance (`config/tenants/greenwood_high.py`):

```python
from config.tenants.schema import TenantConfig

GREENWOOD_HIGH_CONFIG = TenantConfig(
    tenant_id="greenwood-high-001",
    school=dict(
        legal_name="Greenwood High International School",
        display_name="Greenwood High",
        address_line1="12 Lakeview Road",
        city="Kanpur",
        country_code="IN",
        contact_email="admin@greenwoodhigh.edu",
        contact_phone="+91-512-XXXXXXX",
    ),
    theme=dict(
        primary_color="#0F4C81",
        secondary_color="#F2A900",
        accent_color="#1CA9C9",
        logo_url="https://cdn.example.com/tenants/greenwood/logo.svg",
        favicon_url="https://cdn.example.com/tenants/greenwood/favicon.ico",
    ),
    features=dict(whatsapp_notifications_enabled=True, transport_module_enabled=True),
    academic_calendar=dict(
        term_structure="SEMESTER", terms_per_year=2,
        academic_year_start_month=6,
        working_days=["MON","TUE","WED","THU","FRI","SAT"],
    ),
    grading_policy=dict(
        scale_type="PERCENTAGE", passing_threshold=33,
        grade_bands={"A+": (90,100), "A": (80,89), "B": (70,79), "C": (60,69), "D": (33,59), "F": (0,32)},
    ),
)
```

**Resolution mechanism:** `TenantConfigMiddleware` reads `tenant_id` from subdomain/JWT claim → loads via `ITenantConfigRepository` (Phase 1: Python module registry keyed by `tenant_id`; Phase 2: swap to DB-backed / S3 JSON without touching consumers) → attaches `request.tenant_config: TenantConfigDTO`. All views/services read from `request.tenant_config`, never from a global import.

## 2.2 Web Dashboard — `src/config/theme.config.ts`

```typescript
// src/config/theme.schema.ts — the contract (Zod for runtime validation)
import { z } from "zod";

export const ThemeTokensSchema = z.object({
  primaryColor: z.string().regex(/^#[0-9A-Fa-f]{6}$/),
  secondaryColor: z.string().regex(/^#[0-9A-Fa-f]{6}$/),
  accentColor: z.string().regex(/^#[0-9A-Fa-f]{6}$/),
  successColor: z.string().default("#16A34A"),
  warningColor: z.string().default("#D97706"),
  errorColor: z.string().default("#DC2626"),
  fontHeading: z.string().default("Inter"),
  fontBody: z.string().default("Inter"),
  logoUrl: z.string().url(),
  logoDarkVariantUrl: z.string().url().optional(),
  faviconUrl: z.string().url(),
  loginBackgroundUrl: z.string().url().optional(),
  borderRadiusScale: z.enum(["sharp", "soft", "round"]).default("soft"),
});

export const FeatureFlagsSchema = z.object({
  aiAnalyticsEnabled: z.boolean().default(true),
  whatsappNotificationsEnabled: z.boolean().default(false),
  biometricAttendanceEnabled: z.boolean().default(false),
  onlineFeePaymentEnabled: z.boolean().default(true),
  multiCampusEnabled: z.boolean().default(false),
  transportModuleEnabled: z.boolean().default(false),
  libraryModuleEnabled: z.boolean().default(false),
});

export const TenantConfigSchema = z.object({
  tenantId: z.string(),
  schoolDisplayName: z.string(),
  schoolTagline: z.string().optional(),
  theme: ThemeTokensSchema,
  features: FeatureFlagsSchema,
  locale: z.string().default("en-IN"),
  currencyCode: z.string().default("INR"),
});

export type TenantConfig = z.infer<typeof TenantConfigSchema>;
```

```typescript
// src/config/theme.config.ts — fetched at app bootstrap from
// GET /api/v1/core/tenant-config (never bundled/hardcoded at build time,
// so ONE web build serves ALL tenants)
import { TenantConfig, TenantConfigSchema } from "./theme.schema";

export async function loadTenantConfig(tenantSlug: string): Promise<TenantConfig> {
  const res = await fetch(`/api/v1/core/tenant-config?tenant=${tenantSlug}`);
  const raw = await res.json();
  return TenantConfigSchema.parse(raw); // fail fast on malformed tenant config
}
```

```typescript
// src/config/ThemeProvider.tsx — injects CSS custom properties, NO component
// ever imports a color/logo directly.
import { createContext, useContext, useEffect } from "react";
import type { TenantConfig } from "./theme.schema";

const TenantConfigContext = createContext<TenantConfig | null>(null);

export function TenantConfigProvider({ config, children }: { config: TenantConfig; children: React.ReactNode }) {
  useEffect(() => {
    const root = document.documentElement;
    root.style.setProperty("--color-primary", config.theme.primaryColor);
    root.style.setProperty("--color-secondary", config.theme.secondaryColor);
    root.style.setProperty("--color-accent", config.theme.accentColor);
    root.style.setProperty("--font-heading", config.theme.fontHeading);
    root.style.setProperty("--font-body", config.theme.fontBody);
    document.title = config.schoolDisplayName;
  }, [config]);

  return <TenantConfigContext.Provider value={config}>{children}</TenantConfigContext.Provider>;
}

export const useTenantConfig = (): TenantConfig => {
  const ctx = useContext(TenantConfigContext);
  if (!ctx) throw new Error("useTenantConfig must be used within TenantConfigProvider");
  return ctx;
};

export const useFeatureFlag = (key: keyof TenantConfig["features"]): boolean =>
  useTenantConfig().features[key];
```

`tailwind.config.ts` maps Tailwind semantic classes to the CSS custom properties above (`bg-brand-primary` → `var(--color-primary)`) — **never** a literal hex in any `.tsx` file. Components use `className="bg-brand-primary text-brand-onPrimary"`, never `className="bg-[#0F4C81]"`.

## 2.3 Mobile (Expo) — `src/config/app.theme.js`

```javascript
// src/config/theme.schema.js — mirrors the web Zod schema via Yup (RN-friendly)
import * as Yup from "yup";

export const ThemeTokensSchema = Yup.object({
  primaryColor: Yup.string().matches(/^#[0-9A-Fa-f]{6}$/).required(),
  secondaryColor: Yup.string().matches(/^#[0-9A-Fa-f]{6}$/).required(),
  accentColor: Yup.string().matches(/^#[0-9A-Fa-f]{6}$/).required(),
  fontHeading: Yup.string().default("Inter"),
  fontBody: Yup.string().default("Inter"),
  logoUri: Yup.string().url().required(),
  splashLogoUri: Yup.string().url().required(),
});

export const TenantConfigSchema = Yup.object({
  tenantId: Yup.string().required(),
  schoolDisplayName: Yup.string().required(),
  theme: ThemeTokensSchema.required(),
  features: Yup.object({
    whatsappNotificationsEnabled: Yup.boolean().default(false),
    biometricAttendanceEnabled: Yup.boolean().default(false),
    pushNotificationsEnabled: Yup.boolean().default(true),
  }),
});
```

```javascript
// src/config/TenantConfigContext.js — resolved at splash-screen boot via
// a tenant slug baked into the Expo build profile (app.config.ts "extra"
// field) OR via a QR/code entry for a single multi-tenant build.
import React, { createContext, useContext, useEffect, useState } from "react";
import { fetchTenantConfig } from "../api/coreApi";

const TenantConfigContext = createContext(null);

export function TenantConfigProvider({ tenantSlug, children }) {
  const [config, setConfig] = useState(null);

  useEffect(() => {
    fetchTenantConfig(tenantSlug).then(setConfig);
  }, [tenantSlug]);

  if (!config) return null; // splash screen stays until config resolves

  return (
    <TenantConfigContext.Provider value={config}>
      {children}
    </TenantConfigContext.Provider>
  );
}

export const useTenantTheme = () => useContext(TenantConfigContext).theme;
export const useTenantFeature = (key) => useContext(TenantConfigContext).features[key];
```

`app.config.ts` (Expo dynamic config) reads `EXPO_PUBLIC_TENANT_SLUG` env var per build flavor (EAS Build profiles: `greenwood-high`, `st-marys`, …) so app name, icon, and splash screen are generated per-tenant at **build time**, while in-app colors/copy are resolved per-tenant at **runtime** — giving both app-store-listing white-labeling and instant runtime reskinning from one codebase.

## 2.4 Config Propagation Diagram

```
        ┌────────────────────────┐
        │   school_config.py      │   (Backend — source of truth,
        │   per-tenant instance    │    Pydantic-validated)
        └───────────┬─────────────┘
                     │  GET /api/v1/core/tenant-config?tenant=X
        ┌────────────┼─────────────┐
        ▼                          ▼
┌───────────────┐         ┌───────────────────┐
│ theme.config.ts│         │  app.theme.js       │
│ (Web, Zod-      │         │  (Mobile, Yup-       │
│  validated,      │         │   validated, cached   │
│  CSS var inject) │         │   in AsyncStorage)     │
└───────────────┘         └───────────────────┘
```

No color/logo/business-rule constant is ever duplicated by hand across the three platforms — Web and Mobile always fetch from the Backend's single source of truth. Only the *validation schema* is duplicated (necessarily, since TS and Python/JS type systems don't share a runtime), and both schemas are contractually pinned to the same field set via a shared OpenAPI spec generated from the Pydantic model.

---

# SECTION 3: INDEXED MODULE TREE

Notation: `[Module X.0]` = top-level bounded context · `[Sub-Module X.Y]` = vertical slice within it · `[Function/Service X.Y.Z]` = concrete function/service with a signature.

---

## [Module 1.0] Core System Infrastructure & Multi-Tenant Config Module

**Bounded Context Responsibility:** Owns tenant resolution, configuration/theme distribution, feature flagging, and cross-cutting infra concerns (audit logging, request context). This is the *only* module every other module is allowed to depend on directly (it sits at the architectural center as a shared kernel utility, not as a business dependency).

### [Sub-Module 1.1] Tenant Resolution & Context Middleware

- **Purpose & Responsibility:** Identify the requesting tenant (from subdomain, header, or JWT claim) and attach a validated `TenantConfigDTO` to the request context before any business logic runs.
- **Cohesion Type:** Functional (single responsibility: tenant identification + context binding).
- **Inputs:** HTTP request (`Host` header / `X-Tenant-Slug` header / JWT `tenant_id` claim).
- **Outputs:** `TenantConfigDTO` bound to `request.tenant_config`; raises `TenantNotFoundError` (HTTP 404) or `TenantSuspendedError` (HTTP 403) otherwise.
- **Dependencies:** `ITenantConfigRepository` (interface; Phase 1 impl = in-memory registry over `config/tenants/*.py`, Phase 2 impl = DB-backed).
- **Dummy Data Mocking Strategy:** N/A — this module is infra-only; dummy tenants (`greenwood-high-001`, `st-marys-002`) are pre-registered as static config objects for local/dev environments.

**[Function 1.1.1]**
```python
class TenantResolutionMiddleware:
    def resolve_tenant(self, request: HttpRequest) -> TenantConfigDTO: ...
    def _extract_tenant_slug(self, request: HttpRequest) -> str: ...
```

### [Sub-Module 1.2] Tenant Configuration Service (Theme + Feature Flags API)

- **Purpose & Responsibility:** Serve the validated tenant configuration payload to Web/Mobile clients; the single HTTP endpoint that powers §2.4's propagation diagram.
- **Cohesion Type:** Functional (single responsibility: config retrieval and serialization).
- **Inputs:** `GetTenantConfigRequestDTO(tenant_slug: str)`
- **Outputs:** `TenantConfigResponseDTO` (mirrors `TenantConfig` Pydantic schema from §2.1, serialized to JSON)
- **Dependencies:** `ITenantConfigProvider` (§1.3.3)
- **Dummy Data Mocking Strategy:** Dummy tenants ship with fully populated `ThemeTokens` (real placeholder hex codes + placeholder logo URLs pointing to a local asset CDN mock) so Web/Mobile devs never hit an empty theme.

**[Function 1.2.1]**
```python
class TenantConfigService:
    def __init__(self, config_provider: ITenantConfigProvider): ...
    def get_public_config(self, tenant_slug: str) -> TenantConfigResponseDTO: ...
    def get_feature_flags(self, tenant_id: str) -> dict[str, bool]: ...
```
**[Endpoint 1.2.2]** `GET /api/v1/core/tenant-config?tenant={slug}` → `TenantConfigResponseDTO`

### [Sub-Module 1.3] Feature Flag Evaluation Engine

- **Purpose & Responsibility:** Central boolean-gate evaluator so business logic never inlines `if tenant == "greenwood"` checks — only `if feature_flags.is_enabled("transport_module")`.
- **Cohesion Type:** Functional (single responsibility: flag evaluation, no business rules).
- **Inputs:** `FeatureFlagCheckRequestDTO(tenant_id: str, feature_key: str, user_role: str | None)`
- **Outputs:** `bool`
- **Dependencies:** `ITenantConfigProvider`
- **Dummy Data Mocking Strategy:** Dummy tenants toggle a representative mix of flags on/off (e.g., Greenwood has `transport_module_enabled=True`, St. Mary's has it `False`) to exercise both UI code paths in QA.

**[Function 1.3.1]**
```python
class FeatureFlagService:
    def is_enabled(self, tenant_id: str, feature_key: str) -> bool: ...
    def get_all_flags(self, tenant_id: str) -> dict[str, bool]: ...
```

### [Sub-Module 1.4] Audit Logging & Request Context Service

- **Purpose & Responsibility:** Capture who-did-what-when across all modules via a single decorator/middleware, without any module hand-rolling its own logging.
- **Cohesion Type:** Functional (single responsibility: audit trail persistence).
- **Inputs:** `AuditEventDTO(actor_id, tenant_id, action, resource_type, resource_id, metadata, timestamp)`
- **Outputs:** `ResultDTO[None]`
- **Dependencies:** `IAuditLogRepository`, `IEventBus` (subscribes to all domain events tagged `audit: true`)
- **Dummy Data Mocking Strategy:** Dummy Data Generator (Module 3.0) seeds 90 days of synthetic audit trail entries correlated with generated attendance/fee events for realistic dashboard demos.

**[Function 1.4.1]**
```python
class AuditLogService:
    def record(self, event: AuditEventDTO) -> None: ...
    def query_trail(self, filters: AuditQueryFilterDTO) -> PaginatedDTO[AuditEventDTO]: ...
```

---

## [Module 2.0] Authentication, RBAC & User Management Module

**Bounded Context Responsibility:** Owns identity, authentication, role-based access control, and user profile lifecycle for all actor types (Admin, Principal, Teacher, Staff, Parent, Student). Exposes identity facts to other modules **only** via `UserProfileDTO` — no other module queries the `User` table directly.

### [Sub-Module 2.1] Authentication Service (JWT + Refresh Token)

- **Purpose & Responsibility:** Credential verification and token issuance/rotation only — no authorization logic here.
- **Cohesion Type:** Functional (authentication is strictly separated from authorization, per single-responsibility).
- **Inputs:** `LoginRequestDTO(identifier: str, password: str, tenant_id: str, device_info: DeviceInfoDTO | None)`
- **Outputs:** `AuthTokenResponseDTO(access_token: str, refresh_token: str, expires_in: int, user_summary: UserSummaryDTO)`
- **Dependencies:** `IUserCredentialRepository`, `ITokenService`, `IPasswordHasher`
- **Dummy Data Mocking Strategy:** Dummy Data Generator seeds one login per synthetic role (`admin@demo.school`, `teacher01@demo.school`, `parent-of-student-0042@demo.school`) with a fixed dev password, printed to a `SEED_CREDENTIALS.md` for QA — never committed with real-looking data.

**[Function 2.1.1]**
```python
class AuthenticationService:
    def __init__(self, credential_repo: IUserCredentialRepository, token_service: ITokenService): ...
    def login(self, request: LoginRequestDTO) -> ResultDTO[AuthTokenResponseDTO]: ...
    def refresh_token(self, refresh_token: str) -> ResultDTO[AuthTokenResponseDTO]: ...
    def logout(self, user_id: UUID, refresh_token: str) -> ResultDTO[None]: ...
    def request_password_reset(self, identifier: str, tenant_id: str) -> ResultDTO[None]: ...
    def confirm_password_reset(self, reset_token: str, new_password: str) -> ResultDTO[None]: ...
```

### [Sub-Module 2.2] RBAC / Permission Engine

- **Purpose & Responsibility:** Role → Permission → Resource mapping and enforcement; exposes a single `has_permission()` gate consumed by every other module's API layer via a decorator.
- **Cohesion Type:** Functional (single responsibility: authorization decisions, zero business rules).
- **Inputs:** `PermissionCheckRequestDTO(user_id: UUID, permission_key: str, resource_scope: ResourceScopeDTO | None)`
- **Outputs:** `bool`
- **Dependencies:** `IRolePermissionRepository`
- **Dummy Data Mocking Strategy:** Seeds a fixed RBAC matrix (`Admin`, `Principal`, `Teacher`, `AccountsStaff`, `Parent`, `Student`) with realistic permission sets (e.g., `Teacher` can `attendance.mark_own_class` but not `fee.view_all_invoices`).

**[Function 2.2.1]**
```python
class RBACService:
    def has_permission(self, user_id: UUID, permission_key: str, scope: ResourceScopeDTO | None = None) -> bool: ...
    def get_role_permissions(self, role_key: str) -> list[str]: ...
    def assign_role(self, user_id: UUID, role_key: str, assigned_by: UUID) -> ResultDTO[None]: ...
```
**[Decorator 2.2.2]**
```python
def require_permission(permission_key: str):
    """Applied to DRF view methods / FastAPI route handlers across ALL modules.
    This is the ONLY sanctioned way to gate an endpoint — no module hand-rolls
    role checks inline."""
```

### [Sub-Module 2.3] User Profile & Lifecycle Management

- **Purpose & Responsibility:** CRUD + lifecycle state (Active/Suspended/Archived) for user identity records, decoupled from role-specific profile data (e.g., a Teacher's subject specialization lives in Module 4.0, not here).
- **Cohesion Type:** Functional (identity lifecycle only; domain-specific profile attributes are deliberately excluded to avoid a "God User" anti-pattern).
- **Inputs:** `CreateUserRequestDTO`, `UpdateUserRequestDTO(user_id, fields)`, `DeactivateUserRequestDTO(user_id, reason)`
- **Outputs:** `UserProfileDTO(user_id, tenant_id, full_name, email, phone, role_key, status, avatar_url, created_at)`
- **Dependencies:** `IUserRepository`, `IEventBus` (publishes `UserCreatedEvent`, `UserDeactivatedEvent`)
- **Dummy Data Mocking Strategy:** `UserProfileFactory` (Module 3.0) generates N synthetic users per role using `Faker` with locale seeding (`en_IN`) for realistic Indian names/phone formats, cross-linked to Student/Staff domain records via foreign UUIDs.

**[Function 2.3.1]**
```python
class UserProfileService:
    def create_user(self, request: CreateUserRequestDTO) -> ResultDTO[UserProfileDTO]: ...
    def get_profile(self, user_id: UUID) -> ResultDTO[UserProfileDTO]: ...
    def update_profile(self, request: UpdateUserRequestDTO) -> ResultDTO[UserProfileDTO]: ...
    def deactivate_user(self, request: DeactivateUserRequestDTO) -> ResultDTO[None]: ...
    def search_users(self, filters: UserSearchFilterDTO) -> PaginatedDTO[UserProfileDTO]: ...
```

### [Sub-Module 2.4] Multi-Factor & Session Management

- **Purpose & Responsibility:** OTP-based MFA (for Admin/Principal roles) and active session tracking/revocation across web + mobile devices.
- **Cohesion Type:** Functional (session security, isolated from core auth token issuance).
- **Inputs:** `MFAChallengeRequestDTO(user_id)`, `MFAVerifyRequestDTO(user_id, otp_code)`
- **Outputs:** `ResultDTO[MFAChallengeResponseDTO]`, `list[ActiveSessionDTO]`
- **Dependencies:** `IOTPProvider` (itself resolved through `INotificationProvider`, §1.3.2 — reuses SMS/Email channel rather than owning its own dispatch logic), `ISessionRepository`
- **Dummy Data Mocking Strategy:** Dummy OTP provider always returns a fixed testable code (`000000`) in non-prod environments, gated by `settings.ENV != "production"`.

**[Function 2.4.1]**
```python
class MFAService:
    def issue_challenge(self, user_id: UUID) -> ResultDTO[MFAChallengeResponseDTO]: ...
    def verify_challenge(self, request: MFAVerifyRequestDTO) -> ResultDTO[bool]: ...
    def list_active_sessions(self, user_id: UUID) -> list[ActiveSessionDTO]: ...
    def revoke_session(self, user_id: UUID, session_id: UUID) -> ResultDTO[None]: ...
```

---

## [Module 3.0] Dummy Data Generator Engine

**Bounded Context Responsibility:** Simulates the entire operational dataset (students, staff, classes, timetables, attendance events, fee transactions) that would otherwise come from the CV/OCR pipeline and manual data entry, so every downstream module (4.0–9.0) can be built, tested, and demoed against realistic data. **Architecturally critical:** this module is 100% swappable — it implements the exact same repository interfaces (`IStudentRepository`, `IAttendanceIngestionSource`, etc.) that a real OCR/biometric pipeline would implement in Phase 2. No consumer code changes when Phase 2 lands; only the DI wiring in `container.py` changes from `DummyAttendanceSource` to `CVPipelineAttendanceSource`.

### [Sub-Module 3.1] Synthetic Identity & Demographics Factory

- **Purpose & Responsibility:** Generate statistically realistic student/staff/parent identity records (names, DOB, gender distribution, addresses) using locale-aware `Faker` providers.
- **Cohesion Type:** Functional (identity generation only — no academic/attendance logic here).
- **Inputs:** `GenerateIdentitiesRequestDTO(tenant_id, count, role_key, locale="en_IN", seed: int | None)`
- **Outputs:** `list[SyntheticIdentityDTO(full_name, dob, gender, guardian_name, phone, address, blood_group)]`
- **Dependencies:** None (pure generation utility — deliberately dependency-free so it's trivially unit-testable and reusable by any seeding script).
- **Dummy Data Mocking Strategy:** *Is* the mocking strategy — wraps `Faker(locale)` with custom providers for Indian phone number formats, school-appropriate age ranges (student DOB constrained to grade-appropriate bands), and weighted gender/blood-group distributions matching real demographic ratios.

**[Function 3.1.1]**
```python
class SyntheticIdentityFactory:
    def __init__(self, seed: int | None = None): ...
    def generate_student_identities(self, count: int, grade_level: int) -> list[SyntheticIdentityDTO]: ...
    def generate_staff_identities(self, count: int, department: str) -> list[SyntheticIdentityDTO]: ...
    def generate_guardian_identity(self, student_identity: SyntheticIdentityDTO) -> SyntheticIdentityDTO: ...
```

### [Sub-Module 3.2] Class, Section & Timetable Generator

- **Purpose & Responsibility:** Produce a coherent academic structure — grades, sections, subjects, teacher-subject-section assignments, and a conflict-free weekly timetable.
- **Cohesion Type:** Functional (structural/scheduling generation only).
- **Inputs:** `GenerateAcademicStructureRequestDTO(tenant_id, grade_levels: list[int], sections_per_grade: int, subjects: list[str], periods_per_day: int)`
- **Outputs:** `AcademicStructureDTO(classes: list[ClassSectionDTO], timetable_entries: list[TimetableEntryDTO])`
- **Dependencies:** `IStaffRepository` (read-only, to assign real generated teacher IDs to periods — respects module boundary via facade, doesn't reach into Module 2.0's tables)
- **Dummy Data Mocking Strategy:** Constraint-satisfaction generator ensures no teacher is double-booked in the same period and no section has two simultaneous subjects — produces *usable*, not just random, timetables.

**[Function 3.2.1]**
```python
class AcademicStructureGenerator:
    def generate_class_sections(self, request: GenerateAcademicStructureRequestDTO) -> list[ClassSectionDTO]: ...
    def generate_timetable(self, class_sections: list[ClassSectionDTO], available_teachers: list[TeacherSummaryDTO]) -> list[TimetableEntryDTO]: ...
    def _resolve_scheduling_conflicts(self, draft_entries: list[TimetableEntryDTO]) -> list[TimetableEntryDTO]: ...
```

### [Sub-Module 3.3] Dummy Attendance Ingestion Source *(Phase-2-swap boundary)*

- **Purpose & Responsibility:** Implements `IAttendanceIngestionSource` to simulate daily attendance events — the exact interface a future camera/OCR pipeline will implement.
- **Cohesion Type:** Functional (simulated ingestion only; does NOT persist — that's Module 5.0's job. This module only *produces* raw attendance signal).
- **Inputs:** `SimulateAttendanceRequestDTO(tenant_id, class_section_id, date, attendance_rate: float = 0.93)`
- **Outputs:** `list[RawAttendanceSignalDTO(student_id, timestamp, status, confidence_score, source="DUMMY_GENERATOR")]`
- **Dependencies:** None beyond the interface it implements (`IAttendanceIngestionSource`) — this is the textbook example of Strategy Pattern replaceability.
- **Dummy Data Mocking Strategy:** Weighted-random status generator (Present/Absent/Late) using a configurable `attendance_rate`, with realistic patterns (e.g., higher absenteeism on Mondays/Fridays, occasional multi-day absence streaks to simulate illness) rather than pure uniform randomness.

**[Function 3.3.1]**
```python
class DummyAttendanceIngestionSource:  # implements IAttendanceIngestionSource
    def fetch_daily_signals(self, request: SimulateAttendanceRequestDTO) -> list[RawAttendanceSignalDTO]: ...
    def _apply_realistic_absence_pattern(self, student_ids: list[UUID], date: date) -> dict[UUID, str]: ...

# The interface this satisfies (declared in Module 5.0's application layer):
class IAttendanceIngestionSource(Protocol):
    def fetch_daily_signals(self, request: SimulateAttendanceRequestDTO) -> list[RawAttendanceSignalDTO]: ...
```

### [Sub-Module 3.4] Dummy Fee Transaction Generator

- **Purpose & Responsibility:** Backfill historically plausible fee invoices, partial payments, overdue records, and payment-gateway transaction logs.
- **Cohesion Type:** Functional (financial data simulation only).
- **Inputs:** `GenerateFeeHistoryRequestDTO(tenant_id, student_ids, terms, fee_structure: FeeStructureDTO, on_time_payment_rate: float = 0.8)`
- **Outputs:** `list[SyntheticFeeTransactionDTO(invoice_id, student_id, amount_due, amount_paid, due_date, paid_date, status, payment_method)]`
- **Dependencies:** `IPaymentGatewayStrategy` (uses the `DummyGatewayAdapter` concretely, §1.3.1 — reuses the real strategy interface rather than inventing a parallel fake path)
- **Dummy Data Mocking Strategy:** Simulates realistic payment-method distribution (UPI/Card/Cash/Bank Transfer weighted by locale) and a configurable defaulter percentage to stress-test the Fee Management dashboards' overdue-alerts logic.

**[Function 3.4.1]**
```python
class FeeHistoryGenerator:
    def generate_invoices(self, request: GenerateFeeHistoryRequestDTO) -> list[SyntheticFeeTransactionDTO]: ...
    def _simulate_payment_behavior(self, invoice: SyntheticFeeTransactionDTO, on_time_rate: float) -> SyntheticFeeTransactionDTO: ...
```

### [Sub-Module 3.5] Seed Orchestrator / CLI

- **Purpose & Responsibility:** Single entry-point management command that composes 3.1–3.4 in correct dependency order to stand up a fully populated demo tenant in one call.
- **Cohesion Type:** Functional (orchestration only — contains no generation logic itself, purely sequences calls to the other sub-modules).
- **Inputs:** CLI args / `SeedTenantRequestDTO(tenant_id, student_count, staff_count, historical_days=90)`
- **Outputs:** `SeedSummaryDTO(students_created, staff_created, classes_created, attendance_records_created, fee_records_created, duration_seconds)`
- **Dependencies:** All Sub-Modules 3.1–3.4 via their interfaces; `IEventBus` (emits `TenantSeedCompletedEvent`)
- **Dummy Data Mocking Strategy:** N/A — this *is* the mocking orchestrator. Exposed as `python manage.py seed_demo_tenant --tenant=greenwood-high-001 --students=500 --days=90`.

**[Function 3.5.1]**
```python
class DemoTenantSeedOrchestrator:
    def run(self, request: SeedTenantRequestDTO) -> SeedSummaryDTO: ...
```

---

## [Module 4.0] Student & Academic Management Module

**Bounded Context Responsibility:** Owns the academic system-of-record — student enrollment, class/section assignment, subject curriculum, grading, and academic records. Consumes identity from Module 2.0 via `UserProfileDTO`, never owns login credentials itself.

### [Sub-Module 4.1] Student Enrollment & Profile Service

- **Purpose & Responsibility:** Manage the student academic profile (roll number, grade, section, guardian linkage, enrollment status) as distinct from the generic `UserProfileDTO` identity record.
- **Cohesion Type:** Functional (academic profile only; login/identity concerns stay in Module 2.0).
- **Inputs:** `EnrollStudentRequestDTO(user_id, grade_level, section_id, roll_number, guardian_user_ids, admission_date)`
- **Outputs:** `StudentAcademicProfileDTO(student_id, user_id, roll_number, grade_level, section_id, enrollment_status, guardian_links)`
- **Dependencies:** `IStudentRepository`, `UserProfileService` facade (§2.3, read-only call for identity fields), `IEventBus` (publishes `StudentEnrolledEvent`)
- **Dummy Data Mocking Strategy:** Consumes `SyntheticIdentityDTO` output from Module 3.1 and cross-links to generated `ClassSectionDTO` from Module 3.2 to build a coherent, queryable roster.

**[Function 4.1.1]**
```python
class StudentEnrollmentService:
    def enroll_student(self, request: EnrollStudentRequestDTO) -> ResultDTO[StudentAcademicProfileDTO]: ...
    def transfer_section(self, student_id: UUID, new_section_id: UUID, reason: str) -> ResultDTO[None]: ...
    def get_academic_profile(self, student_id: UUID) -> ResultDTO[StudentAcademicProfileDTO]: ...
    def get_class_roster(self, section_id: UUID) -> list[StudentAcademicProfileDTO]: ...
```

### [Sub-Module 4.2] Class, Section & Subject Curriculum Management

- **Purpose & Responsibility:** CRUD for the academic structure entities (grades, sections, subjects, subject-teacher assignments) — the persisted counterpart to what Module 3.2 generates synthetically.
- **Cohesion Type:** Functional (structural CRUD only, no scheduling logic — that's 4.3).
- **Inputs:** `CreateSectionRequestDTO`, `AssignSubjectTeacherRequestDTO(section_id, subject_id, teacher_user_id)`
- **Outputs:** `ClassSectionDTO`, `SubjectDTO`, `ResultDTO[None]`
- **Dependencies:** `IClassSectionRepository`, `ISubjectRepository`
- **Dummy Data Mocking Strategy:** Seeded directly from Module 3.2 output at tenant creation time.

**[Function 4.2.1]**
```python
class AcademicStructureService:
    def create_section(self, request: CreateSectionRequestDTO) -> ResultDTO[ClassSectionDTO]: ...
    def assign_subject_teacher(self, request: AssignSubjectTeacherRequestDTO) -> ResultDTO[None]: ...
    def list_subjects_for_grade(self, grade_level: int) -> list[SubjectDTO]: ...
```

### [Sub-Module 4.3] Timetable Query Service

- **Purpose & Responsibility:** Read-optimized query layer over timetable data for Web/Mobile display (today's schedule, weekly view, teacher's personal schedule) — deliberately separated from the generation logic (3.2) and structural CRUD (4.2) per functional cohesion.
- **Cohesion Type:** Functional (read/query only).
- **Inputs:** `GetTimetableRequestDTO(scope: "SECTION"|"TEACHER"|"STUDENT", scope_id: UUID, date_range: DateRangeDTO)`
- **Outputs:** `list[TimetableEntryDTO(period_number, subject_name, teacher_name, start_time, end_time, room)]`
- **Dependencies:** `ITimetableRepository`
- **Dummy Data Mocking Strategy:** Reads directly from Module 3.2-generated data; no separate mock needed since this is a pure query layer.

**[Function 4.3.1]**
```python
class TimetableQueryService:
    def get_timetable(self, request: GetTimetableRequestDTO) -> list[TimetableEntryDTO]: ...
    def get_todays_schedule(self, scope: str, scope_id: UUID) -> list[TimetableEntryDTO]: ...
```

### [Sub-Module 4.4] Grading & Academic Records Service

- **Purpose & Responsibility:** Record and retrieve exam/assessment scores, compute term GPA/percentage per the tenant's `GradingPolicy` (§2.1), and generate report-card-ready data.
- **Cohesion Type:** Functional (grading computation and storage only — PDF rendering lives in Module 9.0).
- **Inputs:** `RecordAssessmentScoreRequestDTO(student_id, subject_id, assessment_type, score, max_score, term_id)`
- **Outputs:** `AssessmentRecordDTO`, `TermReportCardDataDTO(student_id, term_id, subject_scores: list, computed_grade, gpa_or_percentage)`
- **Dependencies:** `IAssessmentRepository`, `ITenantConfigProvider` (reads `GradingPolicy` — grade bands are never hardcoded in this service)
- **Dummy Data Mocking Strategy:** `AssessmentScoreGenerator` (extension of Module 3.0) produces a normal-distributed score spread per subject per student across 2–3 terms.

**[Function 4.4.1]**
```python
class GradingService:
    def __init__(self, assessment_repo: IAssessmentRepository, tenant_config: ITenantConfigProvider): ...
    def record_score(self, request: RecordAssessmentScoreRequestDTO) -> ResultDTO[AssessmentRecordDTO]: ...
    def compute_term_report(self, student_id: UUID, term_id: UUID) -> ResultDTO[TermReportCardDataDTO]: ...
    def _apply_grading_policy(self, raw_percentage: Decimal, policy: GradingPolicy) -> str: ...
```

---

## [Module 5.0] Attendance Management Module (Dummy Ingestion & Manual Override)

**Bounded Context Responsibility:** Owns the attendance system-of-record. Ingests raw signals from a pluggable `IAttendanceIngestionSource` (Dummy today, CV/OCR in Phase 2 — **zero code change required in this module when that swap happens**), persists authoritative attendance state, and supports manual teacher override.

### [Sub-Module 5.1] Attendance Ingestion Orchestrator

- **Purpose & Responsibility:** Pull raw signals from whichever `IAttendanceIngestionSource` is DI-wired for the tenant, validate against the roster, and hand off to persistence — the orchestration seam where Phase 2's CV pipeline plugs in.
- **Cohesion Type:** Functional (orchestration only; no persistence logic — delegates to 5.2).
- **Inputs:** `IngestDailyAttendanceRequestDTO(tenant_id, class_section_id, date)`
- **Outputs:** `ResultDTO[IngestionSummaryDTO(signals_received, records_created, anomalies_flagged)]`
- **Dependencies:** `IAttendanceIngestionSource` (§3.3 — **this is the exact interface boundary Phase 2 replaces**), `AttendanceRecordService` (5.2, facade call)
- **Dummy Data Mocking Strategy:** In Phase 1, DI container resolves `IAttendanceIngestionSource` → `DummyAttendanceIngestionSource` (Module 3.3). Config flag `biometric_attendance_enabled` (§2.1) is the documented Phase-2 cutover switch — flipping it swaps the DI binding to `CVPipelineAttendanceSource`, no other code touched.

**[Function 5.1.1]**
```python
class AttendanceIngestionOrchestrator:
    def __init__(self, ingestion_source: IAttendanceIngestionSource, record_service: "AttendanceRecordService"): ...
    def ingest_for_date(self, request: IngestDailyAttendanceRequestDTO) -> ResultDTO[IngestionSummaryDTO]: ...
    def _flag_anomalies(self, signals: list[RawAttendanceSignalDTO], roster: list[StudentAcademicProfileDTO]) -> list[AttendanceAnomalyDTO]: ...
```

### [Sub-Module 5.2] Attendance Record Persistence & Query Service

- **Purpose & Responsibility:** Authoritative CRUD over the `AttendanceRecord` aggregate; single source of truth queried by Analytics (9.0), Notification (7.0 — absence alerts), and AI Engine (8.0) read-only views.
- **Cohesion Type:** Functional (persistence + query, no ingestion or override-approval logic).
- **Inputs:** `PersistAttendanceRecordsRequestDTO(records: list[AttendanceRecordDTO])`, `GetAttendanceRequestDTO(scope, scope_id, date_range)`
- **Outputs:** `ResultDTO[int]` (records persisted), `list[AttendanceRecordDTO(student_id, date, status, marked_by, source, period_number)]`
- **Dependencies:** `IAttendanceRepository`, `IEventBus` (publishes `AttendanceMarkedEvent`, `StudentAbsentEvent` per record for Module 7.0 to consume)
- **Dummy Data Mocking Strategy:** N/A — pure persistence layer, agnostic to whether upstream data was dummy or real.

**[Function 5.2.1]**
```python
class AttendanceRecordService:
    def persist_records(self, request: PersistAttendanceRecordsRequestDTO) -> ResultDTO[int]: ...
    def get_attendance(self, request: GetAttendanceRequestDTO) -> list[AttendanceRecordDTO]: ...
    def get_student_attendance_summary(self, student_id: UUID, term_id: UUID) -> AttendanceSummaryDTO: ...
```

### [Sub-Module 5.3] Manual Override & Correction Service

- **Purpose & Responsibility:** Allow a Teacher/Admin to correct an ingested (dummy or real) attendance record, with a mandatory audit trail — deliberately isolated from 5.2 so override permissions/validation don't bloat the core persistence service.
- **Cohesion Type:** Functional (override workflow + approval only).
- **Inputs:** `OverrideAttendanceRequestDTO(record_id, new_status, overridden_by, justification)`
- **Outputs:** `ResultDTO[AttendanceRecordDTO]`
- **Dependencies:** `IAttendanceRepository`, `RBACService` facade (§2.2, checks `attendance.override` permission), `AuditLogService` facade (§1.4, mandatory audit entry)
- **Dummy Data Mocking Strategy:** QA seed script randomly flags ~2% of generated dummy records as "pending teacher review" to exercise the override UI without manual setup.

**[Function 5.3.1]**
```python
class AttendanceOverrideService:
    def override_record(self, request: OverrideAttendanceRequestDTO) -> ResultDTO[AttendanceRecordDTO]: ...
    def get_pending_review_records(self, section_id: UUID) -> list[AttendanceRecordDTO]: ...
```

### [Sub-Module 5.4] Attendance Anomaly & Alert Detection

- **Purpose & Responsibility:** Detect patterns (consecutive absences, sudden drop in attendance rate) and emit domain events for Module 7.0 to notify parents — contains detection logic only, never sends notifications itself.
- **Cohesion Type:** Functional (pattern detection, decoupled from delivery mechanism via event bus).
- **Inputs:** Triggered by `AttendanceMarkedEvent` subscription (async).
- **Outputs:** Publishes `ConsecutiveAbsenceDetectedEvent(student_id, consecutive_days, threshold_breached)`
- **Dependencies:** `IAttendanceRepository` (read), `IEventBus` (subscribe + publish)
- **Dummy Data Mocking Strategy:** Dummy generator's realistic absence-streak simulation (§3.3) is specifically designed to trigger this detector during demos.

**[Function 5.4.1]**
```python
class AttendanceAnomalyDetector:
    def on_attendance_marked(self, event: AttendanceMarkedEvent) -> None: ...
    def _check_consecutive_absence_threshold(self, student_id: UUID) -> int: ...
```

---

## [Module 6.0] Fee Management & Payment Gateway Module (Strategy Pattern)

**Bounded Context Responsibility:** Owns fee structure definition, invoice generation, payment collection (via pluggable `IPaymentGatewayStrategy`, §1.3.1), and reconciliation. No other module ever touches the `Invoice` or `Payment` tables directly.

### [Sub-Module 6.1] Fee Structure Configuration Service

- **Purpose & Responsibility:** Define per-grade, per-term fee heads (tuition, transport, lab, library) as tenant-configurable data — never hardcoded amounts in code.
- **Cohesion Type:** Functional (configuration CRUD only).
- **Inputs:** `DefineFeeStructureRequestDTO(tenant_id, grade_level, term_id, fee_heads: list[FeeHeadDTO(name, amount, is_optional)])`
- **Outputs:** `FeeStructureDTO`
- **Dependencies:** `IFeeStructureRepository`
- **Dummy Data Mocking Strategy:** Seeded with a realistic Indian-school fee head mix (Tuition, Transport, Lab, Library, Annual Day fund) with plausible amounts, consumed directly by Module 3.4's generator.

**[Function 6.1.1]**
```python
class FeeStructureService:
    def define_structure(self, request: DefineFeeStructureRequestDTO) -> ResultDTO[FeeStructureDTO]: ...
    def get_structure_for_grade(self, grade_level: int, term_id: UUID) -> FeeStructureDTO: ...
```

### [Sub-Module 6.2] Invoice Generation & Ledger Service

- **Purpose & Responsibility:** Generate per-student invoices from a `FeeStructureDTO`, track payment status, maintain the running ledger — pure bookkeeping, zero payment-processing logic (that's 6.3).
- **Cohesion Type:** Functional (ledger/bookkeeping only).
- **Inputs:** `GenerateInvoicesRequestDTO(section_id, fee_structure_id, due_date)`
- **Outputs:** `list[InvoiceDTO(invoice_id, student_id, amount_due, amount_paid, balance, due_date, status)]`
- **Dependencies:** `IInvoiceRepository`, `IEventBus` (publishes `InvoiceGeneratedEvent`, consumed by Module 7.0 for due-date reminders)
- **Dummy Data Mocking Strategy:** Bulk-populated by Module 3.4's `FeeHistoryGenerator`.

**[Function 6.2.1]**
```python
class InvoiceLedgerService:
    def generate_invoices_for_section(self, request: GenerateInvoicesRequestDTO) -> ResultDTO[list[InvoiceDTO]]: ...
    def get_student_ledger(self, student_id: UUID) -> list[InvoiceDTO]: ...
    def get_overdue_invoices(self, tenant_id: UUID, as_of_date: date) -> list[InvoiceDTO]: ...
    def _apply_payment_to_invoice(self, invoice_id: UUID, amount: Decimal) -> ResultDTO[InvoiceDTO]: ...
```

### [Sub-Module 6.3] Payment Processing Service (Strategy Consumer)

- **Purpose & Responsibility:** Orchestrate payment initiation/verification through whichever `IPaymentGatewayStrategy` the tenant is configured for (§2.1 `payment_gateway_provider`) — this service **never** imports Razorpay/Stripe SDKs directly.
- **Cohesion Type:** Functional (payment orchestration only; delegates ledger updates to 6.2 via facade call, doesn't touch invoice tables itself).
- **Inputs:** `InitiatePaymentRequestDTO(invoice_id, amount, payer_contact)`
- **Outputs:** `ResultDTO[PaymentInitiationResponseDTO]`
- **Dependencies:** `IPaymentGatewayStrategy` (resolved per-tenant via `IGatewayResolver` factory), `InvoiceLedgerService` (6.2, facade), `IEventBus` (publishes `FeePaymentReceivedEvent`)
- **Dummy Data Mocking Strategy:** `DummyGatewayAdapter` implements the full `IPaymentGatewayStrategy` interface with simulated latency and a configurable success/failure rate — lets Web/Mobile build the entire payment UX (including failure states) without any real gateway account.

**[Function 6.3.1]**
```python
class PaymentProcessingService:
    def __init__(self, gateway_resolver: "IGatewayResolver", ledger_service: InvoiceLedgerService, event_bus: IEventBus): ...
    def initiate_payment(self, request: InitiatePaymentRequestDTO) -> ResultDTO[PaymentInitiationResponseDTO]: ...
    def handle_gateway_webhook(self, provider_name: str, raw_payload: bytes, signature: str) -> ResultDTO[None]: ...
    def process_refund(self, invoice_id: UUID, amount: Decimal, reason: str) -> ResultDTO[PaymentVerificationResponseDTO]: ...

class IGatewayResolver(Protocol):
    def resolve(self, tenant_id: str) -> IPaymentGatewayStrategy: ...
```

```python
# modules/fee_management/infrastructure/gateways/dummy_gateway.py
class DummyGatewayAdapter:  # implements IPaymentGatewayStrategy
    provider_name = "dummy_gateway"
    def __init__(self, simulated_success_rate: float = 0.92, simulated_latency_ms: int = 800): ...
    def initiate_payment(self, request: PaymentInitiationRequestDTO) -> PaymentInitiationResponseDTO: ...
    def verify_payment(self, provider_reference_id: str) -> PaymentVerificationResponseDTO: ...
    def process_refund(self, provider_reference_id: str, amount: Decimal) -> PaymentVerificationResponseDTO: ...
    def handle_webhook(self, raw_payload: bytes, signature_header: str) -> PaymentVerificationResponseDTO: ...
```

### [Sub-Module 6.4] Reconciliation & Defaulter Reporting Service

- **Purpose & Responsibility:** Daily reconciliation job matching gateway settlement reports against internal ledger; produces the defaulter list consumed by Module 9.0's dashboards.
- **Cohesion Type:** Functional (reconciliation/reporting logic only).
- **Inputs:** `ReconcileSettlementRequestDTO(date, provider_name)`
- **Outputs:** `ReconciliationReportDTO(matched_count, mismatched_count, mismatches: list[LedgerMismatchDTO])`
- **Dependencies:** `IPaymentGatewayStrategy`, `IInvoiceRepository`
- **Dummy Data Mocking Strategy:** `DummyGatewayAdapter` exposes a `get_settlement_report(date)` test-only method producing a synthetic settlement file matching ~98% of generated transactions (2% deliberate mismatch to exercise reconciliation-alert UI).

**[Function 6.4.1]**
```python
class ReconciliationService:
    def run_daily_reconciliation(self, request: ReconcileSettlementRequestDTO) -> ReconciliationReportDTO: ...
    def get_defaulters_list(self, tenant_id: UUID, grace_period_days: int) -> list[DefaulterDTO]: ...
```

---

## [Module 7.0] Parent Notification & Communication Engine (Strategy Pattern)

**Bounded Context Responsibility:** Owns all outbound communication — templated, multi-channel, event-driven. Never triggered by direct calls from business modules; **exclusively** reacts to domain events published on `IEventBus`, keeping it fully decoupled (Attendance and Fee modules have zero import dependency on this module).

### [Sub-Module 7.1] Notification Template Registry

- **Purpose & Responsibility:** Single source of truth for message copy per template key/locale/channel — so no module ever inlines a notification string.
- **Cohesion Type:** Functional (template storage/resolution only).
- **Inputs:** `GetTemplateRequestDTO(template_key, channel, locale)`
- **Outputs:** `ResolvedTemplateDTO(subject, body, variables_expected: list[str])`
- **Dependencies:** `ITemplateRepository`
- **Dummy Data Mocking Strategy:** Seeded with standard templates (`attendance.absent_alert`, `fee.payment_reminder`, `fee.payment_success`, `academic.report_card_published`) in tenant-neutral copy, with `{{school_display_name}}` variables resolved from `TenantConfigDTO` at render time — never a hardcoded school name in the template.

**[Function 7.1.1]**
```python
class NotificationTemplateService:
    def get_resolved_template(self, request: GetTemplateRequestDTO) -> ResolvedTemplateDTO: ...
    def render(self, template: ResolvedTemplateDTO, variables: dict) -> RenderedMessageDTO: ...
```

### [Sub-Module 7.2] Event-Driven Notification Router (Strategy Consumer)

- **Purpose & Responsibility:** Subscribes to domain events from other modules (`StudentAbsentEvent`, `FeePaymentReceivedEvent`, `ConsecutiveAbsenceDetectedEvent`) and routes to the correct `INotificationProvider` per recipient's channel preference and tenant feature flags.
- **Cohesion Type:** Functional (routing/orchestration only — delivery mechanics live in 7.3's provider adapters).
- **Inputs:** Subscribed `DomainEvent` instances (async).
- **Outputs:** `NotificationDispatchResultDTO` (logged, not directly returned — this is event-driven, not request/response)
- **Dependencies:** `IEventBus` (subscribe), `INotificationProvider` (resolved per channel via `IProviderResolver`), `NotificationTemplateService` (7.1, facade), `ITenantConfigProvider` (feature-flag gated: e.g., skip WhatsApp if `whatsapp_notifications_enabled=False`)
- **Dummy Data Mocking Strategy:** `DummyChannelProvider` logs would-be notifications to a `notification_outbox` table instead of real dispatch, viewable in an admin debug panel — lets QA verify "the right event triggered the right message" without a live Twilio/Sendgrid account.

**[Function 7.2.1]**
```python
class NotificationRouter:
    def __init__(self, provider_resolver: "IProviderResolver", template_service: NotificationTemplateService, tenant_config: ITenantConfigProvider): ...
    def on_student_absent(self, event: "StudentAbsentEvent") -> None: ...
    def on_fee_payment_received(self, event: FeePaymentReceivedEvent) -> None: ...
    def on_consecutive_absence_detected(self, event: "ConsecutiveAbsenceDetectedEvent") -> None: ...
    def _dispatch(self, request: NotificationRequestDTO) -> NotificationDispatchResultDTO: ...

class IProviderResolver(Protocol):
    def resolve(self, tenant_id: str, channel: NotificationChannel) -> INotificationProvider: ...
```

### [Sub-Module 7.3] Channel Provider Adapters

- **Purpose & Responsibility:** Concrete `INotificationProvider` implementations per channel — each adapter's *only* job is translating a `NotificationRequestDTO` into a specific third-party API call.
- **Cohesion Type:** Functional (one adapter class = one channel = one responsibility).
- **Inputs:** `NotificationRequestDTO`
- **Outputs:** `NotificationDispatchResultDTO`
- **Dependencies:** Third-party SDKs (Twilio, SendGrid, FCM, WhatsApp Cloud API) — isolated entirely within this sub-module, never leaking their SDK types outward.
- **Dummy Data Mocking Strategy:** `DummyChannelProvider` (implements `INotificationProvider` for all channels) used in dev/staging; production DI config swaps in real adapters per tenant's `notification_providers` config map (§2.1).

**[Function 7.3.1]**
```python
class DummyChannelProvider:  # implements INotificationProvider
    channel: NotificationChannel
    def send(self, request: NotificationRequestDTO) -> NotificationDispatchResultDTO: ...
    def get_delivery_status(self, dispatch_id: str) -> str: ...

class TwilioSmsProvider:  # implements INotificationProvider, channel = SMS
    def send(self, request: NotificationRequestDTO) -> NotificationDispatchResultDTO: ...

class FcmPushProvider:  # implements INotificationProvider, channel = PUSH
    def send(self, request: NotificationRequestDTO) -> NotificationDispatchResultDTO: ...
```

### [Sub-Module 7.4] In-App Communication & Broadcast Service

- **Purpose & Responsibility:** Principal/Admin-authored broadcast announcements (e.g., "school closed tomorrow") targeted by role/grade/section — distinct from event-triggered transactional notifications (7.2).
- **Cohesion Type:** Functional (author-initiated broadcast, not event-reactive).
- **Inputs:** `CreateBroadcastRequestDTO(tenant_id, author_id, title, body, target_scope: BroadcastScopeDTO, channels: list[NotificationChannel])`
- **Outputs:** `BroadcastDTO(broadcast_id, recipient_count, dispatch_status)`
- **Dependencies:** `IBroadcastRepository`, `NotificationRouter` (7.2, facade call to fan out), `UserProfileService` facade (resolve target audience)
- **Dummy Data Mocking Strategy:** Demo seed includes 2–3 sample past broadcasts (e.g., "PTM scheduled", "Holiday notice") for dashboard realism.

**[Function 7.4.1]**
```python
class BroadcastCommunicationService:
    def create_broadcast(self, request: CreateBroadcastRequestDTO) -> ResultDTO[BroadcastDTO]: ...
    def get_broadcast_history(self, tenant_id: UUID, filters: BroadcastFilterDTO) -> PaginatedDTO[BroadcastDTO]: ...
```

---

## [Module 8.0] AI Text-to-SQL Conversational Analytics Engine (Read-Only RAG)

**Bounded Context Responsibility:** Translates natural-language questions from Admin/Principal users into safe, tenant-scoped, read-only SQL queries and returns conversational + tabular answers. Connects via a **strictly read-only DB role/connection**, and never shares this connection with any write-capable module — a hard infrastructure boundary, not just a code-level one.

### [Sub-Module 8.1] Read-Only Database Connection & Schema Introspection Gateway

- **Purpose & Responsibility:** Owns the isolated read-only PostgreSQL connection (separate `pg_role` with `SELECT`-only grants, no `INSERT/UPDATE/DELETE`, and **row-level security scoped to `tenant_id`**) and exposes a vetted, curated schema subset to the LLM — never the full schema (excludes `auth_credentials`, `payment_gateway_secrets`, etc.).
- **Cohesion Type:** Functional (connection + schema-exposure gatekeeping only, zero query-generation logic).
- **Inputs:** N/A (infra bootstrap) / `GetQueryableSchemaRequestDTO(tenant_id)`
- **Outputs:** `QueryableSchemaDTO(tables: list[TableSchemaDTO(name, columns, description)])`
- **Dependencies:** Dedicated read-replica or RLS-scoped connection pool (`READ_ONLY_ANALYTICS_DB_URL`, distinct env var from the main app DB URL)
- **Dummy Data Mocking Strategy:** N/A — this sub-module governs access to whatever data exists (dummy or real); it has no generation responsibility itself, by design (keeps it identical in Phase 1 and Phase 2).

**[Function 8.1.1]**
```python
class ReadOnlySchemaGateway:
    def __init__(self, readonly_connection_pool: "ConnectionPool"): ...
    def get_queryable_schema(self, tenant_id: str) -> QueryableSchemaDTO: ...
    def _apply_column_allowlist(self, raw_schema: dict) -> dict: ...  # strips PII/secret columns before ever reaching the LLM prompt
```

### [Sub-Module 8.2] Natural Language → SQL Translation Service (Vanna.ai / LangChain)

- **Purpose & Responsibility:** Given a user's question + the allowlisted schema (8.1) + few-shot examples, produce a single validated, tenant-scoped `SELECT` statement. Contains zero database execution logic (that's 8.3).
- **Cohesion Type:** Functional (translation only).
- **Inputs:** `NLQueryRequestDTO(tenant_id, user_id, question: str, conversation_history: list[ChatTurnDTO])`
- **Outputs:** `ResultDTO[GeneratedSQLDTO(sql_statement, confidence_score, referenced_tables, explanation)]`
- **Dependencies:** `ILLMProvider` (abstracts Vanna.ai/LangChain + underlying model choice — itself swappable), `ReadOnlySchemaGateway` (8.1, facade)
- **Dummy Data Mocking Strategy:** Vanna's RAG training set is seeded with the dummy tenant's realistic schema + a curated set of Q&A training pairs (e.g., "How many students were absent yesterday?" → correct SQL pattern) so the assistant demos well against the synthetic dataset from Module 3.0.

**[Function 8.2.1]**
```python
class TextToSQLService:
    def __init__(self, llm_provider: "ILLMProvider", schema_gateway: ReadOnlySchemaGateway): ...
    def generate_sql(self, request: NLQueryRequestDTO) -> ResultDTO[GeneratedSQLDTO]: ...
    def _inject_tenant_scope_filter(self, sql: str, tenant_id: str) -> str: ...  # forcibly appends WHERE tenant_id = :tenant_id
```

### [Sub-Module 8.3] Query Validation & Guarded Execution Service

- **Purpose & Responsibility:** The **security gate** — validates generated SQL against an allowlist (SELECT-only, no `DROP`/`DELETE`/`UPDATE`/`;`-stacked statements, mandatory `tenant_id` predicate, row-limit cap) before ever executing it, then runs it on the read-only connection.
- **Cohesion Type:** Functional (validation + guarded execution, deliberately separated from generation so a prompt-injection attempt in 8.2 still can't reach the DB with a destructive statement).
- **Inputs:** `GeneratedSQLDTO`
- **Outputs:** `ResultDTO[QueryExecutionResultDTO(rows: list[dict], row_count, truncated: bool, execution_time_ms)]`
- **Dependencies:** `ReadOnlySchemaGateway` (8.1, uses its connection pool), `ISQLValidator`
- **Dummy Data Mocking Strategy:** N/A — executes against whatever data is present; validation logic is tested with adversarial prompt-injection fixtures regardless of underlying data being dummy or real.

**[Function 8.3.1]**
```python
class GuardedQueryExecutor:
    def validate_and_execute(self, generated: GeneratedSQLDTO, tenant_id: str) -> ResultDTO[QueryExecutionResultDTO]: ...
    def _is_statement_safe(self, sql: str) -> bool: ...  # AST-level check via sqlparse/sqlglot, not regex
    def _enforce_row_limit(self, sql: str, max_rows: int = 500) -> str: ...
```

### [Sub-Module 8.4] Conversational Response Composer

- **Purpose & Responsibility:** Turn raw query results (8.3) into a natural-language answer + optional chart-ready DTO for the frontend — the only sub-module that talks back to the user in prose.
- **Cohesion Type:** Functional (response composition only).
- **Inputs:** `QueryExecutionResultDTO`, original `question: str`
- **Outputs:** `ConversationalAnswerDTO(narrative_answer: str, data_table: TableDataDTO | None, suggested_chart_type: str | None, follow_up_suggestions: list[str])`
- **Dependencies:** `ILLMProvider` (summarization call, same abstraction as 8.2 — different prompt)
- **Dummy Data Mocking Strategy:** Same synthetic dataset; response quality is evaluated against a fixed eval set of Q&A pairs run in CI (`tests/ai_engine/eval_qa_pairs.yaml`).

**[Function 8.4.1]**
```python
class ConversationalAnswerComposer:
    def compose(self, execution_result: QueryExecutionResultDTO, original_question: str) -> ConversationalAnswerDTO: ...
```

**[Endpoint 8.5]** `POST /api/v1/ai-analytics/ask` → orchestrates 8.2 → 8.3 → 8.4 in sequence, wrapped in a single Application Service (`ConversationalAnalyticsFacade`) so the API layer never calls sub-modules individually.

```python
class ConversationalAnalyticsFacade:
    def __init__(self, translator: TextToSQLService, executor: GuardedQueryExecutor, composer: ConversationalAnswerComposer): ...
    def ask(self, request: NLQueryRequestDTO) -> ResultDTO[ConversationalAnswerDTO]: ...
```

---

## [Module 9.0] Analytics & Reporting Engine (Visualizations & Exports)

**Bounded Context Responsibility:** Pre-aggregated, dashboard-ready analytics (distinct from Module 8.0's ad-hoc conversational queries) plus static export generation (PDF report cards, Excel fee reports). Reads from other modules **exclusively** via their read-facade DTOs, never via cross-module SQL joins.

### [Sub-Module 9.1] Attendance Analytics Aggregation Service

- **Purpose & Responsibility:** Pre-compute attendance KPIs (daily/weekly/term attendance rate, per-section comparison, trend lines) for the Admin dashboard — heavy aggregation kept out of Module 5.0 to keep that module's cohesion strictly "record management."
- **Cohesion Type:** Functional (attendance-specific aggregation only).
- **Inputs:** `GetAttendanceAnalyticsRequestDTO(tenant_id, scope, date_range, granularity: "DAY"|"WEEK"|"MONTH")`
- **Outputs:** `AttendanceAnalyticsDTO(time_series: list[DataPointDTO], overall_rate, section_comparison: list[SectionRateDTO])`
- **Dependencies:** `AttendanceRecordService` facade (§5.2, read-only)
- **Dummy Data Mocking Strategy:** Consumes 90 days of Module 3.3-generated data (seeded with realistic weekday/absence patterns) to produce demo-ready, non-flat trend charts.

**[Function 9.1.1]**
```python
class AttendanceAnalyticsService:
    def get_analytics(self, request: GetAttendanceAnalyticsRequestDTO) -> AttendanceAnalyticsDTO: ...
```

### [Sub-Module 9.2] Fee Collection Analytics Service

- **Purpose & Responsibility:** Collection-rate KPIs, overdue aging buckets, payment-method distribution charts.
- **Cohesion Type:** Functional (fee-specific aggregation only).
- **Inputs:** `GetFeeAnalyticsRequestDTO(tenant_id, term_id)`
- **Outputs:** `FeeAnalyticsDTO(total_collected, total_outstanding, aging_buckets: list[AgingBucketDTO], payment_method_breakdown: dict)`
- **Dependencies:** `InvoiceLedgerService` facade (§6.2, read-only), `ReconciliationService` facade (§6.4)
- **Dummy Data Mocking Strategy:** Module 3.4's configurable `on_time_payment_rate` produces realistic aging-bucket distribution out of the box.

**[Function 9.2.1]**
```python
class FeeAnalyticsService:
    def get_analytics(self, request: GetFeeAnalyticsRequestDTO) -> FeeAnalyticsDTO: ...
```

### [Sub-Module 9.3] Academic Performance Analytics Service

- **Purpose & Responsibility:** Grade distribution, subject-wise performance trends, top/at-risk student identification.
- **Cohesion Type:** Functional (academic-performance aggregation only).
- **Inputs:** `GetAcademicAnalyticsRequestDTO(tenant_id, term_id, scope)`
- **Outputs:** `AcademicAnalyticsDTO(grade_distribution: dict, subject_averages: list[SubjectAverageDTO], at_risk_students: list[StudentRiskDTO])`
- **Dependencies:** `GradingService` facade (§4.4, read-only)
- **Dummy Data Mocking Strategy:** Consumes Module 4.4's normal-distributed synthetic scores.

**[Function 9.3.1]**
```python
class AcademicAnalyticsService:
    def get_analytics(self, request: GetAcademicAnalyticsRequestDTO) -> AcademicAnalyticsDTO: ...
```

### [Sub-Module 9.4] Export & Document Generation Service

- **Purpose & Responsibility:** Render dashboard data and academic records into downloadable artifacts (PDF report cards, Excel fee statements, CSV data dumps) — pure rendering, no data-aggregation logic (consumes 9.1–9.3's DTOs as input).
- **Cohesion Type:** Functional (rendering/export only).
- **Inputs:** `GenerateReportCardPDFRequestDTO(student_id, term_id)`, `GenerateFeeExcelRequestDTO(tenant_id, term_id)`
- **Outputs:** `ExportedFileDTO(file_url, file_type, generated_at, expires_at)`
- **Dependencies:** `GradingService` facade (9.3 data), `IDocumentRenderer` (abstracts the PDF/Excel templating engine — swappable between e.g. WeasyPrint and a headless-Chrome renderer), `ITenantConfigProvider` (branded letterhead: logo, colors, school name pulled from theme tokens — **never hardcoded in the PDF template**)
- **Dummy Data Mocking Strategy:** Report-card and fee-statement templates render correctly against any of the pre-seeded demo tenants, proving the white-label branding pipeline end-to-end (§2.1 → rendered PDF letterhead).

**[Function 9.4.1]**
```python
class ExportDocumentService:
    def __init__(self, document_renderer: "IDocumentRenderer", tenant_config: ITenantConfigProvider): ...
    def generate_report_card_pdf(self, request: GenerateReportCardPDFRequestDTO) -> ResultDTO[ExportedFileDTO]: ...
    def generate_fee_statement_excel(self, request: GenerateFeeExcelRequestDTO) -> ResultDTO[ExportedFileDTO]: ...
    def _apply_tenant_letterhead(self, template_context: dict, theme: ThemeTokensDTO) -> dict: ...
```

### [Sub-Module 9.5] Dashboard Widget Composition Service

- **Purpose & Responsibility:** Assemble the role-specific dashboard payload (which widgets, in what order, respecting feature flags) consumed by Web/Mobile in a single call — avoids the frontend making 6 separate API calls per dashboard load.
- **Cohesion Type:** Functional (composition/orchestration only — delegates all actual computation to 9.1–9.3).
- **Inputs:** `GetDashboardRequestDTO(tenant_id, user_id, role_key)`
- **Outputs:** `DashboardPayloadDTO(widgets: list[WidgetDataDTO])`
- **Dependencies:** `AttendanceAnalyticsService`, `FeeAnalyticsService`, `AcademicAnalyticsService` (all as facades), `FeatureFlagService` facade (§1.3, to omit widgets for disabled features, e.g. no transport widget if `transport_module_enabled=False`)
- **Dummy Data Mocking Strategy:** N/A — pure composition of already-mocked upstream data.

**[Function 9.5.1]**
```python
class DashboardCompositionService:
    def get_dashboard(self, request: GetDashboardRequestDTO) -> DashboardPayloadDTO: ...
    def _select_widgets_for_role(self, role_key: str, feature_flags: dict[str, bool]) -> list[str]: ...
```

---

# SECTION 4: RECOMMENDED DIRECTORY STRUCTURE

Vertical Slice Architecture: each top-level module from Section 3 is a **self-contained folder** with its own `domain/`, `application/`, `infrastructure/`, and `api/` layers. No module folder imports another module's `infrastructure/` package — only its `application/interfaces` (facades/DTOs) or `shared_kernel`.

## 4.1 Backend (Django REST Framework / FastAPI)

```
backend/
├── manage.py
├── pyproject.toml
├── config/
│   ├── settings/
│   │   ├── base.py                    # infra-only settings (DB URL, secret key)
│   │   ├── local.py
│   │   ├── staging.py
│   │   └── production.py
│   ├── tenants/                        # SECTION 2.1 — isolated tenant configs
│   │   ├── schema.py                   # Pydantic TenantConfig contract
│   │   ├── greenwood_high.py
│   │   ├── st_marys.py
│   │   └── registry.py                 # ITenantConfigRepository impl (Phase 1: in-memory)
│   ├── di/
│   │   └── container.py                # global DI wiring — the ONLY place
│   │                                    # concrete adapters are bound to interfaces
│   └── urls.py                         # aggregates each module's api/urls.py
│
├── shared_kernel/                      # Module 1.0 lives partly here + core_infrastructure/
│   ├── contracts/
│   │   ├── base_dto.py                 # BaseDTO, ResultDTO, PaginatedDTO
│   │   └── base_event.py               # DomainEvent
│   ├── events/
│   │   ├── event_bus.py                # IEventBus + InProcessEventBus impl
│   │   └── event_registry.py
│   └── exceptions/
│       └── domain_exceptions.py
│
├── modules/
│   ├── core_infrastructure/            # [Module 1.0]
│   │   ├── domain/
│   │   ├── application/
│   │   │   ├── interfaces/
│   │   │   │   ├── theme_provider.py           # ITenantConfigProvider
│   │   │   │   └── tenant_config_repository.py # ITenantConfigRepository
│   │   │   └── services/
│   │   │       ├── tenant_config_service.py     # 1.2
│   │   │       ├── feature_flag_service.py       # 1.3
│   │   │       └── audit_log_service.py          # 1.4
│   │   ├── infrastructure/
│   │   │   ├── middleware/tenant_resolution.py   # 1.1
│   │   │   └── repositories/audit_log_repo.py
│   │   └── api/
│   │       ├── views.py
│   │       ├── serializers.py
│   │       └── urls.py
│   │
│   ├── identity_access/                # [Module 2.0]
│   │   ├── domain/entities/user.py
│   │   ├── application/
│   │   │   ├── interfaces/
│   │   │   │   ├── user_repository.py
│   │   │   │   ├── token_service.py
│   │   │   │   └── otp_provider.py
│   │   │   └── services/
│   │   │       ├── authentication_service.py   # 2.1
│   │   │       ├── rbac_service.py              # 2.2
│   │   │       ├── user_profile_service.py      # 2.3
│   │   │       └── mfa_service.py                # 2.4
│   │   ├── infrastructure/
│   │   │   ├── repositories/user_repository.py
│   │   │   ├── jwt_token_service.py
│   │   │   └── password_hasher.py
│   │   └── api/
│   │
│   ├── dummy_data_engine/               # [Module 3.0]
│   │   ├── application/
│   │   │   └── services/
│   │   │       ├── synthetic_identity_factory.py    # 3.1
│   │   │       ├── academic_structure_generator.py   # 3.2
│   │   │       ├── dummy_attendance_source.py         # 3.3 — implements IAttendanceIngestionSource
│   │   │       ├── fee_history_generator.py            # 3.4
│   │   │       └── seed_orchestrator.py                 # 3.5
│   │   ├── management/commands/
│   │   │   └── seed_demo_tenant.py       # CLI entrypoint
│   │   └── fixtures/
│   │       └── locale_providers/en_IN.py # custom Faker providers
│   │
│   ├── student_academic/                # [Module 4.0]
│   │   ├── domain/entities/{student.py, class_section.py, assessment.py}
│   │   ├── application/
│   │   │   ├── interfaces/{student_repository.py, class_section_repository.py, ...}
│   │   │   └── services/
│   │   │       ├── student_enrollment_service.py    # 4.1
│   │   │       ├── academic_structure_service.py     # 4.2
│   │   │       ├── timetable_query_service.py          # 4.3
│   │   │       └── grading_service.py                   # 4.4
│   │   ├── infrastructure/repositories/
│   │   └── api/
│   │
│   ├── attendance_management/           # [Module 5.0]
│   │   ├── domain/entities/attendance_record.py
│   │   ├── application/
│   │   │   ├── interfaces/
│   │   │   │   ├── attendance_ingestion_source.py   # IAttendanceIngestionSource (PORT — Phase 2 swap point)
│   │   │   │   └── attendance_repository.py
│   │   │   └── services/
│   │   │       ├── attendance_ingestion_orchestrator.py  # 5.1
│   │   │       ├── attendance_record_service.py            # 5.2
│   │   │       ├── attendance_override_service.py           # 5.3
│   │   │       └── attendance_anomaly_detector.py             # 5.4
│   │   ├── infrastructure/repositories/
│   │   └── api/
│   │
│   ├── fee_management/                  # [Module 6.0]
│   │   ├── domain/entities/{invoice.py, payment.py}
│   │   ├── application/
│   │   │   ├── interfaces/
│   │   │   │   ├── payment_gateway.py              # IPaymentGatewayStrategy (PORT)
│   │   │   │   ├── invoice_repository.py
│   │   │   │   └── gateway_resolver.py
│   │   │   └── services/
│   │   │       ├── fee_structure_service.py        # 6.1
│   │   │       ├── invoice_ledger_service.py        # 6.2
│   │   │       ├── payment_processing_service.py     # 6.3
│   │   │       └── reconciliation_service.py           # 6.4
│   │   ├── infrastructure/
│   │   │   ├── gateways/
│   │   │   │   ├── dummy_gateway.py           # DummyGatewayAdapter
│   │   │   │   ├── razorpay_gateway.py        # Phase-2-ready, DI-swappable
│   │   │   │   └── stripe_gateway.py
│   │   │   └── repositories/
│   │   └── api/
│   │
│   ├── notification_engine/             # [Module 7.0]
│   │   ├── application/
│   │   │   ├── interfaces/
│   │   │   │   ├── notification_provider.py     # INotificationProvider (PORT)
│   │   │   │   └── provider_resolver.py
│   │   │   └── services/
│   │   │       ├── notification_template_service.py  # 7.1
│   │   │       ├── notification_router.py              # 7.2
│   │   │       └── broadcast_communication_service.py    # 7.4
│   │   ├── infrastructure/
│   │   │   └── providers/
│   │   │       ├── dummy_channel_provider.py    # 7.3
│   │   │       ├── twilio_sms_provider.py
│   │   │       ├── sendgrid_email_provider.py
│   │   │       ├── fcm_push_provider.py
│   │   │       └── whatsapp_cloud_provider.py
│   │   └── api/
│   │
│   ├── ai_analytics_engine/             # [Module 8.0]
│   │   ├── application/
│   │   │   ├── interfaces/{llm_provider.py, sql_validator.py}
│   │   │   └── services/
│   │   │       ├── readonly_schema_gateway.py       # 8.1
│   │   │       ├── text_to_sql_service.py             # 8.2
│   │   │       ├── guarded_query_executor.py            # 8.3
│   │   │       ├── conversational_answer_composer.py      # 8.4
│   │   │       └── conversational_analytics_facade.py       # 8.5 orchestrator
│   │   ├── infrastructure/
│   │   │   ├── vanna_llm_provider.py
│   │   │   ├── readonly_connection_pool.py    # separate DB credentials, RLS-scoped
│   │   │   └── sql_ast_validator.py           # sqlglot-based validator
│   │   └── api/
│   │
│   └── analytics_reporting/             # [Module 9.0]
│       ├── application/
│       │   ├── interfaces/document_renderer.py
│       │   └── services/
│       │       ├── attendance_analytics_service.py    # 9.1
│       │       ├── fee_analytics_service.py             # 9.2
│       │       ├── academic_analytics_service.py          # 9.3
│       │       ├── export_document_service.py               # 9.4
│       │       └── dashboard_composition_service.py           # 9.5
│       ├── infrastructure/
│       │   ├── renderers/{pdf_renderer.py, excel_renderer.py}
│       │   └── templates/
│       │       ├── report_card.html.j2      # uses {{ theme.primary_color }}, never literal hex
│       │       └── fee_statement.xlsx.j2
│       └── api/
│
└── tests/
    ├── unit/                            # mirrors modules/ structure 1:1
    ├── integration/
    └── ai_engine/eval_qa_pairs.yaml     # 8.4's evaluation fixture set
```

## 4.2 Web Dashboard (React.js + Tailwind, Admin/Principal)

```
web-dashboard/
├── package.json
├── tailwind.config.ts                  # maps semantic classes → CSS vars (§2.2)
├── src/
│   ├── config/                          # SECTION 2.2 — isolated theme/config
│   │   ├── theme.schema.ts              # Zod TenantConfigSchema
│   │   ├── theme.config.ts              # loadTenantConfig()
│   │   └── ThemeProvider.tsx            # TenantConfigProvider + useFeatureFlag()
│   │
│   ├── shared/                          # cross-slice reusable primitives ONLY
│   │   ├── components/ui/               # Button, Card, Table — theme-token driven, zero business logic
│   │   ├── hooks/{useApi.ts, usePagination.ts}
│   │   └── types/dto.ts                 # mirrors backend DTOs (generated from OpenAPI)
│   │
│   ├── features/                        # VERTICAL SLICES — 1:1 with backend modules
│   │   ├── core-config/                 # [Module 1.0]
│   │   │   └── api/tenantConfigApi.ts
│   │   ├── auth/                        # [Module 2.0]
│   │   │   ├── components/{LoginForm.tsx, MFAChallengeModal.tsx}
│   │   │   ├── hooks/useAuth.ts
│   │   │   └── api/authApi.ts
│   │   ├── student-academic/            # [Module 4.0]
│   │   │   ├── components/{StudentRosterTable.tsx, TimetableGrid.tsx, ReportCardView.tsx}
│   │   │   ├── hooks/{useStudents.ts, useGrading.ts}
│   │   │   └── api/studentApi.ts
│   │   ├── attendance/                  # [Module 5.0]
│   │   │   ├── components/{AttendanceHeatmap.tsx, OverrideDialog.tsx}
│   │   │   ├── hooks/useAttendance.ts
│   │   │   └── api/attendanceApi.ts
│   │   ├── fee-management/              # [Module 6.0]
│   │   │   ├── components/{InvoiceTable.tsx, PaymentStatusBadge.tsx, DefaulterList.tsx}
│   │   │   ├── hooks/useFeeLedger.ts
│   │   │   └── api/feeApi.ts
│   │   ├── notifications/               # [Module 7.0]
│   │   │   ├── components/{BroadcastComposer.tsx, NotificationOutboxLog.tsx}
│   │   │   └── api/notificationApi.ts
│   │   ├── ai-analytics/                # [Module 8.0]
│   │   │   ├── components/{ChatQueryBox.tsx, GeneratedChartRenderer.tsx}
│   │   │   ├── hooks/useConversationalQuery.ts
│   │   │   └── api/aiAnalyticsApi.ts
│   │   └── dashboard-reporting/         # [Module 9.0]
│   │       ├── components/{KPIWidget.tsx, TrendChart.tsx, ExportButton.tsx}
│   │       └── api/analyticsApi.ts
│   │
│   ├── layouts/DashboardLayout.tsx      # reads theme via useTenantConfig() only
│   ├── routes/                          # route tree, one file per feature slice
│   └── App.tsx
└── tests/                               # mirrors src/features/ 1:1
```

## 4.3 Mobile App (React Native / Expo — Teacher/Staff)

```
mobile-app/
├── app.config.ts                       # EAS build profiles per tenant slug (§2.3)
├── package.json
├── src/
│   ├── config/                          # SECTION 2.3 — isolated theme/config
│   │   ├── theme.schema.js              # Yup TenantConfigSchema
│   │   └── TenantConfigContext.js       # useTenantTheme(), useTenantFeature()
│   │
│   ├── shared/
│   │   ├── components/ui/               # theme-token driven primitives (StyleSheet uses theme values, not literals)
│   │   ├── hooks/
│   │   └── api/apiClient.js             # base fetch wrapper w/ auth interceptor
│   │
│   ├── features/                        # VERTICAL SLICES — mirrors backend modules
│   │   ├── auth/
│   │   │   ├── screens/{LoginScreen.js, MFAScreen.js}
│   │   │   └── api/authApi.js
│   │   ├── attendance/                  # [Module 5.0] — Teacher's primary daily workflow
│   │   │   ├── screens/{MarkAttendanceScreen.js, AttendanceHistoryScreen.js}
│   │   │   ├── components/StudentAttendanceRow.js
│   │   │   └── api/attendanceApi.js
│   │   ├── timetable/                   # [Module 4.0 slice]
│   │   │   ├── screens/MyScheduleScreen.js
│   │   │   └── api/timetableApi.js
│   │   ├── student-academic/            # [Module 4.0]
│   │   │   ├── screens/{GradeEntryScreen.js, StudentProfileScreen.js}
│   │   │   └── api/studentApi.js
│   │   └── notifications/               # [Module 7.0] — push notification handling
│   │       ├── screens/NotificationInboxScreen.js
│   │       └── api/notificationApi.js
│   │
│   ├── navigation/AppNavigator.js
│   └── App.js
└── tests/
```

## 4.4 Cross-Cutting: OpenAPI Contract Sync

```
contracts/
├── openapi.yaml                # auto-generated from backend Pydantic/DRF serializers
└── scripts/
    └── generate_ts_types.ts    # generates web-dashboard/src/shared/types/dto.ts
                                 # AND mobile-app equivalent — the mechanism that
                                 # keeps Web/Mobile DTOs contractually pinned to
                                 # Backend DTOs without manual duplication drift
```

---

## Summary: Why This Satisfies the Three Mandates

| Mandate | Enforcement Mechanism |
|---|---|
| **Functional Cohesion** | Every sub-module in Section 3 has exactly one stated Purpose; generation (3.x), persistence (5.2/6.2), orchestration (5.1/8.5/9.5), and delivery (7.3) are always split into separate sub-modules even when tempting to merge |
| **Loose Coupling** | All cross-module calls go through `Protocol`-typed interfaces + immutable DTOs (§1.2); the event bus (§1.2.2) further decouples Notification (7.0) from Attendance/Fee entirely |
| **Extreme Modularity** | Section 4's `modules/*/` and `features/*/` folders are deletable/replaceable units; the Dummy Data Engine (3.0) and Payment/Notification adapters (6.3/7.3) are the concrete proof — Phase 2's CV/OCR pipeline, real payment gateways, and real SMS/WhatsApp providers all slot in via existing interfaces with **zero changes to Modules 4.0, 5.0(core), 6.0(core), 7.0(core), 8.0, or 9.0** |


## APPENDIX: RESOLVED TECHNICAL DECISIONS

1. **Framework Choice:** FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2.
2. **Event Bus Handling:** In-process event handlers execute asynchronously via FastAPI `BackgroundTasks` post-response to prevent DB transaction blocking.
3. **Frontend Validation:** Zod standardized across both Web (React.js) and Mobile (React Native / Expo).
4. **Dev DB Policy:** SQLite / standard Postgres permitted in dev mode; AST AST-level SQL validation enforced in all environments.
5. **Seeding Performance:** All synthetic generators in Module 3.0 must execute bulk SQL writes.
