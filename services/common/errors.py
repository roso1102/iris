"""Typed service errors and the single public error envelope (Phase 0.1).

Public responses never contain ``str(exc)``. Every error that reaches a client
is rendered as::

    {"error": {"code": "...", "message": "...", "correlation_id": "..."}}

Codes are stable machine-readable identifiers; messages are constant strings
chosen by us, never provider/library text.
"""

from __future__ import annotations

from typing import Optional


class ErrorCode:
    INVALID_REQUEST = "INVALID_REQUEST"
    UNAUTHENTICATED = "UNAUTHENTICATED"
    FORBIDDEN = "FORBIDDEN"
    NOT_FOUND = "NOT_FOUND"
    CONFLICT = "CONFLICT"
    RATE_LIMITED = "RATE_LIMITED"
    BAD_UPSTREAM_RESPONSE = "BAD_UPSTREAM_RESPONSE"
    DEPENDENCY_UNAVAILABLE = "DEPENDENCY_UNAVAILABLE"
    DEPENDENCY_TIMEOUT = "DEPENDENCY_TIMEOUT"
    SESSION_STORE_UNAVAILABLE = "SESSION_STORE_UNAVAILABLE"
    EMBEDDING_INVALID = "EMBEDDING_INVALID"
    INTERNAL_ERROR = "INTERNAL_ERROR"


class RejectionCode:
    """Enumerated ingestion rejection reasons (never raw exception text)."""

    PDF_CORRUPT = "PDF_CORRUPT"
    PDF_TOO_LARGE = "PDF_TOO_LARGE"
    PDF_EMPTY = "PDF_EMPTY"
    PDF_PAGE_LIMIT_EXCEEDED = "PDF_PAGE_LIMIT_EXCEEDED"
    UNSUPPORTED_PDF = "UNSUPPORTED_PDF"
    INVALID_REQUEST = "INVALID_REQUEST"


REJECTION_MESSAGES = {
    RejectionCode.PDF_CORRUPT: "The document is corrupt or unreadable.",
    RejectionCode.PDF_TOO_LARGE: "The document exceeds the size limit.",
    RejectionCode.PDF_EMPTY: "The document is empty.",
    RejectionCode.PDF_PAGE_LIMIT_EXCEEDED: "The document exceeds the page limit.",
    RejectionCode.UNSUPPORTED_PDF: "The document is not a supported PDF.",
    RejectionCode.INVALID_REQUEST: "The request is invalid.",
}


# Canonical HTTP status for each code.
STATUS_BY_CODE = {
    ErrorCode.INVALID_REQUEST: 422,
    ErrorCode.UNAUTHENTICATED: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.CONFLICT: 409,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.BAD_UPSTREAM_RESPONSE: 502,
    ErrorCode.DEPENDENCY_UNAVAILABLE: 503,
    ErrorCode.DEPENDENCY_TIMEOUT: 504,
    ErrorCode.SESSION_STORE_UNAVAILABLE: 503,
    ErrorCode.EMBEDDING_INVALID: 500,
    ErrorCode.INTERNAL_ERROR: 500,
}

# HTTP status -> stable code, used when converting framework-level errors.
STATUS_TO_CODE = {
    400: ErrorCode.INVALID_REQUEST,
    401: ErrorCode.UNAUTHENTICATED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    409: ErrorCode.CONFLICT,
    422: ErrorCode.INVALID_REQUEST,
    429: ErrorCode.RATE_LIMITED,
    500: ErrorCode.INTERNAL_ERROR,
    502: ErrorCode.BAD_UPSTREAM_RESPONSE,
    503: ErrorCode.DEPENDENCY_UNAVAILABLE,
    504: ErrorCode.DEPENDENCY_TIMEOUT,
}

DEFAULT_MESSAGES = {
    ErrorCode.INVALID_REQUEST: "The request is invalid.",
    ErrorCode.UNAUTHENTICATED: "Authentication is required.",
    ErrorCode.FORBIDDEN: "You are not permitted to perform this action.",
    ErrorCode.NOT_FOUND: "The requested resource was not found.",
    ErrorCode.CONFLICT: "The request conflicts with the current state.",
    ErrorCode.RATE_LIMITED: "Too many requests.",
    ErrorCode.BAD_UPSTREAM_RESPONSE: "An upstream service returned an invalid response.",
    ErrorCode.DEPENDENCY_UNAVAILABLE: "A required service is temporarily unavailable.",
    ErrorCode.DEPENDENCY_TIMEOUT: "A required service timed out.",
    ErrorCode.SESSION_STORE_UNAVAILABLE: "The session store is temporarily unavailable.",
    ErrorCode.EMBEDDING_INVALID: "An embedding response was invalid.",
    ErrorCode.INTERNAL_ERROR: "An unexpected internal error occurred.",
}


class ServiceError(Exception):
    """Base class for errors that may be safely rendered to a client."""

    code = ErrorCode.INTERNAL_ERROR
    status_code = 500
    retryable = False

    def __init__(
        self,
        message: Optional[str] = None,
        *,
        code: Optional[str] = None,
        status_code: Optional[int] = None,
        retryable: Optional[bool] = None,
        safe_detail: Optional[str] = None,
    ) -> None:
        self.code = code or self.code
        if status_code is not None:
            self.status_code = status_code
        if retryable is not None:
            self.retryable = retryable
        self.public_message = message or DEFAULT_MESSAGES.get(self.code, DEFAULT_MESSAGES[ErrorCode.INTERNAL_ERROR])
        # `safe_detail` is a short, developer-authored hint that is safe to
        # expose (e.g. a field name). It must never be exception text.
        self.safe_detail = safe_detail
        super().__init__(self.public_message)

    @property
    def public_code(self) -> str:
        return self.code

    def envelope(self, correlation_id: str = "") -> dict:
        return error_envelope(self.public_code, self.public_message, correlation_id)


class InvalidInput(ServiceError):
    code = ErrorCode.INVALID_REQUEST
    status_code = 422


class NotFound(ServiceError):
    code = ErrorCode.NOT_FOUND
    status_code = 404


class Conflict(ServiceError):
    code = ErrorCode.CONFLICT
    status_code = 409


class DependencyUnavailable(ServiceError):
    code = ErrorCode.DEPENDENCY_UNAVAILABLE
    status_code = 503
    retryable = True


class DependencyTimeout(ServiceError):
    code = ErrorCode.DEPENDENCY_TIMEOUT
    status_code = 504
    retryable = True


class BadUpstreamResponse(ServiceError):
    code = ErrorCode.BAD_UPSTREAM_RESPONSE
    status_code = 502


def error_envelope(code: str, message: str, correlation_id: str = "") -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "correlation_id": correlation_id,
        }
    }
