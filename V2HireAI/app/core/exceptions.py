"""
Custom exception hierarchy for the AI Recruitment Platform.

Each exception maps to a specific HTTP status code and carries
a machine-readable error_code for API clients.
"""
from typing import Any, Dict, Optional


class ATSBaseException(Exception):
    """Base for all platform exceptions."""

    status_code: int = 500
    error_code: str = "INTERNAL_ERROR"

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(message)


# ── 400 Bad Request ────────────────────────────────────────────────────────────

class FileValidationError(ATSBaseException):
    status_code = 400
    error_code = "FILE_VALIDATION_ERROR"


class InvalidFileTypeError(FileValidationError):
    error_code = "INVALID_FILE_TYPE"


class FileSizeExceededError(FileValidationError):
    error_code = "FILE_SIZE_EXCEEDED"


class ParseError(ATSBaseException):
    status_code = 422
    error_code = "PARSE_ERROR"


# ── 401 Unauthorized ───────────────────────────────────────────────────────────

class AuthenticationError(ATSBaseException):
    status_code = 401
    error_code = "AUTHENTICATION_ERROR"


class InvalidCredentialsError(AuthenticationError):
    error_code = "INVALID_CREDENTIALS"


class TokenExpiredError(AuthenticationError):
    error_code = "TOKEN_EXPIRED"


class InvalidTokenError(AuthenticationError):
    error_code = "INVALID_TOKEN"


class InactiveUserError(AuthenticationError):
    error_code = "USER_INACTIVE"


class InsufficientPermissionsError(AuthenticationError):
    status_code = 403
    error_code = "INSUFFICIENT_PERMISSIONS"


# ── 404 Not Found ──────────────────────────────────────────────────────────────

class ResumeNotFoundError(ATSBaseException):
    status_code = 404
    error_code = "RESUME_NOT_FOUND"


class CandidateNotFoundError(ATSBaseException):
    status_code = 404
    error_code = "CANDIDATE_NOT_FOUND"


class NotFoundError(ATSBaseException):
    """Tenant or model not found."""
    status_code = 404
    error_code = "NOT_FOUND"


# ── 409 Conflict ───────────────────────────────────────────────────────────────

class DuplicateResumeError(ATSBaseException):
    status_code = 409
    error_code = "DUPLICATE_RESUME"


class DuplicateResourceError(ATSBaseException):
    status_code = 409
    error_code = "DUPLICATE_RESOURCE"


# ── 422 Validation ─────────────────────────────────────────────────────────────

class ValidationError(ATSBaseException):
    status_code = 422
    error_code = "VALIDATION_ERROR"


class SubscriptionLimitError(ATSBaseException):
    status_code = 403
    error_code = "SUBSCRIPTION_LIMIT_EXCEEDED"


# ── 500 Internal ───────────────────────────────────────────────────────────────

class ScoringError(ATSBaseException):
    status_code = 500
    error_code = "SCORING_ERROR"


class DatabaseError(ATSBaseException):
    status_code = 500
    error_code = "DATABASE_ERROR"


class EmailServiceError(ATSBaseException):
    status_code = 500
    error_code = "EMAIL_SERVICE_ERROR"
