"""
modules/attendance/api/views.py — Module 5.0
=============================================
GET  /api/v1/attendance/summary      — daily/range attendance summary (role-scoped)
GET  /api/v1/attendance/student/{id} — per-student 30-day history (tenant-scoped)
GET  /api/v1/attendance/me          — student personal attendance (JWT-identity)
GET  /api/v1/attendance/my-child     — parent child attendance (JWT-identity)
POST /api/v1/attendance/submit       — ingest mobile attendance signals
"""
from __future__ import annotations

import logging
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from shared_kernel.auth.jwt_utils import TokenPayload, get_current_tenant_context
from modules.dummy_data_engine.infrastructure.db.session import SessionLocal
from modules.dummy_data_engine.infrastructure.db.models import Student, ClassSection
from modules.attendance.application.facades import AttendanceFacade

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/attendance", tags=["Attendance"])


# ── Response Models ────────────────────────────────────────────────────────────

class DailyAttendanceStat(BaseModel):
    date: str
    section: str
    total: int
    present: int
    absent: int
    late: int
    attendance_pct: float


class AttendanceSummaryResponse(BaseModel):
    tenant_id: str
    section: Optional[str]
    from_date: str
    to_date: str
    daily_stats: list[DailyAttendanceStat]
    overall_present_pct: float
    chronic_absentees: list[dict]   # [{student_id, full_name, absent_days}]


class StudentAttendanceDay(BaseModel):
    date: str
    status: str      # P / A / L
    source: str


class StudentAttendanceHistory(BaseModel):
    student_id: str
    full_name: str
    section: str
    total_days: int
    present: int
    absent: int
    late: int
    attendance_pct: float
    history: list[StudentAttendanceDay]


class AttendanceSubmitRequest(BaseModel):
    signals: list[dict]


class AttendanceSubmitResponse(BaseModel):
    status: str = "ok"
    ingested_count: int
    message: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=AttendanceSummaryResponse,
    summary="Get attendance summary",
    description="Returns daily attendance stats for a date range, scoped by role.",
)
async def get_attendance_summary(
    section: Optional[str] = Query(None, description="Class section e.g. '10-A'"),
    from_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    to_date: Optional[str] = Query(None, description="YYYY-MM-DD"),
    token: TokenPayload = Depends(get_current_tenant_context),
) -> AttendanceSummaryResponse:
    facade = AttendanceFacade(tenant_id=token.tenant_id)
    result = facade.get_summary(
        section=section,
        from_date=from_date,
        to_date=to_date,
        role=token.role,
        assigned_sections=token.assigned_sections,
    )
    return AttendanceSummaryResponse(**result)


@router.get(
    "/me",
    response_model=StudentAttendanceHistory,
    summary="Get authenticated student's attendance history",
)
async def get_my_attendance(
    days: int = Query(30, ge=1, le=90),
    token: TokenPayload = Depends(get_current_tenant_context),
) -> StudentAttendanceHistory:
    """Identity-resolved attendance for student role (Section 2.7)."""
    with SessionLocal() as session:
        student = session.query(Student).filter(
            Student.tenant_id == token.tenant_id,
            Student.email == token.sub,
        ).first()
        if not student:
            raise HTTPException(status_code=404, detail="No student record linked to this account.")
        student_id = student.id

    facade = AttendanceFacade(tenant_id=token.tenant_id)
    result = facade.get_student_history(student_id=student_id, days=days)
    return StudentAttendanceHistory(**result)


@router.get(
    "/my-child",
    response_model=StudentAttendanceHistory,
    summary="Get parent's child attendance history",
)
async def get_my_child_attendance(
    days: int = Query(30, ge=1, le=90),
    token: TokenPayload = Depends(get_current_tenant_context),
) -> StudentAttendanceHistory:
    """Identity-resolved attendance for parent role (Section 2.7)."""
    with SessionLocal() as session:
        student = session.query(Student).filter(
            Student.tenant_id == token.tenant_id,
            Student.guardian_user_id == token.sub,
        ).first()
        if not student:
            raise HTTPException(status_code=404, detail="No student record linked to this parent account.")
        student_id = student.id

    facade = AttendanceFacade(tenant_id=token.tenant_id)
    result = facade.get_student_history(student_id=student_id, days=days)
    return StudentAttendanceHistory(**result)


@router.get(
    "/student/{student_id}",
    response_model=StudentAttendanceHistory,
    summary="Get student attendance history",
)
async def get_student_attendance(
    student_id: str,
    days: int = Query(30, ge=1, le=90, description="Number of historical days"),
    token: TokenPayload = Depends(get_current_tenant_context),
) -> StudentAttendanceHistory:
    facade = AttendanceFacade(tenant_id=token.tenant_id)
    result = facade.get_student_history(student_id=student_id, days=days)
    return StudentAttendanceHistory(**result)


@router.post(
    "/submit",
    response_model=AttendanceSubmitResponse,
    summary="Submit mobile attendance signals",
)
async def submit_attendance_signals(
    body: AttendanceSubmitRequest,
    token: TokenPayload = Depends(get_current_tenant_context),
) -> AttendanceSubmitResponse:
    facade = AttendanceFacade(tenant_id=token.tenant_id)
    count = facade.ingest_signals(body.signals)
    return AttendanceSubmitResponse(
        status="ok",
        ingested_count=count,
        message=f"Successfully ingested {count} attendance records into server database.",
    )
