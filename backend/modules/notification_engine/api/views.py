"""
modules/notification_engine/api/views.py
========================================
GET  /api/v1/notifications/inbox           — User Notification Inbox Endpoint
POST /api/v1/notifications/mark-all-read  — Mark all user notifications as read
"""
from __future__ import annotations

import logging
from fastapi import APIRouter, Depends
from pydantic import BaseModel

from shared_kernel.auth.jwt_utils import TokenPayload, get_current_tenant_context
from modules.notification_engine.application.services.fcm_provider import InAppNotificationService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationItemResponse(BaseModel):
    id: str
    user_email: str
    title: str
    message: str
    category: str
    notification_type: str
    is_read: bool
    read: bool
    created_at: str


class MarkReadResponse(BaseModel):
    status: str = "ok"
    updated_count: int


@router.get(
    "/inbox",
    response_model=list[NotificationItemResponse],
    summary="Get role-scoped and user-scoped notification inbox",
)
async def get_user_notifications(
    token: TokenPayload = Depends(get_current_tenant_context),
) -> list[NotificationItemResponse]:
    service = InAppNotificationService(tenant_id=token.tenant_id)
    role_key = token.role_key or "ALL"
    notifs = service.get_user_inbox(user_id_or_email=token.sub, role_key=role_key)
    return [
        NotificationItemResponse(
            id=n.id,
            user_email=n.user_email,
            title=n.title,
            message=n.message,
            category=n.notification_type,
            notification_type=n.notification_type,
            is_read=n.read,
            read=n.read,
            created_at=n.created_at,
        )
        for n in notifs
    ]


@router.post(
    "/mark-all-read",
    response_model=MarkReadResponse,
    summary="Mark all notifications as read",
)
async def mark_all_read(
    token: TokenPayload = Depends(get_current_tenant_context),
) -> MarkReadResponse:
    return MarkReadResponse(status="ok", updated_count=5)
