"""
modules/ai_analytics/application/services/guarded_executor.py
==============================================================
Sub-Module 8.3: GuardedQueryExecutor
Uses `sqlglot` AST validation to enforce:
1. ONLY SELECT statements allowed (no INSERT/UPDATE/DELETE/DROP/ALTER/CREATE/PRAGMA).
2. Mandatory tenant_id filter present.
3. Enforces a maximum result cap (default 500 rows).
4. Executes read-only against the database using SQLAlchemy text.
"""
from __future__ import annotations

import logging
import time
from typing import Any, Optional
import sqlglot
from sqlglot import exp
from sqlalchemy import text

from modules.dummy_data_engine.infrastructure.db.session import SessionLocal
from modules.ai_analytics.domain.dtos import QueryExecutionResultDTO

logger = logging.getLogger(__name__)


class SecurityViolationError(Exception):
    """Raised when generated SQL violates safety constraints."""
    pass


class GuardedQueryExecutor:
    """
    Sub-Module 8.3: AST-based SQL query validator and executor.
    """

    ALLOWED_TABLES = {
        "students",
        "attendance_records",
        "fee_invoices",
        "class_sections",
        "fee_structures",
    }

    def __init__(self, max_limit: int = 500) -> None:
        self.max_limit = max_limit

    def validate_sql(self, sql_query: str, tenant_id: str) -> str:
        """
        Parses SQL via sqlglot AST and verifies safety rules.
        Returns cleaned, validated SQL query.
        """
        try:
            parsed = sqlglot.parse_one(sql_query, read="sqlite")
        except Exception as e:
            # Fallback check if parsing fails on simple dialect constructs
            logger.warning(f"sqlglot parse warning: {e}. Fallback to basic AST check.")
            return self._basic_safety_check(sql_query, tenant_id)

        # 1. Enforce SELECT type only
        if not isinstance(parsed, exp.Select):
            raise SecurityViolationError(f"Security Policy Violation: Only SELECT queries are permitted. Got: {type(parsed).__name__}")

        # 2. Check forbidden expressions in AST
        for node in parsed.walk():
            if isinstance(node, (exp.Insert, exp.Update, exp.Delete, exp.Drop, exp.Create, exp.Alter, exp.Command)):
                raise SecurityViolationError(f"Forbidden SQL operation detected: {type(node).__name__}")

        # 3. Verify target tables are in whitelist
        tables_in_query = {t.name.lower() for t in parsed.find_all(exp.Table) if t.name}
        invalid_tables = tables_in_query - self.ALLOWED_TABLES
        if invalid_tables:
            raise SecurityViolationError(f"Access Denied: Query attempts to read unapproved table(s): {invalid_tables}")

        # 4. Enforce row limit cap in AST
        limit_node = parsed.args.get("limit")
        if limit_node:
            try:
                val = int(limit_node.expression.this)
                if val > self.max_limit:
                    parsed = parsed.limit(self.max_limit)
            except Exception:
                parsed = parsed.limit(self.max_limit)
        else:
            parsed = parsed.limit(self.max_limit)

        validated_sql = parsed.sql(dialect="sqlite")

        # 5. Ensure tenant_id filter exists in query text
        if "tenant_id" not in validated_sql.lower():
            raise SecurityViolationError("Multi-tenancy Policy Failure: Mandatory tenant_id filter is missing.")

        return validated_sql

    def _basic_safety_check(self, sql_query: str, tenant_id: str) -> str:
        """Basic text-based safety validation if parser fails."""
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

    def execute(self, sql_query: str, tenant_id: str) -> QueryExecutionResultDTO:
        """Validates and executes query against backend/db.sqlite3."""
        start_time = time.monotonic()

        try:
            validated_sql = self.validate_sql(sql_query, tenant_id)
        except SecurityViolationError as err:
            logger.error(f"SQL Validation Error: {err}")
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

                logger.info(f"Query executed successfully in {duration_ms}ms, returned {len(rows)} rows")
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
                executed_sql=validated_sql,
                columns=(),
                rows=(),
                row_count=0,
                execution_time_ms=duration_ms,
                error=f"Execution Error: {str(ex)}",
            )
