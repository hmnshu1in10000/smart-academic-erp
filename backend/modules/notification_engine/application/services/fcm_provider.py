"""
modules/notification_engine/application/services/fcm_provider.py
==================================================================
Sub-Module 100% Free Notification Engine.
Integrates FcmPushProvider (FCM payload dispatch simulation) + InAppNotificationService.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
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
        logger.info("[FCM PUSH SENT] DeviceToken: '%s...' | Title: '%s' | Body: '%s'", device_token[:15], title, body)
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

    def get_user_inbox(self, user_id_or_email: str, role_key: str = "ALL") -> list[NotificationResponseDTO]:
        """Retrieves strictly role-scoped and user-scoped inbox notifications from DB."""
        role_upper = (role_key or "ALL").upper()
        uid_lower = (user_id_or_email or "").lower()

        with SessionLocal() as session:
            all_rows = (
                session.query(InAppNotification)
                .filter(InAppNotification.tenant_id == self._tenant_id)
                .order_by(InAppNotification.created_at.desc())
                .all()
            )

            filtered = []
            for r in all_rows:
                target = (r.target_role or r.role or "ALL").upper()
                recip = (r.recipient_user_id or r.user_email or "").lower()

                # 1. Targeted personal notification for this specific user ID or email
                if recip and recip == uid_lower:
                    filtered.append(r)
                # 2. Targeted role broadcast (e.g. TEACHER, PARENT, STUDENT, ADMIN, PRINCIPAL)
                elif target != "ALL" and target == role_upper:
                    filtered.append(r)
                # 3. Universal school-wide broadcast (ALL)
                elif target == "ALL" and not recip:
                    filtered.append(r)

            return [
                NotificationResponseDTO(
                    id=r.id,
                    user_email=r.recipient_user_id or r.user_email or user_id_or_email,
                    title=r.title,
                    message=r.message,
                    notification_type=r.category or r.notification_type or "INFO",
                    read=r.is_read or r.read,
                    created_at=str(r.created_at),
                )
                for r in filtered
            ]

