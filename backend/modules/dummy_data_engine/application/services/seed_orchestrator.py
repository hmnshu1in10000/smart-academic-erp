"""
modules/dummy_data_engine/application/services/seed_orchestrator.py
=====================================================================
Sub-Module 3.5 — Seed Orchestrator / CLI Backend.
Source of truth: ARCHITECTURE.md §3.5

Single entry-point that composes Sub-Modules 3.1 → 3.2 → 3.3 → 3.4
in correct dependency order to fully populate a demo tenant's database.

Rule: This module contains NO generation logic — it only sequences
calls to the other sub-modules and orchestrates DB persistence.

Output: SeedSummaryDTO with full counts and duration for verification.
"""
from __future__ import annotations

import logging
import time
from datetime import date, timedelta
from uuid import UUID, uuid4

from modules.dummy_data_engine.application.services.academic_structure_generator import (
    AcademicStructureGenerator,
)
from modules.dummy_data_engine.application.services.dummy_attendance_source import (
    DummyAttendanceIngestionSource,
)
from modules.dummy_data_engine.application.services.fee_history_generator import (
    FeeHistoryGenerator, TERM_DEFINITIONS,
)
from modules.dummy_data_engine.application.services.synthetic_identity_factory import (
    SyntheticIdentityFactory,
)
from modules.dummy_data_engine.domain.dtos import (
    ClassSectionDTO,
    GenerateAcademicStructureRequestDTO,
    GenerateFeeHistoryRequestDTO,
    SeedSummaryDTO,
    SeedTenantRequestDTO,
    SimulateAttendanceRequestDTO,
)
from modules.dummy_data_engine.infrastructure.db.repositories import (
    AttendanceRepository,
    ClassSectionRepository,
    FeeInvoiceRepository,
    FeeStructureRepository,
    StudentRepository,
    UserRepository,
    TimetableRepository,
)
from modules.dummy_data_engine.infrastructure.db.session import (
    create_all_tables,
    drop_all_tables,
    get_db_session,
)

logger = logging.getLogger(__name__)


class DemoTenantSeedOrchestrator:
    """
    Sub-Module 3.5: Sequences 3.1–3.4 to produce a fully populated demo tenant.

    Dependency order:
    1. Create teachers & staff users (UserRepository)
    2. Create class sections with class_teacher_id (ClassSectionRepository)
    3. Create timetable entries linked to teachers & sections (TimetableRepository)
    4. Generate student identities and insert per section (StudentRepository)
    5. Generate attendance signals and insert per section (AttendanceRepository)
    6. Generate fee structures and insert (FeeStructureRepository)
    7. Generate fee invoices per student and insert (FeeInvoiceRepository)
    """

    GRADE_LEVEL = 10
    SECTIONS = ["A", "B"]
    SUBJECTS = [
        "Mathematics", "Science", "English Language",
        "Social Science", "Hindi", "Computer Science", "Physical Education",
    ]

    def __init__(self) -> None:
        self._identity_factory: SyntheticIdentityFactory | None = None
        self._structure_generator: AcademicStructureGenerator | None = None
        self._attendance_source: DummyAttendanceIngestionSource | None = None
        self._fee_generator: FeeHistoryGenerator | None = None

    def run(self, request: SeedTenantRequestDTO) -> SeedSummaryDTO:
        """
        Execute the full seeding pipeline.
        Returns SeedSummaryDTO with counts for CLI verification output.
        """
        start_time = time.monotonic()
        logger.info(
            "=== Starting seed for tenant: %s (students=%d, days=%d, seed=%d) ===",
            request.tenant_id, request.student_count,
            request.historical_days, request.random_seed,
        )

        # ── Phase 0: Database preparation ──────────────────────────────────────
        if request.drop_existing:
            logger.warning("Dropping existing tables...")
            drop_all_tables()

        create_all_tables()

        # ── Initialize generators with shared seed ─────────────────────────────
        self._identity_factory = SyntheticIdentityFactory(seed=request.random_seed)
        self._structure_generator = AcademicStructureGenerator(seed=request.random_seed)
        self._attendance_source = DummyAttendanceIngestionSource(seed=request.random_seed)
        self._fee_generator = FeeHistoryGenerator(seed=request.random_seed)

        students_per_section = request.student_count // len(self.SECTIONS)
        remainder = request.student_count % len(self.SECTIONS)

        sections_created = 0
        students_created = 0
        attendance_records_created = 0
        fee_invoices_created = 0
        all_student_ids: list[UUID] = []

        # ── Phase 1: Generate specialized teachers and staff ───────────────────
        logger.info("Phase 1/4: Generating staff, sections, and timetable...")

        teacher_profiles = [
            {
                "id": "teacher_rajesh_kumar",
                "tenant_id": request.tenant_id,
                "email": "teacher01@demo.school",
                "full_name": "Mr. Rajesh Kumar",
                "role_key": "TEACHER",
                "phone": "+91-98765-43212",
                "assigned_sections": "10-A",
                "subject": "Mathematics",
            },
            {
                "id": "teacher_priya_singh",
                "tenant_id": request.tenant_id,
                "email": "teacher02@demo.school",
                "full_name": "Ms. Priya Singh",
                "role_key": "TEACHER",
                "phone": "+91-98765-43213",
                "assigned_sections": "10-B",
                "subject": "Science",
            },
            {
                "id": "teacher_amit_verma",
                "tenant_id": request.tenant_id,
                "email": "amit.verma@greenwoodhigh.edu.in",
                "full_name": "Mr. Amit Verma",
                "role_key": "TEACHER",
                "phone": "+91-98765-43214",
                "assigned_sections": None,
                "subject": "English Language",
            },
            {
                "id": "teacher_sunita_sharma",
                "tenant_id": request.tenant_id,
                "email": "sunita.sharma@greenwoodhigh.edu.in",
                "full_name": "Ms. Sunita Sharma",
                "role_key": "TEACHER",
                "phone": "+91-98765-43215",
                "assigned_sections": None,
                "subject": "Social Science",
            },
            {
                "id": "teacher_vikram_malhotra",
                "tenant_id": request.tenant_id,
                "email": "vikram.malhotra@greenwoodhigh.edu.in",
                "full_name": "Mr. Vikram Malhotra",
                "role_key": "TEACHER",
                "phone": "+91-98765-43216",
                "assigned_sections": None,
                "subject": "Computer Science",
            },
            {
                "id": "teacher_kavita_joshi",
                "tenant_id": request.tenant_id,
                "email": "kavita.joshi@greenwoodhigh.edu.in",
                "full_name": "Ms. Kavita Joshi",
                "role_key": "TEACHER",
                "phone": "+91-98765-43217",
                "assigned_sections": None,
                "subject": "Hindi",
            },
            {
                "id": "admin_erp_user",
                "tenant_id": request.tenant_id,
                "email": "admin@demo.school",
                "full_name": "ERP Admin",
                "role_key": "ADMIN",
                "phone": "+91-98765-43210",
                "assigned_sections": None,
                "subject": None,
            },
            {
                "id": "principal_anita_sharma",
                "tenant_id": request.tenant_id,
                "email": "principal@demo.school",
                "full_name": "Dr. Anita Sharma",
                "role_key": "PRINCIPAL",
                "phone": "+91-98765-43211",
                "assigned_sections": None,
                "subject": None,
            },
        ]

        # Insert users
        with get_db_session() as session:
            user_repo = UserRepository(session)
            user_repo.bulk_insert(teacher_profiles)

        # Build class sections with exact class teachers
        sec_a_id = uuid4()
        sec_b_id = uuid4()
        class_sections = [
            ClassSectionDTO(
                section_id=sec_a_id,
                tenant_id=request.tenant_id,
                grade_level=10,
                section_name="A",
                display_name="Class 10-A",
                class_teacher_id=UUID(int=1),  # temporary marker, mapped below
                room_number="Room 101",
                max_strength=30,
            ),
            ClassSectionDTO(
                section_id=sec_b_id,
                tenant_id=request.tenant_id,
                grade_level=10,
                section_name="B",
                display_name="Class 10-B",
                class_teacher_id=UUID(int=2),
                room_number="Room 102",
                max_strength=30,
            ),
        ]

        with get_db_session() as session:
            sec_repo = ClassSectionRepository(session)
            # Custom section insert to set class_teacher_id directly
            from modules.dummy_data_engine.infrastructure.db.models import ClassSection
            s1 = ClassSection(
                id=str(sec_a_id),
                tenant_id=request.tenant_id,
                grade_level=10,
                section_name="A",
                display_name="Class 10-A",
                class_teacher_id="teacher_rajesh_kumar",
                room_number="Room 101",
                max_strength=30,
            )
            s2 = ClassSection(
                id=str(sec_b_id),
                tenant_id=request.tenant_id,
                grade_level=10,
                section_name="B",
                display_name="Class 10-B",
                class_teacher_id="teacher_priya_singh",
                room_number="Room 102",
                max_strength=30,
            )
            session.add_all([s1, s2])
            session.commit()
            sections_created = 2

        # Generate realistic timetable entries linked to teachers & subjects
        subjects = [
            ("Mathematics", "MATH10", "teacher_rajesh_kumar"),
            ("Science", "SCI10", "teacher_priya_singh"),
            ("English Language", "ENG10", "teacher_amit_verma"),
            ("Social Science", "SST10", "teacher_sunita_sharma"),
            ("Computer Science", "CS10", "teacher_vikram_malhotra"),
            ("Hindi", "HIN10", "teacher_kavita_joshi"),
            ("Physical Education", "PE10", "teacher_rajesh_kumar"),
        ]

        days = ["MON", "TUE", "WED", "THU", "FRI", "SAT"]
        times = [
            (1, "08:00", "08:45"),
            (2, "08:45", "09:30"),
            (3, "09:30", "10:15"),
            (4, "10:30", "11:15"),
            (5, "11:15", "12:00"),
            (6, "12:00", "12:45"),
            (7, "13:30", "14:15"),
            (8, "14:15", "15:00"),
        ]

        timetable_records = []
        for sec in [("Class 10-A", str(sec_a_id), "Room 101"), ("Class 10-B", str(sec_b_id), "Room 102")]:
            sec_name, sec_id_str, room_no = sec
            for day in days:
                for period_num, st, et in times:
                    # Pick subject cyclically
                    subj_tuple = subjects[(period_num - 1 + days.index(day)) % len(subjects)]
                    subj_name, subj_code, t_id = subj_tuple
                    timetable_records.append({
                        "id": str(uuid4()),
                        "tenant_id": request.tenant_id,
                        "class_section_id": sec_id_str,
                        "teacher_id": t_id,
                        "subject_name": subj_name,
                        "subject_code": subj_code,
                        "day_of_week": day,
                        "period_number": period_num,
                        "start_time": st,
                        "end_time": et,
                        "room_number": room_no,
                    })

        with get_db_session() as session:
            tt_repo = TimetableRepository(session)
            tt_repo.bulk_insert(timetable_records)

        logger.info(
            "  [OK] %d sections, %d teachers, %d timetable entries",
            sections_created, len(teacher_profiles), len(timetable_records),
        )

        # ── Phase 2: Generate and insert students per section ──────────────────
        logger.info("Phase 2/4: Generating %d students...", request.student_count)

        for sec_idx, section in enumerate(class_sections):
            count = students_per_section + (1 if sec_idx < remainder else 0)
            identities = self._identity_factory.generate_student_identities(
                count=count, grade_level=self.GRADE_LEVEL
            )
            with get_db_session() as session:
                student_repo = StudentRepository(session)
                inserted_ids = student_repo.bulk_insert(
                    identities=identities,
                    section_id=str(section.section_id),
                    tenant_id=request.tenant_id,
                    roll_number_offset=1,
                )
            students_created += len(inserted_ids)
            # Store UUIDs for attendance + fee generation
            all_student_ids.extend([id_.identity_id for id_ in identities])

        logger.info("  [OK] %d students created across %d sections",
                    students_created, len(class_sections))

        # ── Phase 3: Generate attendance records ───────────────────────────────
        logger.info(
            "Phase 3/4: Generating %d days of attendance...", request.historical_days
        )

        end_date = date.today()
        start_date = end_date - timedelta(days=request.historical_days + 10)

        for section in class_sections:
            # Get student IDs for this section from all_student_ids
            section_idx = class_sections.index(section)
            sec_size = students_per_section + (1 if section_idx < remainder else 0)
            start_idx = sum(
                students_per_section + (1 if i < remainder else 0)
                for i in range(section_idx)
            )
            section_student_ids = all_student_ids[start_idx : start_idx + sec_size]

            signals = self._attendance_source.generate_multi_day_signals(
                student_ids=section_student_ids,
                class_section_id=section.section_id,
                tenant_id=request.tenant_id,
                start_date=start_date,
                num_days=request.historical_days,
                attendance_rate=0.93,
                skip_weekends=True,
            )

            with get_db_session() as session:
                att_repo = AttendanceRepository(session)
                attendance_records_created += att_repo.bulk_insert(
                    signals=signals,
                    tenant_id=request.tenant_id,
                )

        logger.info("  [OK] %d attendance records created", attendance_records_created)

        # ── Phase 4: Generate fee structures and invoices ──────────────────────
        logger.info("Phase 4/4: Generating fee structures and invoices...")

        fee_structures = self._fee_generator.generate_fee_structures(
            tenant_id=request.tenant_id
        )

        fee_structures_created = 0
        fee_structure_id_map: dict[tuple[str, str], str] = {}
        with get_db_session() as session:
            fee_struct_repo = FeeStructureRepository(session)
            count, id_map = fee_struct_repo.bulk_insert(
                structures=fee_structures,
                tenant_id=request.tenant_id,
            )
            fee_structures_created = count
            fee_structure_id_map = id_map

        # Generate invoices for ALL students across BOTH terms
        all_student_uuids = tuple(all_student_ids)
        for structure in fee_structures:
            fee_request = GenerateFeeHistoryRequestDTO(
                tenant_id=request.tenant_id,
                student_ids=all_student_uuids,
                fee_structure=structure,
                on_time_payment_rate=0.80,
            )
            transactions = self._fee_generator.generate_invoices(fee_request)

            with get_db_session() as session:
                invoice_repo = FeeInvoiceRepository(session)
                fee_invoices_created += invoice_repo.bulk_insert(
                    transactions=transactions,
                    tenant_id=request.tenant_id,
                    fee_structure_id_map=fee_structure_id_map,
                )

        logger.info("  [OK] %d fee invoices created", fee_invoices_created)

        # ── Finalize ───────────────────────────────────────────────────────────
        duration = time.monotonic() - start_time

        # Write SEED_CREDENTIALS.md
        creds_path = self._write_seed_credentials(request.tenant_id)

        summary = SeedSummaryDTO(
            tenant_id=request.tenant_id,
            students_created=students_created,
            staff_created=len(teacher_profiles),
            classes_created=sections_created,
            subjects_created=len(subjects),
            timetable_entries_created=len(timetable_records),
            attendance_records_created=attendance_records_created,
            fee_structures_created=fee_structures_created,
            fee_invoices_created=fee_invoices_created,
            duration_seconds=round(duration, 2),
            seed_credentials_path=creds_path,
        )

        logger.info(
            "=== Seed completed in %.2fs | "
            "Students: %d | Attendance: %d | Invoices: %d ===",
            duration, students_created, attendance_records_created, fee_invoices_created,
        )
        return summary

    def _write_seed_credentials(self, tenant_id: str) -> str:
        """
        Write SEED_CREDENTIALS.md — demo login info for QA.
        Rule (ARCHITECTURE §2.1): never commit with real-looking credentials.
        """
        import os
        backend_dir = os.path.dirname(
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.abspath(__file__))
            )))
        )
        creds_path = os.path.join(backend_dir, "SEED_CREDENTIALS.md")

        content = f"""# SEED CREDENTIALS — DEMO ONLY
**Tenant:** `{tenant_id}`
**Generated:** {date.today().isoformat()}

> ⚠️ These are synthetic demo credentials. Never use in production.

| Role          | Email                              | Password     |
|---------------|------------------------------------|--------------|
| Admin         | admin@demo.school                  | Demo@1234!   |
| Principal     | principal@demo.school              | Demo@1234!   |
| Teacher (1)   | teacher01@demo.school              | Demo@1234!   |
| Teacher (2)   | teacher02@demo.school              | Demo@1234!   |
| Parent        | parent-of-student-01@demo.school   | Demo@1234!   |

> Dummy OTP code for MFA: `000000`
"""
        with open(creds_path, "w", encoding="utf-8") as f:
            f.write(content)

        logger.info("Seed credentials written to: %s", creds_path)
        return creds_path
