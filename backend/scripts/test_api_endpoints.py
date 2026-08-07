"""
backend/scripts/test_api_endpoints.py
======================================
Integration verification script using FastAPI TestClient to test all Phase 2 endpoints & AI Text-to-SQL engine.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def run_tests():
    print("=" * 60)
    print("🚀 Starting Phase 2 API Verification Tests")
    print("=" * 60)

    # 1. Health Check
    res = client.get("/health")
    print(f"\n1. GET /health -> Status {res.status_code}")
    assert res.status_code == 200, f"Health check failed: {res.text}"
    print("   Result:", res.json())

    # 2. Tenant Config
    res = client.get("/api/v1/core/tenant-config?tenant_id=greenwood-high-001")
    print(f"\n2. GET /api/v1/core/tenant-config -> Status {res.status_code}")
    assert res.status_code == 200, f"Tenant config failed: {res.text}"
    data = res.json()
    print(f"   School: '{data['school_name']}' | Primary Color: {data['theme']['primary']}")

    # 3. Login Endpoint
    res = client.post("/api/v1/auth/login", data={"username": "admin@demo.school", "password": "Demo@1234!"})
    print(f"\n3. POST /api/v1/auth/login -> Status {res.status_code}")
    assert res.status_code == 200, f"Login failed: {res.text}"
    token_data = res.json()
    token = token_data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print(f"   Logged in as {token_data['full_name']} | Role: {token_data['role']} | Token snippet: {token[:20]}...")

    # 4. Students List Endpoint
    res = client.get("/api/v1/students?page=1&page_size=5", headers=headers)
    print(f"\n4. GET /api/v1/students -> Status {res.status_code}")
    assert res.status_code == 200, f"Students endpoint failed: {res.text}"
    students_data = res.json()
    print(f"   Total Students: {students_data['total']} | Page Items: {len(students_data['items'])}")
    print(f"   First Student: Roll {students_data['items'][0]['roll_number']} - {students_data['items'][0]['full_name']} ({students_data['items'][0]['class_section']})")

    # 5. Attendance Summary Endpoint
    res = client.get("/api/v1/attendance/summary?section=10-A", headers=headers)
    print(f"\n5. GET /api/v1/attendance/summary -> Status {res.status_code}")
    assert res.status_code == 200, f"Attendance endpoint failed: {res.text}"
    att_data = res.json()
    print(f"   Overall Attendance Rate: {att_data['overall_present_pct']}% | Daily records: {len(att_data['daily_stats'])}")
    print(f"   Chronic Absentees Detected: {len(att_data['chronic_absentees'])}")

    # 6. Fees Invoices Endpoint
    res = client.get("/api/v1/fees/invoices?status=PAID&page=1&page_size=5", headers=headers)
    print(f"\n6. GET /api/v1/fees/invoices -> Status {res.status_code}")
    assert res.status_code == 200, f"Fees endpoint failed: {res.text}"
    fee_data = res.json()
    print(f"   Paid Invoices Count: {fee_data['total']} | Returned Items: {len(fee_data['items'])}")

    # 7. AI Text-to-SQL Analytics Endpoint (The Objective Query!)
    test_queries = [
        "How many students are in Class 10-A?",
        "How many students were absent in Class 10-A?",
        "Show all overdue fee invoices"
    ]

    print("\n7. POST /api/v1/ai-analytics/ask -> Testing Conversational Analytics Engine")
    for q in test_queries:
        res = client.post("/api/v1/ai-analytics/ask", json={"query": q}, headers=headers)
        print(f"\n   Query: '{q}' -> Status {res.status_code}")
        assert res.status_code == 200, f"AI Analytics failed for '{q}': {res.text}"
        ai_resp = res.json()
        print(f"   Generated SQL : {ai_resp['generated_sql']}")
        print(f"   Rows Returned : {ai_resp['row_count']}")
        print(f"   Summary Answer: {ai_resp['summary_answer']}")

    print("\n" + "=" * 60)
    print("✅ ALL PHASE 2 ENDPOINTS & AI TEXT-TO-SQL ENGINE VERIFIED PERFECTLY!")
    print("=" * 60)

if __name__ == "__main__":
    run_tests()
