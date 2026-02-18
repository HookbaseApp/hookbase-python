from __future__ import annotations

from typing import Any


class HookbaseError(Exception):
    """Base error for all Hookbase SDK errors."""


class APIError(HookbaseError):
    """Error returned by the Hookbase API."""

    status_code: int
    code: str
    request_id: str | None
    details: dict[str, Any] | None

    def __init__(
        self,
        message: str,
        status_code: int,
        code: str = "unknown_error",
        request_id: str | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.request_id = request_id
        self.details = details

    @classmethod
    def from_response(
        cls,
        status_code: int,
        body: dict[str, Any],
        request_id: str | None = None,
    ) -> APIError:
        error = body.get("error", body)
        if isinstance(error, str):
            message = error
            code = "unknown_error"
        elif isinstance(error, dict):
            message = error.get("message", f"API error: {status_code}")
            code = error.get("code", "unknown_error")
        else:
            message = f"API error: {status_code}"
            code = "unknown_error"

        if status_code in (400, 422):
            validation_errors = None
            if isinstance(error, dict):
                validation_errors = error.get("validationErrors")
            return ValidationError(
                message=message,
                request_id=request_id,
                validation_errors=validation_errors,
            )
        if status_code == 401:
            return AuthenticationError(message=message, request_id=request_id)
        if status_code == 403:
            return ForbiddenError(message=message, request_id=request_id)
        if status_code == 404:
            return NotFoundError(message=message, request_id=request_id)
        if status_code == 409:
            return ConflictError(message=message, request_id=request_id)
        if status_code == 429:
            return RateLimitError(message=message, request_id=request_id)
        return cls(
            message=message,
            status_code=status_code,
            code=code,
            request_id=request_id,
        )


class AuthenticationError(APIError):
    """Raised on 401 responses."""

    def __init__(
        self,
        message: str = "Authentication failed",
        request_id: str | None = None,
    ) -> None:
        super().__init__(message, 401, "authentication_error", request_id)


class ForbiddenError(APIError):
    """Raised on 403 responses (also for LIMIT_EXCEEDED, FEATURE_DISABLED)."""

    def __init__(
        self,
        message: str = "Access forbidden",
        request_id: str | None = None,
    ) -> None:
        super().__init__(message, 403, "forbidden", request_id)


class NotFoundError(APIError):
    """Raised on 404 responses."""

    def __init__(
        self,
        message: str = "Resource not found",
        request_id: str | None = None,
    ) -> None:
        super().__init__(message, 404, "not_found", request_id)


class ValidationError(APIError):
    """Raised on 400/422 responses."""

    validation_errors: dict[str, list[str]] | None

    def __init__(
        self,
        message: str = "Validation failed",
        request_id: str | None = None,
        validation_errors: dict[str, list[str]] | None = None,
    ) -> None:
        super().__init__(message, 400, "validation_error", request_id)
        self.validation_errors = validation_errors


class ConflictError(APIError):
    """Raised on 409 responses."""

    def __init__(
        self,
        message: str = "Resource conflict",
        request_id: str | None = None,
    ) -> None:
        super().__init__(message, 409, "conflict", request_id)


class RateLimitError(APIError):
    """Raised on 429 responses."""

    retry_after: float

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: float = 60.0,
        request_id: str | None = None,
    ) -> None:
        super().__init__(message, 429, "rate_limit_exceeded", request_id)
        self.retry_after = retry_after


class TimeoutError(HookbaseError):
    """Raised when a request times out."""


class NetworkError(HookbaseError):
    """Raised when a network error occurs."""

    cause: Exception | None

    def __init__(self, message: str = "Network error", cause: Exception | None = None) -> None:
        super().__init__(message)
        self.cause = cause


class WebhookVerificationError(HookbaseError):
    """Raised when webhook signature verification fails."""
