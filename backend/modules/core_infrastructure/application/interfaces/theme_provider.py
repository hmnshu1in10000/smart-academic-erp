"""
modules/core_infrastructure/application/interfaces/theme_provider.py
======================================================================
ITenantConfigProvider protocol — the single dependency all modules
consult for tenant-specific configuration.
Source of truth: ARCHITECTURE.md §1.3.3
"""
from __future__ import annotations

from typing import Protocol

from config.tenants.schema import TenantConfig, ThemeTokens


class ITenantConfigProvider(Protocol):
    """
    Single dependency for all tenant-specific data access.
    Rule (§1.3.3): No module may read settings.py constants for school-specific
    data — they all depend only on this interface.
    """

    def get_config(self, tenant_id: str) -> TenantConfig: ...
    def get_theme(self, tenant_id: str) -> ThemeTokens: ...
    def is_feature_enabled(self, tenant_id: str, feature_key: str) -> bool: ...
