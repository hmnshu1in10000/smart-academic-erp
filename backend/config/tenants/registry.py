"""
config/tenants/registry.py
===========================
In-memory ITenantConfigRepository implementation — Phase 1 resolution.
Phase 2: swap this for a DB-backed or S3-backed repository without
touching any consumer (they all depend on ITenantConfigProvider protocol).

Source of truth: ARCHITECTURE.md §1.2 (Service Facade + DTO), §2.1
"""
from __future__ import annotations

from typing import Protocol

from config.tenants.schema import TenantConfig
from config.tenants.greenwood_high import GREENWOOD_HIGH_CONFIG


# ── Protocol (the "port" — owned by application layer) ────────────────────────

class ITenantConfigRepository(Protocol):
    """Read-only access to tenant configurations."""

    def get_by_id(self, tenant_id: str) -> TenantConfig | None: ...
    def get_by_slug(self, slug: str) -> TenantConfig | None: ...
    def list_all(self) -> list[TenantConfig]: ...


# ── In-Memory Registry (Phase 1 adapter) ──────────────────────────────────────

class InMemoryTenantConfigRegistry:
    """
    Phase-1 implementation: a static dict of TenantConfig objects.
    Register new tenants here during development.
    Phase 2: replace with DBTenantConfigRepository(ITenantConfigRepository).
    """

    def __init__(self) -> None:
        self._configs: dict[str, TenantConfig] = {}
        self._slug_index: dict[str, str] = {}   # slug → tenant_id

        # Register all known dev tenants
        self._register(GREENWOOD_HIGH_CONFIG, slugs=["greenwood-high", "greenwood"])

    def _register(self, config: TenantConfig, slugs: list[str] | None = None) -> None:
        self._configs[config.tenant_id] = config
        for slug in (slugs or []):
            self._slug_index[slug] = config.tenant_id

    def get_by_id(self, tenant_id: str) -> TenantConfig | None:
        return self._configs.get(tenant_id)

    def get_by_slug(self, slug: str) -> TenantConfig | None:
        tenant_id = self._slug_index.get(slug)
        if tenant_id:
            return self._configs.get(tenant_id)
        return None

    def list_all(self) -> list[TenantConfig]:
        return list(self._configs.values())


# ── Singleton instance for DI container ───────────────────────────────────────
_registry_instance: InMemoryTenantConfigRegistry | None = None


def get_tenant_registry() -> InMemoryTenantConfigRegistry:
    global _registry_instance
    if _registry_instance is None:
        _registry_instance = InMemoryTenantConfigRegistry()
    return _registry_instance
