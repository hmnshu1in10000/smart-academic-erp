"""
modules/students/application/facades.py — Module 4.0 Facade
=============================================================
Reads from the seeded students + class_sections tables.
Returns plain dict objects (consumed by the API layer as Pydantic models).
Rule: NO ORM models cross this facade boundary — only dicts/scalars.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy import select, func, text
from sqlalchemy.orm import Session

from modules.dummy_data_engine.infrastructure.db.session import SessionLocal
from modules.dummy_data_engine.infrastructure.db.models import Student, ClassSection

logger = logging.getLogger(__name__)

# Hardcoded CBSE Class 10 timetable structure (same data generated in Phase 1 3.2)
_DEFAULT_TIMETABLE = [
    {"day": "MON", "period": 1, "subject": "Mathematics",       "teacher": "Class Teacher", "start_time": "08:00", "end_time": "08:45", "room": "R10A"},
    {"day": "MON", "period": 2, "subject": "Science",           "teacher": "Science Dept",  "start_time": "08:45", "end_time": "09:30", "room": "R10A"},
    {"day": "MON", "period": 3, "subject": "English Language",  "teacher": "English Dept",  "start_time": "09:30", "end_time": "10:15", "room": "R10A"},
    {"day": "MON", "period": 4, "subject": "Hindi",             "teacher": "Hindi Dept",    "start_time": "10:30", "end_time": "11:15", "room": "R10A"},
    {"day": "MON", "period": 5, "subject": "Social Science",    "teacher": "SST Dept",      "start_time": "11:15", "end_time": "12:00", "room": "R10A"},
    {"day": "TUE", "period": 1, "subject": "Science",           "teacher": "Science Dept",  "start_time": "08:00", "end_time": "08:45", "room": "R10A"},
    {"day": "TUE", "period": 2, "subject": "Mathematics",       "teacher": "Math Dept",     "start_time": "08:45", "end_time": "09:30", "room": "R10A"},
    {"day": "TUE", "period": 3, "subject": "Computer Science",  "teacher": "CS Dept",       "start_time": "09:30", "end_time": "10:15", "room": "R10A"},
    {"day": "TUE", "period": 4, "subject": "Hindi",             "teacher": "Hindi Dept",    "start_time": "10:30", "end_time": "11:15", "room": "R10A"},
    {"day": "TUE", "period": 5, "subject": "English Language",  "teacher": "English Dept",  "start_time": "11:15", "end_time": "12:00", "room": "R10A"},
    {"day": "WED", "period": 1, "subject": "Mathematics",       "teacher": "Math Dept",     "start_time": "08:00", "end_time": "08:45", "room": "R10A"},
    {"day": "WED", "period": 2, "subject": "Social Science",    "teacher": "SST Dept",      "start_time": "08:45", "end_time": "09:30", "room": "R10A"},
    {"day": "WED", "period": 3, "subject": "English Language",  "teacher": "English Dept",  "start_time": "09:30", "end_time": "10:15", "room": "R10A"},
    {"day": "WED", "period": 4, "subject": "Science",           "teacher": "Science Dept",  "start_time": "10:30", "end_time": "11:15", "room": "R10A"},
    {"day": "WED", "period": 5, "subject": "Physical Education","teacher": "PE Dept",       "start_time": "11:15", "end_time": "12:00", "room": "Ground"},
    {"day": "THU", "period": 1, "subject": "Hindi",             "teacher": "Hindi Dept",    "start_time": "08:00", "end_time": "08:45", "room": "R10A"},
    {"day": "THU", "period": 2, "subject": "Mathematics",       "teacher": "Math Dept",     "start_time": "08:45", "end_time": "09:30", "room": "R10A"},
    {"day": "THU", "period": 3, "subject": "Science",           "teacher": "Science Dept",  "start_time": "09:30", "end_time": "10:15", "room": "R10A"},
    {"day": "THU", "period": 4, "subject": "Computer Science",  "teacher": "CS Dept",       "start_time": "10:30", "end_time": "11:15", "room": "Lab"},
    {"day": "THU", "period": 5, "subject": "Social Science",    "teacher": "SST Dept",      "start_time": "11:15", "end_time": "12:00", "room": "R10A"},
    {"day": "FRI", "period": 1, "subject": "English Language",  "teacher": "English Dept",  "start_time": "08:00", "end_time": "08:45", "room": "R10A"},
    {"day": "FRI", "period": 2, "subject": "Mathematics",       "teacher": "Math Dept",     "start_time": "08:45", "end_time": "09:30", "room": "R10A"},
    {"day": "FRI", "period": 3, "subject": "Social Science",    "teacher": "SST Dept",      "start_time": "09:30", "end_time": "10:15", "room": "R10A"},
    {"day": "FRI", "period": 4, "subject": "Hindi",             "teacher": "Hindi Dept",    "start_time": "10:30", "end_time": "11:15", "room": "R10A"},
    {"day": "FRI", "period": 5, "subject": "Physical Education","teacher": "PE Dept",       "start_time": "11:15", "end_time": "12:00", "room": "Ground"},
    {"day": "SAT", "period": 1, "subject": "Science",           "teacher": "Science Dept",  "start_time": "08:00", "end_time": "08:45", "room": "R10A"},
    {"day": "SAT", "period": 2, "subject": "Computer Science",  "teacher": "CS Dept",       "start_time": "08:45", "end_time": "09:30", "room": "Lab"},
    {"day": "SAT", "period": 3, "subject": "Mathematics",       "teacher": "Math Dept",     "start_time": "09:30", "end_time": "10:15", "room": "R10A"},
]


class StudentsFacade:
    """Module 4.0 Application Service — student read operations."""

    def __init__(self, tenant_id: str) -> None:
        self._tenant_id = tenant_id

    def list_students(
        self,
        section: Optional[str],
        page: int,
        page_size: int,
    ) -> dict:
        with SessionLocal() as session:
            q = (
                session.query(Student, ClassSection.display_name)
                .join(ClassSection, Student.class_section_id == ClassSection.id)
                .filter(Student.tenant_id == self._tenant_id)
            )
            if section:
                q = q.filter(ClassSection.display_name.ilike(f"%{section}%"))

            total = q.count()
            rows = q.offset((page - 1) * page_size).limit(page_size).all()

            items = [
                {
                    "id": s.id,
                    "roll_number": s.roll_number,
                    "full_name": s.full_name,
                    "gender": s.gender,
                    "class_section": display_name,
                    "guardian_name": s.guardian_name,
                    "guardian_phone": s.guardian_phone,
                    "enrollment_status": s.enrollment_status,
                }
                for s, display_name in rows
            ]
            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "has_next": (page * page_size) < total,
            }

    def get_student(self, student_id: str) -> Optional[dict]:
        with SessionLocal() as session:
            row = (
                session.query(Student, ClassSection.display_name)
                .join(ClassSection, Student.class_section_id == ClassSection.id)
                .filter(Student.id == student_id, Student.tenant_id == self._tenant_id)
                .first()
            )
            if not row:
                return None
            s, display_name = row
            return {
                "id": s.id,
                "roll_number": s.roll_number,
                "full_name": s.full_name,
                "gender": s.gender,
                "class_section": display_name,
                "dob": str(s.dob) if s.dob else None,
                "blood_group": s.blood_group,
                "phone": s.phone,
                "email": s.email,
                "address": s.address,
                "guardian_name": s.guardian_name,
                "guardian_phone": s.guardian_phone,
                "guardian_relation": s.guardian_relation,
                "enrollment_status": s.enrollment_status,
            }

    def get_student_timetable(self, student_id: str) -> Optional[list[dict]]:
        """Returns timetable for the student's section. Uses static timetable for Phase 1."""
        with SessionLocal() as session:
            row = (
                session.query(Student, ClassSection.display_name)
                .join(ClassSection, Student.class_section_id == ClassSection.id)
                .filter(Student.id == student_id, Student.tenant_id == self._tenant_id)
                .first()
            )
            if not row:
                return None
            _student, display_name = row
            # Customize room label per section
            section_suffix = display_name.replace("Class ", "").replace("-", "")
            return [
                {**entry, "room": f"R{section_suffix}"}
                for entry in _DEFAULT_TIMETABLE
            ]
