"""
shared_kernel/contracts/base_event.py
======================================
Domain Event base contracts for the in-process event bus.
Source of truth: ARCHITECTURE.md §1.2.2
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import UUID, uuid4


@dataclass(frozen=True, slots=True)
class DomainEvent:
    """
    Base for all domain events published on IEventBus.
    Phase 1: dispatched synchronously in-process.
    Phase 2: swap IEventBus impl to Celery+Redis or Kafka — zero publisher/subscriber changes.
    """
    event_id: UUID = field(default_factory=uuid4)
    tenant_id: str = ""
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    event_type: str = ""
    payload: dict = field(default_factory=dict)
    correlation_id: str | None = None


# ── Concrete domain events ─────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class FeePaymentReceivedEvent(DomainEvent):
    event_type: str = "fee.payment.received"
    # payload keys: student_id, amount, invoice_id, payment_method


@dataclass(frozen=True, slots=True)
class StudentAbsentEvent(DomainEvent):
    event_type: str = "attendance.student_absent"
    # payload keys: student_id, date, class_section_id


@dataclass(frozen=True, slots=True)
class ConsecutiveAbsenceDetectedEvent(DomainEvent):
    event_type: str = "attendance.consecutive_absence_detected"
    # payload keys: student_id, consecutive_days, threshold_breached


@dataclass(frozen=True, slots=True)
class TenantSeedCompletedEvent(DomainEvent):
    event_type: str = "system.tenant_seed_completed"
    # payload keys: students_created, attendance_records_created, fee_records_created
