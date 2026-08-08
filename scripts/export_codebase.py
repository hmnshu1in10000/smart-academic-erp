#!/usr/bin/env python3
"""
scripts/export_codebase.py
==========================
Compiles the entire codebase into a single comprehensive context document: codebase.txt
for LLM analysis, architectural audits, and complete offline onboarding.

Sections:
1. PROJECT VISION & EXECUTIVE SUMMARY
2. COMPLETE FILE & DIRECTORY TREE
3. SYSTEM ARCHITECTURE & MODULE MAP
4. FULL SOURCE CODE DUMP
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Root directory of the repository
ROOT_DIR = Path(__file__).resolve().parent.parent
OUTPUT_FILE = ROOT_DIR / "codebase.txt"

# Directories to strictly exclude
EXCLUDED_DIRS = {
    ".git",
    ".logs",
    ".expo",
    ".pytest_cache",
    ".idea",
    ".vscode",
    ".next",
    ".cache",
    "venv",
    ".venv",
    "node_modules",
    "dist",
    "build",
    "__pycache__",
}

# File extensions to strictly exclude (binaries, lockfiles, images, databases)
EXCLUDED_EXTENSIONS = {
    ".sqlite3",
    ".db",
    ".sqlite",
    ".pyc",
    ".pyo",
    ".pyd",
    ".png",
    ".jpg",
    ".jpeg",
    ".ico",
    ".gif",
    ".svg",
    ".webp",
    ".bmp",
    ".tiff",
    ".woff",
    ".woff2",
    ".ttf",
    ".eot",
    ".otf",
    ".map",
    ".log",
}

# Specific filenames to exclude
EXCLUDED_FILENAMES = {
    ".env",
    "codebase.txt",
    "package-lock.json",
    "pnpm-lock.yaml",
    "yarn.lock",
    ".DS_Store",
    "Thumbs.db",
}


def is_excluded(path: Path) -> bool:
    """Check if a file or directory path should be skipped."""
    for part in path.parts:
        if part in EXCLUDED_DIRS:
            return True

    if path.is_file():
        if path.name in EXCLUDED_FILENAMES:
            return True
        if path.suffix.lower() in EXCLUDED_EXTENSIONS:
            return True

    return False


def build_ascii_tree(dir_path: Path, prefix: str = "") -> list[str]:
    """Generates a clean ASCII tree of the project structure."""
    lines: list[str] = []
    
    try:
        entries = sorted(
            [e for e in dir_path.iterdir() if not is_excluded(e)],
            key=lambda x: (not x.is_dir(), x.name.lower())
        )
    except PermissionError:
        return lines

    for i, entry in enumerate(entries):
        is_last = (i == len(entries) - 1)
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{entry.name}{'/' if entry.is_dir() else ''}")

        if entry.is_dir():
            extension = "    " if is_last else "│   "
            lines.extend(build_ascii_tree(entry, prefix + extension))

    return lines


def collect_source_files(root: Path) -> list[Path]:
    """Collect all relevant source code and documentation files in sorted order."""
    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        # Modify dirnames in-place to avoid descending into excluded dirs
        dirnames[:] = [d for d in dirnames if d not in EXCLUDED_DIRS]
        for f in filenames:
            p = Path(dirpath) / f
            if not is_excluded(p):
                files.append(p)

    return sorted(files, key=lambda x: str(x.relative_to(root)).replace("\\", "/"))


def generate_codebase_txt():
    print(f"[*] Scanning repository from: {ROOT_DIR}")
    source_files = collect_source_files(ROOT_DIR)
    print(f"[*] Collected {len(source_files)} source files for export.")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as out:
        # =====================================================================
        # SECTION 1: PROJECT VISION & EXECUTIVE SUMMARY
        # =====================================================================
        out.write("=" * 80 + "\n")
        out.write("SECTION 1: PROJECT VISION & EXECUTIVE SUMMARY\n")
        out.write("=" * 80 + "\n\n")

        out.write("# AI-Powered Smart Academic ERP with Conversational Analytics & Hybrid OCR Attendance\n\n")
        out.write("## 1. Executive Summary & Problem Statement\n")
        out.write(
            "In thousands of primary and secondary schools across India and emerging educational markets, "
            "attendance tracking and fee collection remain deeply tethered to physical paper registers. "
            "Teachers spend 15–25 minutes per period manually calling roll numbers and marking physical sheets, "
            "leading to lost instructional time, clerical transcription errors, delayed parent notifications, "
            "and administrative blindspots. Furthermore, school leaders lack real-time visibility into daily "
            "operational metrics, requiring complex manual SQL queries or cumbersome legacy desktop software.\n\n"
        )

        out.write("## 2. Core Solution: Hybrid Physical-to-Digital ERP\n")
        out.write(
            "The Smart Academic ERP provides a seamless, hybrid operational workflow that bridges physical classroom "
            "registers with automated digital records. Teachers can record attendance via interactive multi-state tap grids "
            "(Present, Absent, Late) on mobile or web, or upload photos of handwritten paper attendance sheets for OCR batch extraction. "
            "All student attendance, fee invoicing, and demographic records are synchronized in real-time to a central "
            "multi-tenant cloud backend, enabling automated parent SMS/push triggers and immediate executive analytics.\n\n"
        )

        out.write("## 3. Key Architectural & Product Innovations\n")
        out.write(
            "1. Clean Architecture FastAPI Backend:\n"
            "   - Strictly modularized domain-driven architecture (Auth, Students/Timetable, Attendance, Fee Invoices, AI Analytics).\n"
            "   - Dependency injection, repository abstraction, and decoupled domain transfer objects (DTOs).\n\n"
            "2. Multi-Tenant Data Isolation & Hardened RBAC (tenant_id RLS + JWT Scoping):\n"
            "   - Every request is cryptographically bound to a tenant ID and assigned section(s) claim in verified JWT tokens.\n"
            "   - Role-scoped facades guarantee teachers only see assigned sections, and parents/students only see their own records.\n\n"
            "3. Conversational Text-to-SQL RAG Engine (Module 8.0):\n"
            "   - Universal System Prompt Architecture with JSON output contract (sql + single/multi/zero phrasing templates).\n"
            "   - AST-Guarded SQL Executor: Validates SELECT-only, table whitelist, row cap, and enforces AST-level identity predicates.\n"
            "   - Non-admin queries fail closed if guardian/student identity predicates are absent.\n"
            "   - Local Template Interpolation: Data binding happens locally in Python via str.format(); LLM never sees raw result rows.\n"
            "   - Multi-Turn Conversation History: Resolves pronouns and contextual follow-ups across consecutive chat turns.\n"
            "   - Local PII Sanitizer: Redacts phone numbers and email addresses pre-inference before external LLM dispatch.\n\n"
            "4. White-Label Dynamic Theme Engine:\n"
            "   - Schools customize brand colors, logos, school crests, and portal names via real-time CSS variable injection.\n\n"
            "5. Multi-Role React 19 Web Dashboard:\n"
            "   - Unified role-based router (Admin, Principal, Teacher, Student, Parent) using single source-of-truth roleNavigation.ts.\n"
            "   - Dedicated screens: OverviewDashboard, StudentRoster, AttendanceAnalytics, FeeDashboard, ChatQueryBox (with collapsible debug SQL panel),\n"
            "     TeacherScheduleScreen, TeacherAttendanceScreen (with manual override dialog), AcademicGradesScreen (report card), PersonalAttendanceScreen, PersonalFeeScreen (Razorpay test sandbox).\n\n"
            "6. React Native (Expo) Teacher Mobile App with Offline-First Queueing:\n"
            "   - Low-latency attendance submission supporting offline AsyncStorage queueing with automatic background sync.\n"
            "   - Hybrid OCR register camera capture for instant batch digitisation.\n\n"
            "7. Free FCM / WebPush Notifications:\n"
            "   - Automated event-driven push dispatch notifying parents immediately when a child is marked absent or late.\n\n"
        )

        # =====================================================================
        # SECTION 2: COMPLETE FILE & DIRECTORY TREE
        # =====================================================================
        out.write("\n" + "=" * 80 + "\n")
        out.write("SECTION 2: COMPLETE FILE & DIRECTORY TREE\n")
        out.write("=" * 80 + "\n\n")

        out.write(f"smart-academic-erp/\n")
        tree_lines = build_ascii_tree(ROOT_DIR)
        out.write("\n".join(tree_lines) + "\n\n")

        # =====================================================================
        # SECTION 3: SYSTEM ARCHITECTURE & MODULE MAP
        # =====================================================================
        out.write("=" * 80 + "\n")
        out.write("SECTION 3: SYSTEM ARCHITECTURE & MODULE MAP\n")
        out.write("=" * 80 + "\n\n")

        out.write("### Backend Module Map & Endpoints (`backend/`)\n")
        out.write("  ├── Core Config (`backend/core/` & `backend/config/`)\n")
        out.write("  │     ├── config.py                - Environment variables, JWT secrets, DB connection strings\n")
        out.write("  │     └── database.py              - SQLAlchemy engine & async session factories\n")
        out.write("  ├── Shared Kernel (`backend/shared_kernel/`)\n")
        out.write("  │     ├── auth/jwt_utils.py        - JWT token encode/decode, assigned_sections claim, tenant context\n")
        out.write("  │     ├── security/pii_sanitizer.py - Zero-dependency regex phone & email redaction\n")
        out.write("  │     ├── contracts/base_dto.py    - Frozen base DTO structures\n")
        out.write("  │     └── events/event_bus.py      - In-process decoupled domain event publishing\n")
        out.write("  ├── Module 1: Auth & RBAC (`backend/modules/auth/`)\n")
        out.write("  │     ├── POST /api/v1/auth/login  - Multi-tenant credential verification & JWT generation (with assigned_sections)\n")
        out.write("  │     └── GET  /api/v1/auth/me     - Current user profile and permissions from token\n")
        out.write("  ├── Module 2: Students & Classes (`backend/modules/students/`)\n")
        out.write("  │     ├── GET  /api/v1/students    - Role-scoped student roster (teacher sees assigned sections, admin sees all)\n")
        out.write("  │     ├── GET  /api/v1/students/{id} - Role-scoped student detail\n")
        out.write("  │     └── GET  /api/v1/students/{id}/timetable - Weekly student timetable\n")
        out.write("  ├── Module 3: Attendance (`backend/modules/attendance/`)\n")
        out.write("  │     ├── GET  /api/v1/attendance/summary - Daily attendance stats (role-scoped by assigned_sections for teachers)\n")
        out.write("  │     ├── GET  /api/v1/attendance/student/{id} - Student 30-day attendance history\n")
        out.write("  │     ├── GET  /api/v1/attendance/me     - Identity-resolved attendance history for student\n")
        out.write("  │     ├── GET  /api/v1/attendance/my-child - Identity-resolved attendance history for parent\n")
        out.write("  │     └── POST /api/v1/attendance/submit  - Ingest mobile/web attendance signals\n")
        out.write("  ├── Module 4: Fee Invoices (`backend/modules/fees/`)\n")
        out.write("  │     ├── GET  /api/v1/fees/invoices    - Paginated invoice ledger (role-scoped)\n")
        out.write("  │     ├── GET  /api/v1/fees/summary     - Collection KPIs & status breakdown\n")
        out.write("  │     ├── GET  /api/v1/fees/me          - Identity-resolved fee ledger for student\n")
        out.write("  │     ├── GET  /api/v1/fees/my-child    - Identity-resolved fee ledger for parent\n")
        out.write("  │     └── POST /api/v1/fees/pay-invoice - Free Razorpay test sandbox payment trigger\n")
        out.write("  ├── Module 5: Parent & Student Dedicated Portals (`backend/modules/parent/` & `backend/modules/student/`)\n")
        out.write("  │     ├── GET  /api/v1/parent/child-summary    - Identity-scoped child attendance & fee rollup\n")
        out.write("  │     ├── GET  /api/v1/parent/academic-summary - Identity-scoped child report card & grades\n")
        out.write("  │     └── GET  /api/v1/student/academic-summary - Identity-scoped student report card & grades\n")
        out.write("  ├── Module 8: AI Text-to-SQL Analytics (`backend/modules/ai_analytics/`)\n")
        out.write("  │     ├── POST /api/v1/ai-analytics/ask - Multi-turn conversational SQL translation with JWT tenant lock\n")
        out.write("  │     ├── application/services/text_to_sql.py - Universal prompt with JSON contract & fallback\n")
        out.write("  │     ├── application/services/guarded_executor.py - Hardened AST validation & row-level identity enforcement\n")
        out.write("  │     ├── application/services/analytics_facade.py - Local template interpolation without LLM data leakage\n")
        out.write("  │     └── application/services/schema_gateway.py - Domain schema metadata provider\n\n")

        out.write("### Web Dashboard Feature Slices (`web-dashboard/src/`)\n")
        out.write("  ├── config/roleNavigation.ts - Single source-of-truth role-to-navigation mapping\n")
        out.write("  ├── context/AuthContext.tsx  - JWT authentication state with assigned_sections\n")
        out.write("  ├── features/auth/           - Multi-tenant login screen\n")
        out.write("  ├── features/dashboard/      - Admin/Principal OverviewDashboard (KPIs, enrollment, attendance rate)\n")
        out.write("  ├── features/student-academic/ - StudentRoster table and directory\n")
        out.write("  ├── features/attendance/     - AttendanceAnalytics (admin) & PersonalAttendanceScreen (student/parent)\n")
        out.write("  ├── features/fee-management/ - FeeDashboard (admin) & PersonalFeeScreen (student/parent + Razorpay modal)\n")
        out.write("  ├── features/teacher/        - TeacherScheduleScreen (timetable) & TeacherAttendanceScreen (tap grid + override)\n")
        out.write("  ├── features/academic/       - AcademicGradesScreen (student/parent report card & subject grade breakdown)\n")
        out.write("  └── features/ai-analytics/   - ChatQueryBox (multi-turn SQL assistant with collapsible debug execution panel)\n\n")

        out.write("### Mobile App Feature Screens (`mobile-app/src/features/`)\n")
        out.write("  ├── auth/            - Teacher mobile authentication and tenant selection\n")
        out.write("  ├── attendance/      - Low-latency quick-tap attendance matrix (P / A / L)\n")
        out.write("  ├── ocr-camera/      - Paper register photo capture and bounding box preview\n")
        out.write("  └── offline-queue/   - AsyncStorage sync queue with connection listener\n\n")

        out.write("### Shared Kernel Contracts & Data Flow\n")
        out.write("  - DTO Contracts: NLQueryRequestDTO, ChatTurnDTO, GeneratedSQLDTO, QueryExecutionResultDTO, ConversationalAnswerDTO\n")
        out.write("  - Security: JWT TokenPayload (sub, tenant_id, role, assigned_sections) -> RLS Facades -> AST Guarded Executor\n")
        out.write("  - Event Bus: StudentAbsentEvent -> FCMNotificationHandler -> Push Notification Trigger\n\n")

        # =====================================================================
        # SECTION 4: FULL SOURCE CODE DUMP
        # =====================================================================
        out.write("=" * 80 + "\n")
        out.write("SECTION 4: FULL SOURCE CODE DUMP\n")
        out.write("=" * 80 + "\n\n")

        for file_path in source_files:
            rel_path = file_path.relative_to(ROOT_DIR).as_posix()
            out.write("=" * 70 + "\n")
            out.write(f"FILE PATH: {rel_path}\n")
            out.write("=" * 70 + "\n")

            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    content = f.read()
                out.write(content)
            except Exception as e:
                out.write(f"[ERROR READING FILE: {e}]\n")

            out.write("\n\n")

    file_size_bytes = os.path.getsize(OUTPUT_FILE)
    with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
        line_count = sum(1 for _ in f)

    file_size_kb = file_size_bytes / 1024.0
    file_size_mb = file_size_kb / 1024.0

    print("=" * 80)
    print(f"SUCCESS: codebase.txt successfully generated at {OUTPUT_FILE}")
    print(f"Total Lines: {line_count:,}")
    print(f"Total Size : {file_size_bytes:,} bytes ({file_size_kb:.2f} KB / {file_size_mb:.2f} MB)")
    print("=" * 80)


if __name__ == "__main__":
    generate_codebase_txt()
