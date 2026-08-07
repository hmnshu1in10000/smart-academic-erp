"""
modules/dummy_data_engine/domain/dtos.py
==========================================
All DTOs for Module 3.0 (Dummy Data Generator Engine).
Source of truth: ARCHITECTURE.md §3.1–3.5

Rule: These are immutable frozen dataclasses — never ORM models.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from uuid import UUID, uuid4

from shared_kernel.contracts.base_dto import BaseDTO


# ── Enumerations ───────────────────────────────────────────────────────────────

class AttendanceStatus(str, Enum):
    PRESENT = "P"
    ABSENT = "A"
    LATE = "L"


class FeePaymentStatus(str, Enum):
    PAID = "PAID"
    PENDING = "PENDING"
    OVERDUE = "OVERDUE"
    PARTIAL = "PARTIAL"
    WAIVED = "WAIVED"


class PaymentMethod(str, Enum):
    UPI = "UPI"
    CARD = "CARD"
    CASH = "CASH"
    BANK_TRANSFER = "BANK_TRANSFER"
    CHEQUE = "CHEQUE"


class Gender(str, Enum):
    MALE = "M"
    FEMALE = "F"
    OTHER = "O"


# ── Sub-Module 3.1 DTOs ────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class SyntheticIdentityDTO(BaseDTO):
    """Generated identity record for a student, staff member, or guardian."""
    identity_id: UUID
    full_name: str
    dob: date
    gender: Gender
    phone: str
    email: str
    address: str
    blood_group: str
    guardian_name: str | None = None
    guardian_phone: str | None = None
    guardian_relation: str | None = None   # "Father" | "Mother" | "Guardian"


@dataclass(frozen=True, slots=True)
class GenerateIdentitiesRequestDTO(BaseDTO):
    tenant_id: str
    count: int
    role_key: str   # "student" | "teacher" | "admin" | "staff"
    grade_level: int | None = None
    locale: str = "en_IN"
    seed: int | None = None


# ── Sub-Module 3.2 DTOs ────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class ClassSectionDTO(BaseDTO):
    section_id: UUID
    tenant_id: str
    grade_level: int
    section_name: str           # "A" | "B" | "C"
    display_name: str           # "Class 10-A"
    class_teacher_id: UUID | None = None
    room_number: str | None = None
    max_strength: int = 30


@dataclass(frozen=True, slots=True)
class SubjectDTO(BaseDTO):
    subject_id: UUID
    name: str
    code: str
    grade_level: int
    periods_per_week: int = 5


@dataclass(frozen=True, slots=True)
class TimetableEntryDTO(BaseDTO):
    entry_id: UUID
    section_id: UUID
    subject_id: UUID
    subject_name: str
    teacher_id: UUID | None
    teacher_name: str
    day_of_week: str            # "MON" | "TUE" | ...
    period_number: int
    start_time: str             # "09:00"
    end_time: str               # "09:45"
    room: str


@dataclass(frozen=True, slots=True)
class GenerateAcademicStructureRequestDTO(BaseDTO):
    tenant_id: str
    grade_levels: list[int]
    sections_per_grade: int
    subjects: list[str]
    periods_per_day: int = 8


@dataclass(frozen=True, slots=True)
class AcademicStructureDTO(BaseDTO):
    classes: tuple[ClassSectionDTO, ...]
    subjects: tuple[SubjectDTO, ...]
    timetable_entries: tuple[TimetableEntryDTO, ...]


# ── Sub-Module 3.3 DTOs ────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class RawAttendanceSignalDTO(BaseDTO):
    """
    Raw attendance event produced by DummyAttendanceIngestionSource.
    Same structure a future CV/OCR pipeline (Phase 2) will produce —
    this is the exact interface boundary that gets swapped.
    """
    signal_id: UUID
    student_id: UUID
    class_section_id: UUID
    timestamp: datetime
    status: AttendanceStatus
    confidence_score: float     # 0.0–1.0 (always 1.0 for dummy; real CV uses model confidence)
    source: str = "DUMMY_GENERATOR"
    notes: str | None = None


@dataclass(frozen=True, slots=True)
class SimulateAttendanceRequestDTO(BaseDTO):
    tenant_id: str
    class_section_id: UUID
    date: date
    student_ids: tuple[UUID, ...]
    attendance_rate: float = 0.93


# ── Sub-Module 3.4 DTOs ────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class FeeHeadDTO(BaseDTO):
    name: str
    amount: Decimal
    is_optional: bool = False
    description: str = ""


@dataclass(frozen=True, slots=True)
class FeeStructureDTO(BaseDTO):
    structure_id: UUID
    tenant_id: str
    grade_level: int
    term_label: str             # "Term 1 2024-25"
    academic_year: str          # "2024-25"
    fee_heads: tuple[FeeHeadDTO, ...]
    total_amount: Decimal


@dataclass(frozen=True, slots=True)
class SyntheticFeeTransactionDTO(BaseDTO):
    invoice_id: UUID
    student_id: UUID
    fee_structure_id: UUID
    fee_head_name: str
    amount_due: Decimal
    amount_paid: Decimal
    due_date: date
    paid_date: date | None
    status: FeePaymentStatus
    payment_method: PaymentMethod | None
    transaction_reference: str | None   # Dummy gateway ref ID


@dataclass(frozen=True, slots=True)
class GenerateFeeHistoryRequestDTO(BaseDTO):
    tenant_id: str
    student_ids: tuple[UUID, ...]
    fee_structure: FeeStructureDTO
    on_time_payment_rate: float = 0.80


# ── Sub-Module 3.5 DTOs ────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class SeedTenantRequestDTO(BaseDTO):
    tenant_id: str
    student_count: int = 50
    staff_count: int = 10
    historical_days: int = 30
    random_seed: int = 42
    drop_existing: bool = False


@dataclass(frozen=True, slots=True)
class SeedSummaryDTO(BaseDTO):
    tenant_id: str
    students_created: int
    staff_created: int
    classes_created: int
    subjects_created: int
    timetable_entries_created: int
    attendance_records_created: int
    fee_structures_created: int
    fee_invoices_created: int
    duration_seconds: float
    seed_credentials_path: str
