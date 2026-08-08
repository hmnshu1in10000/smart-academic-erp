"""
modules/ai_analytics/application/services/analytics_facade.py
==============================================================
Sub-Module 8.5: ConversationalAnalyticsFacade
Application facade coordinating TextToSQLService, GuardedQueryExecutor, and answer composition.
Source of truth: ARCHITECTURE.md §8.5 / correction.md §3.3

Key change (correction.md §3.3):
- All answer interpolation now happens LOCALLY in Python using templates
  proposed by the LLM at generation time.
- The LLM NEVER sees execution results (result rows never leave the process).
- _compose_summary is replaced by _interpolate_summary / _resolve_zero_result / _local_fallback_summary.
"""
from __future__ import annotations

import logging
from modules.ai_analytics.domain.dtos import (
    NLQueryRequestDTO,
    GeneratedSQLDTO,
    QueryExecutionResultDTO,
    ConversationalAnswerDTO,
)
from modules.ai_analytics.application.services.text_to_sql import TextToSQLService
from modules.ai_analytics.application.services.guarded_executor import GuardedQueryExecutor

logger = logging.getLogger(__name__)

# Hints for out-of-scope grade/class questions (correction.md §3.4)
OUT_OF_SCOPE_GRADE_HINTS = (
    "class 7", "class 8", "class 9",
    "grade 7", "grade 8", "grade 9",
    "7th", "8th", "9th", "11th", "12th",
)


class ConversationalAnalyticsFacade:
    """
    Sub-Module 8.5: Entry point facade for natural language conversational analytics.
    """

    def __init__(self) -> None:
        self._text_to_sql = TextToSQLService()
        self._executor = GuardedQueryExecutor(max_limit=500)

    def ask(self, request: NLQueryRequestDTO) -> ConversationalAnswerDTO:
        """Processes a natural language query end-to-end."""
        logger.info(
            "Processing AI analytics query for tenant '%s', role '%s': '%s'",
            request.tenant_id,
            request.current_role_key,
            request.query,
        )

        # 1. Translate question → SQL with phrasing templates (LLM outputs JSON)
        gen_sql_dto = self._text_to_sql.generate_sql(
            query=request.query,
            tenant_id=request.tenant_id,
            user_id=request.current_user_id or "",
            role_key=request.current_role_key or "ADMIN",
            chat_history=request.chat_history,
        )

        # 2. Execute with full AST-level guardrails (role_key + user_id now required)
        exec_result = self._executor.execute(
            gen_sql_dto.sql,
            request.tenant_id,
            role_key=request.current_role_key or "ADMIN",
            user_id=request.current_user_id or "",
        )

        # 3. Hard error path — surfaces SecurityViolationError or DB execution errors
        if exec_result.error:
            return ConversationalAnswerDTO(
                question=request.query,
                generated_sql=gen_sql_dto.sql,
                explanation=gen_sql_dto.explanation,
                columns=(),
                rows=(),
                row_count=0,
                summary_answer=f"Could not compute result: {exec_result.error}",
                error=exec_result.error,
                execution_time_ms=exec_result.execution_time_ms,
            )

        # 4. Local template interpolation — no LLM re-call, no data boundary crossing
        summary = self._interpolate_summary(gen_sql_dto, exec_result)

        return ConversationalAnswerDTO(
            question=request.query,
            generated_sql=exec_result.executed_sql,
            explanation=gen_sql_dto.explanation,
            columns=exec_result.columns,
            rows=exec_result.rows,
            row_count=exec_result.row_count,
            summary_answer=summary,
            error=None,
            execution_time_ms=exec_result.execution_time_ms,
        )

    # ------------------------------------------------------------------
    # Local template interpolation (correction.md §3.3)
    # ------------------------------------------------------------------

    def _interpolate_summary(
        self,
        gen_sql_dto: GeneratedSQLDTO,
        exec_result: QueryExecutionResultDTO,
    ) -> str:
        """
        Interpolate LLM-proposed templates with locally-fetched data.
        The LLM proposed the SHAPE of the sentence at generation time (before
        any query ran) and never sees the actual result values. All data
        binding happens here via pure Python str.format().
        """
        row_count = exec_result.row_count

        if row_count == 0:
            return self._resolve_zero_result(gen_sql_dto, exec_result)

        # Build bindings: column_alias → first_row_value + row_count
        bindings: dict = {}
        if exec_result.rows:
            bindings = dict(zip(exec_result.columns, exec_result.rows[0]))
        bindings["row_count"] = row_count

        template = (
            gen_sql_dto.single_result_template
            if row_count == 1
            else gen_sql_dto.multi_result_template
        )

        if not template:
            return self._local_fallback_summary(exec_result)

        try:
            return template.format(**bindings)
        except (KeyError, IndexError) as e:
            logger.warning("Template placeholder mismatch (%s) — using local fallback.", e)
            return self._local_fallback_summary(exec_result)

    def _resolve_zero_result(
        self,
        gen_sql_dto: GeneratedSQLDTO,
        exec_result: QueryExecutionResultDTO,
    ) -> str:
        """
        Return zero-result message. Tries the LLM-proposed template first,
        then falls back to deterministic hint detection.
        """
        if gen_sql_dto.zero_result_template:
            try:
                return gen_sql_dto.zero_result_template.format(row_count=0)
            except (KeyError, IndexError):
                pass  # fall through to deterministic fallback

        question_lower = gen_sql_dto.raw_query.lower()
        if any(hint in question_lower for hint in OUT_OF_SCOPE_GRADE_HINTS):
            return (
                "No records found. Greenwood High currently only has enrolled data "
                "for Grade 10 (Class 10-A and Class 10-B)."
            )
        return "No matching records found for your query."

    def _local_fallback_summary(self, exec_result: QueryExecutionResultDTO) -> str:
        """
        Deterministic fallback summary used when LLM template is absent or
        has a placeholder mismatch. Guaranteed safe — uses only local data.
        """
        columns, rows = exec_result.columns, exec_result.rows

        # Single-column aggregate (count / total)
        if len(columns) == 1 and any(k in columns[0].lower() for k in ("count", "total")):
            return f"Found {rows[0][0]} matching records."

        # Single row, multiple columns
        if len(rows) == 1 and len(columns) > 1:
            return "Result: " + ", ".join(f"{c}: {v}" for c, v in zip(columns, rows[0]))

        return f"Retrieved {len(rows)} record(s)."
