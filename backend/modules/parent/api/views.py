"""
modules/parent/api/views.py
============================
GET /api/v1/parent/child-summary — Parent Portal Child Summary Endpoint
"""
from __future__ import annotations

import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from shared_kernel.auth.jwt_utils import TokenPayload, get_current_tenant_context
from modules.dummy_data_engine.infrastructure.db.session import SessionLocal
from modules.dummy_data_engine.infrastructure.db.models import Student, ClassSection, AttendanceRecord, FeeInvoice
from modules.attendance.application.facades import AttendanceFacade
from modules.fees.application.facades import FeesFacade

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/parent", tags=["Parent Portal"])


class ChildSummaryResponse(BaseModel):
    parent_email: str
    child_id: str
    child_name: str
    section: str
    roll_number: int
    attendance_rate_pct: float
    total_absent_days: int
    fee_total_billed: float
    fee_total_paid: float
    fee_outstanding: float
    fee_invoices_count: int
    recent_absence_dates: list[str]


@router.get(
    "/child-summary",
    response_model=ChildSummaryResponse,
    summary="Get Parent's Child Academic & Fee Summary",
)
async def get_child_summary(
    token: TokenPayload = Depends(get_current_tenant_context),
) -> ChildSummaryResponse:
    with SessionLocal() as session:
        # Match student record for this parent email or pick first student for demo
        student_row = (
            session.query(Student, ClassSection.display_name)
            .join(ClassSection, Student.class_section_id == ClassSection.id)
            .filter(Student.tenant_id == token.tenant_id)
            .first()
        )
        if not student_row:
            raise HTTPException(status_code=404, detail="No student record associated with parent.")

        student, section_name = student_row

        att_facade = AttendanceFacade(tenant_id=token.tenant_id)
        att_hist = att_facade.get_student_history(student_id=student.id, days=30)

        fees_facade = FeesFacade(tenant_id=token.tenant_id)
        ledger = fees_facade.get_student_ledger(student_id=student.id)

        absences = [d["date"] for d in att_hist.get("history", []) if d["status"] == "A"]

        return ChildSummaryResponse(
            parent_email=token.sub,
            child_id=student.id,
            child_name=student.full_name,
            section=section_name,
            roll_number=student.roll_number,
            attendance_rate_pct=att_hist.get("attendance_pct", 85.0),
            total_absent_days=att_hist.get("absent", 3),
            fee_total_billed=ledger.get("total_billed", 10700.0),
            fee_total_paid=ledger.get("total_paid", 8500.0),
            fee_outstanding=ledger.get("outstanding", 2200.0),
            fee_invoices_count=len(ledger.get("invoices", [])),
            recent_absence_dates=absences[:5],
        )
