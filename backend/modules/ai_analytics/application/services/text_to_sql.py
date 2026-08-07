"""
modules/ai_analytics/application/services/text_to_sql.py
========================================================
Sub-Module 8.2: TextToSQLService
Translates natural language questions into single SQLite SELECT statements using LLM (Groq / Gemini Flash).
"""
from __future__ import annotations

import logging
import os
import re
import requests

from modules.ai_analytics.domain.dtos import GeneratedSQLDTO
from modules.ai_analytics.application.services.schema_gateway import ReadOnlySchemaGateway

logger = logging.getLogger(__name__)

# System prompt for LLM SQL generation
SYSTEM_PROMPT = """You are an expert SQL Generator for SQLite database of Smart Academic ERP.
Given a natural language user question and database schema, generate EXACTLY ONE executable SQLite SELECT statement.

CRITICAL RULES:
1. ONLY generate SELECT statements. No INSERT, UPDATE, DELETE, DROP, ALTER.
2. ALWAYS include `tenant_id = :tenant_id` or `tenant_id = '{tenant_id}'` in the WHERE clause for main tables.
3. Do NOT wrap SQL in markdown codeblocks (no ```sql). Output RAW SQL ONLY.
4. Keep column names exact as specified in the schema.
5. Case-insensitive text matching should use UPPER() or LIKE if appropriate.

Schema:
{schema_context}
"""


class TextToSQLService:
    """
    Sub-Module 8.2: Text-to-SQL translation engine.
    Uses Groq API (`GROQ_API_KEY`) or Gemini API (`GEMINI_API_KEY`) or local fallback.
    """

    def __init__(self) -> None:
        self._schema_gateway = ReadOnlySchemaGateway()

    def generate_sql(self, query: str, tenant_id: str) -> GeneratedSQLDTO:
        """Translates user query to SQL."""
        schema_text = self._schema_gateway.get_schema_context()
        sys_prompt = SYSTEM_PROMPT.format(schema_context=schema_text, tenant_id=tenant_id)
        user_prompt = f"Tenant ID: '{tenant_id}'\nUser Question: {query}\n\nGenerated SQLite SQL:"

        sql = self._call_llm(sys_prompt, user_prompt, query, tenant_id)
        cleaned_sql = self._clean_sql(sql, tenant_id)

        return GeneratedSQLDTO(
            raw_query=query,
            sql=cleaned_sql,
            explanation=f"Generated SQL for query: '{query}'",
            confidence_score=0.95,
        )

    def _clean_sql(self, sql: str, tenant_id: str) -> str:
        """Strip markdown fences and clean up formatting."""
        sql = sql.strip()
        # Remove markdown code fences
        if "```" in sql:
            sql = re.sub(r"```[a-zA-Z]*\n?", "", sql)
            sql = sql.replace("```", "")
        sql = sql.strip()
        if sql.endswith(";"):
            sql = sql[:-1].strip()

        # Enforce tenant_id filtering if missing in table queries
        if "tenant_id" not in sql.lower():
            if "where" in sql.lower():
                sql = re.sub(r"(?i)\bWHERE\b", f"WHERE tenant_id = '{tenant_id}' AND ", sql, count=1)
            else:
                # Append WHERE tenant_id = '...' before ORDER BY / GROUP BY / LIMIT
                m = re.search(r"(?i)\b(GROUP BY|ORDER BY|LIMIT)\b", sql)
                if m:
                    idx = m.start()
                    sql = f"{sql[:idx]} WHERE tenant_id = '{tenant_id}' {sql[idx:]}"
                else:
                    sql = f"{sql} WHERE tenant_id = '{tenant_id}'"

        return sql

    def _call_llm(self, sys_prompt: str, user_prompt: str, original_query: str, tenant_id: str) -> str:
        """Attempts calling Groq API -> Gemini API -> Smart Rule Fallback."""
        groq_key = os.getenv("GROQ_API_KEY", "")
        gemini_key = os.getenv("GEMINI_API_KEY", "")

        # 1. Try Groq API if key present
        if groq_key and groq_key != "your_groq_api_key_here":
            try:
                res = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={
                        "model": "llama-3.1-8b-instant",
                        "messages": [
                            {"role": "system", "content": sys_prompt},
                            {"role": "user", "content": user_prompt},
                        ],
                        "temperature": 0.1,
                    },
                    timeout=10,
                )
                if res.status_code == 200:
                    output = res.json()["choices"][0]["message"]["content"]
                    logger.info("Successfully generated SQL using Groq API")
                    return output
            except Exception as e:
                logger.warning(f"Groq API call failed: {e}")

        # 2. Try Gemini API if key present
        if gemini_key and gemini_key != "your_google_ai_studio_key_here":
            try:
                from google import genai
                client = genai.Client(api_key=gemini_key)
                resp = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=f"{sys_prompt}\n\n{user_prompt}",
                )
                if resp and resp.text:
                    logger.info("Successfully generated SQL using Gemini API")
                    return resp.text
            except Exception as e:
                logger.warning(f"Gemini API call failed: {e}")

        # 3. Rule-based Fallback Heuristic Generator for common queries
        logger.info("Using heuristic rule-based SQL generator fallback")
        return self._rule_based_fallback(original_query, tenant_id)

    def _rule_based_fallback(self, query: str, tenant_id: str) -> str:
        """Deterministic heuristic fallback for demo analytics queries."""
        q = query.lower()

        # "How many students were absent in Class 10-A?" or "How many students are in Class 10-A?"
        if "how many students" in q or "count of students" in q or "number of students" in q:
            if "absent" in q:
                if "10-a" in q:
                    return f"SELECT count(a.id) as absent_count FROM attendance_records a JOIN class_sections c ON a.class_section_id = c.id WHERE a.tenant_id = '{tenant_id}' AND c.display_name = 'Class 10-A' AND a.status = 'A'"
                elif "10-b" in q:
                    return f"SELECT count(a.id) as absent_count FROM attendance_records a JOIN class_sections c ON a.class_section_id = c.id WHERE a.tenant_id = '{tenant_id}' AND c.display_name = 'Class 10-B' AND a.status = 'A'"
                return f"SELECT count(id) as absent_count FROM attendance_records WHERE tenant_id = '{tenant_id}' AND status = 'A'"
            
            if "10-a" in q:
                return f"SELECT count(s.id) as student_count FROM students s JOIN class_sections c ON s.class_section_id = c.id WHERE s.tenant_id = '{tenant_id}' AND c.display_name = 'Class 10-A'"
            elif "10-b" in q:
                return f"SELECT count(s.id) as student_count FROM students s JOIN class_sections c ON s.class_section_id = c.id WHERE s.tenant_id = '{tenant_id}' AND c.display_name = 'Class 10-B'"
            return f"SELECT count(id) as student_count FROM students WHERE tenant_id = '{tenant_id}'"

        if "overdue" in q or "unpaid" in q:
            return f"SELECT s.full_name, c.display_name as section, f.fee_head_name, f.amount_due, f.due_date, f.status FROM fee_invoices f JOIN students s ON f.student_id = s.id JOIN class_sections c ON s.class_section_id = c.id WHERE f.tenant_id = '{tenant_id}' AND f.status = 'OVERDUE'"

        if "fee" in q or "invoice" in q:
            return f"SELECT status, count(*) as count, sum(amount_due) as total_billed, sum(amount_paid) as total_paid FROM fee_invoices WHERE tenant_id = '{tenant_id}' GROUP BY status"

        if "attendance" in q or "absent" in q:
            return f"SELECT status, count(*) as count FROM attendance_records WHERE tenant_id = '{tenant_id}' GROUP BY status"

        # Default fallback
        return f"SELECT s.roll_number, s.full_name, c.display_name as section FROM students s JOIN class_sections c ON s.class_section_id = c.id WHERE s.tenant_id = '{tenant_id}' LIMIT 10"
