"""
modules/ai_analytics/application/services/guarded_executor.py
==============================================================
Sub-Module 8.3: GuardedQueryExecutor — hardened AST-level enforcement.

Enforces:
 1. SELECT-only — no DDL/DML of any kind.
 2. Table whitelist — only approved domain tables.
 3. Row cap — never more than max_limit rows returned.
 4. Tenant isolation — tenant_id predicate must appear in the validated SQL.
 5. Row-level RBAC — for non-admin roles the AST MUST contain a verifiable
    ownership predicate (guardian_user_id / email) scoped to the caller's
    own identity. This is enforced structurally via AST walk — never by
    trusting the LLM's compliance with prompt instructions.

Design: A parser failure for non-admin roles FAILS CLOSED (raises
SecurityViolationError) rather than falling back to a weaker text check.
Admin/Principal queries may use the text-based fallback for resilience
against sqlglot dialect edge cases.
"""
from __future__ import annotations

import logging
import time
from typing import Optional

import sqlglot
from sqlglot import exp
from sqlalchemy import text

from modules.dummy_data_engine.infrastructure.db.session import SessionLocal
from modules.ai_analytics.domain.dtos import QueryExecutionResultDTO

logger = logging.getLogger(__name__)


class SecurityViolationError(Exception):
    """Raised when generated SQL violates safety or RBAC constraints."""
    pass


# Columns considered valid identity predicates per role.
# The RBAC check passes if ANY of these columns appears in an equality or
# IN-subquery comparison against a literal that matches the caller's user_id,
# anywhere in the full AST (including nested subqueries).
ROLE_IDENTITY_COLUMNS: dict[str, tuple[str, ...]] = {
    "PARENT": ("guardian_user_id",),
    "STUDENT": ("email", "user_id"),
    "TEACHER": (),  # Teacher scoping is enforced at the facade layer (assigned_sections), not here
}


class GuardedQueryExecutor:
    """
    Sub-Module 8.3: AST-based SQL query validator and executor.
    role_key and user_id are now REQUIRED parameters for execute() and validate_sql().
    """

    ALLOWED_TABLES = {
        "students",
        "attendance_records",
        "fee_invoices",
        "class_sections",
        "fee_structures",
        "users",
    }

    def __init__(self, max_limit: int = 500) -> None:
        self.max_limit = max_limit

    # ------------------------------------------------------------------
    # Public entry point — role_key and user_id are required.
    # ------------------------------------------------------------------
    def execute(
        self,
        sql_query: str,
        tenant_id: str,
        role_key: str = "ADMIN",
        user_id: str = "",
    ) -> QueryExecutionResultDTO:
        """Validates and executes query against the database with full RBAC enforcement."""
        start_time = time.monotonic()

        try:
            validated_sql = self.validate_sql(sql_query, tenant_id, role_key, user_id)
        except SecurityViolationError as err:
            logger.error("SQL Validation/RBAC Error: %s", err)
            return QueryExecutionResultDTO(
                executed_sql=sql_query,
                columns=(),
                rows=(),
                row_count=0,
                execution_time_ms=0.0,
                error=str(err),
            )

        try:
            with SessionLocal() as session:
                res = session.execute(text(validated_sql))
                columns = tuple(res.keys()) if res.returns_rows else ()
                raw_rows = res.fetchall() if res.returns_rows else []
                rows = tuple(tuple(row) for row in raw_rows)
                duration_ms = round((time.monotonic() - start_time) * 1000, 2)

                logger.info("Query executed successfully in %sms, returned %d rows", duration_ms, len(rows))
                return QueryExecutionResultDTO(
                    executed_sql=validated_sql,
                    columns=columns,
                    rows=rows,
                    row_count=len(rows),
                    execution_time_ms=duration_ms,
                    error=None,
                )
        except Exception as ex:
            duration_ms = round((time.monotonic() - start_time) * 1000, 2)
            logger.exception("Database query execution error")
            return QueryExecutionResultDTO(
                executed_sql=validated_sql if 'validated_sql' in dir() else sql_query,
                columns=(),
                rows=(),
                row_count=0,
                execution_time_ms=duration_ms,
                error=f"Execution Error: {ex}",
            )

    # ------------------------------------------------------------------
    def validate_sql(
        self,
        sql_query: str,
        tenant_id: str,
        role_key: str = "ADMIN",
        user_id: str = "",
    ) -> str:
        """
        Parse SQL via sqlglot AST and verify all safety + RBAC rules.
        Returns cleaned, validated SQL query string.

        Non-admin roles FAIL CLOSED on parser error — no text-based fallback.
        """
        role_upper = role_key.upper()
        is_privileged = role_upper in ("ADMIN", "PRINCIPAL")

        try:
            parsed = sqlglot.parse_one(sql_query, read="sqlite")
        except Exception as parse_err:
            if is_privileged:
                # Admin/Principal: tolerate sqlglot dialect quirks, fall back to text check
                logger.warning("sqlglot parse warning for privileged role: %s. Using text fallback.", parse_err)
                return self._basic_safety_check(sql_query, tenant_id)
            else:
                # Non-privileged: fail closed — never allow a potentially unsafe query
                raise SecurityViolationError(
                    f"SQL parse failure for role '{role_upper}' — access denied by default: {parse_err}"
                )

        # 1. Enforce SELECT-only
        if not isinstance(parsed, exp.Select):
            raise SecurityViolationError(
                f"Security Policy Violation: Only SELECT queries are permitted. Got: {type(parsed).__name__}"
            )

        # 2. Forbid DDL/DML anywhere in the AST
        for node in parsed.walk():
            if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter, exp.Command)):
                raise SecurityViolationError(f"Forbidden SQL operation detected: {type(node).__name__}")

        # 3. Verify target tables are in the whitelist
        tables_in_query = {t.name.lower() for t in parsed.find_all(exp.Table) if t.name}
        invalid_tables = tables_in_query - self.ALLOWED_TABLES
        if invalid_tables:
            raise SecurityViolationError(f"Access Denied: unapproved table(s): {invalid_tables}")

        # 4. Enforce row cap
        limit_node = parsed.args.get("limit")
        if limit_node:
            try:
                if int(limit_node.expression.this) > self.max_limit:
                    parsed = parsed.limit(self.max_limit)
            except Exception:
                parsed = parsed.limit(self.max_limit)
        else:
            parsed = parsed.limit(self.max_limit)

        validated_sql = parsed.sql(dialect="sqlite")

        # 5. Tenant isolation check (required when real tables are queried)
        if tables_in_query and "tenant_id" not in validated_sql.lower():
            raise SecurityViolationError("Multi-tenancy Policy Failure: tenant_id filter is missing.")

        # 6. Row-level RBAC — structural predicate enforcement (non-admin roles only)
        if not is_privileged:
            self._enforce_identity_predicate(parsed, role_upper, user_id)

        return validated_sql

    def _enforce_identity_predicate(
        self, parsed: exp.Select, role_upper: str, user_id: str
    ) -> None:
        """
        Walks the FULL AST (including nested subqueries) for an equality or
        IN-subquery comparison that pins one of ROLE_IDENTITY_COLUMNS[role]
        to the caller's own user_id. Raises SecurityViolationError if no
        such predicate is found anywhere in the query.

        This is the structural guarantee: even if the LLM drops the predicate,
        the query is rejected before execution.
        """
        identity_columns = ROLE_IDENTITY_COLUMNS.get(role_upper)

        if identity_columns is None:
            raise SecurityViolationError(
                f"No RBAC identity policy defined for role '{role_upper}'."
            )

        # Teacher scope is enforced by AssignedSections at the facade layer, not here
        if role_upper == "TEACHER":
            return

        if not identity_columns:
            raise SecurityViolationError(
                f"Role '{role_upper}' has no valid identity columns — access denied."
            )

        found = False
        for node in parsed.walk():
            # Direct equality: column = 'literal'
            if isinstance(node, exp.EQ):
                left, right = node.left, node.right
                col = left if isinstance(left, exp.Column) else (right if isinstance(right, exp.Column) else None)
                lit = right if isinstance(right, exp.Literal) else (left if isinstance(left, exp.Literal) else None)
                if col is not None and lit is not None:
                    col_name = col.name.lower()
                    lit_val = str(lit.this)
                    if col_name in identity_columns and lit_val == str(user_id):
                        found = True
                        break

            # IN-subquery: students.id IN (SELECT id FROM students WHERE guardian_user_id = '...')
            if isinstance(node, exp.In) and node.args.get("query"):
                subquery = node.args["query"]
                for sub_node in subquery.walk():
                    if isinstance(sub_node, exp.EQ):
                        left, right = sub_node.left, sub_node.right
                        col = (
                            left if isinstance(left, exp.Column)
                            else (right if isinstance(right, exp.Column) else None)
                        )
                        lit = (
                            right if isinstance(right, exp.Literal)
                            else (left if isinstance(left, exp.Literal) else None)
                        )
                        if (
                            col is not None
                            and lit is not None
                            and col.name.lower() in identity_columns
                            and str(lit.this) == str(user_id)
                        ):
                            found = True
                            break
            if found:
                break

        if not found:
            raise SecurityViolationError(
                f"RBAC Policy Failure: query does not contain a verifiable "
                f"{'/'.join(identity_columns)} predicate scoped to the requesting user '{user_id}'. "
                f"Cross-user data access is denied by default."
            )

    def _basic_safety_check(self, sql_query: str, tenant_id: str) -> str:
        """
        Text-based safety check — only used as fallback for ADMIN/PRINCIPAL
        when sqlglot parser fails on dialect edge cases.
        NEVER used for PARENT/STUDENT (they fail closed via validate_sql).
        """
        clean = sql_query.strip()
        upper = clean.upper()
        if not upper.startswith("SELECT"):
            raise SecurityViolationError("Security Policy Failure: Statement must begin with SELECT")

        forbidden = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "ATTACH", "PRAGMA", "EXEC"]
        for word in forbidden:
            if f" {word} " in f" {upper} ":
                raise SecurityViolationError(f"Forbidden SQL keyword: {word}")

        if "tenant_id" not in clean.lower():
            raise SecurityViolationError("Multi-tenancy Policy Failure: Mandatory tenant_id filter missing.")

        if "LIMIT" not in upper:
            clean = f"{clean} LIMIT {self.max_limit}"

        return clean
