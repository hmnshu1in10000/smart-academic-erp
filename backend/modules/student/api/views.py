"""
modules/student/api/views.py
=============================
GET /api/v1/student/academic-summary — Student Portal Academic Summary Endpoint
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from shared_kernel.auth.jwt_utils import TokenPayload, get_current_tenant_context
from modules.dummy_data_engine.infrastructure.db.session import SessionLocal
from modules.dummy_data_engine.infrastructure.db.models import Student, ClassSection
from modules.students.application.facades import StudentsFacade
from modules.attendance.application.facades import AttendanceFacade

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/student", tags=["Student Portal"])


class SubjectGradeItem(BaseModel):
    subject_name: str
    teacher_name: str
    grade: str
    score_pct: float


class StudentAcademicSummaryResponse(BaseModel):
    student_id: str
    student_name: str
    section: str
    roll_number: int
    attendance_rate_pct: float
    report_card: list[SubjectGradeItem]
    timetable_count: int


@router.get(
    "/academic-summary",
    response_model=StudentAcademicSummaryResponse,
    summary="Get Student Personal Academic Summary & Report Card",
)
async def get_student_academic_summary(
    token: TokenPayload = Depends(get_current_tenant_context),
) -> StudentAcademicSummaryResponse:
    with SessionLocal() as session:
        student_row = (
            session.query(Student, ClassSection.display_name)
            .join(ClassSection, Student.class_section_id == ClassSection.id)
            .filter(Student.tenant_id == token.tenant_id)
            .first()
        )
        if not student_row:
            raise HTTPException(status_code=404, detail="No student record associated with account.")

        student, section_name = student_row

        students_facade = StudentsFacade(tenant_id=token.tenant_id)
        timetable = students_facade.get_student_timetable(student_id=student.id) or []

        att_facade = AttendanceFacade(tenant_id=token.tenant_id)
        att_hist = att_facade.get_student_history(student_id=student.id, days=30)

        report_card = [
            SubjectGradeItem(subject_name="Mathematics", teacher_name="Mr. Rajesh Kumar", grade="A+", score_pct=92.5),
            SubjectGradeItem(subject_name="Science", teacher_name="Ms. Priya Singh", grade="A", score_pct=88.0),
            SubjectGradeItem(subject_name="English Language", teacher_name="English Dept", grade="A", score_pct=85.5),
            SubjectGradeItem(subject_name="Social Science", teacher_name="SST Dept", grade="B+", score_pct=78.0),
            SubjectGradeItem(subject_name="Computer Science", teacher_name="CS Dept", grade="A+", score_pct=96.0),
        ]

        return StudentAcademicSummaryResponse(
            student_id=student.id,
            student_name=student.full_name,
            section=section_name,
            roll_number=student.roll_number,
            attendance_rate_pct=att_hist.get("attendance_pct", 90.0),
            report_card=report_card,
            timetable_count=len(timetable),
        )
