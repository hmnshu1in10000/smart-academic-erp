"""
shared_kernel/exceptions/domain_exceptions.py
===============================================
Base domain exceptions used across all modules.
These are framework-agnostic — HTTP status mapping happens in the API layer.
"""


class DomainException(Exception):
    """Base for all domain-layer exceptions."""
    error_code: str = "DOMAIN_ERROR"

    def __init__(self, message: str, error_code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if error_code:
            self.error_code = error_code


class TenantNotFoundError(DomainException):
    """Raised when no tenant matches the provided ID or slug. → HTTP 404"""
    error_code = "TENANT_NOT_FOUND"


class TenantSuspendedError(DomainException):
    """Raised when a tenant exists but is suspended. → HTTP 403"""
    error_code = "TENANT_SUSPENDED"


class ResourceNotFoundError(DomainException):
    """Generic 404 for domain entities. → HTTP 404"""
    error_code = "RESOURCE_NOT_FOUND"


EntityNotFoundError = ResourceNotFoundError


class ValidationError(DomainException):
    """Domain-level validation failure (distinct from Pydantic/HTTP validation). → HTTP 422"""
    error_code = "VALIDATION_ERROR"


class UnauthorizedError(DomainException):
    """Action not permitted for the requesting actor. → HTTP 403"""
    error_code = "UNAUTHORIZED"


class ConflictError(DomainException):
    """Resource already exists or state conflict. → HTTP 409"""
    error_code = "CONFLICT"
