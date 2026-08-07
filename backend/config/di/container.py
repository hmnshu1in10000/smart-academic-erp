"""
config/di/container.py
========================
Global DI wiring — the ONLY place concrete adapters are bound to interfaces.
Source of truth: ARCHITECTURE.md §1.4 (Dependency Injection Convention)

Rule: Business logic (services, use cases) NEVER imports from this file.
Only FastAPI startup, CLI commands, and tests import from here.

Phase 1: All adapters are "Dummy" variants.
Phase 2: Swap bindings here → zero changes in any module's business logic.
"""
from __future__ import annotations

from modules.core_infrastructure.application.interfaces.theme_provider import (
    ITenantConfigProvider,
)
from config.tenants.registry import InMemoryTenantConfigRegistry, get_tenant_registry
from shared_kernel.events.event_bus import InProcessEventBus, get_event_bus
from config.tenants.schema import TenantConfig, ThemeTokens
from shared_kernel.exceptions.domain_exceptions import TenantNotFoundError


# ── Concrete ITenantConfigProvider (Phase 1: in-memory registry) ────────────

class InMemoryTenantConfigProvider:
    """
    Wraps InMemoryTenantConfigRegistry to implement ITenantConfigProvider.
    Phase 2 swap: DBTenantConfigProvider(ITenantConfigProvider)
    """

    def __init__(self, registry: InMemoryTenantConfigRegistry) -> None:
        self._registry = registry

    def get_config(self, tenant_id: str) -> TenantConfig:
        config = self._registry.get_by_id(tenant_id)
        if config is None:
            raise TenantNotFoundError(
                f"Tenant '{tenant_id}' not found in registry.",
                error_code="TENANT_NOT_FOUND",
            )
        return config

    def get_theme(self, tenant_id: str) -> ThemeTokens:
        return self.get_config(tenant_id).theme

    def is_feature_enabled(self, tenant_id: str, feature_key: str) -> bool:
        config = self.get_config(tenant_id)
        return getattr(config.features, feature_key, False)


# ── Container ─────────────────────────────────────────────────────────────────

class Container:
    """Lightweight manual DI container for Phase 1."""

    def __init__(self) -> None:
        # Infrastructure singletons
        self._event_bus = get_event_bus()
        self._tenant_registry = get_tenant_registry()
        self._tenant_config_provider = InMemoryTenantConfigProvider(self._tenant_registry)

    @property
    def event_bus(self) -> InProcessEventBus:
        return self._event_bus

    @property
    def tenant_config_provider(self) -> InMemoryTenantConfigProvider:
        return self._tenant_config_provider


# ── Global singleton ──────────────────────────────────────────────────────────
_container: Container | None = None


def get_container() -> Container:
    global _container
    if _container is None:
        _container = Container()
    return _container
