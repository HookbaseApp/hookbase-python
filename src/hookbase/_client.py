from __future__ import annotations

import logging
import random
import time
from typing import Any

import httpx

from ._constants import DEFAULT_BASE_URL, DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT, RETRY_STATUS_CODES
from ._version import __version__
from .errors import (
    APIError,
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)

logger = logging.getLogger("hookbase")


def _parse_error(status_code: int, body: dict[str, Any], request_id: str | None) -> APIError:
    error = body.get("error", body)
    if isinstance(error, str):
        message = error
        code = "unknown_error"
        validation_errors = None
    elif isinstance(error, dict):
        message = error.get("message") or body.get("message") or f"API error: {status_code}"
        code = error.get("code", "unknown_error")
        validation_errors = error.get("validationErrors")
    else:
        message = body.get("message") or f"API error: {status_code}"
        code = "unknown_error"
        validation_errors = None

    if status_code == 401:
        return AuthenticationError(message=message, request_id=request_id)
    if status_code == 403:
        return ForbiddenError(message=message, request_id=request_id)
    if status_code == 404:
        return NotFoundError(message=message, request_id=request_id)
    if status_code in (400, 422):
        return ValidationError(
            message=message, request_id=request_id, validation_errors=validation_errors
        )
    if status_code == 409:
        return ConflictError(message=message, request_id=request_id)
    if status_code == 429:
        return RateLimitError(message=message, request_id=request_id)
    return APIError(
        message=message, status_code=status_code, code=code, request_id=request_id
    )


def _build_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": f"hookbase-python/{__version__}",
        "Accept": "application/json",
    }


def _should_retry(status_code: int) -> bool:
    return status_code in RETRY_STATUS_CODES


def _backoff(attempt: int) -> float:
    base = min(1.0 * (2**attempt), 10.0)
    jitter = random.random()  # noqa: S311
    return base + jitter


def _clean_params(params: dict[str, Any] | None) -> dict[str, Any] | None:
    if params is None:
        return None
    return {k: v for k, v in params.items() if v is not None}


class SyncTransport:
    """Synchronous HTTP transport backed by httpx.Client."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        debug: bool = False,
        http_client: httpx.Client | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._debug = debug
        self._headers = _build_headers(api_key)
        self._client = http_client or httpx.Client(
            base_url=self._base_url,
            headers=self._headers,
            timeout=timeout,
        )
        self._owns_client = http_client is None

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        cleaned = _clean_params(params)
        headers: dict[str, str] = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        if self._debug:
            logger.debug("[Hookbase] %s %s params=%s", method, path, cleaned)

        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = self._client.request(
                    method,
                    path,
                    json=json,
                    params=cleaned,
                    headers=headers,
                )
            except httpx.TimeoutException as exc:
                last_exc = TimeoutError(f"Request timed out after {self._timeout}s")
                last_exc.__cause__ = exc
                if attempt < self._max_retries:
                    time.sleep(_backoff(attempt))
                    continue
                raise last_exc from exc
            except httpx.HTTPError as exc:
                last_exc = NetworkError(str(exc), cause=exc)
                if attempt < self._max_retries:
                    time.sleep(_backoff(attempt))
                    continue
                raise last_exc from exc

            request_id = resp.headers.get("x-request-id")

            if resp.status_code == 204:
                return None

            if resp.is_success:
                return resp.json()

            # Parse error body
            try:
                body = resp.json()
            except Exception:
                body = {}

            error = _parse_error(resp.status_code, body, request_id)

            # For 429, use Retry-After header
            if isinstance(error, RateLimitError):
                retry_after_header = resp.headers.get("retry-after")
                if retry_after_header:
                    try:
                        error.retry_after = float(retry_after_header)
                    except ValueError:
                        pass

            # Don't retry client errors (except 429 and 409)
            if not _should_retry(resp.status_code):
                raise error

            last_exc = error

            if attempt < self._max_retries:
                if isinstance(error, RateLimitError):
                    time.sleep(error.retry_after)
                else:
                    time.sleep(_backoff(attempt))
            else:
                raise error

        if last_exc is not None:
            raise last_exc
        raise NetworkError("Request failed after retries")  # pragma: no cover

    def close(self) -> None:
        if self._owns_client:
            self._client.close()


class AsyncTransport:
    """Asynchronous HTTP transport backed by httpx.AsyncClient."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        debug: bool = False,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._max_retries = max_retries
        self._debug = debug
        self._headers = _build_headers(api_key)
        self._client = http_client or httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=timeout,
        )
        self._owns_client = http_client is None

    async def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        import asyncio

        cleaned = _clean_params(params)
        headers: dict[str, str] = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key

        if self._debug:
            logger.debug("[Hookbase] %s %s params=%s", method, path, cleaned)

        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._client.request(
                    method,
                    path,
                    json=json,
                    params=cleaned,
                    headers=headers,
                )
            except httpx.TimeoutException as exc:
                last_exc = TimeoutError(f"Request timed out after {self._timeout}s")
                last_exc.__cause__ = exc
                if attempt < self._max_retries:
                    await asyncio.sleep(_backoff(attempt))
                    continue
                raise last_exc from exc
            except httpx.HTTPError as exc:
                last_exc = NetworkError(str(exc), cause=exc)
                if attempt < self._max_retries:
                    await asyncio.sleep(_backoff(attempt))
                    continue
                raise last_exc from exc

            request_id = resp.headers.get("x-request-id")

            if resp.status_code == 204:
                return None

            if resp.is_success:
                return resp.json()

            try:
                body = resp.json()
            except Exception:
                body = {}

            error = _parse_error(resp.status_code, body, request_id)

            if isinstance(error, RateLimitError):
                retry_after_header = resp.headers.get("retry-after")
                if retry_after_header:
                    try:
                        error.retry_after = float(retry_after_header)
                    except ValueError:
                        pass

            if not _should_retry(resp.status_code):
                raise error

            last_exc = error

            if attempt < self._max_retries:
                if isinstance(error, RateLimitError):
                    await asyncio.sleep(error.retry_after)
                else:
                    await asyncio.sleep(_backoff(attempt))
            else:
                raise error

        if last_exc is not None:
            raise last_exc
        raise NetworkError("Request failed after retries")  # pragma: no cover

    async def close(self) -> None:
        if self._owns_client:
            await self._client.aclose()
