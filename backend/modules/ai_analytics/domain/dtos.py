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
class ChatTurnDTO(BaseDTO):
    """
    A single turn in a multi-turn conversation.

    role    : 'user' | 'assistant'
    content : the raw question the user asked, or the summary the assistant returned.
    sql     : (optional) the SQL that was executed for this turn — used so the LLM
              can carry forward filters from previous turns.
    """
    role: str           # 'user' | 'assistant'
    content: str        # question text or answer summary
    sql: Optional[str] = None  # generated SQL (assistant turns only)


@dataclass(frozen=True, slots=True)
class NLQueryRequestDTO(BaseDTO):
    """User natural language query input."""
    query: str
    tenant_id: str
    user_role: str = "admin"
    current_user_id: str = ""
    current_role_key: str = "ADMIN"
    limit: int = 500
    # Multi-turn conversation history (oldest → newest, up to last 6 turns)
    chat_history: tuple[ChatTurnDTO, ...] = field(default_factory=tuple)
    # Debug mode — returns generated SQL/timing in response (dev environment only)
    debug_mode: bool = True


@dataclass(frozen=True, slots=True)
class GeneratedSQLDTO(BaseDTO):
    """SQL string translated by LLM engine, with local interpolation templates."""
    raw_query: str
    sql: str
    explanation: str
    confidence_score: float = 1.0
    # LLM-proposed phrasing templates for local Python interpolation (Section 3.2)
    single_result_template: str = ""   # used when query returns exactly 1 row
    multi_result_template: str = ""    # used when query returns > 1 rows
    zero_result_template: str = ""     # used when query returns 0 rows


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
    execution_time_ms: float = 0.0
