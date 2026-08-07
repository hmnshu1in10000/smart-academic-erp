"""
modules/fees/application/facades.py — Module 6.0 Facade
=========================================================
Reads from seeded fee_invoices + fee_structures + students + class_sections.
Returns plain dicts for the API layer.
"""
from __future__ import annotations

import logging
from decimal import Decimal
from typing import Optional

from sqlalchemy import func

from modules.dummy_data_engine.infrastructure.db.session import SessionLocal
from modules.dummy_data_engine.infrastructure.db.models import (
    FeeInvoice, FeeStructure, Student, ClassSection,
)

logger = logging.getLogger(__name__)


def _invoice_to_dict(inv: FeeInvoice, student_name: str, section_name: str) -> dict:
    amt_outstanding = float(inv.amount_due) - float(inv.amount_paid)
    return {
        "id": inv.id,
        "student_id": inv.student_id,
        "student_name": student_name,
        "section": section_name,
        "fee_head": inv.fee_head_name,
        "term_label": "",   # Fetched separately if needed
        "amount_due": float(inv.amount_due),
        "amount_paid": float(inv.amount_paid),
        "outstanding": round(amt_outstanding, 2),
        "due_date": str(inv.due_date),
        "paid_date": str(inv.paid_date) if inv.paid_date else None,
        "status": inv.status,
        "payment_method": inv.payment_method,
        "transaction_ref": inv.transaction_reference,
    }


class FeesFacade:
    """Module 6.0 Application Service — fee read operations."""

    def __init__(self, tenant_id: str) -> None:
        self._tenant_id = tenant_id

    def list_invoices(
        self,
        section: Optional[str],
        status: Optional[str],
        term: Optional[str],
        page: int,
        page_size: int,
    ) -> dict:
        with SessionLocal() as session:
            q = (
                session.query(
                    FeeInvoice,
                    Student.full_name,
                    ClassSection.display_name,
                    FeeStructure.term_label,
                )
                .join(Student, FeeInvoice.student_id == Student.id)
                .join(ClassSection, Student.class_section_id == ClassSection.id)
                .join(FeeStructure, FeeInvoice.fee_structure_id == FeeStructure.id)
                .filter(FeeInvoice.tenant_id == self._tenant_id)
            )
            if section:
                q = q.filter(ClassSection.display_name.ilike(f"%{section}%"))
            if status:
                q = q.filter(FeeInvoice.status == status.upper())
            if term:
                q = q.filter(FeeStructure.term_label.ilike(f"%{term}%"))

            total = q.count()
            rows = q.offset((page - 1) * page_size).limit(page_size).all()

            items = []
            for inv, name, sec, tl in rows:
                d = _invoice_to_dict(inv, name, sec)
                d["term_label"] = tl
                items.append(d)

            return {
                "items": items,
                "total": total,
                "page": page,
                "page_size": page_size,
                "has_next": (page * page_size) < total,
            }

    def get_collection_summary(self, term: Optional[str]) -> dict:
        with SessionLocal() as session:
            q = session.query(
                func.sum(FeeInvoice.amount_due).label("billed"),
                func.sum(FeeInvoice.amount_paid).label("collected"),
                func.count(FeeInvoice.id).label("count"),
            ).filter(FeeInvoice.tenant_id == self._tenant_id)

            if term:
                q = q.join(FeeStructure, FeeInvoice.fee_structure_id == FeeStructure.id)
                q = q.filter(FeeStructure.term_label.ilike(f"%{term}%"))

            row = q.first()
            billed = float(row.billed or 0)
            collected = float(row.collected or 0)
            outstanding = billed - collected

            # Status breakdown
            status_rows = (
                session.query(FeeInvoice.status, func.count(FeeInvoice.id))
                .filter(FeeInvoice.tenant_id == self._tenant_id)
                .group_by(FeeInvoice.status)
                .all()
            )
            status_map = {s: c for s, c in status_rows}

            return {
                "tenant_id": self._tenant_id,
                "total_billed": round(billed, 2),
                "total_collected": round(collected, 2),
                "total_outstanding": round(outstanding, 2),
                "collection_rate_pct": round(collected / billed * 100, 1) if billed else 0.0,
                "paid_count": status_map.get("PAID", 0),
                "pending_count": status_map.get("PENDING", 0),
                "overdue_count": status_map.get("OVERDUE", 0),
                "partial_count": status_map.get("PARTIAL", 0),
            }

    def get_student_ledger(self, student_id: str) -> dict:
        with SessionLocal() as session:
            student_row = (
                session.query(Student, ClassSection.display_name)
                .join(ClassSection, Student.class_section_id == ClassSection.id)
                .filter(Student.id == student_id, Student.tenant_id == self._tenant_id)
                .first()
            )
            if not student_row:
                from shared_kernel.exceptions.domain_exceptions import EntityNotFoundError
                raise EntityNotFoundError(f"Student {student_id} not found", "STUDENT_NOT_FOUND")

            student, section_name = student_row

            invoices = (
                session.query(FeeInvoice, FeeStructure.term_label)
                .join(FeeStructure, FeeInvoice.fee_structure_id == FeeStructure.id)
                .filter(
                    FeeInvoice.student_id == student_id,
                    FeeInvoice.tenant_id == self._tenant_id,
                )
                .order_by(FeeInvoice.due_date)
                .all()
            )

            billed = sum(float(i.amount_due) for i, _ in invoices)
            paid = sum(float(i.amount_paid) for i, _ in invoices)

            items = []
            for inv, tl in invoices:
                d = _invoice_to_dict(inv, student.full_name, section_name)
                d["term_label"] = tl
                items.append(d)

            return {
                "student_id": student.id,
                "student_name": student.full_name,
                "section": section_name,
                "total_billed": round(billed, 2),
                "total_paid": round(paid, 2),
                "outstanding": round(billed - paid, 2),
                "invoices": items,
            }
