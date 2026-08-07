"""
modules/attendance/application/facades.py — Module 5.0 Facade
==============================================================
Reads from the seeded attendance_records + students + class_sections tables.
Returns plain dicts for the API layer.
"""
from __future__ import annotations

import logging
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import func, text

from modules.dummy_data_engine.infrastructure.db.session import SessionLocal
from modules.dummy_data_engine.infrastructure.db.models import (
    AttendanceRecord, Student, ClassSection,
)

logger = logging.getLogger(__name__)

_CHRONIC_ABSENT_THRESHOLD = 5   # ≥5 absent days in period → chronic absentee


class AttendanceFacade:
    """Module 5.0 Application Service — attendance read & write operations."""

    def __init__(self, tenant_id: str) -> None:
        self._tenant_id = tenant_id

    def ingest_signals(self, signals: list[dict]) -> int:
        """Ingests mobile attendance signals and writes to attendance_records DB table."""
        if not signals:
            return 0

        with SessionLocal() as session:
            # Check or resolve valid class_section_id and student_id
            first_section = session.query(ClassSection).filter(
                ClassSection.tenant_id == self._tenant_id
            ).first()
            default_sec_id = first_section.id if first_section else "default_sec"

            first_student = session.query(Student).filter(
                Student.tenant_id == self._tenant_id
            ).first()
            default_student_id = first_student.id if first_student else "default_student"

            records = []
            for s in signals:
                sid = s.get("student_id", default_student_id)
                if len(sid) < 10:
                    sid = default_student_id

                sec_id = s.get("class_section_id", default_sec_id)
                if len(sec_id) < 10:
                    sec_id = default_sec_id

                # Delete any pre-existing record for this student on today's date
                session.query(AttendanceRecord).filter(
                    AttendanceRecord.tenant_id == self._tenant_id,
                    AttendanceRecord.student_id == sid,
                    AttendanceRecord.attendance_date == date.today(),
                ).delete(synchronize_session=False)

                rec = AttendanceRecord(
                    id=s.get("signal_id", f"sig_{date.today()}_{sid[:8]}"),
                    tenant_id=self._tenant_id,
                    student_id=sid,
                    class_section_id=sec_id,
                    attendance_date=date.today(),
                    status=s.get("status", "P"),
                    source=s.get("source", "TEACHER_MOBILE_APP"),
                    notes=s.get("notes"),
                )
                records.append(rec)

            session.add_all(records)
            session.commit()
            logger.info("Successfully ingested %d mobile attendance signals for tenant %s", len(records), self._tenant_id)
            return len(records)

    def get_summary(
        self,
        section: Optional[str],
        from_date: Optional[str],
        to_date: Optional[str],
    ) -> dict:
        """Aggregate daily attendance stats for a date range."""
        with SessionLocal() as session:
            end = date.fromisoformat(to_date) if to_date else date.today()
            start = date.fromisoformat(from_date) if from_date else end - timedelta(days=29)

            q = (
                session.query(
                    AttendanceRecord.attendance_date,
                    ClassSection.display_name,
                    AttendanceRecord.status,
                    func.count(AttendanceRecord.id).label("cnt"),
                )
                .join(Student, AttendanceRecord.student_id == Student.id)
                .join(ClassSection, AttendanceRecord.class_section_id == ClassSection.id)
                .filter(
                    AttendanceRecord.tenant_id == self._tenant_id,
                    AttendanceRecord.attendance_date >= start,
                    AttendanceRecord.attendance_date <= end,
                )
            )
            if section:
                q = q.filter(ClassSection.display_name.ilike(f"%{section}%"))

            q = q.group_by(
                AttendanceRecord.attendance_date,
                ClassSection.display_name,
                AttendanceRecord.status,
            ).order_by(AttendanceRecord.attendance_date)

            rows = q.all()

            # Pivot into per-day stats
            daily: dict[tuple[str, str], dict] = {}
            for att_date, sec_name, status, cnt in rows:
                key = (str(att_date), sec_name)
                if key not in daily:
                    daily[key] = {"date": str(att_date), "section": sec_name,
                                  "total": 0, "present": 0, "absent": 0, "late": 0}
                daily[key]["total"] += cnt
                if status == "P":
                    daily[key]["present"] += cnt
                elif status == "A":
                    daily[key]["absent"] += cnt
                elif status == "L":
                    daily[key]["late"] += cnt

            daily_stats = []
            total_p = total_all = 0
            for d in sorted(daily.values(), key=lambda x: x["date"]):
                if d["total"] > 0:
                    d["attendance_pct"] = round(
                        (d["present"] + d["late"]) / d["total"] * 100, 1
                    )
                else:
                    d["attendance_pct"] = 0.0
                daily_stats.append(d)
                total_p += d["present"] + d["late"]
                total_all += d["total"]

            overall_pct = round(total_p / total_all * 100, 1) if total_all else 0.0

            # Chronic absentees
            chronic_q = (
                session.query(
                    Student.id,
                    Student.full_name,
                    func.count(AttendanceRecord.id).label("absent_days"),
                )
                .join(AttendanceRecord, AttendanceRecord.student_id == Student.id)
                .join(ClassSection, AttendanceRecord.class_section_id == ClassSection.id)
                .filter(
                    AttendanceRecord.tenant_id == self._tenant_id,
                    AttendanceRecord.status == "A",
                    AttendanceRecord.attendance_date >= start,
                    AttendanceRecord.attendance_date <= end,
                )
            )
            if section:
                chronic_q = chronic_q.filter(ClassSection.display_name.ilike(f"%{section}%"))
            chronic_q = chronic_q.group_by(Student.id, Student.full_name).having(
                func.count(AttendanceRecord.id) >= _CHRONIC_ABSENT_THRESHOLD
            ).order_by(func.count(AttendanceRecord.id).desc()).limit(10)

            chronic = [
                {"student_id": r.id, "full_name": r.full_name, "absent_days": r.absent_days}
                for r in chronic_q.all()
            ]

            return {
                "tenant_id": self._tenant_id,
                "section": section,
                "from_date": str(start),
                "to_date": str(end),
                "daily_stats": daily_stats,
                "overall_present_pct": overall_pct,
                "chronic_absentees": chronic,
            }

    def get_student_history(self, student_id: str, days: int) -> dict:
        """Per-student attendance history for the last N days."""
        with SessionLocal() as session:
            end = date.today()
            start = end - timedelta(days=days - 1)

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

            records = (
                session.query(AttendanceRecord)
                .filter(
                    AttendanceRecord.student_id == student_id,
                    AttendanceRecord.tenant_id == self._tenant_id,
                    AttendanceRecord.attendance_date >= start,
                    AttendanceRecord.attendance_date <= end,
                )
                .order_by(AttendanceRecord.attendance_date)
                .all()
            )

            history = [
                {"date": str(r.attendance_date), "status": r.status, "source": r.source}
                for r in records
            ]
            total = len(records)
            present = sum(1 for r in records if r.status == "P")
            absent = sum(1 for r in records if r.status == "A")
            late = sum(1 for r in records if r.status == "L")

            return {
                "student_id": student.id,
                "full_name": student.full_name,
                "section": section_name,
                "total_days": total,
                "present": present,
                "absent": absent,
                "late": late,
                "attendance_pct": round((present + late) / total * 100, 1) if total else 0.0,
                "history": history,
            }
