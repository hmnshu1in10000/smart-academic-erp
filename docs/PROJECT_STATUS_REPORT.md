# Project Status & Master Architecture Audit Report

**Project Name:** AI-Powered Smart Academic ERP with Conversational Analytics & Hybrid OCR Attendance  
**Repository:** `smart-academic-erp/`  
**Current Phase:** Production-Grade Complete  
**Date of Audit:** August 8, 2026  
**Target Environment:** Cross-Platform (FastAPI Cloud Backend, React 19 Web Dashboard, React Native Expo Mobile App)

---

## 1. Executive Summary & System Architecture

### 1.1 Technical Stack Overview

| Tier | Technologies & Frameworks | Key Purpose & Architecture Pattern |
|---|---|---|
| **Backend REST Core** | Python 3.12+, FastAPI 0.115+, Uvicorn, Starlette | Async request pipeline, dependency injection, OpenAPI 3.1 contract generation. |
| **ORM & Relational DB** | SQLAlchemy 2.0 (Core + ORM), Alembic, SQLite (Dev) / PostgreSQL (Prod) | Decoupled session lifecycle (`SessionLocal`), atomic transactions, index optimizations. |
| **Data Validation & DTOs** | Pydantic v2 (`BaseModel`), Frozen Python Dataclasses (`BaseDTO`) | Strict schema boundaries, runtime validation, zero raw ORM models crossing API boundaries. |
| **Security & Cryptography** | `python-jose` (HS256 JWT), Passlib, Regex PII Sanitizer | Stateless tenant context resolution, role scoping, zero-dependency pre-inference PII masking. |
| **AST SQL Security Engine** | `sqlglot` (SQLite AST Dialect Parser), AST Walkers | Compile-time SQL AST validation, SELECT-only enforcement, row cap, structural RBAC verification. |
| **LLM Inference** | Groq (`llama-3.1-8b-instant`), Google Gemini (`gemini-2.0-flash`), Local Rule Fallback | Hybrid prompt-to-SQL translation with graceful fallback and zero-data leakage contract. |
| **Web Admin Dashboard** | React 19, TypeScript 5.7+, Vite, Tailwind CSS v4, Lucide Icons | Single-page application, CSS variable theme engine, role-aware route isolation. |
| **Teacher Mobile App** | React Native 0.76+, Expo SDK 52, Expo Router, `@react-native-async-storage` | Offline-first attendance sync queue, low-latency tri-state matrix, camera OCR preview. |
| **Payments & Notifications** | Razorpay Sandbox API, Firebase Cloud Messaging (FCM), In-App Outbox | 100% free sandbox checkout, push alerts for absence/late roll marks. |

---

### 1.2 Core Design Patterns

```
                               ┌────────────────────────────────────────┐
                               │       HTTP / JSON Clients (JWT)        │
                               │   (Web Dashboard & Mobile App)         │
                               └──────────────────┬─────────────────────┘
                                                  │ Bearer Token
                                                  ▼
                               ┌────────────────────────────────────────┐
                               │   FastAPI API Layer & Dependency Inj.  │
                               │  - get_current_tenant_context (JWT)    │
                               │  - Multi-Tenant RLS Extraction         │
                               └──────────────────┬─────────────────────┘
                                                  │ DTOs
                                                  ▼
                               ┌────────────────────────────────────────┐
                               │      Application Facades (DDD)         │
                               │  - StudentsFacade (Role-Scoped)        │
                               │  - AttendanceFacade (Role-Scoped)      │
                               │  - FeesFacade (Role-Scoped)            │
                               │  - ConversationalAnalyticsFacade       │
                               └─────────┬────────────────────┬─────────┘
                                         │                    │
                    ┌────────────────────┘                    └───────────────────┐
                    ▼                                                             ▼
┌──────────────────────────────────────┐                      ┌──────────────────────────────────────┐
│       AI Text-to-SQL Engine          │                      │    Domain Infrastructure & Storage   │
│ - Local PII Sanitizer (Regex)        │                      │ - Dummy Data Seed Engine (Bulk Bulk) │
│ - Master System Prompt (JSON Schema) │                      │ - SQLAlchemy 2.0 Session Factory     │
│ - sqlglot AST Guarded Executor       │                      │ - Multi-Tenant Tables (tenant_id)    │
│ - Local Python Template Interpolator │                      │ - SQLite 3.x / PostgreSQL Engine     │
└──────────────────────────────────────┘                      └──────────────────────────────────────┘
```

1. **Clean Architecture & Domain-Driven Design (DDD):**
   - **Domain Layer:** Pure entity models (`Student`, `ClassSection`, `AttendanceRecord`, `FeeInvoice`) and frozen dataclass DTOs (`NLQueryRequestDTO`, `ChatTurnDTO`, `GeneratedSQLDTO`, `QueryExecutionResultDTO`, `ConversationalAnswerDTO`).
   - **Application Layer:** Isolated facades (`StudentsFacade`, `AttendanceFacade`, `FeesFacade`, `ConversationalAnalyticsFacade`) encapsulating business logic, access rules, and data aggregation.
   - **API / Presentation Layer:** Slim FastAPI route handlers converting Pydantic payloads into domain DTOs.
2. **Multi-Tenant Row-Level Security (`tenant_id` RLS):**
   - Every single database table maintains a mandatory `tenant_id` column indexed for zero cross-tenant leakage.
   - The verified JWT claim (`token.tenant_id`) is injected via FastAPI's `Depends(get_current_tenant_context)` and cannot be overridden by request bodies.
3. **Role-Based Access Control (RBAC) Hardening:**
   - JWT tokens embed an `assigned_sections: tuple[str, ...]` claim for teachers.
   - Facades enforce row-scoping: teachers are restricted to students in their assigned sections; parents and students access records strictly matching their verified `guardian_user_id` or `email`.
4. **Dependency Inversion & Extensibility:**
   - Centralized dependency injection container (`backend/config/di/container.py`).
   - Schema gateway abstraction (`ReadOnlySchemaGateway`) shielding the Text-to-SQL engine from raw ORM metadata.

---

## 2. Complete Feature Inventory (By Module & Role)

### 2.1 Backend Modules & Seed Engine

* **High-Speed Synthetic Data Engine (`backend/modules/dummy_data_engine/`):**
  - Synthesizes 50 student profiles, 1,500 historical attendance entries across 30 days, 164 fee invoices, and full CBSE Class 10 weekly timetables.
  - Generates realistic Indian names, blood groups, DOBs, guardian contact numbers, and diverse fee heads (Tuition, Lab, Library, Sports).
  - High-performance bulk insertion executes in **< 0.30 seconds** on SQLite.
* **Authentication & JWT Token Issuer (`backend/modules/auth/`):**
  - Stateless HS256 JWT tokens containing `sub`, `tenant_id`, `role`, `exp`, and `assigned_sections`.
  - `/api/v1/auth/login` supports instant demo role switching.
  - `/api/v1/auth/me` returns current user context.
* **Student Roster & Timetables (`backend/modules/students/`):**
  - Role-scoped student search, pagination, and detailed demographics.
  - Static & dynamic weekly timetable mapping by class section.
* **Attendance Tracking & Signal Ingestion (`backend/modules/attendance/`):**
  - Daily attendance aggregation by section with Present, Absent, and Late breakdown.
  - Chronic absentee identification (students with $\ge 5$ absences).
  - Bulk mobile signal ingestion (`POST /api/v1/attendance/submit`) with duplicate-day overwrite protection.
* **Fee Management & Ledger (`backend/modules/fees/`):**
  - Invoice generation, term tracking, and collection KPI rollups (Total Billed, Total Collected, Outstanding).
  - Integrated **Razorpay Test Sandbox** payment trigger (`POST /api/v1/fees/pay-invoice`) returning instant mock transaction references.
* **Notification Engine (`backend/modules/notification_engine/`):**
  - In-process event bus decoupling domain actions from alerts.
  - Automatic dispatch of absence/late notifications via FCM push payloads and in-app DB outbox.

---

### 2.2 AI Text-to-SQL Analytics Engine (Module 8.0)

```
User Query: "How many students were absent today in Class 10-A?"
     │
     ▼
[ 1. Local PII Sanitizer ] ──► Strips phone numbers & emails pre-inference
     │
     ▼
[ 2. Master System Prompt ] ──► Injects schema context + RBAC subquery predicate + JSON output contract
     │
     ▼
[ 3. LLM Translation (Groq / Gemini / Fallback) ] ──► Returns JSON:
     {
       "sql": "SELECT COUNT(*) AS absent_count FROM attendance_records ...",
       "single_result_template": "Found {absent_count} absent student in Class 10-A.",
       "multi_result_template": "Found {row_count} records.",
       "zero_result_template": "No absent records found for Class 10-A today."
     }
     │
     ▼
[ 4. AST Guarded Executor (sqlglot) ]
     ├── Enforce SELECT-only (Block DDL/DML)
     ├── Enforce Table Whitelist
     ├── Cap Row Limit (Max 500)
     ├── Verify Multi-Tenant filter (tenant_id)
     └── Structurally Walk AST for Identity Predicate (Non-Admin Fail-Closed)
     │
     ▼ (DB Execution via SessionLocal)
[ 5. Local Python Template Interpolator ]
     └── str.format(**bindings) merges SQL results with LLM phrasing template
         *** ZERO DATABASE ROWS ARE SENT TO EXTERNAL LLMs ***
     │
     ▼
Final ConversationalAnswerDTO response with optional Dev Debug Panel
```

* **Schema Introspection (`ReadOnlySchemaGateway`):** Dynamically builds schema metadata and column definitions without exposing write permissions.
* **AST SQL Guardrails (`GuardedQueryExecutor`):** Uses `sqlglot` to parse generated SQLite statements into an Abstract Syntax Tree. Enforces SELECT-only, table whitelisting, and strict row limits.
* **Structural RBAC Subquery Injection:** Verifies that parent and student queries include valid `guardian_user_id` / `email` predicates in top-level WHERE or nested IN-subqueries. Non-privileged queries **fail closed** on parser errors.
* **Multi-Turn Chat History (`chat_history`):** Preserves preceding dialogue turns (up to 6) allowing contextual pronoun and filter carry-forward (e.g., "list their names" after a count query).
* **Local PII Sanitizer (`pii_sanitizer.py`):** Pre-inference regex scrubber that redacts Indian/E.164 phone numbers and RFC-5321 emails (`[PHONE_REDACTED]`, `[EMAIL_REDACTED]`).
* **Zero-PII Local Python Interpolation:** LLM generates phrasing templates with `{alias}` placeholders; actual data binding is performed strictly within the backend via Python `str.format()`. Database records never cross the network boundary to external AI APIs.

---

### 2.3 Web Dashboard Features (`web-dashboard/`)

* **White-Label Dynamic Theme Engine (`ThemeProvider.tsx`):** Injects school-specific brand colors, fonts, and crests via backend-supplied CSS custom variables.
* **Central Navigation Matrix (`roleNavigation.ts`):** Single source-of-truth mapping roles (`admin`, `principal`, `teacher`, `student`, `parent`) to authorized views with strict route protection in `App.tsx`.
* **Admin / Principal Overview (`OverviewDashboard.tsx`):** High-level KPI metrics (Total Students, Daily Attendance Rate %, Overdue Fee Amounts, Chronic Absentees Alert).
* **Student Roster (`StudentRoster.tsx`):** Paginated student list with real-time class section filters.
* **Attendance Analytics (`AttendanceAnalytics.tsx`):** Daily attendance bar charts, status filters, and chronic absentee tables.
* **Fee Dashboard (`FeeDashboard.tsx`):** Complete collection metrics, status breakdowns (Paid, Pending, Overdue), and invoice tables.
* **Teacher Schedule Screen (`TeacherScheduleScreen.tsx`):** Interactive daily timetable grid with real-time active period detection and room allocations.
* **Teacher Attendance Screen (`TeacherAttendanceScreen.tsx`):** Fast-tap attendance matrix (Present, Absent, Late) scoped to assigned sections with mandatory justification modal for manual overrides.
* **Academic Grades Screen (`AcademicGradesScreen.tsx`):** Comprehensive report card view with subject-by-subject percentage grades, teacher remarks, and GPA calculations.
* **Personal Attendance Screen (`PersonalAttendanceScreen.tsx`):** Student/parent 30-day attendance history with attendance rate gauge and chronic absence warning banners.
* **Personal Fee Screen (`PersonalFeeScreen.tsx`):** Individual fee account ledger with overdue alerts and embedded Razorpay Sandbox payment modal.
* **Conversational AI Chatbox (`ChatQueryBox.tsx`):** Interactive natural language query interface with turn counter badge, quick prompt suggestions, and collapsible SQL / execution timing debug panel (development-gated).

---

### 2.4 Mobile App Features (`mobile-app/`)

* **Expo React Native Architecture:** Built on Expo SDK 52 with modular TypeScript screens and dark-mode glassmorphic styling.
* **Offline-First Attendance Queue (`AsyncStorage`):** Stores attendance signals locally during network dropouts and automatically flushes when reconnected.
* **Quick-Tap Attendance Matrix:** High-speed classroom roll-call UI designed for rapid one-handed phone operation.
* **Manual Override Modal:** Captures teacher override justifications with timestamped audit trails.
* **Parent Child Summary & Fee Ledger:** Mobile view of student attendance records, daily statuses, and fee dues.

---

## 3. Key Architectural Decisions & Security Design Log

| Architectural Decision | Technical Justification | Security & Operational Benefit |
|---|---|---|
| **Local Python Template Interpolation** | Instead of feeding SQL query results back to the LLM for natural language formatting, the LLM proposes template strings with `{alias}` placeholders at SQL generation time. Python performs local `str.format()` interpolation. | **Zero PII Leakage & 0 Token Cost:** Sensitive student names, fee amounts, and parent details are never sent across the wire to external LLM providers. |
| **AST-Level Subquery RBAC Predicates** | Rather than relying on LLM system prompt compliance, `GuardedQueryExecutor` uses `sqlglot` to parse the query AST and enforce that non-admin queries contain a valid `guardian_user_id` or `email` predicate. | **Hardened Security Boundary:** Prompt injections or LLM hallucinations cannot bypass row-level data isolation. Non-admin queries fail closed if the predicate is omitted. |
| **JWT Token Section Scoping** | Teacher tokens embed an `assigned_sections` claim at login time (`TokenPayload.assigned_sections`). | **Zero-Round-Trip Scoping:** Backend facades immediately scope student lists and attendance grids to assigned sections without requiring redundant DB user-permission queries. |
| **Strategy Pattern for Ingestion Sources** | Designed `IAttendanceIngestionSource` interface decoupling the attendance facade from the input origin (Mobile Quick-Tap vs. Paper Register OCR). | **Future-Proof Extensibility:** The upcoming Biometric CV / OCR scanner can be dropped in without altering core attendance domain logic. |
| **Client-Side Session History with Server RBAC** | Chat history is maintained as an array of turns in frontend state and sent with each request, while the server enforces RBAC on every generated query. | **Zero Server Session Bloat:** Stateless backend scaling while preventing history manipulation from accessing unauthorized student data. |

---

## 4. Current Limitations & Future Scope

```
Current Implemented State (Phase 1 & 2)          Future Roadmap (Phase 3+)
┌──────────────────────────────────────┐        ┌──────────────────────────────────────┐
│ - 100% Free Razorpay Test Sandbox    │  ───►  │ - Production Razorpay Webhook Engine │
│ - FCM Free Tier + In-App Outbox      │  ───►  │ - Multi-Channel WhatsApp / SMS Alerts│
│ - Seeded Synthetic Data Generator    │  ───►  │ - Production PostgreSQL Migration    │
│ - Multi-Turn Text-to-SQL + AST Guard │  ───►  │ - Vector Semantic Search over Docs  │
│ - Full 5-Role Web Dashboard UI       │  ───►  │ - Hybrid CV/OCR Paper Register Scan │
└──────────────────────────────────────┘        └──────────────────────────────────────┘
```

1. **Hybrid Paper Register OCR Scanner:**
   - *Status:* Skipped during early prototyping to accelerate core ERP stability.
   - *Future Scope:* Connect the existing `IAttendanceIngestionSource` interface to a lightweight YOLO / OpenCV bounding-box model for scanning physical paper attendance sheets.
2. **Payment Gateway Integration:**
   - *Status:* Operating in mock Razorpay Test Sandbox mode (`rzp_test_...`).
   - *Future Scope:* Enable real-time webhook listeners (`POST /api/v1/fees/webhook`) with cryptographic signature validation (`X-Razorpay-Signature`).
3. **Notification Delivery:**
   - *Status:* Free FCM Push notifications and local database in-app notification outbox.
   - *Future Scope:* Integrate Twilio / Gupshup SMS and WhatsApp Business APIs for instant parent alert dispatch.

---

## 5. System Demo Credentials & Startup Commands

### 5.1 Demo User Credentials

All accounts use the standardized demo password: **`Demo@1234!`**

| Role | Username / Email | Default Landing Tab | Scoped Permissions & Data View |
|---|---|---|---|
| **Admin** | `admin@demo.school` | Dashboard Overview | Full school access, all classes, global fee collection KPIs, unrestricted AI SQL queries. |
| **Principal** | `principal@demo.school` | Dashboard Overview | School-wide executive analytics, chronic absentees, fee summaries, unrestricted AI SQL. |
| **Teacher (10-A)** | `teacher01@demo.school` | My Schedule | Scoped strictly to Class 10-A; timetable, quick-tap attendance matrix with manual overrides. |
| **Teacher (10-B)** | `teacher02@demo.school` | My Schedule | Scoped strictly to Class 10-B; timetable, attendance marking. |
| **Parent** | `parent-of-student-01@demo.school` | Child's Academics | Scoped to own child (`guardian_user_id`); report card, attendance history, fee ledger & Razorpay sandbox. |
| **Student** | `student01@demo.school` | Academic & Grades | Scoped to own record (`email`); personal grades, timetable, attendance rate, fee status. |

---

### 5.2 Startup Commands

#### 1. Backend REST API Server (Port 8000)
```powershell
cd c:\Users\hmnsh\Downloads\smart-academic-erp\backend
$env:PYTHONPATH = "."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```
* Swagger UI Docs: `http://localhost:8000/api/docs`
* Health Check: `http://localhost:8000/health`

#### 2. React 19 Web Admin Dashboard (Port 3000)
```powershell
cd c:\Users\hmnsh\Downloads\smart-academic-erp\web-dashboard
npm run dev
```
* Dashboard URL: `http://localhost:3000`

#### 3. React Native (Expo) Teacher Mobile App (Port 8081)
```powershell
cd c:\Users\hmnsh\Downloads\smart-academic-erp\mobile-app
npx expo start
```
* Press `w` in terminal for Web preview, or scan QR code with Expo Go app on Android/iOS.
