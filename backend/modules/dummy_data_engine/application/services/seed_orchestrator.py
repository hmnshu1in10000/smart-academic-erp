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
from uuid import UUID

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

    Dependency order (mandatory — violating this causes FK constraint failures):
    1. Create class sections (ClassSectionRepository)
    2. Generate student identities and insert per section (StudentRepository)
    3. Generate attendance signals and insert per section (AttendanceRepository)
    4. Generate fee structures and insert (FeeStructureRepository)
    5. Generate fee invoices per student and insert (FeeInvoiceRepository)
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

        # ── Phase 1: Generate academic structure ───────────────────────────────
        logger.info("Phase 1/4: Generating academic structure...")
        structure_request = GenerateAcademicStructureRequestDTO(
            tenant_id=request.tenant_id,
            grade_levels=[self.GRADE_LEVEL],
            sections_per_grade=len(self.SECTIONS),
            subjects=self.SUBJECTS,
        )

        # Generate staff for class-teacher assignment
        staff_identities = self._identity_factory.generate_staff_identities(
            count=max(8, len(self.SUBJECTS)),
            department="Teaching"
        )

        class_sections = self._structure_generator.generate_class_sections(
            request=structure_request,
            staff_identities=staff_identities,
        )
        subjects = self._structure_generator.generate_subjects(
            grade_level=self.GRADE_LEVEL
        )
        timetable_entries = self._structure_generator.generate_timetable(
            class_sections=class_sections,
            subjects=subjects,
            staff_identities=staff_identities,
        )
        # Resolve conflicts (safety net)
        timetable_entries = self._structure_generator._resolve_scheduling_conflicts(
            timetable_entries
        )

        # ── Phase 1 DB: Insert sections ────────────────────────────────────────
        with get_db_session() as session:
            section_repo = ClassSectionRepository(session)
            sections_created = section_repo.bulk_insert(class_sections)

        logger.info(
            "  ✓ %d sections, %d subjects, %d timetable entries",
            sections_created, len(subjects), len(timetable_entries),
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

        logger.info("  ✓ %d students created across %d sections",
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

        logger.info("  ✓ %d attendance records created", attendance_records_created)

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

        logger.info("  ✓ %d fee invoices created", fee_invoices_created)

        # ── Finalize ───────────────────────────────────────────────────────────
        duration = time.monotonic() - start_time

        # Write SEED_CREDENTIALS.md
        creds_path = self._write_seed_credentials(request.tenant_id)

        summary = SeedSummaryDTO(
            tenant_id=request.tenant_id,
            students_created=students_created,
            staff_created=len(staff_identities),
            classes_created=sections_created,
            subjects_created=len(subjects),
            timetable_entries_created=len(timetable_entries),
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
