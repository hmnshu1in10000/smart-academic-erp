"""
modules/dummy_data_engine/application/services/fee_history_generator.py
=========================================================================
Sub-Module 3.4 — Dummy Fee Transaction Generator.
Source of truth: ARCHITECTURE.md §3.4

Generates realistic fee structures (Tuition + Transport) and
transaction histories (Paid/Pending/Overdue) for all students.

Fee structure (CBSE school, Kanpur, typical 2024-25 rates):
  - Tuition Fee:  ₹8,500 per term
  - Transport Fee: ₹2,200 per term (optional, for enrolled bus students)
  - Total per student per term: ₹10,700

Dependencies: None (pure data generation).
"""
from __future__ import annotations

import logging
import random
import string
from datetime import date, timedelta
from decimal import Decimal
from uuid import UUID, uuid4

from modules.dummy_data_engine.domain.dtos import (
    FeeHeadDTO,
    FeePaymentStatus,
    FeeStructureDTO,
    GenerateFeeHistoryRequestDTO,
    PaymentMethod,
    SyntheticFeeTransactionDTO,
)

logger = logging.getLogger(__name__)

# Payment method distribution (weighted for Indian school context)
_PAYMENT_METHODS = [
    PaymentMethod.UPI,
    PaymentMethod.CASH,
    PaymentMethod.CARD,
    PaymentMethod.BANK_TRANSFER,
    PaymentMethod.CHEQUE,
]
_PAYMENT_WEIGHTS = [0.42, 0.28, 0.14, 0.10, 0.06]

# Academic year 2024-25 terms
ACADEMIC_YEAR = "2024-25"
TERM_DEFINITIONS = [
    {
        "label": "Term 1 2024-25",
        "term_num": 1,
        "due_date_offset_days": 0,      # Due at start of term (June 15)
        "reference_date": date(2024, 6, 15),
    },
    {
        "label": "Term 2 2024-25",
        "term_num": 2,
        "due_date_offset_days": 0,
        "reference_date": date(2024, 11, 15),
    },
]

# Fee heads definition
_FEE_HEADS = [
    FeeHeadDTO(
        name="Tuition Fee",
        amount=Decimal("8500.00"),
        is_optional=False,
        description="Academic instruction and school facilities",
    ),
    FeeHeadDTO(
        name="Transport Fee",
        amount=Decimal("2200.00"),
        is_optional=True,
        description="School bus service (routes within 20 km)",
    ),
]


def _generate_txn_reference() -> str:
    """Generate a dummy payment gateway transaction ID."""
    prefix = "DUMMY"
    chars = string.ascii_uppercase + string.digits
    suffix = "".join(random.choices(chars, k=12))
    return f"{prefix}-{suffix}"


class FeeHistoryGenerator:
    """
    Sub-Module 3.4: Generates fee structures and historically plausible
    payment transaction records for all enrolled students.

    Configurable:
    - on_time_payment_rate: fraction of students who pay on time (default 0.80)
    - transport_enrollment_rate: fraction of students using school bus (default 0.60)
    """

    def __init__(
        self,
        seed: int | None = None,
        transport_enrollment_rate: float = 0.60,
    ) -> None:
        if seed is not None:
            random.seed(seed)
        self._transport_rate = transport_enrollment_rate
        logger.debug("FeeHistoryGenerator initialized (seed=%s)", seed)

    def generate_fee_structures(self, tenant_id: str) -> list[FeeStructureDTO]:
        """
        Create FeeStructureDTOs for all terms defined in TERM_DEFINITIONS.
        One structure per term (applies to all grade 10 sections in Phase 1).
        """
        structures = []
        for term_def in TERM_DEFINITIONS:
            structure = FeeStructureDTO(
                structure_id=uuid4(),
                tenant_id=tenant_id,
                grade_level=10,
                term_label=term_def["label"],
                academic_year=ACADEMIC_YEAR,
                fee_heads=tuple(_FEE_HEADS),
                total_amount=sum(h.amount for h in _FEE_HEADS),
            )
            structures.append(structure)
            logger.debug(
                "Created fee structure: %s (total=₹%s)",
                structure.term_label, structure.total_amount
            )
        logger.info("Generated %d fee structures", len(structures))
        return structures

    def generate_invoices(
        self, request: GenerateFeeHistoryRequestDTO
    ) -> list[SyntheticFeeTransactionDTO]:
        """
        Generate per-student, per-fee-head invoices with realistic payment behavior.
        """
        all_invoices: list[SyntheticFeeTransactionDTO] = []

        for student_id in request.student_ids:
            # Determine if this student uses transport (sticky per student)
            uses_transport = random.random() < self._transport_rate
            # Determine if this student is an on-time payer (sticky characteristic)
            is_prompt_payer = random.random() < request.on_time_payment_rate

            for fee_head in request.fee_structure.fee_heads:
                # Skip optional transport if student doesn't use bus
                if fee_head.is_optional and not uses_transport:
                    continue

                # Find term due date from term definitions
                term_label = request.fee_structure.term_label
                term_def = next(
                    (t for t in TERM_DEFINITIONS if t["label"] == term_label),
                    TERM_DEFINITIONS[0],
                )
                due_date: date = term_def["reference_date"]

                invoice = self._simulate_payment_behavior(
                    student_id=student_id,
                    fee_structure_id=request.fee_structure.structure_id,
                    fee_head=fee_head,
                    due_date=due_date,
                    is_prompt_payer=is_prompt_payer,
                )
                all_invoices.append(invoice)

        logger.info(
            "Generated %d fee invoices for %d students (structure=%s)",
            len(all_invoices), len(request.student_ids),
            request.fee_structure.term_label,
        )
        return all_invoices

    def _simulate_payment_behavior(
        self,
        student_id: UUID,
        fee_structure_id: UUID,
        fee_head: FeeHeadDTO,
        due_date: date,
        is_prompt_payer: bool,
    ) -> SyntheticFeeTransactionDTO:
        """
        Simulate realistic payment behavior for one invoice.
        - Prompt payers: pay 0–7 days before due date
        - Late payers: pay 1–30 days after due date  (or still pending)
        - 20% chance of still being pending (defaulter simulation)
        """
        amount_due = fee_head.amount
        today = date(2024, 12, 1)   # Snapshot date for simulation

        if is_prompt_payer:
            # Pay before or on due date
            days_before = random.randint(0, 7)
            paid_date = due_date - timedelta(days=days_before)
            paid_date = min(paid_date, today)   # can't be in future
            status = FeePaymentStatus.PAID
            amount_paid = amount_due
            method = random.choices(_PAYMENT_METHODS, weights=_PAYMENT_WEIGHTS, k=1)[0]
            txn_ref = _generate_txn_reference()
        else:
            # Late payer or defaulter
            if random.random() < 0.35:   # 35% of late payers are still unpaid
                paid_date = None
                if today > due_date:
                    status = FeePaymentStatus.OVERDUE
                else:
                    status = FeePaymentStatus.PENDING
                amount_paid = Decimal("0.00")
                method = None
                txn_ref = None
            elif random.random() < 0.15:  # 15% made partial payment
                partial_pct = Decimal(str(round(random.uniform(0.3, 0.85), 2)))
                amount_paid = (amount_due * partial_pct).quantize(Decimal("0.01"))
                days_late = random.randint(1, 30)
                paid_date = due_date + timedelta(days=days_late)
                paid_date = min(paid_date, today)
                status = FeePaymentStatus.PARTIAL
                method = random.choices(_PAYMENT_METHODS, weights=_PAYMENT_WEIGHTS, k=1)[0]
                txn_ref = _generate_txn_reference()
            else:
                # Paid late but fully
                days_late = random.randint(1, 30)
                paid_date = due_date + timedelta(days=days_late)
                paid_date = min(paid_date, today)
                status = FeePaymentStatus.PAID
                amount_paid = amount_due
                method = random.choices(_PAYMENT_METHODS, weights=_PAYMENT_WEIGHTS, k=1)[0]
                txn_ref = _generate_txn_reference()

        return SyntheticFeeTransactionDTO(
            invoice_id=uuid4(),
            student_id=student_id,
            fee_structure_id=fee_structure_id,
            fee_head_name=fee_head.name,
            amount_due=amount_due,
            amount_paid=amount_paid,
            due_date=due_date,
            paid_date=paid_date,
            status=status,
            payment_method=method,
            transaction_reference=txn_ref,
        )
