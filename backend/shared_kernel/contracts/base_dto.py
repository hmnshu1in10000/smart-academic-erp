"""
shared_kernel/contracts/base_dto.py
====================================
Base DTO contracts for all cross-module communication.
Source of truth: ARCHITECTURE.md §1.2.1

Rule: NO module ever passes an ORM model instance across a module boundary.
All cross-module data transfer uses frozen dataclasses inheriting from BaseDTO.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Generic, TypeVar

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class BaseDTO:
    """
    All cross-module DTOs are immutable, framework-agnostic dataclasses.
    Never expose an ORM model instance across a module boundary.
    """
    pass


@dataclass(frozen=True, slots=True)
class ResultDTO(Generic[T]):
    """
    Standard envelope for all application-service return values.
    Consumers check .success before accessing .data.
    """
    success: bool
    data: T | None
    error_code: str | None = None
    error_message: str | None = None
    trace_id: str | None = None

    @classmethod
    def ok(cls, data: T, trace_id: str | None = None) -> "ResultDTO[T]":
        return cls(success=True, data=data, trace_id=trace_id)

    @classmethod
    def fail(
        cls,
        error_code: str,
        error_message: str,
        trace_id: str | None = None,
    ) -> "ResultDTO[T]":
        return cls(
            success=False,
            data=None,
            error_code=error_code,
            error_message=error_message,
            trace_id=trace_id,
        )


@dataclass(frozen=True, slots=True)
class PaginatedDTO(Generic[T]):
    """Standard pagination envelope."""
    items: list[T]
    total_count: int
    page: int
    page_size: int
    has_next: bool

    @classmethod
    def from_slice(
        cls,
        items: list[T],
        total_count: int,
        page: int,
        page_size: int,
    ) -> "PaginatedDTO[T]":
        return cls(
            items=items,
            total_count=total_count,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total_count,
        )
