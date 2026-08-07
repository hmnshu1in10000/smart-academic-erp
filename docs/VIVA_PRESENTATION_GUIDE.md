# 🎓 University Viva & Project Defense Guide

This document is the official **University Viva Cheat Sheet** for the **AI-Powered Smart Academic ERP**. It provides architectural diagrams, design pattern rationales, and model answers for the top 15 technical questions professors ask during final project defense.

---

## 🏛️ 1. System Architecture & Design Rationale

### High-Level Architecture Diagram

```
+-------------------------------------------------------------------------+
|                              PRESENTATION LAYER                         |
|   React 19 Web Dashboard (Tailwind CSS)  |  React Native Expo Mobile App  |
+------------------------------------+------------------------------------+
                                     | HTTP REST + JWT (Bearer Auth)
                                     v
+-------------------------------------------------------------------------+
|                               API GATEWAY                               |
|               FastAPI Routers + Dependency Injection (Dep)              |
+------------------------------------+------------------------------------+
                                     | DTO Transfer Objects
                                     v
+-------------------------------------------------------------------------+
|                             APPLICATION LAYER                           |
|   Module Facades (AttendanceFacade, FeesFacade, StudentsFacade)          |
|   AI Text-to-SQL Engine (ReadOnlySchemaGateway, AST Query Sanitizer)     |
+------------------------------------+------------------------------------+
                                     | Domain Contracts
                                     v
+-------------------------------------------------------------------------+
|                              INFRASTRUCTURE                             |
|          SQLAlchemy 2.0 ORM  |  SQLite 3 / PostgreSQL Database          |
+-------------------------------------------------------------------------+
```

### Clean Architecture & DDD Layering Rationale
1. **Domain Isolation**: Core business logic and DTOs remain completely independent of external frameworks (FastAPI, React, SQLite).
2. **Facade Pattern**: Modules expose single-entry Facades (`AttendanceFacade`, `FeesFacade`), keeping controller endpoints thin and testable.
3. **AST SQL Injection Guardrails**: Natural language questions are parsed using `sqlglot` abstract syntax trees to enforce `SELECT`-only execution.

---

## ❓ Top 15 Technical Viva Questions & Model Answers

### Q1: Why did you choose Clean Architecture and Domain-Driven Design (DDD)?
> **Model Answer**: "Clean Architecture decouples core academic business rules from external frameworks like databases and UI. By maintaining strict dependency rules pointing inward toward domain entities, we can swap database backends (e.g., from SQLite to PostgreSQL) or replace frontend clients without touching core business logic."

### Q2: How does the AI Text-to-SQL Analytics Engine prevent SQL injection attacks?
> **Model Answer**: "We implement a 3-layer security defense:
> 1. **ReadOnlySchemaGateway**: Exposes only non-sensitive read-only tables.
> 2. **Abstract Syntax Tree (AST) Inspection**: Uses `sqlglot` to parse generated SQL. If the AST contains mutating statements (`DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`), execution is blocked immediately.
> 3. **Database Read-Only Connection**: Executes SQL statements against SQLite in read-only mode."

### Q3: How is multi-tenancy implemented in your ERP system?
> **Model Answer**: "Multi-tenancy uses a discriminator column strategy (`tenant_id`) enforced across all database entities. Tenant configuration (`school_config.py` and `GET /api/v1/core/tenant-config`) delivers runtime custom themes, colors, and logos to the frontend."

### Q4: How does the offline-first attendance queue work on the mobile app?
> **Model Answer**: "When a teacher submits attendance without active internet, `offlineQueue.ts` saves the payload into `AsyncStorage`. Once network connectivity is restored, an auto-sync process posts queued batches to `POST /api/v1/attendance/summary`."

### Q5: How do you handle JWT authentication and authorization across multiple roles?
> **Model Answer**: "The backend uses `python-jose` with `HS256` symmetric encryption. Access tokens carry `sub` (username), `role` (`admin`, `teacher`, `parent`, `student`), and `tenant_id`. FastAPI `Depends(get_current_tenant_context)` verifies token validity on every request."

### Q6: How does the system achieve 100% free notifications?
> **Model Answer**: "Instead of relying on paid SMS APIs, we use Firebase Cloud Messaging (FCM Free Tier) for push payloads and persist messages in the database `in_app_notifications` table for inbox retrieval (`GET /api/v1/notifications/inbox`)."

### Q7: How does Razorpay payment integration work in test sandbox mode?
> **Model Answer**: "We utilize Razorpay Test Mode API keys (`rzp_test_...`). When a parent clicks 'Pay Dues', `POST /api/v1/fees/pay-invoice` generates a test Razorpay order ID (`order_rzp_test_...`) and automatically updates the invoice status in the database."

### Q8: What database ORM is used and why SQLAlchemy 2.0?
> **Model Answer**: "We use SQLAlchemy 2.0 for type-safe Python ORM operations, supporting async sessions, declarative `Mapped[...]` field annotations, and seamless dialect switching between SQLite and PostgreSQL."

### Q9: How are historic attendance logs generated for initial bootstrapping?
> **Model Answer**: "Module 3.0 (`dummy_generator.py`) generates realistic historic records for 50 students over 30 days using deterministic weighted random distributions (85% Present, 10% Absent, 5% Late)."

### Q10: How does runtime white-labeling work in the web dashboard?
> **Model Answer**: "The React web application features a custom `ThemeProvider.tsx` that fetches tenant configuration at boot and dynamically injects CSS custom properties (`--color-primary`, `--color-secondary`) into the document root element."

### Q11: How do you handle database concurrency during bulk attendance signal ingestion?
> **Model Answer**: "In `AttendanceFacade.ingest_signals()`, we execute single atomic transactions within `SessionLocal()` blocks, deleting existing daily records before inserting new signals to guarantee idempotent upserts."

### Q12: How are unit and E2E tests structured?
> **Model Answer**: "We use `pytest` with FastAPI's `TestClient` in `backend/tests/test_e2e_pipeline.py`, covering Auth, Roster, Attendance Ingestion, Razorpay Sandbox Payments, AI Text-to-SQL, and Notifications."

### Q13: What is the purpose of FastAPI's `lifespan` context manager?
> **Model Answer**: "The `lifespan` context manager handles startup and shutdown events, ensuring database tables are initialized via `create_all_tables()` before accepting incoming HTTP requests."

### Q14: How does the parent portal link parents to students?
> **Model Answer**: "The `GET /api/v1/parent/child-summary` endpoint resolves parent accounts via JWT claims and joins `students`, `class_sections`, and `fee_invoices` tables."

### Q15: What are the future scalability plans for this ERP architecture?
> **Model Answer**: "Future extensions include migrating from SQLite to PostgreSQL with Row-Level Security (RLS), deploying Redis for token revocation blacklists, and deploying the Expo app to Apple App Store and Google Play Store."
