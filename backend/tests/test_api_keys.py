"""
Test script to verify if GROQ_API_KEY and GEMINI_API_KEY are working
by sending real mock queries to the LLM endpoints and testing end-to-end
SQL generation and execution.
"""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Ensure .env is loaded
env_path = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(env_path)

groq_key = os.getenv("GROQ_API_KEY", "")
gemini_key = os.getenv("GEMINI_API_KEY", "")

print("=" * 70)
print("🔑 API KEY CONFIGURATION CHECK")
print("=" * 70)
print(f"GROQ_API_KEY  : {'PRESENT (' + groq_key[:10] + '...)' if groq_key else 'MISSING'}")
print(f"GEMINI_API_KEY: {'PRESENT (' + gemini_key[:10] + '...)' if gemini_key else 'MISSING'}")
print()

# -----------------------------------------------------------------------------
# 1. Direct Groq API Test
# -----------------------------------------------------------------------------
print("-" * 70)
print("1. TESTING GROQ API (llama-3.1-8b-instant)...")
print("-" * 70)

if groq_key and groq_key != "your_groq_api_key_here":
    import requests
    test_messages = [
        {"role": "system", "content": "You are a SQLite expert. Output JSON only: {\"sql\": \"...\", \"single_result_template\": \"...\", \"multi_result_template\": \"...\", \"zero_result_template\": \"...\"}"},
        {"role": "user", "content": "User Question: How many active students are enrolled in Class 10-A?\n\nReturn JSON:"}
    ]
    try:
        res = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
            json={"model": "llama-3.1-8b-instant", "messages": test_messages, "temperature": 0.1},
            timeout=15,
        )
        print(f"HTTP Status: {res.status_code}")
        if res.status_code == 200:
            data = res.json()
            content = data["choices"][0]["message"]["content"]
            print("✓ GROQ API IS WORKING SUCCESSFULLY!")
            print(f"Response Snippet:\n{content[:250]}...")
        else:
            print(f"✗ GROQ API ERROR: {res.text}")
    except Exception as e:
        print(f"✗ GROQ EXCEPTION: {e}")
else:
    print("⚠ Skipping Groq test: Key not configured or placeholder.")

print()

# -----------------------------------------------------------------------------
# 2. Direct Gemini API Test
# -----------------------------------------------------------------------------
print("-" * 70)
print("2. TESTING GEMINI API (Google AI Studio / Gemini 2.0)...")
print("-" * 70)

if gemini_key and gemini_key not in ("your_google_ai_studio_key_here", "your_gemini_api_key_here"):
    try:
        from google import genai
        client = genai.Client(api_key=gemini_key)
        resp = client.models.generate_content(
            model="gemini-2.0-flash",
            contents="Say 'Gemini API is working' in JSON format: {\"status\": \"ok\"}",
        )
        print("✓ GEMINI API IS WORKING SUCCESSFULLY!")
        print(f"Response: {resp.text.strip()}")
    except Exception as e:
        print(f"✗ GEMINI EXCEPTION: {e}")
else:
    print("⚠ Skipping Gemini test: Key not configured or placeholder.")

print()

# -----------------------------------------------------------------------------
# 3. End-to-End AI Text-to-SQL Mock Questions Test
# -----------------------------------------------------------------------------
print("-" * 70)
print("3. END-TO-END AI CHAT ENGINE MOCK QUESTIONS TEST")
print("-" * 70)

from modules.ai_analytics.domain.dtos import NLQueryRequestDTO
from modules.ai_analytics.application.services.analytics_facade import ConversationalAnalyticsFacade

facade = ConversationalAnalyticsFacade()

mock_questions = [
    "How many students are enrolled in Class 10-A?",
    "List name of students whose fees is partially paid",
    "What is the total fee collection efficiency rate for the school?",
    "Which students were absent yesterday in Class 10-A?",
]

for idx, q in enumerate(mock_questions, 1):
    print(f"\n[Mock Question {idx}]: \"{q}\"")
    req = NLQueryRequestDTO(
        query=q,
        tenant_id="greenwood-high-001",
        current_role_key="ADMIN",
    )
    ans = facade.ask(req)
    print(f"  → Generated SQL: {ans.generated_sql}")
    print(f"  → Row Count:     {ans.row_count}")
    print(f"  → Summary:       {ans.summary_answer}")
    if ans.error:
        print(f"  → Error:         {ans.error}")
    else:
        print(f"  → Status:        ✓ SUCCESS")

print("\n" + "=" * 70)
print("ALL MOCK TESTS COMPLETED")
print("=" * 70)
