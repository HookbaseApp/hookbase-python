from __future__ import annotations

from typing import Any

# Top-level body keys that are part of the error envelope itself rather than extra detail.
_ENVELOPE_KEYS = frozenset({"error", "code", "message", "details"})


def _body_details(container: dict[str, Any]) -> dict[str, Any] | None:
    """The structured detail an error body carries, or None.

    The API sends ``details`` beside ``error`` (Zod's ``{ fieldErrors, formErrors }`` for
    validation failures). Some errors instead put their detail in extra top-level fields, such
    as ``LIMIT_EXCEEDED``'s ``current`` and ``max``; those are returned when ``details`` is absent.
    """
    details = container.get("details")
    if isinstance(details, dict):
        return details
    extras = {k: v for k, v in container.items() if k not in _ENVELOPE_KEYS}
    if details is not None:
        extras["details"] = details
    return extras or None


class HookbaseError(Exception):
    """Base error for all Hookbase SDK errors."""


class APIError(HookbaseError):
    """Error returned by the Hookbase API.

    Attributes:
        status_code: The HTTP status of the response.
        code: The ``code`` from the response body (e.g. ``LIMIT_EXCEEDED``), or the error
            class's default (``forbidden``, ``not_found``, ...) when the body has none.
        request_id: The ``x-request-id`` response header, if any.
        details: Structured detail from the body (its ``details`` object, or any extra
            top-level fields), or None.
    """

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
        body: Any,
        request_id: str | None = None,
    ) -> APIError:
        """Build the matching error for a non-2xx response body."""
        if not isinstance(body, dict):
            body = {}
        error = body.get("error", body)
        code: str | None
        details: dict[str, Any] | None
        validation_errors: Any = None
        if isinstance(error, str):
            # The real API sends `error` as a plain string, with `code` and `details` as
            # siblings of `error` at the top level of the body, never nested inside it.
            message = error
            code = body.get("code")
            details = _body_details(body)
            raw = body.get("details")
            if isinstance(raw, dict):
                validation_errors = raw.get("fieldErrors")
        elif isinstance(error, dict) and error is not body:
            message = error.get("message") or body.get("message") or f"API error: {status_code}"
            code = error.get("code") or body.get("code")
            details = _body_details(error)
            validation_errors = error.get("validationErrors")
            if validation_errors is None and isinstance(error.get("details"), dict):
                validation_errors = error["details"].get("fieldErrors")
        else:
            message = body.get("message") or f"API error: {status_code}"
            code = body.get("code")
            details = _body_details(body) if body else None
        if not isinstance(code, str) or not code:
            code = None
        if not isinstance(message, str):
            message = str(message)
        if not isinstance(validation_errors, dict):
            validation_errors = None

        common: dict[str, Any] = {
            "message": message,
            "request_id": request_id,
            "details": details,
        }
        if code is not None:
            common["code"] = code

        if status_code in (400, 422):
            return ValidationError(
                status_code=status_code, validation_errors=validation_errors, **common
            )
        if status_code == 401:
            return AuthenticationError(**common)
        if status_code == 403:
            return ForbiddenError(**common)
        if status_code == 404:
            return NotFoundError(**common)
        if status_code == 409:
            return ConflictError(**common)
        if status_code == 429:
            return RateLimitError(**common)
        return APIError(status_code=status_code, **common)


class AuthenticationError(APIError):
    """Raised on 401 responses."""

    def __init__(
        self,
        message: str = "Authentication failed",
        request_id: str | None = None,
        *,
        code: str = "authentication_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, 401, code, request_id, details)


class ForbiddenError(APIError):
    """Raised on 403 responses (also for LIMIT_EXCEEDED, FEATURE_DISABLED: see ``code``)."""

    def __init__(
        self,
        message: str = "Access forbidden",
        request_id: str | None = None,
        *,
        code: str = "forbidden",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, 403, code, request_id, details)


class NotFoundError(APIError):
    """Raised on 404 responses."""

    def __init__(
        self,
        message: str = "Resource not found",
        request_id: str | None = None,
        *,
        code: str = "not_found",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, 404, code, request_id, details)


class ValidationError(APIError):
    """Raised on 400/422 responses. ``status_code`` is the status actually returned."""

    validation_errors: dict[str, list[str]] | None

    def __init__(
        self,
        message: str = "Validation failed",
        request_id: str | None = None,
        validation_errors: dict[str, list[str]] | None = None,
        *,
        status_code: int = 400,
        code: str = "validation_error",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, status_code, code, request_id, details)
        self.validation_errors = validation_errors


class ConflictError(APIError):
    """Raised on 409 responses."""

    def __init__(
        self,
        message: str = "Resource conflict",
        request_id: str | None = None,
        *,
        code: str = "conflict",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, 409, code, request_id, details)


class RateLimitError(APIError):
    """Raised on 429 responses."""

    retry_after: float

    def __init__(
        self,
        message: str = "Rate limit exceeded",
        retry_after: float = 60.0,
        request_id: str | None = None,
        *,
        code: str = "rate_limit_exceeded",
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(message, 429, code, request_id, details)
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
