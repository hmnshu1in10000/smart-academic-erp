"""
shared_kernel/events/event_bus.py
==================================
IEventBus protocol + InProcessEventBus Phase-1 implementation.
Source of truth: ARCHITECTURE.md §1.2.2

Phase 1: synchronous in-process dispatcher (Django-signals-style).
Phase 2: swap InProcessEventBus → CeleryEventBus or KafkaEventBus
         without touching any publisher or subscriber code.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable, Protocol

from shared_kernel.contracts.base_event import DomainEvent

logger = logging.getLogger(__name__)


# ── Interface (the "port") ─────────────────────────────────────────────────────

class IEventBus(Protocol):
    def publish(self, event: DomainEvent) -> None: ...
    def subscribe(self, event_type: str, handler: Callable[[DomainEvent], None]) -> None: ...


# ── In-Process Implementation (Phase 1 adapter) ───────────────────────────────

class InProcessEventBus:
    """
    Synchronous, in-process event bus.
    All handlers run in the same thread/process as the publisher.
    Exceptions in handlers are caught and logged — they never propagate to
    the publisher (fire-and-forget semantic per ARCHITECTURE §1.2.2).
    """

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[DomainEvent], None]]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable[[DomainEvent], None]) -> None:
        """Register a handler for a specific event_type string."""
        self._handlers[event_type].append(handler)
        logger.debug("EventBus: subscribed %s → %s", event_type, handler.__qualname__)

    def publish(self, event: DomainEvent) -> None:
        """Dispatch event to all registered handlers. Errors are isolated per handler."""
        handlers = self._handlers.get(event.event_type, [])
        logger.info(
            "EventBus: publishing %s (id=%s, tenant=%s, handlers=%d)",
            event.event_type, event.event_id, event.tenant_id, len(handlers),
        )
        for handler in handlers:
            try:
                handler(event)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "EventBus: handler %s failed for event %s: %s",
                    handler.__qualname__, event.event_type, exc,
                )


# ── Singleton for DI container ─────────────────────────────────────────────────
_event_bus_instance: InProcessEventBus | None = None


def get_event_bus() -> InProcessEventBus:
    global _event_bus_instance
    if _event_bus_instance is None:
        _event_bus_instance = InProcessEventBus()
    return _event_bus_instance
