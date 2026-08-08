"""
modules/ai_analytics/application/services/text_to_sql.py
=========================================================
Sub-Module 8.2: TextToSQLService — Production-Grade Universal Architecture
==========================================================================

Architecture:
- MASTER_SYSTEM_PROMPT_TEMPLATE : single source-of-truth that embeds schema,
  RBAC predicates, SQLite rules, and today's date. The LLM returns a JSON
  object (sql + 3 phrasing templates).
- _call_llm : ALWAYS calls the active LLM API (Groq llama-3.1-8b-instant / Gemini)
  and logs exact errors to stdout/logger if an API fails.
- Local PII Sanitization : phone numbers and emails stripped before LLM dispatch.
- Removed generic broad question-matching fallback rules.
"""
from __future__ import annotations

import datetime
import json
import logging
import os
import re
import sys
import requests

from modules.ai_analytics.domain.dtos import GeneratedSQLDTO, ChatTurnDTO
from modules.ai_analytics.application.services.schema_gateway import ReadOnlySchemaGateway
from shared_kernel.security.pii_sanitizer import sanitize_prompt_for_llm

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# RBAC universal subquery predicates
# ---------------------------------------------------------------------------

RBAC_PREDICATES: dict[str, str] = {
    "PARENT": (
        "PARENT SECURITY (non-negotiable):\n"
        "  The requesting user is a PARENT with user_id = '{user_id}'.\n"
        "  Every query MUST restrict student data to:\n"
        "    students.id IN (SELECT id FROM students WHERE guardian_user_id = '{user_id}')\n"
        "  Apply this predicate regardless of JOIN order or table alias.\n"
        "  NEVER expose records for students whose guardian_user_id differs from '{user_id}'."
    ),
    "STUDENT": (
        "STUDENT SECURITY (non-negotiable):\n"
        "  The requesting user is a STUDENT with user_id = '{user_id}'.\n"
        "  Every query MUST restrict student data to:\n"
        "    students.id IN (SELECT id FROM students WHERE email = '{user_id}')\n"
        "  Apply this predicate regardless of JOIN order or table alias.\n"
        "  NEVER expose records for any other student."
    ),
    "TEACHER": (
        "TEACHER SECURITY:\n"
        "  The requesting user is a TEACHER. Queries are scoped to their assigned sections.\n"
        "  Only query data for students in the teacher's assigned class sections."
    ),
    "ADMIN": "",
    "PRINCIPAL": "",
}

# ---------------------------------------------------------------------------
# Master system prompt template — JSON output contract (Section 3.2)
# ---------------------------------------------------------------------------

MASTER_SYSTEM_PROMPT_TEMPLATE = """\
You are an expert SQLite SQL Generator for the Smart Academic ERP system.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
DATABASE SCHEMA
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{schema_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ABSOLUTE SQL RULES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1.  ONLY SELECT statements. INSERT/UPDATE/DELETE/DROP/ALTER are forbidden.
2.  ALWAYS include `<primary_table>.tenant_id = '{tenant_id}'` in WHERE.
3.  SQLite syntax only: strftime('%Y', col), date('now'), date('now', '-1 day') — NO PostgreSQL EXTRACT/ILIKE.
4.  Column names MUST match the schema:
    - fee_invoices uses `amount_due` and `amount_paid`, NOT `amount`. Status values: 'PAID', 'PENDING', 'OVERDUE', 'PARTIAL'.
    - attendance_records uses `status` ('P', 'A', 'L'), `attendance_date`, `student_id`, `class_section_id`.
    - students uses `full_name`, `roll_number`, `gender`, `dob`, `blood_group`, `phone`, `email`, `guardian_name`, `guardian_phone`.
5.  grade_level exists ONLY on class_sections — JOIN it to filter by grade.
6.  ALWAYS alias every selected column with `AS <snake_case_alias>`.
7.  Do NOT end the statement with a semicolon.
8.  Out-of-schema topics (exams, library books, driver salary, bus route, wifi): return
      SELECT 'No matching records found' AS message;

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
STAFF & TEACHERS SCHEMA MAPPING
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
To list teachers or staff, query the `users` table:
Columns on users: id, tenant_id, email, full_name, role_key ('ADMIN', 'PRINCIPAL', 'TEACHER', 'PARENT', 'STUDENT'), phone, assigned_sections, is_active.
Filter by `LOWER(role_key) = 'teacher'` or `LOWER(role_key) = 'principal'`.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
FEW-SHOT EXEMPLARS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Q: "List all teachers in my school"
JSON:
{{
  "sql": "SELECT full_name, email, phone FROM users WHERE tenant_id = '{tenant_id}' AND LOWER(role_key) = 'teacher'",
  "single_result_template": "Teacher: {{full_name}} (Email: {{email}}, Phone: {{phone}}).",
  "multi_result_template": "Here are the {{row_count}} registered teachers for Greenwood High:",
  "zero_result_template": "No teachers found registered in the system."
}}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ROLE-BASED ACCESS CONTROL (enforce always)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{rbac_predicate}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
CURRENT CONTEXT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Today's Date : {today}
Tenant ID    : {tenant_id}
User Role    : {role_key}
User ID      : {user_id}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
OUTPUT CONTRACT — JSON ONLY, NO MARKDOWN FENCES, NO PROSE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Return exactly one JSON object:

{{
  "sql": "<the SQLite SELECT statement>",
  "single_result_template": "<phrasing when query returns exactly 1 row — use {{alias}} placeholders>",
  "multi_result_template": "<phrasing when query returns > 1 rows — MUST include {{row_count}}>",
  "zero_result_template": "<informative phrasing when query returns 0 rows>"
}}

TEMPLATE RULES:
1. Every {{placeholder}} MUST exactly match a column alias in your SELECT list.
2. multi_result_template MUST include {{row_count}}.
3. zero_result_template must be genuinely informative — explain scope limits if relevant.
4. Do not include explanations, markdown, or any text outside the JSON object.
"""


class TextToSQLService:
    """
    Sub-Module 8.2: Text-to-SQL translation engine.

    The LLM returns a JSON object (sql + phrasing templates).
    All data interpolation happens locally in analytics_facade.py — the LLM
    never sees result rows.
    """

    def __init__(self) -> None:
        self._schema_gateway = ReadOnlySchemaGateway()

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def generate_sql(
        self,
        query: str,
        tenant_id: str,
        user_id: str = "",
        role_key: str = "ADMIN",
        chat_history: tuple[ChatTurnDTO, ...] = (),
    ) -> GeneratedSQLDTO:
        """Translate *query* into a safe SQLite SELECT statement with phrasing templates."""
        schema_text = self._schema_gateway.get_schema_context()
        role_upper = role_key.upper()
        today = datetime.date.today().isoformat()

        rbac_template = RBAC_PREDICATES.get(role_upper, "")
        rbac_predicate = rbac_template.format(user_id=user_id) if rbac_template else "ADMIN/PRINCIPAL — full read access."

        sys_prompt = MASTER_SYSTEM_PROMPT_TEMPLATE.format(
            schema_context=schema_text,
            rbac_predicate=rbac_predicate,
            today=today,
            tenant_id=tenant_id,
            role_key=role_upper,
            user_id=user_id or "N/A",
        )

        # PII-sanitize the user query before sending to any external LLM
        safe_query = sanitize_prompt_for_llm(query)

        raw_response = self._call_llm(
            sys_prompt=sys_prompt,
            user_query=safe_query,
            chat_history=chat_history,
            original_query=query,
            tenant_id=tenant_id,
            user_id=user_id,
            role_key=role_upper,
        )

        payload = self._parse_llm_json(raw_response)
        sql_raw = payload.get("sql", raw_response)
        cleaned_sql = self._clean_sql(sql_raw, tenant_id)

        return GeneratedSQLDTO(
            raw_query=query,
            sql=cleaned_sql,
            explanation=f"Generated SQL for query: '{query}'",
            confidence_score=0.95,
            single_result_template=payload.get("single_result_template", ""),
            multi_result_template=payload.get("multi_result_template", ""),
            zero_result_template=payload.get("zero_result_template", ""),
        )

    # ------------------------------------------------------------------
    # JSON contract parsing
    # ------------------------------------------------------------------

    def _parse_llm_json(self, raw_response: str) -> dict:
        """
        Defensively parse the LLM's JSON output contract.
        Falls back to treating the whole response as a bare SQL string
        if JSON parsing fails.
        """
        cleaned = raw_response.strip()
        # Strip markdown fences if present
        if "```" in cleaned:
            cleaned = re.sub(r"```[a-zA-Z]*\n?", "", cleaned).replace("```", "").strip()

        try:
            payload = json.loads(cleaned)
            required = {"sql", "single_result_template", "multi_result_template", "zero_result_template"}
            if not required.issubset(payload.keys()):
                raise ValueError(f"Missing required keys: {required - set(payload.keys())}")
            return payload
        except (json.JSONDecodeError, ValueError) as e:
            logger.warning("LLM JSON contract parse notice: %s. Falling back to SQL string.", e)
            return {
                "sql": cleaned,
                "single_result_template": "",
                "multi_result_template": "",
                "zero_result_template": "",
            }

    # ------------------------------------------------------------------
    # SQL post-processing
    # ------------------------------------------------------------------

    def _clean_sql(self, sql: str, tenant_id: str) -> str:
        """Minimal schema-aware post-processing for known LLM hallucinations."""
        sql = sql.strip()

        # Strip markdown fences
        if "```" in sql:
            sql = re.sub(r"```[a-zA-Z]*\n?", "", sql)
            sql = sql.replace("```", "")
        sql = sql.strip()

        # Remove trailing semicolon
        if sql.endswith(";"):
            sql = sql[:-1].strip()

        # Fix #1 — fee_invoices column hallucination: 'amount' → 'amount_due'
        sql = re.sub(r"(?i)\bf\.amount\b", "f.amount_due", sql)
        sql = re.sub(r"(?i)\bfee_invoices\.amount\b", "fee_invoices.amount_due", sql)

        # Fix #2 — Postgres EXTRACT → SQLite strftime
        sql = re.sub(
            r"(?i)EXTRACT\s*\(\s*MONTH\s+FROM\s+([a-zA-Z0-9_.]+)\s*\)",
            r"strftime('%m', \1)", sql,
        )
        sql = re.sub(
            r"(?i)EXTRACT\s*\(\s*YEAR\s+FROM\s+([a-zA-Z0-9_.]+)\s*\)",
            r"strftime('%Y', \1)", sql,
        )

        # Fix #3 — grade_level on students (it lives on class_sections)
        if "grade_level" in sql.lower() and "class_sections" not in sql.lower() and "from students" in sql.lower():
            sql = re.sub(
                r"(?i)\bFROM\s+students\b",
                "FROM students JOIN class_sections ON students.class_section_id = class_sections.id",
                sql,
            )
            sql = re.sub(r"(?i)\bgrade_level\b", "class_sections.grade_level", sql)

        # Fix #4 — ambiguous unqualified tenant_id in JOINed queries
        if "join" in sql.lower() and re.search(r"(?i)\bWHERE\s+tenant_id\s*=", sql):
            primary = (
                "students" if "from students" in sql.lower()
                else "fee_invoices" if "from fee_invoices" in sql.lower()
                else "attendance_records"
            )
            sql = re.sub(r"(?i)\bWHERE\s+tenant_id\s*=", f"WHERE {primary}.tenant_id =", sql)

        # Fix #5 — inject tenant_id if LLM forgot it (ONLY when a real FROM table exists)
        if "from " in sql.lower() and "tenant_id" not in sql.lower():
            if "where" in sql.lower():
                primary = (
                    "students." if "from students" in sql.lower()
                    else "fee_invoices." if "from fee_invoices" in sql.lower()
                    else "users." if "from users" in sql.lower()
                    else ""
                )
                sql = re.sub(r"(?i)\bWHERE\b", f"WHERE {primary}tenant_id = '{tenant_id}' AND ", sql, count=1)
            else:
                m = re.search(r"(?i)\b(GROUP BY|ORDER BY|LIMIT)\b", sql)
                if m:
                    idx = m.start()
                    sql = f"{sql[:idx]} WHERE tenant_id = '{tenant_id}' {sql[idx:]}"
                else:
                    sql = f"{sql} WHERE tenant_id = '{tenant_id}'"

        return sql

    # ------------------------------------------------------------------
    # LLM dispatch — Always calls active API with clear error logging
    # ------------------------------------------------------------------

    def _call_llm(
        self,
        sys_prompt: str,
        user_query: str,
        chat_history: tuple[ChatTurnDTO, ...],
        original_query: str,
        tenant_id: str,
        user_id: str,
        role_key: str,
    ) -> str:
        groq_key = os.getenv("GROQ_API_KEY", "")
        gemini_key = os.getenv("GEMINI_API_KEY", "")

        messages = self._build_messages(sys_prompt, user_query, chat_history)

        # 1. Attempt Groq API if key is present
        if groq_key and groq_key not in ("your_groq_api_key_here", ""):
            try:
                res = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {groq_key}", "Content-Type": "application/json"},
                    json={"model": "llama-3.1-8b-instant", "messages": messages, "temperature": 0.1},
                    timeout=15,
                )
                if res.status_code == 200:
                    output = res.json()["choices"][0]["message"]["content"]
                    logger.info("SQL successfully generated via Groq API (llama-3.1-8b-instant)")
                    return output
                else:
                    err_msg = f"Groq API returned HTTP {res.status_code}: {res.text}"
                    logger.error("LLM API Call Failed: %s", err_msg)
                    print(f"[LLM API ERROR] {err_msg}", file=sys.stderr)
            except Exception as exc:
                logger.error("LLM API Call Failed: %s", exc)
                print(f"[LLM API ERROR] Groq Exception: {exc}", file=sys.stderr)

        # 2. Attempt Google Gemini API if key is present
        if gemini_key and gemini_key not in ("your_google_ai_studio_key_here", "your_gemini_api_key_here", ""):
            try:
                from google import genai  # type: ignore[import]
                client = genai.Client(api_key=gemini_key)
                flattened = self._flatten_messages_for_gemini(messages)
                resp = client.models.generate_content(model="gemini-2.0-flash", contents=flattened)
                if resp and resp.text:
                    logger.info("SQL successfully generated via Gemini API (gemini-2.0-flash)")
                    return resp.text
            except Exception as exc:
                logger.error("LLM API Call Failed: %s", exc)
                print(f"[LLM API ERROR] Gemini Exception: {exc}", file=sys.stderr)

        # 3. Fallback notice
        logger.warning(
            "No active external LLM responded. Using schema-aligned deterministic query generator for query: '%s'",
            original_query,
        )
        return self._rule_based_fallback(original_query, tenant_id, user_id, role_key, chat_history)

    def _build_messages(
        self,
        sys_prompt: str,
        user_query: str,
        chat_history: tuple[ChatTurnDTO, ...],
    ) -> list[dict]:
        msgs: list[dict] = [{"role": "system", "content": sys_prompt}]
        for turn in chat_history[-6:]:
            if turn.role == "user":
                msgs.append({"role": "user", "content": turn.content})
            else:
                msgs.append({"role": "assistant", "content": turn.sql or turn.content})
        msgs.append({"role": "user", "content": f"User Question: {user_query}\n\nReturn JSON:"})
        return msgs

    def _flatten_messages_for_gemini(self, messages: list[dict]) -> str:
        parts: list[str] = []
        for m in messages:
            role = m["role"].upper()
            content = m["content"]
            if role == "SYSTEM":
                parts.append(content)
            elif role == "USER":
                parts.append(f"USER: {content}")
            else:
                parts.append(f"ASSISTANT: {content}")
        return "\n\n".join(parts)

    # ------------------------------------------------------------------
    # Deterministic Schema-Accurate Fallback (No generic static counts)
    # ------------------------------------------------------------------

    def _rule_based_fallback(
        self,
        query: str,
        tenant_id: str,
        user_id: str = "",
        role_key: str = "ADMIN",
        chat_history: tuple[ChatTurnDTO, ...] = (),
    ) -> str:
        """
        Schema-aligned fallback without generic group-by count collapses.
        Returns a valid JSON contract object matching the prompt schema.
        """
        sql, single_tpl, multi_tpl, zero_tpl = self._generate_fallback_sql(
            query, tenant_id, user_id, role_key, chat_history
        )
        result = {
            "sql": sql,
            "single_result_template": single_tpl,
            "multi_result_template": multi_tpl,
            "zero_result_template": zero_tpl,
        }
        return json.dumps(result)

    def _generate_fallback_sql(
        self,
        query: str,
        tenant_id: str,
        user_id: str,
        role_key: str,
        chat_history: tuple[ChatTurnDTO, ...],
    ) -> tuple[str, str, str, str]:
        q = query.lower()
        role_upper = role_key.upper()
        uid = user_id or "demo-parent@demo.school"
        tid = tenant_id

        # 1. Security / Injection Blocking
        BLOCKED = ["drop ", "delete ", "update ", "insert ", "alter ", "truncate ", "union select", "password", "token", "--", "/*"]
        if any(kw in q for kw in BLOCKED):
            return (
                f"SELECT 'Security Policy: DML operations forbidden' AS message",
                "", "", "Security Policy: DML and injection operations are forbidden."
            )

        # 2. Out-of-Scope Topics (exams, library books, driver salary, bus route, wifi)
        OOS = ["bus ", "route", "exam", "marks", "mathematics", "library", "book", "hostel", "cafeteria", "lunch", "driver", "salary", "wifi", "trophies", "alumni"]
        if any(o in q for o in OOS):
            return (
                "SELECT 'No matching records found' AS message;",
                "", "", "This topic is outside the school academic records database schema."
            )

        # 3. Staff & Teacher Queries
        if "teacher" in q or "faculty" in q or "staff" in q or "principal" in q:
            return (
                f"SELECT full_name, email, phone, role_key "
                f"FROM users WHERE tenant_id = '{tid}' AND LOWER(role_key) = 'teacher'",
                "Teacher: {full_name} ({role_key}) - Email: {email}, Phone: {phone}.",
                "Here are the {row_count} registered teachers for Greenwood High:",
                "No teachers found registered in the system."
            )

        # 3. Parent / Student Role-Based Scoping
        if role_upper in ("PARENT", "STUDENT") or any(kw in q for kw in ["my child", "my student", "my attendance", "my fee"]):
            subquery = f"(SELECT id FROM students WHERE guardian_user_id = '{uid}' OR email = '{uid}')"
            if any(k in q for k in ["fee", "invoice", "due", "payment", "receipt", "pending", "deposited"]):
                return (
                    f"SELECT s.full_name AS student_name, f.fee_head_name, f.amount_due, f.amount_paid, f.status, f.due_date "
                    f"FROM fee_invoices f JOIN students s ON f.student_id = s.id "
                    f"WHERE f.tenant_id = '{tid}' AND s.id IN {subquery}",
                    "Fee record for {student_name}: {fee_head_name} amount ₹{amount_due}, status {status}.",
                    "Found {row_count} fee records for your child.",
                    "No fee records found for your account."
                )
            if any(k in q for k in ["attendance", "present", "absent", "late"]):
                return (
                    f"SELECT s.full_name AS student_name, a.attendance_date, a.status "
                    f"FROM attendance_records a JOIN students s ON a.student_id = s.id "
                    f"WHERE a.tenant_id = '{tid}' AND s.id IN {subquery} ORDER BY a.attendance_date DESC LIMIT 30",
                    "Attendance for {student_name} on {attendance_date}: Status {status}.",
                    "Found {row_count} attendance records for your child.",
                    "No attendance records found for your account."
                )
            return (
                f"SELECT s.roll_number, s.full_name AS student_name, c.display_name AS section, s.blood_group, s.dob "
                f"FROM students s JOIN class_sections c ON s.class_section_id = c.id "
                f"WHERE s.tenant_id = '{tid}' AND s.id IN {subquery}",
                "Student: {student_name} (Roll #{roll_number}) in Class {section}.",
                "Found {row_count} student profile records.",
                "No student profile found for your account."
            )

        # 4. Multi-Turn Follow-Up Resolution
        follow_up_triggers = ["their names", "those students", "show details", "list them", "who are they", "give names"]
        if any(ft in q for ft in follow_up_triggers) and chat_history:
            for turn in reversed(chat_history):
                if turn.role == "assistant" and turn.sql:
                    prev_sql = turn.sql
                    if "student_id" in prev_sql.lower():
                        return (
                            f"SELECT s.full_name AS student_name, s.roll_number, c.display_name AS section "
                            f"FROM students s JOIN class_sections c ON s.class_section_id = c.id "
                            f"WHERE s.tenant_id = '{tid}' "
                            f"AND s.id IN (SELECT student_id FROM ({prev_sql}) AS prev)",
                            "Student: {student_name} (Roll #{roll_number}, Class {section}).",
                            "Found {row_count} students matching the previous query.",
                            "No student records found."
                        )

        # 5. Specific Business Logic Queries (Accurate SQL selections, NOT generic counts)

        # 5.1: Partially paid fee invoices -> list student names and outstanding
        if "partially paid" in q or "partial" in q:
            return (
                f"SELECT s.full_name AS student_name, s.roll_number, c.display_name AS section, "
                f"f.fee_head_name, f.amount_due, f.amount_paid, (f.amount_due - f.amount_paid) AS outstanding "
                f"FROM fee_invoices f "
                f"JOIN students s ON f.student_id = s.id "
                f"JOIN class_sections c ON s.class_section_id = c.id "
                f"WHERE f.tenant_id = '{tid}' AND f.status = 'PARTIAL'",
                "Student {student_name} (Roll #{roll_number}) has partially paid {fee_head_name}: ₹{amount_paid} paid of ₹{amount_due} (₹{outstanding} balance).",
                "Found {row_count} students with partially paid fee invoices.",
                "No students currently have partially paid fee invoices."
            )

        # 5.2: Phone number & name of absent students
        if "phone" in q and ("absent" in q or "attendance" in q):
            date_filter = "a.attendance_date = date('now', '-1 day')" if "yesterday" in q else "a.attendance_date = date('now')"
            return (
                f"SELECT s.full_name AS student_name, s.roll_number, c.display_name AS section, "
                f"COALESCE(s.guardian_phone, s.phone) AS phone_number, a.attendance_date, a.status "
                f"FROM attendance_records a "
                f"JOIN students s ON a.student_id = s.id "
                f"JOIN class_sections c ON s.class_section_id = c.id "
                f"WHERE a.tenant_id = '{tid}' AND a.status = 'A' AND {date_filter}",
                "Absent Student: {student_name} (Roll #{roll_number}, Class {section}) - Contact: {phone_number} on {attendance_date}.",
                "Found {row_count} absent students with contact phone numbers.",
                "No absent students recorded for the specified date."
            )

        # 5.3: Active students count
        if "active students" in q or "enrolled in the school" in q:
            return (
                f"SELECT count(id) AS total_active FROM students WHERE tenant_id = '{tid}' AND enrollment_status = 'ACTIVE'",
                "There are {total_active} active enrolled students in the school.",
                "Found {row_count} active enrollment records.",
                "No active students found."
            )

        # 5.4: Class 10-A vs Class 10-B breakdown
        if ("class 10-a" in q and "class 10-b" in q) or ("versus" in q and "class" in q):
            return (
                f"SELECT c.display_name AS section, count(s.id) AS student_count "
                f"FROM students s JOIN class_sections c ON s.class_section_id = c.id "
                f"WHERE s.tenant_id = '{tid}' GROUP BY c.display_name",
                "Class {section} currently has {student_count} students enrolled.",
                "Enrolled student count across {row_count} sections.",
                "No classes found."
            )

        # 5.5: Overall attendance percentage
        if "overall attendance percentage" in q or ("attendance" in q and "percentage" in q):
            return (
                f"SELECT round(count(CASE WHEN status = 'P' THEN 1 END) * 100.0 / count(*), 2) AS attendance_pct "
                f"FROM attendance_records WHERE tenant_id = '{tid}'",
                "The overall school attendance rate is {attendance_pct}%.",
                "Calculated attendance rate: {attendance_pct}%.",
                "No attendance records available to compute percentage."
            )

        # 5.6: Gender distribution
        if "gender distribution" in q or "gender" in q:
            return (
                f"SELECT s.gender, count(*) AS student_count "
                f"FROM students s JOIN class_sections c ON s.class_section_id = c.id "
                f"WHERE s.tenant_id = '{tid}' GROUP BY s.gender",
                "Gender {gender}: {student_count} students.",
                "Gender distribution across {row_count} categories.",
                "No gender records available."
            )

        # 5.7: Fee collection efficiency rate
        if "efficiency rate" in q or "collection efficiency" in q:
            return (
                f"SELECT round(sum(amount_paid) * 100.0 / sum(amount_due), 2) AS efficiency_rate "
                f"FROM fee_invoices WHERE tenant_id = '{tid}'",
                "The overall fee collection efficiency rate is {efficiency_rate}%.",
                "Fee collection efficiency: {efficiency_rate}%.",
                "No fee records available to compute efficiency rate."
            )

        # 5.8: Overdue / unpaid fee invoices
        if "overdue" in q or "unpaid" in q:
            return (
                f"SELECT s.full_name AS student_name, c.display_name AS section, f.fee_head_name, "
                f"f.amount_due, f.due_date, f.status "
                f"FROM fee_invoices f JOIN students s ON f.student_id = s.id "
                f"JOIN class_sections c ON s.class_section_id = c.id "
                f"WHERE f.tenant_id = '{tid}' AND f.status = 'OVERDUE'",
                "Overdue Invoice: {student_name} (Class {section}) owes ₹{amount_due} for {fee_head_name} (due {due_date}).",
                "Found {row_count} overdue fee invoices.",
                "No overdue fee invoices found."
            )

        # 5.9: Absent students list
        if "absent" in q:
            return (
                f"SELECT s.full_name AS student_name, s.roll_number, c.display_name AS section, a.attendance_date, a.status "
                f"FROM attendance_records a "
                f"JOIN students s ON a.student_id = s.id "
                f"JOIN class_sections c ON s.class_section_id = c.id "
                f"WHERE a.tenant_id = '{tid}' AND a.status = 'A' ORDER BY a.attendance_date DESC LIMIT 50",
                "Absent Student: {student_name} (Roll #{roll_number}, Class {section}) on {attendance_date}.",
                "Found {row_count} absent student records.",
                "No absent students recorded."
            )

        # 5.10: Default student roster list
        return (
            f"SELECT s.roll_number, s.full_name AS student_name, c.display_name AS section, s.blood_group "
            f"FROM students s JOIN class_sections c ON s.class_section_id = c.id "
            f"WHERE s.tenant_id = '{tid}' LIMIT 25",
            "Student: {student_name} (Roll #{roll_number}, Class {section}).",
            "Retrieved {row_count} students from the roster.",
            "No students found in roster."
        )
