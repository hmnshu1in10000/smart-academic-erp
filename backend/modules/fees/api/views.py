"""
modules/fees/api/views.py — Module 6.0
=======================================
GET  /api/v1/fees/invoices    — Paginated fee invoice ledger (role-scoped)
GET  /api/v1/fees/summary     — Collection KPIs & status breakdown
GET  /api/v1/fees/me          — Student personal fee ledger (JWT-identity)
GET  /api/v1/fees/my-child    — Parent child fee ledger (JWT-identity)
POST /api/v1/fees/pay-invoice — Free Razorpay sandbox payment trigger
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field

from shared_kernel.auth.jwt_utils import TokenPayload, get_current_tenant_context
from modules.dummy_data_engine.infrastructure.db.session import SessionLocal
from modules.dummy_data_engine.infrastructure.db.models import Student
from modules.fees.application.facades import FeesFacade

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fees", tags=["Fee Management"])


# ── Response Models ────────────────────────────────────────────────────────────

class FeeInvoiceResponse(BaseModel):
    id: str
    student_id: str
    student_name: str
    section: str
    fee_head: str
    term_label: str
    amount_due: float
    amount_paid: float
    outstanding: float
    due_date: str
    paid_date: Optional[str]
    status: str
    payment_method: Optional[str]
    transaction_ref: Optional[str]


class PaginatedInvoices(BaseModel):
    items: list[FeeInvoiceResponse]
    total: int
    page: int
    page_size: int
    has_next: bool


class FeeSummaryResponse(BaseModel):
    tenant_id: str
    total_billed: float
    total_collected: float
    total_outstanding: float
    collection_rate_pct: float
    paid_count: int
    pending_count: int
    overdue_count: int
    partial_count: int


class StudentFeeLedgerResponse(BaseModel):
    student_id: str
    student_name: str
    section: str
    total_billed: float
    total_paid: float
    outstanding: float
    invoices: list[FeeInvoiceResponse]


class PayInvoiceRequest(BaseModel):
    invoice_id: str = Field(..., description="Invoice UUID to pay")
    payment_method: str = Field("UPI", description="UPI / CARD / NETBANKING / CASH")


class PayInvoiceResponse(BaseModel):
    status: str
    invoice_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    amount_paid: float
    currency: str = "INR"
    receipt_url: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get(
    "/invoices",
    response_model=PaginatedInvoices,
    summary="List fee invoices",
    description="Returns paginated invoice ledger with student name and section. Scoped by role.",
)
async def list_invoices(
    section: Optional[str] = Query(None, description="Filter by section e.g. '10-A'"),
    status: Optional[str] = Query(None, description="PAID / PENDING / OVERDUE / PARTIAL"),
    term: Optional[str] = Query(None, description="Filter by term label"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    token: TokenPayload = Depends(get_current_tenant_context),
) -> PaginatedInvoices:
    facade = FeesFacade(tenant_id=token.tenant_id)
    result = facade.list_invoices(
        section=section,
        status=status,
        term=term,
        page=page,
        page_size=page_size,
        role=token.role,
        assigned_sections=token.assigned_sections,
    )
    return PaginatedInvoices(**result)


@router.get(
    "/summary",
    response_model=FeeSummaryResponse,
    summary="Get fee collection summary KPIs",
)
async def get_fee_summary(
    term: Optional[str] = Query(None, description="Filter by term label"),
    token: TokenPayload = Depends(get_current_tenant_context),
) -> FeeSummaryResponse:
    facade = FeesFacade(tenant_id=token.tenant_id)
    result = facade.get_collection_summary(term=term)
    return FeeSummaryResponse(**result)


@router.get(
    "/me",
    response_model=StudentFeeLedgerResponse,
    summary="Get authenticated student's fee ledger",
)
async def get_my_fee_ledger(
    token: TokenPayload = Depends(get_current_tenant_context),
) -> StudentFeeLedgerResponse:
    """Identity-resolved fee ledger for student role (Section 2.8)."""
    with SessionLocal() as session:
        student = session.query(Student).filter(
            Student.tenant_id == token.tenant_id,
            Student.email == token.sub,
        ).first()
        if not student:
            raise HTTPException(status_code=404, detail="No student record linked to this account.")
        student_id = student.id

    facade = FeesFacade(tenant_id=token.tenant_id)
    result = facade.get_student_ledger(student_id=student_id)
    return StudentFeeLedgerResponse(**result)


@router.get(
    "/my-child",
    response_model=StudentFeeLedgerResponse,
    summary="Get parent's child fee ledger",
)
async def get_my_child_fee_ledger(
    token: TokenPayload = Depends(get_current_tenant_context),
) -> StudentFeeLedgerResponse:
    """Identity-resolved fee ledger for parent role (Section 2.8)."""
    with SessionLocal() as session:
        student = session.query(Student).filter(
            Student.tenant_id == token.tenant_id,
            Student.guardian_user_id == token.sub,
        ).first()
        if not student:
            raise HTTPException(status_code=404, detail="No student record linked to this parent account.")
        student_id = student.id

    facade = FeesFacade(tenant_id=token.tenant_id)
    result = facade.get_student_ledger(student_id=student_id)
    return StudentFeeLedgerResponse(**result)


@router.post(
    "/pay-invoice",
    response_model=PayInvoiceResponse,
    summary="Process sandbox fee payment",
    description="Marks invoice as PAID using free Razorpay test credentials.",
)
async def pay_invoice(
    body: PayInvoiceRequest,
    token: TokenPayload = Depends(get_current_tenant_context),
) -> PayInvoiceResponse:
    if token.role.lower() == "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Teachers are not authorized to process fee payments.",
        )
    facade = FeesFacade(tenant_id=token.tenant_id)
    result = facade.pay_invoice(
        invoice_id=body.invoice_id,
        payment_method=body.payment_method,
    )
    return PayInvoiceResponse(**result)
