"""
modules/ai_analytics/domain/dtos.py
===================================
DTO contracts for Module 8.0 AI Text-to-SQL Conversational Analytics Engine.
Source of truth: ARCHITECTURE.md §8.0
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional

from shared_kernel.contracts.base_dto import BaseDTO


@dataclass(frozen=True, slots=True)
class NLQueryRequestDTO(BaseDTO):
    """User natural language query input."""
    query: str
    tenant_id: str
    user_role: str = "admin"
    limit: int = 500


@dataclass(frozen=True, slots=True)
class GeneratedSQLDTO(BaseDTO):
    """SQL string translated by LLM engine."""
    raw_query: str
    sql: str
    explanation: str
    confidence_score: float = 1.0


@dataclass(frozen=True, slots=True)
class QueryExecutionResultDTO(BaseDTO):
    """Guarded execution result from DB."""
    executed_sql: str
    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]
    row_count: int
    execution_time_ms: float
    error: Optional[str] = None


@dataclass(frozen=True, slots=True)
class ConversationalAnswerDTO(BaseDTO):
    """Final answer presented back to user/client."""
    question: str
    generated_sql: str
    explanation: str
    columns: tuple[str, ...]
    rows: tuple[tuple[Any, ...], ...]
    row_count: int
    summary_answer: str
    error: Optional[str] = None
