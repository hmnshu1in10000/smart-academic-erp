"""
modules/ai_analytics/api/views.py — Module 8.0
================================================
POST /api/v1/ai-analytics/ask — Conversational AI Text-to-SQL Analytics Endpoint
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from shared_kernel.auth.jwt_utils import TokenPayload, get_current_tenant_context
from modules.ai_analytics.domain.dtos import NLQueryRequestDTO
from modules.ai_analytics.application.services.analytics_facade import ConversationalAnalyticsFacade

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/ai-analytics", tags=["AI Analytics"])


# ── Request / Response Models ──────────────────────────────────────────────────

class AskQueryRequest(BaseModel):
    query: str = Field(..., example="How many students are in Class 10-A?", description="Natural language question")
    tenant_id: Optional[str] = Field(None, example="greenwood-high-001", description="Tenant ID (defaults to JWT tenant)")


class AskQueryResponse(BaseModel):
    question: str
    generated_sql: str
    explanation: str
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    summary_answer: str
    error: Optional[str] = None


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post(
    "/ask",
    response_model=AskQueryResponse,
    summary="Ask AI analytics question",
    description=(
        "Translates natural language questions into secure, read-only SQL queries, "
        "executes them against the backend database with strict AST guardrails, and returns "
        "structured data alongside a human-readable summary answer."
    ),
)
async def ask_analytics(
    body: AskQueryRequest,
    token: TokenPayload = Depends(get_current_tenant_context),
) -> AskQueryResponse:
    tenant_id = body.tenant_id or token.tenant_id
    facade = ConversationalAnalyticsFacade()

    req_dto = NLQueryRequestDTO(
        query=body.query,
        tenant_id=tenant_id,
        user_role=token.role,
    )

    ans_dto = facade.ask(req_dto)

    return AskQueryResponse(
        question=ans_dto.question,
        generated_sql=ans_dto.generated_sql,
        explanation=ans_dto.explanation,
        columns=list(ans_dto.columns),
        rows=[list(r) for r in ans_dto.rows],
        row_count=ans_dto.row_count,
        summary_answer=ans_dto.summary_answer,
        error=ans_dto.error,
    )
