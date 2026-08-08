"""
modules/dummy_data_engine/infrastructure/db/models.py
=======================================================
SQLAlchemy 2.0 ORM models for Module 3.0 seeded data.
Source of truth: ARCHITECTURE.md §4.1 (infrastructure layer)

Rule: These models NEVER cross module boundaries. Other modules access
this data ONLY through service facades returning DTOs.

Every table carries tenant_id for multi-tenancy row-level isolation.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey, Integer, Numeric,
    String, Text, UniqueConstraint, Index, Enum as SAEnum,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _new_uuid() -> str:
    return str(uuid.uuid4())


# ── Base ───────────────────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    pass


# ── Class Sections ─────────────────────────────────────────────────────────────

class ClassSection(Base):
    __tablename__ = "class_sections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    grade_level: Mapped[int] = mapped_column(Integer, nullable=False)
    section_name: Mapped[str] = mapped_column(String(10), nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    class_teacher_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    room_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    max_strength: Mapped[int] = mapped_column(Integer, default=30)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        UniqueConstraint("tenant_id", "grade_level", "section_name",
                         name="uq_section_per_tenant"),
    )

    # Relationships
    students: Mapped[list["Student"]] = relationship(
        "Student", back_populates="class_section", lazy="select"
    )
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(
        "AttendanceRecord", back_populates="class_section", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<ClassSection {self.display_name}>"


# ── Students ───────────────────────────────────────────────────────────────────

class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    class_section_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("class_sections.id", ondelete="CASCADE"), nullable=False
    )
    roll_number: Mapped[int] = mapped_column(Integer, nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    gender: Mapped[str] = mapped_column(String(1), nullable=False)     # M/F/O
    dob: Mapped[date | None] = mapped_column(Date, nullable=True)
    blood_group: Mapped[str | None] = mapped_column(String(5), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    email: Mapped[str | None] = mapped_column(String(128), nullable=True)
    address: Mapped[str | None] = mapped_column(Text, nullable=True)
    guardian_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    guardian_phone: Mapped[str | None] = mapped_column(String(20), nullable=True)
    guardian_relation: Mapped[str | None] = mapped_column(String(32), nullable=True)
    guardian_user_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    enrollment_status: Mapped[str] = mapped_column(
        String(16), default="ACTIVE"
    )  # ACTIVE | TRANSFERRED | ARCHIVED
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        UniqueConstraint("tenant_id", "class_section_id", "roll_number",
                         name="uq_roll_per_section"),
        Index("ix_student_name", "tenant_id", "full_name"),
    )

    # Relationships
    class_section: Mapped["ClassSection"] = relationship(
        "ClassSection", back_populates="students"
    )
    attendance_records: Mapped[list["AttendanceRecord"]] = relationship(
        "AttendanceRecord", back_populates="student", lazy="select"
    )
    fee_invoices: Mapped[list["FeeInvoice"]] = relationship(
        "FeeInvoice", back_populates="student", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<Student {self.roll_number}: {self.full_name}>"


# ── Attendance Records ─────────────────────────────────────────────────────────

class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    class_section_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("class_sections.id", ondelete="CASCADE"), nullable=False
    )
    attendance_date: Mapped[date] = mapped_column(Date, nullable=False)
    status: Mapped[str] = mapped_column(String(1), nullable=False)   # P / A / L
    marked_by: Mapped[str | None] = mapped_column(String(36), nullable=True)
    source: Mapped[str] = mapped_column(String(32), default="DUMMY_GENERATOR")
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        UniqueConstraint("student_id", "attendance_date",
                         name="uq_attendance_per_student_date"),
        Index("ix_attendance_date", "tenant_id", "attendance_date"),
        Index("ix_attendance_section_date", "class_section_id", "attendance_date"),
    )

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="attendance_records")
    class_section: Mapped["ClassSection"] = relationship(
        "ClassSection", back_populates="attendance_records"
    )

    def __repr__(self) -> str:
        return f"<AttendanceRecord student={self.student_id} date={self.attendance_date} status={self.status}>"


# ── In-App Notifications ───────────────────────────────────────────────────────

class InAppNotification(Base):
    __tablename__ = "in_app_notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    recipient_user_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    user_email: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    target_role: Mapped[str] = mapped_column(String(32), default="ALL", index=True)  # ADMIN | TEACHER | PARENT | STUDENT | PRINCIPAL | ALL
    role: Mapped[str | None] = mapped_column(String(32), default="ALL")
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(32), default="INFO")  # URGENT | ALERT | INFO
    notification_type: Mapped[str] = mapped_column(String(32), default="INFO")
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    def __repr__(self) -> str:
        return f"<InAppNotification {self.id}: {self.title} (target={self.target_role}, user={self.recipient_user_id})>"



# ── Fee Structures ─────────────────────────────────────────────────────────────

class FeeStructure(Base):
    __tablename__ = "fee_structures"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    grade_level: Mapped[int] = mapped_column(Integer, nullable=False)
    term_label: Mapped[str] = mapped_column(String(64), nullable=False)
    academic_year: Mapped[str] = mapped_column(String(16), nullable=False)
    fee_head_name: Mapped[str] = mapped_column(String(64), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    is_optional: Mapped[bool] = mapped_column(Boolean, default=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    # Relationships
    invoices: Mapped[list["FeeInvoice"]] = relationship(
        "FeeInvoice", back_populates="fee_structure", lazy="select"
    )

    def __repr__(self) -> str:
        return f"<FeeStructure {self.term_label} - {self.fee_head_name}: ₹{self.amount}>"


# ── Fee Invoices ───────────────────────────────────────────────────────────────

class FeeInvoice(Base):
    __tablename__ = "fee_invoices"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    student_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("students.id", ondelete="CASCADE"), nullable=False
    )
    fee_structure_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fee_structures.id", ondelete="CASCADE"), nullable=False
    )
    fee_head_name: Mapped[str] = mapped_column(String(64), nullable=False)
    amount_due: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    amount_paid: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    due_date: Mapped[date] = mapped_column(Date, nullable=False)
    paid_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False)   # PAID/PENDING/OVERDUE/PARTIAL
    payment_method: Mapped[str | None] = mapped_column(String(16), nullable=True)
    transaction_reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        Index("ix_invoice_student", "tenant_id", "student_id"),
        Index("ix_invoice_status", "tenant_id", "status"),
    )

    # Relationships
    student: Mapped["Student"] = relationship("Student", back_populates="fee_invoices")
    fee_structure: Mapped["FeeStructure"] = relationship(
        "FeeStructure", back_populates="invoices"
    )

    def __repr__(self) -> str:
        return f"<FeeInvoice student={self.student_id} {self.fee_head_name} status={self.status}>"


# ── Users / Staff & Faculty ───────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    email: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role_key: Mapped[str] = mapped_column(String(32), nullable=False, default="TEACHER")  # ADMIN/PRINCIPAL/TEACHER/PARENT/STUDENT
    phone: Mapped[str | None] = mapped_column(String(32), nullable=True)
    assigned_sections: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    def __repr__(self) -> str:
        return f"<User {self.full_name} ({self.role_key}) - {self.email}>"


# ── Timetable Entries ─────────────────────────────────────────────────────────

class TimetableEntry(Base):
    __tablename__ = "timetable_entries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_new_uuid)
    tenant_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    class_section_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("class_sections.id", ondelete="CASCADE"), nullable=False
    )
    teacher_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    subject_name: Mapped[str] = mapped_column(String(64), nullable=False)
    subject_code: Mapped[str | None] = mapped_column(String(16), nullable=True)
    day_of_week: Mapped[str] = mapped_column(String(8), nullable=False)  # MON, TUE, WED, THU, FRI, SAT
    period_number: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 to 8
    start_time: Mapped[str] = mapped_column(String(8), nullable=False)   # "08:00"
    end_time: Mapped[str] = mapped_column(String(8), nullable=False)     # "08:45"
    room_number: Mapped[str | None] = mapped_column(String(20), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    __table_args__ = (
        Index("ix_timetable_section_day", "tenant_id", "class_section_id", "day_of_week"),
        Index("ix_timetable_teacher", "tenant_id", "teacher_id"),
    )

    def __repr__(self) -> str:
        return f"<TimetableEntry {self.subject_name} {self.day_of_week} P{self.period_number}>"


