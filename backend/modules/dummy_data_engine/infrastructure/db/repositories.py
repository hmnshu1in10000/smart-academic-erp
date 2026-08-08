"""
modules/dummy_data_engine/infrastructure/db/repositories.py
=============================================================
Concrete repository implementations for bulk-insert seeding operations.
Source of truth: ARCHITECTURE.md Appendix §5 — "bulk SQL writes" required.

These repositories translate DTOs → ORM model instances and perform
bulk inserts. They are the ONLY place in Module 3.0 that touches the DB.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy.orm import Session

from modules.dummy_data_engine.domain.dtos import (
    ClassSectionDTO,
    RawAttendanceSignalDTO,
    SyntheticFeeTransactionDTO,
    SyntheticIdentityDTO,
    FeeStructureDTO,
)
from modules.dummy_data_engine.infrastructure.db.models import (
    AttendanceRecord,
    ClassSection,
    FeeInvoice,
    FeeStructure,
    Student,
    User,
    TimetableEntry,
    InAppNotification,
)

logger = logging.getLogger(__name__)


class NotificationRepository:
    """Persists InAppNotification records to the in_app_notifications table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def bulk_insert(self, notifs: list[dict]) -> int:
        """Bulk insert notification rows."""
        orm_objects = [
            InAppNotification(
                id=n.get("id"),
                tenant_id=n["tenant_id"],
                recipient_user_id=n.get("recipient_user_id"),
                user_email=n.get("recipient_user_id"),
                target_role=n.get("target_role", "ALL"),
                role=n.get("target_role", "ALL"),
                title=n["title"],
                message=n["message"],
                category=n.get("category", "INFO"),
                notification_type=n.get("category", "INFO"),
                is_read=n.get("is_read", False),
                read=n.get("is_read", False),
                created_at=n.get("created_at", datetime.now(timezone.utc)),
            )
            for n in notifs
        ]
        self._session.bulk_save_objects(orm_objects)
        logger.info("Inserted %d in-app notifications", len(orm_objects))
        return len(orm_objects)



class UserRepository:
    """Persists User/Teacher records to the users table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def bulk_insert(self, users_data: list[dict]) -> int:
        """Bulk insert User records avoiding duplicate emails."""
        inserted = 0
        for u in users_data:
            existing = self._session.query(User).filter_by(
                tenant_id=u["tenant_id"], email=u["email"]
            ).first()
            if existing:
                existing.full_name = u["full_name"]
                existing.role_key = u.get("role_key", "TEACHER")
                existing.phone = u.get("phone")
                existing.assigned_sections = u.get("assigned_sections")
            else:
                user_obj = User(
                    id=u.get("id"),
                    tenant_id=u["tenant_id"],
                    email=u["email"],
                    full_name=u["full_name"],
                    role_key=u.get("role_key", "TEACHER"),
                    phone=u.get("phone"),
                    assigned_sections=u.get("assigned_sections"),
                    is_active=True,
                )
                self._session.add(user_obj)
                inserted += 1
        self._session.commit()
        logger.info("Upserted %d users", len(users_data))
        return inserted


class TimetableRepository:
    """Persists TimetableEntry objects to the timetable_entries table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def bulk_insert(self, entries: list[dict]) -> int:
        """Bulk insert timetable entries."""
        orm_objects = [
            TimetableEntry(
                id=e.get("id"),
                tenant_id=e["tenant_id"],
                class_section_id=e["class_section_id"],
                teacher_id=e.get("teacher_id"),
                subject_name=e["subject_name"],
                subject_code=e.get("subject_code"),
                day_of_week=e["day_of_week"],
                period_number=e["period_number"],
                start_time=e["start_time"],
                end_time=e["end_time"],
                room_number=e.get("room_number"),
            )
            for e in entries
        ]
        self._session.bulk_save_objects(orm_objects)
        logger.info("Inserted %d timetable entries", len(orm_objects))
        return len(orm_objects)



class ClassSectionRepository:
    """Persists ClassSectionDTO objects to the class_sections table."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def bulk_insert(self, sections: list[ClassSectionDTO]) -> int:
        """Insert all sections. Returns count of rows inserted."""
        orm_objects = [
            ClassSection(
                id=str(section.section_id),
                tenant_id=section.tenant_id,
                grade_level=section.grade_level,
                section_name=section.section_name,
                display_name=section.display_name,
                class_teacher_id=(
                    str(section.class_teacher_id)
                    if section.class_teacher_id else None
                ),
                room_number=section.room_number,
                max_strength=section.max_strength,
            )
            for section in sections
        ]
        self._session.bulk_save_objects(orm_objects)
        logger.info("Inserted %d class sections", len(orm_objects))
        return len(orm_objects)


class StudentRepository:
    """Persists student identity + enrollment data."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def bulk_insert(
        self,
        identities: list[SyntheticIdentityDTO],
        section_id: str,
        tenant_id: str,
        roll_number_offset: int = 1,
    ) -> list[str]:
        """
        Insert students into a specific section.
        Returns list of inserted student IDs (str UUIDs).
        """
        orm_objects = []
        student_ids = []
        for i, identity in enumerate(identities):
            sid = str(identity.identity_id)
            student_ids.append(sid)
            orm_objects.append(Student(
                id=sid,
                tenant_id=tenant_id,
                class_section_id=section_id,
                roll_number=roll_number_offset + i,
                full_name=identity.full_name,
                gender=identity.gender.value,
                dob=identity.dob,
                blood_group=identity.blood_group,
                phone=identity.phone,
                email=identity.email,
                address=identity.address,
                guardian_name=identity.guardian_name,
                guardian_phone=identity.guardian_phone,
                guardian_relation=identity.guardian_relation,
                enrollment_status="ACTIVE",
            ))
        self._session.bulk_save_objects(orm_objects)
        logger.info(
            "Inserted %d students into section %s", len(orm_objects), section_id
        )
        return student_ids


class AttendanceRepository:
    """Bulk-inserts RawAttendanceSignalDTO objects as AttendanceRecord rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def bulk_insert(
        self,
        signals: list[RawAttendanceSignalDTO],
        tenant_id: str,
    ) -> int:
        """
        Translate signals to ORM records and bulk insert.
        Uses core INSERT (not ORM objects) for maximum performance on large batches.
        """
        if not signals:
            return 0

        # Use mappings for bulk insert — fastest SQLAlchemy path (ARCHITECTURE Appendix §5)
        mappings = [
            {
                "id": str(signal.signal_id),
                "tenant_id": tenant_id,
                "student_id": str(signal.student_id),
                "class_section_id": str(signal.class_section_id),
                "attendance_date": signal.timestamp.date(),
                "status": signal.status.value,
                "source": signal.source,
                "notes": signal.notes,
                "created_at": datetime.now(timezone.utc),
            }
            for signal in signals
        ]
        self._session.bulk_insert_mappings(AttendanceRecord, mappings)
        logger.info("Bulk inserted %d attendance records", len(mappings))
        return len(mappings)


class FeeStructureRepository:
    """
    Persists FeeStructureDTO (one row per fee-head per structure).
    Returns a mapping of (structure_id, fee_head_name) -> db_row_id
    so FeeInvoiceRepository can reference correct FK values.
    """

    def __init__(self, session: Session) -> None:
        self._session = session

    def bulk_insert(
        self, structures: list[FeeStructureDTO], tenant_id: str
    ) -> tuple[int, dict[tuple[str, str], str]]:
        """
        Insert fee structure rows.
        Returns (count, id_map) where id_map maps
        (structure_id_str, fee_head_name) -> db_row_id.
        """
        orm_objects = []
        id_map: dict[tuple[str, str], str] = {}
        for structure in structures:
            for fee_head in structure.fee_heads:
                row_id = str(structure.structure_id) + "_" + fee_head.name[:8].replace(" ", "")
                id_map[(str(structure.structure_id), fee_head.name)] = row_id
                orm_objects.append(FeeStructure(
                    id=row_id,
                    tenant_id=tenant_id,
                    grade_level=structure.grade_level,
                    term_label=structure.term_label,
                    academic_year=structure.academic_year,
                    fee_head_name=fee_head.name,
                    amount=fee_head.amount,
                    is_optional=fee_head.is_optional,
                    description=fee_head.description,
                ))
        self._session.bulk_save_objects(orm_objects)
        logger.info("Inserted %d fee structure rows", len(orm_objects))
        return len(orm_objects), id_map


class FeeInvoiceRepository:
    """Bulk-inserts SyntheticFeeTransactionDTO objects as FeeInvoice rows."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def bulk_insert(
        self,
        transactions: list[SyntheticFeeTransactionDTO],
        tenant_id: str,
        fee_structure_id_map: dict[tuple[str, str], str] | None = None,
    ) -> int:
        """
        Translate DTOs to mappings and bulk insert.
        fee_structure_id_map: maps (structure_uuid_str, fee_head_name) -> actual DB row id.
        If not provided, uses the DTO's fee_structure_id directly.
        """
        if not transactions:
            return 0

        mappings = []
        for txn in transactions:
            # Resolve the correct fee_structure row ID
            if fee_structure_id_map:
                db_structure_id = fee_structure_id_map.get(
                    (str(txn.fee_structure_id), txn.fee_head_name),
                    str(txn.fee_structure_id),
                )
            else:
                db_structure_id = str(txn.fee_structure_id)

            mappings.append({
                "id": str(txn.invoice_id),
                "tenant_id": tenant_id,
                "student_id": str(txn.student_id),
                "fee_structure_id": db_structure_id,
                "fee_head_name": txn.fee_head_name,
                "amount_due": txn.amount_due,
                "amount_paid": txn.amount_paid,
                "due_date": txn.due_date,
                "paid_date": txn.paid_date,
                "status": txn.status.value,
                "payment_method": txn.payment_method.value if txn.payment_method else None,
                "transaction_reference": txn.transaction_reference,
                "created_at": datetime.now(timezone.utc),
            })
        self._session.bulk_insert_mappings(FeeInvoice, mappings)
        logger.info("Bulk inserted %d fee invoices", len(mappings))
        return len(mappings)
