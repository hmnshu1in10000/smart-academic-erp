"""
modules/notification_engine/application/services/fcm_provider.py
==================================================================
Sub-Module 100% Free Notification Engine.
Integrates FcmPushProvider (FCM payload dispatch simulation) + InAppNotificationService.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

from modules.dummy_data_engine.infrastructure.db.session import SessionLocal
from modules.dummy_data_engine.infrastructure.db.models import InAppNotification
from modules.notification_engine.domain.dtos import NotificationRequestDTO, NotificationResponseDTO

logger = logging.getLogger(__name__)


class FcmPushProvider:
    """
    Sub-Module: FCM Push Provider (Firebase Cloud Messaging Free Tier).
    Formats and dispatches push payloads to mobile device tokens.
    """

    def send_push_notification(self, device_token: str, title: str, body: str, data_payload: Optional[dict] = None) -> bool:
        """Simulates FCM Cloud Messaging API call."""
        logger.info(f"[FCM PUSH SENT] DeviceToken: '{device_token[:15]}...' | Title: '{title}' | Body: '{body}'")
        return True


class InAppNotificationService:
    """
    Sub-Module: InAppNotificationService
    Persists notifications to the database and retrieves inbox lists.
    """

    def __init__(self, tenant_id: str) -> None:
        self._tenant_id = tenant_id
        self._fcm_provider = FcmPushProvider()

    def send_notification(self, req: NotificationRequestDTO) -> NotificationResponseDTO:
        """Saves notification in DB and emits FCM push payload."""
        with SessionLocal() as session:
            notif = InAppNotification(
                tenant_id=req.tenant_id,
                user_email=req.user_email,
                role=req.role,
                title=req.title,
                message=req.message,
                notification_type=req.notification_type,
                read=False,
                created_at=datetime.now(timezone.utc),
            )
            session.add(notif)
            session.commit()

            # Emit FCM push simulation
            device_token = f"fcm_token_{req.user_email.split('@')[0]}"
            self._fcm_provider.send_push_notification(device_token, req.title, req.message)

            return NotificationResponseDTO(
                id=notif.id,
                user_email=notif.user_email,
                title=notif.title,
                message=notif.message,
                notification_type=notif.notification_type,
                read=notif.read,
                created_at=str(notif.created_at),
            )

    def get_user_inbox(self, user_email: str) -> list[NotificationResponseDTO]:
        """Retrieves user inbox notifications from DB."""
        with SessionLocal() as session:
            rows = (
                session.query(InAppNotification)
                .filter(
                    InAppNotification.tenant_id == self._tenant_id,
                    InAppNotification.user_email == user_email,
                )
                .order_by(InAppNotification.created_at.desc())
                .all()
            )

            # If user has no notifications yet, return seed notices
            if not rows:
                return [
                    NotificationResponseDTO(
                        id="notif_demo_01",
                        user_email=user_email,
                        title="Welcome to Parent & Student Portal",
                        message="Track daily attendance, fee dues, and timetable in real-time.",
                        notification_type="INFO",
                        read=False,
                        created_at=str(datetime.now(timezone.utc)),
                    )
                ]

            return [
                NotificationResponseDTO(
                    id=r.id,
                    user_email=r.user_email,
                    title=r.title,
                    message=r.message,
                    notification_type=r.notification_type,
                    read=r.read,
                    created_at=str(r.created_at),
                )
                for r in rows
            ]
