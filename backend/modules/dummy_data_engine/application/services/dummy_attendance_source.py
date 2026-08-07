"""
modules/dummy_data_engine/application/services/dummy_attendance_source.py
===========================================================================
Sub-Module 3.3 — Dummy Attendance Ingestion Source.
Source of truth: ARCHITECTURE.md §3.3

Implements IAttendanceIngestionSource — the exact interface a future
CV/OCR camera pipeline (Phase 2) will also implement.

PHASE-2 SWAP BOUNDARY: When biometric_attendance_enabled=True, the DI
container in config/di/container.py swaps DummyAttendanceIngestionSource
→ CVPipelineAttendanceSource. Zero code change elsewhere.

Dependencies: None (implements the interface declared in Module 5.0).
"""
from __future__ import annotations

import logging
import random
from datetime import date, datetime, time, timezone
from typing import Protocol
from uuid import UUID, uuid4

from modules.dummy_data_engine.domain.dtos import (
    AttendanceStatus,
    RawAttendanceSignalDTO,
    SimulateAttendanceRequestDTO,
)

logger = logging.getLogger(__name__)

# Weighted attendance patterns — realistic per-day adjustments
_BASE_ATTENDANCE_RATE = 0.93

# Monday: -4%, Friday: -3%, Saturday: -2% (lazy days)
_DAY_ADJUSTMENT: dict[int, float] = {
    0: -0.04,   # Monday
    1:  0.00,
    2:  0.00,
    3:  0.00,
    4: -0.03,   # Friday
    5: -0.02,   # Saturday
    6:  0.00,   # Sunday (no school)
}

# Students who had absence yesterday have 40% chance of being absent today
_STREAK_CONTINUATION_RATE = 0.40


# ── Interface (PORT) — declared here, consumed by Module 5.0 ──────────────────

class IAttendanceIngestionSource(Protocol):
    """
    Port (interface) for attendance signal sources.
    Phase 1 adapter: DummyAttendanceIngestionSource
    Phase 2 adapter: CVPipelineAttendanceSource (swapped in container.py only)
    """
    def fetch_daily_signals(
        self, request: SimulateAttendanceRequestDTO
    ) -> list[RawAttendanceSignalDTO]: ...


# ── Adapter (IMPLEMENTATION) ──────────────────────────────────────────────────

class DummyAttendanceIngestionSource:
    """
    Sub-Module 3.3: Simulates daily attendance signals with realistic patterns.

    Patterns:
    - Weighted P/A/Late per day-of-week adjustments
    - Absence streaks (sick students tend to be absent multiple days)
    - ~5% Late rate among present students
    - Confidence score always 1.0 (dummy; real CV uses model probability)
    """

    def __init__(self, seed: int | None = None) -> None:
        if seed is not None:
            random.seed(seed)
        # Track absence state per student for streak simulation
        self._was_absent_yesterday: set[UUID] = set()
        logger.debug("DummyAttendanceIngestionSource initialized (seed=%s)", seed)

    def fetch_daily_signals(
        self, request: SimulateAttendanceRequestDTO
    ) -> list[RawAttendanceSignalDTO]:
        """
        Produce a list of RawAttendanceSignalDTO for all students on a given date.
        Called once per (date, section) by the seed orchestrator.
        """
        status_map = self._apply_realistic_absence_pattern(
            list(request.student_ids), request.date, request.attendance_rate
        )
        signals: list[RawAttendanceSignalDTO] = []

        # Arrival time varies: present ≈ 08:00–08:30, late ≈ 08:31–09:15
        for student_id, status in status_map.items():
            if status == AttendanceStatus.ABSENT:
                arrival_hour, arrival_min = 0, 0   # absent → no arrival
            elif status == AttendanceStatus.LATE:
                arrival_hour = 8
                arrival_min = random.randint(31, 74)
                if arrival_min >= 60:
                    arrival_hour = 9
                    arrival_min -= 60
            else:
                arrival_hour = 8
                arrival_min = random.randint(0, 30)

            ts = datetime(
                request.date.year, request.date.month, request.date.day,
                arrival_hour, arrival_min, 0, tzinfo=timezone.utc
            ) if status != AttendanceStatus.ABSENT else datetime(
                request.date.year, request.date.month, request.date.day,
                0, 0, 0, tzinfo=timezone.utc
            )

            signals.append(RawAttendanceSignalDTO(
                signal_id=uuid4(),
                student_id=student_id,
                class_section_id=request.class_section_id,
                timestamp=ts,
                status=status,
                confidence_score=1.0,
                source="DUMMY_GENERATOR",
            ))

        # Update absence memory for next day's streak calculation
        self._was_absent_yesterday = {
            sid for sid, st in status_map.items()
            if st == AttendanceStatus.ABSENT
        }

        logger.debug(
            "Generated %d attendance signals for %s (P=%d A=%d L=%d)",
            len(signals),
            request.date,
            sum(1 for s in signals if s.status == AttendanceStatus.PRESENT),
            sum(1 for s in signals if s.status == AttendanceStatus.ABSENT),
            sum(1 for s in signals if s.status == AttendanceStatus.LATE),
        )
        return signals

    def _apply_realistic_absence_pattern(
        self,
        student_ids: list[UUID],
        for_date: date,
        base_rate: float,
    ) -> dict[UUID, AttendanceStatus]:
        """
        Assign P/A/Late statuses with:
        - Day-of-week adjustments (Mondays/Fridays have higher absenteeism)
        - Absence streaks (students absent yesterday more likely to be absent today)
        - ~5% Late rate among non-absent students
        """
        day_adj = _DAY_ADJUSTMENT.get(for_date.weekday(), 0.0)
        effective_present_rate = max(0.70, min(1.0, base_rate + day_adj))

        status_map: dict[UUID, AttendanceStatus] = {}
        for student_id in student_ids:
            # Streak: if was absent yesterday, elevated chance of another absence
            if student_id in self._was_absent_yesterday:
                r = random.random()
                if r < _STREAK_CONTINUATION_RATE:
                    status_map[student_id] = AttendanceStatus.ABSENT
                    continue

            r = random.random()
            if r < effective_present_rate:
                # Among "present" students, ~5% arrive late
                if random.random() < 0.05:
                    status_map[student_id] = AttendanceStatus.LATE
                else:
                    status_map[student_id] = AttendanceStatus.PRESENT
            else:
                status_map[student_id] = AttendanceStatus.ABSENT

        return status_map

    def generate_multi_day_signals(
        self,
        student_ids: list[UUID],
        class_section_id: UUID,
        tenant_id: str,
        start_date: date,
        num_days: int,
        attendance_rate: float = _BASE_ATTENDANCE_RATE,
        skip_weekends: bool = True,
    ) -> list[RawAttendanceSignalDTO]:
        """
        Generate attendance signals for `num_days` working days starting from `start_date`.
        Sundays are always skipped. Used by the seed orchestrator (Sub-Module 3.5).
        """
        from datetime import timedelta

        all_signals: list[RawAttendanceSignalDTO] = []
        current = start_date
        days_generated = 0

        while days_generated < num_days:
            # Skip Sundays (weekday() == 6)
            if current.weekday() == 6:
                current += timedelta(days=1)
                continue

            request = SimulateAttendanceRequestDTO(
                tenant_id=tenant_id,
                class_section_id=class_section_id,
                date=current,
                student_ids=tuple(student_ids),
                attendance_rate=attendance_rate,
            )
            signals = self.fetch_daily_signals(request)
            all_signals.extend(signals)
            days_generated += 1
            current += timedelta(days=1)

        logger.info(
            "Generated %d total attendance signals over %d working days",
            len(all_signals), num_days,
        )
        return all_signals
