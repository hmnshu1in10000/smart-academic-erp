"""
modules/students/api/views.py — Module 4.0
===========================================
GET /api/v1/students                    — paginated student roster (role-scoped)
GET /api/v1/students/{student_id}       — single student detail (role-scoped)
GET /api/v1/students/{student_id}/timetable — student timetable (role-scoped)

All reads go through StudentsFacade, which applies tenant + role-based row scoping.
"""
from __future__ import annotations

import logging
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from shared_kernel.auth.jwt_utils import TokenPayload, get_current_tenant_context
from modules.students.application.facades import StudentsFacade

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/students", tags=["Students"])


# ── Response Models ────────────────────────────────────────────────────────────

class StudentSummary(BaseModel):
    id: str
    roll_number: int
    full_name: str
    gender: str
    class_section: str
    guardian_name: Optional[str]
    guardian_phone: Optional[str]
    enrollment_status: str


class StudentDetail(StudentSummary):
    dob: Optional[str]
    blood_group: Optional[str]
    phone: Optional[str]
    email: Optional[str]
    address: Optional[str]
    guardian_relation: Optional[str]


class TimetableEntry(BaseModel):
    day: str
    period: int
    subject: str
    teacher: str
    start_time: str
    end_time: str
    room: str


class PaginatedStudents(BaseModel):
    items: list[StudentSummary]
    total: int
    page: int
    page_size: int
    has_next: bool


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=PaginatedStudents,
    summary="List students",
    description="Returns paginated student roster for the authenticated tenant, scoped by role.",
)
async def list_students(
    section: Optional[str] = Query(None, description="Filter by section e.g. '10-A'"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    token: TokenPayload = Depends(get_current_tenant_context),
) -> PaginatedStudents:
    facade = StudentsFacade(
        tenant_id=token.tenant_id,
        role=token.role,
        requesting_user_id=token.sub,
        assigned_sections=token.assigned_sections,
    )
    result = facade.list_students(section=section, page=page, page_size=page_size)
    return PaginatedStudents(**result)


@router.get(
    "/{student_id}",
    response_model=StudentDetail,
    summary="Get student detail",
)
async def get_student(
    student_id: str,
    token: TokenPayload = Depends(get_current_tenant_context),
) -> StudentDetail:
    facade = StudentsFacade(
        tenant_id=token.tenant_id,
        role=token.role,
        requesting_user_id=token.sub,
        assigned_sections=token.assigned_sections,
    )
    student = facade.get_student(student_id)
    if not student:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found")
    return StudentDetail(**student)


@router.get(
    "/{student_id}/timetable",
    response_model=list[TimetableEntry],
    summary="Get student timetable",
    description="Returns the weekly timetable for a student based on their class section.",
)
async def get_student_timetable(
    student_id: str,
    token: TokenPayload = Depends(get_current_tenant_context),
) -> list[TimetableEntry]:
    facade = StudentsFacade(
        tenant_id=token.tenant_id,
        role=token.role,
        requesting_user_id=token.sub,
        assigned_sections=token.assigned_sections,
    )
    entries = facade.get_student_timetable(student_id)
    if entries is None:
        raise HTTPException(status_code=404, detail=f"Student '{student_id}' not found")
    return [TimetableEntry(**e) for e in entries]
