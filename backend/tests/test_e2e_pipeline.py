"""
backend/tests/test_e2e_pipeline.py
===================================
End-to-End Comprehensive Pytest Pipeline Suite.
Covers:
1. Tenant Config Endpoint (Module 1.0)
2. Admin, Teacher, Parent Login & JWT Validation (Module 2.0)
3. Student Roster Listing (Module 4.0)
4. Attendance Summary Aggregation & Mobile Ingestion (Module 5.0)
5. Free Razorpay Sandbox Test Payment Simulation (Module 6.0)
6. AI Text-to-SQL Conversational Analytics Engine Evaluation (Module 8.0)
7. Notifications Inbox Retrieval (Notification Engine)
8. Parent Portal Child Summary Endpoint
9. Student Portal Academic Summary Endpoint
"""
import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
from modules.dummy_data_engine.infrastructure.db.session import SessionLocal, create_all_tables
from modules.dummy_data_engine.infrastructure.db.models import Student, FeeInvoice

# Ensure DB tables exist
create_all_tables()
client = TestClient(app)


def test_01_health_and_tenant_config():
    """Verify health check and tenant configuration endpoint."""
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    res = client.get("/api/v1/core/tenant-config?tenant_id=greenwood-high-001")
    assert res.status_code == 200
    data = res.json()
    assert data["school_name"] == "Greenwood High"
    assert "theme" in data
    assert "features" in data


def test_02_auth_login_all_roles():
    """Verify demo logins for Admin, Teacher, and Parent roles."""
    roles = [
        ("admin@demo.school", "Demo@1234!", "admin"),
        ("teacher01@demo.school", "Demo@1234!", "teacher"),
        ("parent-of-student-01@demo.school", "Demo@1234!", "parent"),
    ]

    for email, pwd, expected_role in roles:
        res = client.post("/api/v1/auth/login", data={"username": email, "password": pwd})
        assert res.status_code == 200, f"Login failed for {email}: {res.text}"
        body = res.json()
        assert "access_token" in body
        assert body["role"] == expected_role


def test_03_student_roster():
    """Verify paginated student roster endpoint."""
    res = client.post("/api/v1/auth/login", data={"username": "admin@demo.school", "password": "Demo@1234!"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/students?page=1&page_size=10", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 50
    assert len(data["items"]) == 10


def test_04_attendance_summary_and_mobile_ingestion():
    """Verify attendance summary and mobile signal ingestion."""
    res = client.post("/api/v1/auth/login", data={"username": "teacher01@demo.school", "password": "Demo@1234!"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Summary GET
    res = client.get("/api/v1/attendance/summary?section=10-A", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "overall_present_pct" in data

    # Fetch a real student ID from DB
    with SessionLocal() as session:
        student = session.query(Student).first()
        student_id = student.id
        sec_id = student.class_section_id

    import uuid
    # Signal Ingestion POST
    payload = {
        "signals": [
            {
                "signal_id": f"pytest_sig_{uuid.uuid4()}",
                "student_id": student_id,
                "class_section_id": sec_id,
                "status": "P",
                "source": "TEACHER_MOBILE_APP",
            }
        ]
    }
    res = client.post("/api/v1/attendance/summary", json=payload, headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_05_razorpay_sandbox_payment():
    """Verify Free Razorpay Sandbox test payment endpoint."""
    res = client.post("/api/v1/auth/login", data={"username": "parent-of-student-01@demo.school", "password": "Demo@1234!"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Fetch a real invoice ID from DB
    with SessionLocal() as session:
        inv = session.query(FeeInvoice).first()
        inv_id = inv.id

    pay_payload = {"invoice_id": inv_id, "payment_method": "UPI"}
    res = client.post("/api/v1/fees/pay-invoice", json=pay_payload, headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "SUCCESS"
    assert body["razorpay_order_id"].startswith("order_rzp_test_")


def test_06_ai_text_to_sql_engine():
    """Verify AI Text-to-SQL Conversational Analytics Engine."""
    res = client.post("/api/v1/auth/login", data={"username": "admin@demo.school", "password": "Demo@1234!"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    queries = [
        "How many students are in Class 10-A?",
        "How many students were absent in Class 10-A?",
        "Show all overdue fee invoices",
    ]

    for q in queries:
        res = client.post("/api/v1/ai-analytics/ask", json={"query": q}, headers=headers)
        assert res.status_code == 200, f"AI query failed for '{q}': {res.text}"
        body = res.json()
        assert "generated_sql" in body
        assert "summary_answer" in body
        assert body["row_count"] >= 1


def test_07_parent_and_student_portals():
    """Verify parent child-summary and student academic-summary endpoints."""
    # Parent Summary
    res = client.post("/api/v1/auth/login", data={"username": "parent-of-student-01@demo.school", "password": "Demo@1234!"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/parent/child-summary", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert "child_name" in body
    assert "attendance_rate_pct" in body

    # Student Summary
    res = client.get("/api/v1/student/academic-summary", headers=headers)
    assert res.status_code == 200
    body = res.json()
    assert "report_card" in body


def test_08_notifications_inbox():
    """Verify user notification inbox endpoint."""
    res = client.post("/api/v1/auth/login", data={"username": "teacher01@demo.school", "password": "Demo@1234!"})
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    res = client.get("/api/v1/notifications/inbox", headers=headers)
    assert res.status_code == 200
    assert isinstance(res.json(), list)
