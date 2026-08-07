"""
modules/ai_analytics/application/services/schema_gateway.py
============================================================
Sub-Module 8.1: ReadOnlySchemaGateway
Extracts clean, safe SQL schema documentation for queryable ERP tables.
Strictly excludes secrets/internal metadata.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


class ReadOnlySchemaGateway:
    """
    Sub-Module 8.1: Returns schema definition context for the LLM prompt.
    Limited to queryable domain tables.
    """

    ALLOWED_TABLES = (
        "students",
        "attendance_records",
        "fee_invoices",
        "class_sections",
        "fee_structures",
    )

    SCHEMA_PROMPT = """
TABLE SCHEMAS:

1. class_sections:
   - id: VARCHAR(36) PRIMARY KEY
   - tenant_id: VARCHAR(64)
   - grade_level: INTEGER (e.g. 10)
   - section_name: VARCHAR(10) (e.g. 'A', 'B')
   - display_name: VARCHAR(64) (e.g. 'Class 10-A', 'Class 10-B')
   - room_number: VARCHAR(20)

2. students:
   - id: VARCHAR(36) PRIMARY KEY
   - tenant_id: VARCHAR(64)
   - class_section_id: VARCHAR(36) FOREIGN KEY -> class_sections.id
   - roll_number: INTEGER
   - full_name: VARCHAR(128)
   - gender: VARCHAR(1) ('M', 'F', 'O')
   - dob: DATE
   - blood_group: VARCHAR(5)
   - phone: VARCHAR(20)
   - email: VARCHAR(128)
   - guardian_name: VARCHAR(128)
   - guardian_phone: VARCHAR(20)
   - guardian_relation: VARCHAR(32)
   - enrollment_status: VARCHAR(16) ('ACTIVE', 'TRANSFERRED', 'ARCHIVED')

3. attendance_records:
   - id: VARCHAR(36) PRIMARY KEY
   - tenant_id: VARCHAR(64)
   - student_id: VARCHAR(36) FOREIGN KEY -> students.id
   - class_section_id: VARCHAR(36) FOREIGN KEY -> class_sections.id
   - attendance_date: DATE (YYYY-MM-DD)
   - status: VARCHAR(1) ('P' = Present, 'A' = Absent, 'L' = Late)
   - source: VARCHAR(32)

4. fee_structures:
   - id: VARCHAR(36) PRIMARY KEY
   - tenant_id: VARCHAR(64)
   - grade_level: INTEGER
   - term_label: VARCHAR(64) (e.g. 'Term 1 2024-25')
   - academic_year: VARCHAR(16) ('2024-25')
   - fee_head_name: VARCHAR(64) ('Tuition Fee', 'Transport Fee')
   - amount: NUMERIC(10,2)

5. fee_invoices:
   - id: VARCHAR(36) PRIMARY KEY
   - tenant_id: VARCHAR(64)
   - student_id: VARCHAR(36) FOREIGN KEY -> students.id
   - fee_structure_id: VARCHAR(36) FOREIGN KEY -> fee_structures.id
   - fee_head_name: VARCHAR(64)
   - amount_due: NUMERIC(10,2)
   - amount_paid: NUMERIC(10,2)
   - due_date: DATE
   - paid_date: DATE (nullable)
   - status: VARCHAR(16) ('PAID', 'PENDING', 'OVERDUE', 'PARTIAL')
   - payment_method: VARCHAR(16) ('UPI', 'CARD', 'CASH', 'BANK_TRANSFER', 'CHEQUE')

RELATIONSHIPS:
- students.class_section_id = class_sections.id
- attendance_records.student_id = students.id
- attendance_records.class_section_id = class_sections.id
- fee_invoices.student_id = students.id
- fee_invoices.fee_structure_id = fee_structures.id
"""

    def get_schema_context(self) -> str:
        """Return table descriptions formatted for LLM system context."""
        return self.SCHEMA_PROMPT.strip()
