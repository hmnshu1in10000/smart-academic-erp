"""
modules/ai_analytics/api/views.py — Module 8.0
================================================
POST /api/v1/ai-analytics/ask — Conversational AI Text-to-SQL Analytics Endpoint

Security changes (correction.md §1.4, §4.2, §4.3):
- tenant_id is NEVER taken from the request body — always from verified JWT.
- debug_mode: effective only when ENVIRONMENT == "development" server-side.
- Generated SQL, explanation, raw_data_table, and execution timing are returned
  ONLY when effective_debug is True — hidden from non-dev environments automatically.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from shared_kernel.auth.jwt_utils import TokenPayload, get_current_tenant_context
from modules.ai_analytics.domain.dtos import NLQueryRequestDTO, ChatTurnDTO
from modules.ai_analytics.application.services.analytics_facade import ConversationalAnalyticsFacade
from config.settings.base import ENVIRONMENT

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai-analytics", tags=["AI Analytics"])


# ── Request / Response Models ──────────────────────────────────────────────────

class ChatTurnPayload(BaseModel):
    """A single conversation turn sent by the client."""
    role: str = Field(..., example="user", description="'user' or 'assistant'")
    content: str = Field(..., description="The question or answer text for this turn")
    sql: Optional[str] = Field(None, description="Executed SQL from assistant turn (helps context resolution)")


class AskQueryRequest(BaseModel):
    query: str = Field(
        ...,
        example="How many students are in Class 10-A?",
        description="Natural language question",
    )
    # accepted for schema compatibility, NEVER read for security (correction.md §1.4)
    tenant_id: Optional[str] = Field(
        None,
        description="Ignored — tenant is always derived from the verified JWT claim.",
    )
    chat_history: list[ChatTurnPayload] = Field(
        default_factory=list,
        description="Previous conversation turns (oldest→newest, up to 6) for multi-turn context",
    )
    debug_mode: bool = Field(
        True,
        description=(
            "Include raw SQL and timing in response. "
            "Effective only when ENVIRONMENT == 'development' server-side (correction.md §4.3)."
        ),
    )


class AskQueryResponse(BaseModel):
    question: str
    summary_answer: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    error: Optional[str] = None
    # Populated ONLY when effective_debug is True (development environment):
    generated_sql: Optional[str] = None
    explanation: Optional[str] = None
    raw_data_table: Optional[dict] = None      # {"columns": [...], "rows": [[...]]}
    execution_time_ms: Optional[float] = None


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post(
    "/ask",
    response_model=AskQueryResponse,
    summary="Ask AI analytics question",
    description=(
        "Translates natural language questions into secure, read-only SQL queries, "
        "executes them against the backend database with strict AST guardrails, and returns "
        "structured data alongside a human-readable summary answer. "
        "Supports multi-turn conversation history for contextual follow-up queries. "
        "tenant_id is always derived from the verified JWT — never from the request body."
    ),
)
async def ask_analytics(
    body: AskQueryRequest,
    token: TokenPayload = Depends(get_current_tenant_context),
) -> AskQueryResponse:
    # SECURITY: tenant_id is NEVER taken from the request body (correction.md §1.4)
    tenant_id = token.tenant_id

    # Debug mode only active when the server is running in development (correction.md §4.3)
    effective_debug: bool = body.debug_mode and ENVIRONMENT == "development"

    facade = ConversationalAnalyticsFacade()

    # Convert Pydantic ChatTurnPayload → frozen ChatTurnDTO
    history_dtos = tuple(
        ChatTurnDTO(role=t.role, content=t.content, sql=t.sql)
        for t in (body.chat_history or [])
    )

    req_dto = NLQueryRequestDTO(
        query=body.query,
        tenant_id=tenant_id,
        user_role=token.role,
        current_user_id=token.sub,
        current_role_key=token.role.upper(),
        chat_history=history_dtos,
        debug_mode=effective_debug,
    )

    ans_dto = facade.ask(req_dto)

    return AskQueryResponse(
        question=ans_dto.question,
        summary_answer=ans_dto.summary_answer,
        columns=list(ans_dto.columns),
        rows=[list(r) for r in ans_dto.rows],
        row_count=ans_dto.row_count,
        error=ans_dto.error,
        # Debug-only fields — None outside development:
        generated_sql=ans_dto.generated_sql if effective_debug else None,
        explanation=ans_dto.explanation if effective_debug else None,
        raw_data_table=(
            {"columns": list(ans_dto.columns), "rows": [list(r) for r in ans_dto.rows]}
            if effective_debug else None
        ),
        execution_time_ms=ans_dto.execution_time_ms if effective_debug else None,
    )
