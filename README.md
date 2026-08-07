# 🎓 AI-Powered Smart Academic ERP

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61DAFB.svg?style=flat&logo=react)](https://react.dev)
[![React Native](https://img.shields.io/badge/React_Native-Expo_57-000000.svg?style=flat&logo=expo)](https://expo.dev)
[![Python](https://img.shields.io/badge/Python-3.12-3776AB.svg?style=flat&logo=python)](https://python.org)
[![SQLite](https://img.shields.io/badge/Database-SQLite%2FPostgreSQL-003B57.svg?style=flat&logo=sqlite)](https://sqlite.org)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

An enterprise-grade, white-labeled **AI-Powered Smart Academic ERP System** featuring modular Clean Architecture, Domain-Driven Design (DDD), Multi-Tenant schema isolation, Natural Language AI Text-to-SQL analytics, and cross-platform Web + Mobile interfaces.

---

## 🌟 Key System Capabilities

- **Modular Clean Architecture**: Domain-driven isolation across Core, Auth, Student Academic, Attendance, Fee Management, Notification Engine, Parent/Student Portals, and AI Analytics modules.
- **AI Text-to-SQL Analytics Engine**: Natural language conversational queries ("How many students were absent in Class 10-A?") translated to AST-validated SQLite/PostgreSQL queries with read-only schema gateway and SQL injection guardrails (`sqlglot`).
- **Multi-Tenant White-Labeling**: Runtime tenant configuration (`GET /api/v1/core/tenant-config`) enabling dynamic custom branding, color themes, logo URLs, and feature toggling per school.
- **Cross-Platform Mobile App (React Native / Expo)**: Dedicated Teacher, Parent, and Student mobile workflows with AsyncStorage offline-first queueing and auto-sync.
- **100% Free Notification Engine**: Firebase Cloud Messaging (FCM Free Tier) simulation + persisted DB `in_app_notifications` inbox.
- **Free Razorpay Sandbox Integration**: Seamless test fee payments (`POST /api/v1/fees/pay-invoice`) returning test order IDs (`order_rzp_test_...`).
- **End-to-End Test Automation**: 100% passed `pytest` suite testing all endpoints across Admin, Teacher, Parent, and Student roles.

---

## 📐 Architecture Overview

```
                          ┌──────────────────────────┐
                          │    React Web Admin &     │
                          │   React Native Expo App  │
                          └─────────────┬────────────┘
                                        │ HTTP / REST (JWT)
                                        ▼
    ┌────────────────────────────────────────────────────────────────────────┐
    │                      FastAPI REST API Gateway                          │
    ├──────────────┬──────────────┬──────────────┬─────────────┬─────────────┤
    │ Core Tenant  │   Auth DTO   │ Students API │ Attendance  │  Fees API   │
    │   Module     │   Module     │   Module     │   Module    │   Module    │
    └──────┬───────┴──────┬───────┴──────┬───────┴──────┬──────┴──────┬──────┘
           │              │              │              │             │
           ▼              ▼              ▼              ▼             ▼
    ┌────────────────────────────────────────────────────────────────────────┐
    │              AI Text-to-SQL Engine (sqlglot + AST Guard)              │
    └───────────────────────────────────┬────────────────────────────────────┘
                                        │ SQLAlchemy ORM
                                        ▼
    ┌────────────────────────────────────────────────────────────────────────┐
    │                     SQLite / PostgreSQL Database                        │
    │  (students, attendance_records, fee_invoices, in_app_notifications)    │
    └────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Quick Start & Run Instructions

### 1. Environment Setup
```powershell
# Clone repository
git clone https://github.com/hmnshu1in10000/smart-academic-erp.git
cd smart-academic-erp

# Activate Python virtual environment
.\venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r backend/requirements.txt
```

### 2. Launch FastAPI Backend Server
```powershell
# Set PYTHONPATH and start server on port 8000
$env:PYTHONPATH="C:\Users\hmnsh\Downloads\smart-academic-erp\backend"
venv\Scripts\python backend\manage.py runserver --port 8000
```
Backend Interactive API Docs available at: `http://localhost:8000/api/docs`

### 3. Run Web Admin Dashboard
```powershell
cd web-dashboard
npm install
npm run dev
```
Access Web Dashboard at: `http://localhost:3000`

### 4. Run Mobile App (Expo)
```powershell
cd mobile-app
npm install
npx expo start
```

### 5. Run Automated Pytest Suite
```powershell
$env:PYTHONPATH="C:\Users\hmnsh\Downloads\smart-academic-erp\backend"
venv\Scripts\python -m pytest backend/tests/test_e2e_pipeline.py -v
```

---

## 🔐 Pre-Seeded Demo Credentials

| Role | Username / Email | Password | Access Scope |
|---|---|---|---|
| **Admin** | `admin@demo.school` | `Demo@1234!` | Full ERP Web Dashboard & AI Analytics |
| **Teacher** | `teacher01@demo.school` | `Demo@1234!` | Class Schedule & Mobile Attendance Mark |
| **Parent** | `parent-of-student-01@demo.school` | `Demo@1234!` | Child Attendance, Absences & Razorpay Fee Dues |
| **Student** | `student01@demo.school` | `Demo@1234!` | Personal Timetable, Report Card & Attendance |

---

## 📚 Viva Presentation Guide
Refer to [`docs/VIVA_PRESENTATION_GUIDE.md`](docs/VIVA_PRESENTATION_GUIDE.md) for the complete viva cheat sheet containing system architecture rationale and top 15 technical viva Q&A pairs with model answers.
