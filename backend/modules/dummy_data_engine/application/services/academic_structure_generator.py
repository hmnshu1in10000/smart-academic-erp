"""
modules/dummy_data_engine/application/services/academic_structure_generator.py
=================================================================================
Sub-Module 3.2 — Class, Section & Timetable Generator.
Source of truth: ARCHITECTURE.md §3.2

Produces a coherent academic structure: grades, sections, subjects,
teacher-subject-section assignments, and a conflict-free weekly timetable.

Dependencies: None (structural generation, no DB reach).
"""
from __future__ import annotations

import logging
import random
from uuid import UUID, uuid4

from modules.dummy_data_engine.domain.dtos import (
    AcademicStructureDTO,
    ClassSectionDTO,
    GenerateAcademicStructureRequestDTO,
    SubjectDTO,
    SyntheticIdentityDTO,
    TimetableEntryDTO,
)

logger = logging.getLogger(__name__)

# Default subject list for Class 10 (CBSE curriculum)
DEFAULT_SUBJECTS_GRADE_10 = [
    ("Mathematics",         "MATH10",   6),
    ("Science",             "SCI10",    6),
    ("English Language",    "ENG10",    5),
    ("Social Science",      "SST10",    5),
    ("Hindi",               "HIN10",    5),
    ("Computer Science",    "CS10",     3),
    ("Physical Education",  "PE10",     2),
]

# Period timing grid (45-min periods, 2 breaks)
_PERIOD_TIMES = [
    (1, "08:00", "08:45"),
    (2, "08:45", "09:30"),
    (3, "09:30", "10:15"),
    # --- Short Break ---
    (4, "10:30", "11:15"),
    (5, "11:15", "12:00"),
    (6, "12:00", "12:45"),
    # --- Lunch Break ---
    (7, "13:30", "14:15"),
    (8, "14:15", "15:00"),
]

_WORKING_DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]


class AcademicStructureGenerator:
    """
    Sub-Module 3.2: Generates class sections, subjects, and a conflict-free timetable.
    Constraint: no teacher double-booked in the same period across sections.
    """

    def __init__(self, seed: int | None = None) -> None:
        if seed is not None:
            random.seed(seed)
        logger.debug("AcademicStructureGenerator initialized (seed=%s)", seed)

    def generate_class_sections(
        self,
        request: GenerateAcademicStructureRequestDTO,
        staff_identities: list[SyntheticIdentityDTO] | None = None,
    ) -> list[ClassSectionDTO]:
        """Create section objects for the requested grade levels."""
        sections: list[ClassSectionDTO] = []
        section_labels = [chr(ord("A") + i) for i in range(request.sections_per_grade)]

        staff_pool = list(staff_identities or [])
        teacher_index = 0

        for grade in request.grade_levels:
            for label in section_labels:
                class_teacher_id: UUID | None = None
                if staff_pool:
                    class_teacher_id = staff_pool[teacher_index % len(staff_pool)].identity_id
                    teacher_index += 1

                section = ClassSectionDTO(
                    section_id=uuid4(),
                    tenant_id=request.tenant_id,
                    grade_level=grade,
                    section_name=label,
                    display_name=f"Class {grade}-{label}",
                    class_teacher_id=class_teacher_id,
                    room_number=f"R{grade}{label}",
                    max_strength=30,
                )
                sections.append(section)
                logger.debug("Created section: %s", section.display_name)

        logger.info(
            "Generated %d class sections (grades=%s)", len(sections), request.grade_levels
        )
        return sections

    def generate_subjects(
        self,
        grade_level: int,
        subject_definitions: list[tuple[str, str, int]] | None = None,
    ) -> list[SubjectDTO]:
        """Generate Subject DTOs for a given grade."""
        definitions = subject_definitions or DEFAULT_SUBJECTS_GRADE_10
        subjects = [
            SubjectDTO(
                subject_id=uuid4(),
                name=name,
                code=code,
                grade_level=grade_level,
                periods_per_week=ppw,
            )
            for name, code, ppw in definitions
        ]
        logger.info("Generated %d subjects for grade %d", len(subjects), grade_level)
        return subjects

    def generate_timetable(
        self,
        class_sections: list[ClassSectionDTO],
        subjects: list[SubjectDTO],
        staff_identities: list[SyntheticIdentityDTO] | None = None,
    ) -> list[TimetableEntryDTO]:
        """
        Generate a conflict-free timetable for all sections.
        Constraint satisfaction: no teacher assigned to two sections in the same period.
        """
        staff_pool = list(staff_identities or [])
        # Map subject → assigned teacher (stable across sections)
        subject_teacher_map: dict[UUID, tuple[UUID | None, str]] = {}
        for i, subj in enumerate(subjects):
            if staff_pool:
                teacher = staff_pool[i % len(staff_pool)]
                subject_teacher_map[subj.subject_id] = (
                    teacher.identity_id, teacher.full_name
                )
            else:
                subject_teacher_map[subj.subject_id] = (None, "TBD")

        entries: list[TimetableEntryDTO] = []
        # Track teacher occupancy: (teacher_id, day, period) → section_id
        teacher_occupancy: dict[tuple[UUID | None, str, int], UUID] = {}

        for section in class_sections:
            # Build a pool of (day, period) slots and shuffle them
            slots = [
                (day, p_num, p_start, p_end)
                for day in _WORKING_DAYS
                for p_num, p_start, p_end in [(p[0], p[1], p[2]) for p in _PERIOD_TIMES]
            ]
            random.shuffle(slots)

            # Distribute subject periods across slots
            subject_slot_pool: list[SubjectDTO] = []
            for subj in subjects:
                # Each subject gets periods_per_week slots per week
                subject_slot_pool.extend([subj] * subj.periods_per_week)
            random.shuffle(subject_slot_pool)

            assigned_count = 0
            for slot_day, slot_period, slot_start, slot_end in slots:
                if assigned_count >= len(subject_slot_pool):
                    break
                subj = subject_slot_pool[assigned_count]
                teacher_id, teacher_name = subject_teacher_map[subj.subject_id]

                # Skip if teacher is already occupied this slot
                occupancy_key = (teacher_id, slot_day, slot_period)
                if teacher_id and occupancy_key in teacher_occupancy:
                    continue

                if teacher_id:
                    teacher_occupancy[occupancy_key] = section.section_id

                entry = TimetableEntryDTO(
                    entry_id=uuid4(),
                    section_id=section.section_id,
                    subject_id=subj.subject_id,
                    subject_name=subj.name,
                    teacher_id=teacher_id,
                    teacher_name=teacher_name,
                    day_of_week=slot_day,
                    period_number=slot_period,
                    start_time=slot_start,
                    end_time=slot_end,
                    room=section.room_number or f"ROOM-{section.display_name}",
                )
                entries.append(entry)
                assigned_count += 1

        logger.info(
            "Generated %d timetable entries for %d sections",
            len(entries), len(class_sections)
        )
        return entries

    def _resolve_scheduling_conflicts(
        self, draft_entries: list[TimetableEntryDTO]
    ) -> list[TimetableEntryDTO]:
        """Remove any double-booked teacher entries (safety net)."""
        seen: set[tuple[UUID | None, str, int]] = set()
        resolved = []
        removed = 0
        for entry in draft_entries:
            key = (entry.teacher_id, entry.day_of_week, entry.period_number)
            if key in seen and entry.teacher_id is not None:
                removed += 1
                continue
            seen.add(key)
            resolved.append(entry)
        if removed:
            logger.warning("Resolved %d scheduling conflicts", removed)
        return resolved
