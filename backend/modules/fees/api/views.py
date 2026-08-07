"""
modules/fees/api/views.py — Module 6.0
========================================
GET /api/v1/fees/invoices          — paginated fee invoices
GET /api/v1/fees/summary           — collection rate, overdue count
GET /api/v1/fees/student/{id}      — per-student fee ledger
"""
from __future__ import annotations

import logging
from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from shared_kernel.auth.jwt_utils import TokenPayload, get_current_tenant_context
from modules.fees.application.facades import FeesFacade

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/fees", tags=["Fees"])


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


class FeeCollectionSummary(BaseModel):
    tenant_id: str
    total_billed: float
    total_collected: float
    total_outstanding: float
    collection_rate_pct: float
    paid_count: int
    pending_count: int
    overdue_count: int
    partial_count: int


class StudentFeeLedger(BaseModel):
    student_id: str
    student_name: str
    section: str
    total_billed: float
    total_paid: float
    outstanding: float
    invoices: list[FeeInvoiceResponse]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get(
    "/invoices",
    response_model=PaginatedInvoices,
    summary="List fee invoices",
    description=(
        "Returns paginated fee invoices. Filter by section, status, or term. "
        "Reads from seeded fee_invoices table."
    ),
)
async def list_invoices(
    section: Optional[str] = Query(None, description="Class section e.g. '10-A'"),
    status: Optional[str] = Query(None, description="PAID | PENDING | OVERDUE | PARTIAL"),
    term: Optional[str] = Query(None, description="e.g. 'Term 1 2024-25'"),
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    token: TokenPayload = Depends(get_current_tenant_context),
) -> PaginatedInvoices:
    facade = FeesFacade(tenant_id=token.tenant_id)
    result = facade.list_invoices(
        section=section, status=status, term=term, page=page, page_size=page_size
    )
    return PaginatedInvoices(**result)


@router.get(
    "/summary",
    response_model=FeeCollectionSummary,
    summary="Fee collection summary",
)
async def fee_summary(
    term: Optional[str] = Query(None, description="Filter by term"),
    token: TokenPayload = Depends(get_current_tenant_context),
) -> FeeCollectionSummary:
    facade = FeesFacade(tenant_id=token.tenant_id)
    result = facade.get_collection_summary(term=term)
    return FeeCollectionSummary(**result)


class PayInvoiceRequest(BaseModel):
    invoice_id: str
    payment_method: Optional[str] = "UPI"


class PayInvoiceResponse(BaseModel):
    status: str
    invoice_id: str
    razorpay_order_id: str
    razorpay_payment_id: str
    amount_paid: float
    currency: str = "INR"
    receipt_url: str


@router.get(
    "/student/{student_id}",
    response_model=StudentFeeLedger,
    summary="Get student fee ledger",
)
async def student_fee_ledger(
    student_id: str,
    token: TokenPayload = Depends(get_current_tenant_context),
) -> StudentFeeLedger:
    facade = FeesFacade(tenant_id=token.tenant_id)
    result = facade.get_student_ledger(student_id=student_id)
    return StudentFeeLedger(**result)


@router.post(
    "/pay-invoice",
    response_model=PayInvoiceResponse,
    summary="Pay Fee Invoice via Free Razorpay Sandbox",
)
async def pay_invoice_sandbox(
    body: PayInvoiceRequest,
    token: TokenPayload = Depends(get_current_tenant_context),
) -> PayInvoiceResponse:
    facade = FeesFacade(tenant_id=token.tenant_id)
    res = facade.pay_invoice(invoice_id=body.invoice_id, payment_method=body.payment_method or "UPI")
    return PayInvoiceResponse(**res)
