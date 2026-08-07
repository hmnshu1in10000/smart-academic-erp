"""
modules/notification_engine/domain/dtos.py
============================================
DTO contracts for Notification Engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional
from shared_kernel.contracts.base_dto import BaseDTO


@dataclass(frozen=True, slots=True)
class NotificationRequestDTO(BaseDTO):
    tenant_id: str
    user_email: str
    role: str
    title: str
    message: str
    notification_type: str = "ALERT"


@dataclass(frozen=True, slots=True)
class NotificationResponseDTO(BaseDTO):
    id: str
    user_email: str
    title: str
    message: str
    notification_type: str
    read: bool
    created_at: str
