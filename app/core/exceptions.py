"""Custom exception classes for the application.

Provides a hierarchy of exceptions with error codes for consistent error handling.
"""

from typing import Any


class AppException(Exception):
    """Base exception for all application errors."""

    error_code: str = "INTERNAL_ERROR"
    status_code: int = 500
    message: str = "An internal error occurred"

    def __init__(
        self,
        message: str | None = None,
        details: dict[str, Any] | None = None,
        error_code: str | None = None,
    ) -> None:
        self.message = message or self.message
        self.details = details or {}
        if error_code:
            self.error_code = error_code
        super().__init__(self.message)


# =============================================================================
# Resource Exceptions (4xx)
# =============================================================================


class ResourceNotFoundError(AppException):
    """Resource not found (404)."""

    error_code = "RESOURCE_NOT_FOUND"
    status_code = 404
    message = "The requested resource was not found"


class ResourceAlreadyExistsError(AppException):
    """Resource already exists (409)."""

    error_code = "RESOURCE_ALREADY_EXISTS"
    status_code = 409
    message = "A resource with the same identifier already exists"


class ValidationError(AppException):
    """Validation error (400)."""

    error_code = "VALIDATION_ERROR"
    status_code = 400
    message = "The request contains invalid data"


class BadRequestError(AppException):
    """Bad request (400)."""

    error_code = "BAD_REQUEST"
    status_code = 400
    message = "The request is malformed or invalid"


# =============================================================================
# Authentication & Authorization Exceptions
# =============================================================================


class AuthenticationError(AppException):
    """Authentication failed (401)."""

    error_code = "AUTHENTICATION_FAILED"
    status_code = 401
    message = "Authentication failed"


class AuthorizationError(AppException):
    """Authorization failed (403)."""

    error_code = "AUTHORIZATION_FAILED"
    status_code = 403
    message = "You do not have permission to perform this action"


class TokenExpiredError(AuthenticationError):
    """Token expired (401)."""

    error_code = "TOKEN_EXPIRED"
    message = "The authentication token has expired"


class InvalidTokenError(AuthenticationError):
    """Invalid token (401)."""

    error_code = "INVALID_TOKEN"
    message = "The authentication token is invalid"


# =============================================================================
# Service Exceptions (5xx)
# =============================================================================


class ServiceUnavailableError(AppException):
    """Service unavailable (503)."""

    error_code = "SERVICE_UNAVAILABLE"
    status_code = 503
    message = "The service is temporarily unavailable"


class DatabaseError(AppException):
    """Database error (500)."""

    error_code = "DATABASE_ERROR"
    status_code = 500
    message = "A database error occurred"


class CacheError(AppException):
    """Cache error (500)."""

    error_code = "CACHE_ERROR"
    status_code = 500
    message = "A cache error occurred"


class ExternalServiceError(AppException):
    """External service error (502)."""

    error_code = "EXTERNAL_SERVICE_ERROR"
    status_code = 502
    message = "An external service returned an error"


# =============================================================================
# Rate Limiting
# =============================================================================


class RateLimitExceededError(AppException):
    """Rate limit exceeded (429)."""

    error_code = "RATE_LIMIT_EXCEEDED"
    status_code = 429
    message = "Rate limit exceeded. Please try again later"
