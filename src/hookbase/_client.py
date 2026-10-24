from __future__ import annotations

import logging
import math
import random
import time
from email.utils import parsedate_to_datetime
from typing import Any, Union

import httpx

from ._constants import (
    DEFAULT_BASE_URL,
    DEFAULT_MAX_RETRIES,
    DEFAULT_RETRY_AFTER,
    DEFAULT_TIMEOUT,
    MAX_RETRY_AFTER,
    NOT_GIVEN,
    NotGiven,
)
from ._version import __version__
from .errors import APIError, NetworkError, RateLimitError, TimeoutError

logger = logging.getLogger("hookbase")

#: `timeout` as callers may pass it; NOT_GIVEN means "use the default".
TimeoutArg = Union[float, httpx.Timeout, None, NotGiven]


def _parse_error(status_code: int, body: Any, request_id: str | None) -> APIError:
    return APIError.from_response(status_code, body, request_id)


def _build_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": f"hookbase-python/{__version__}",
        "Accept": "application/json",
    }


def _should_retry(status_code: int) -> bool:
    """429 and every 5xx (including Cloudflare's 52x) are worth another attempt."""
    return status_code == 429 or status_code >= 500


def _parse_retry_after(header: str | None, now: float | None = None) -> float:
    """Seconds to wait from a ``Retry-After`` header: delta-seconds or an HTTP-date.

    A missing or unusable value gives DEFAULT_RETRY_AFTER; a negative delay or a date in the
    past gives 0.
    """
    if header is None:
        return DEFAULT_RETRY_AFTER
    value = header.strip()
    if not value:
        return DEFAULT_RETRY_AFTER
    try:
        seconds = float(value)
    except ValueError:
        try:
            when = parsedate_to_datetime(value)
        except (TypeError, ValueError, IndexError):
            return DEFAULT_RETRY_AFTER
        if when is None or when.tzinfo is None:  # pragma: no cover - not an RFC 9110 date
            return DEFAULT_RETRY_AFTER
        seconds = when.timestamp() - (time.time() if now is None else now)
    if not math.isfinite(seconds):
        return DEFAULT_RETRY_AFTER
    return max(0.0, seconds)


# A POST creates something or triggers work, so repeating one that may already have reached the
# server (a 5xx, a read timeout, a dropped connection) can do it twice. Only retry those when the
# request carries an idempotency key the server can deduplicate on. A 429 was rejected before any
# work was done, and a connect failure never reached the server, so those stay retryable.
_NON_IDEMPOTENT_METHODS = frozenset({"POST"})


def _may_repeat(method: str, idempotency_key: str | None) -> bool:
    """Whether a request that may already have been processed is safe to send again."""
    return method.upper() not in _NON_IDEMPOTENT_METHODS or bool(idempotency_key)


def _never_sent(exc: Exception) -> bool:
    """Whether the transport failed before the request reached the server."""
    return isinstance(exc, (httpx.ConnectError, httpx.ConnectTimeout))


def _decode_body(resp: httpx.Response) -> Any:
    """JSON for JSON responses; the text for anything else (e.g. a CSV export).

    An empty body is None. A JSON response that does not parse raises APIError rather than
    leaking a ``json.JSONDecodeError`` past the SDK's error types.
    """
    content_type = resp.headers.get("content-type", "")
    if content_type and "json" not in content_type.lower():
        return resp.text
    if not resp.content.strip():
        return None
    try:
        return resp.json()
    except ValueError as exc:
        raise APIError(
            f"Invalid JSON in {resp.status_code} response: {exc}",
            resp.status_code,
            code="invalid_response",
            request_id=resp.headers.get("x-request-id"),
        ) from exc


def _worth_waiting(error: APIError) -> bool:
    """Whether to sleep and retry a retryable error, or hand it back now.

    A 429 whose ``Retry-After`` is longer than MAX_RETRY_AFTER (a quota window, a far-off
    HTTP-date) is raised at once with ``retry_after`` set, so the caller decides how to spend
    that time. Everything else that reached this point waits out its backoff.
    """
    return not isinstance(error, RateLimitError) or error.retry_after <= MAX_RETRY_AFTER


def _backoff(attempt: int) -> float:
    base = min(1.0 * (2**attempt), 10.0)
    jitter = random.random()  # noqa: S311
    return base + jitter


def _clean_params(params: dict[str, Any] | None) -> dict[str, Any] | None:
    if params is None:
        return None
    return {k: v for k, v in params.items() if v is not None}


def _is_config_error(exc: Exception) -> bool:
    """A request that can never succeed as built (bad base_url, unsupported scheme)."""
    return isinstance(exc, (httpx.InvalidURL, httpx.UnsupportedProtocol))


class _BaseTransport:
    """Request building and response handling shared by the sync and async transports.

    Every request carries an absolute URL, the SDK's headers and (when one applies) the SDK
    timeout, so a caller-supplied ``http_client`` works as given and is never mutated.
    """

    def __init__(
        self,
        api_key: str,
        base_url: str,
        timeout: TimeoutArg,
        max_retries: int,
        debug: bool,
        custom_client: bool,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        # An explicit `timeout` (including None, meaning no timeout, as in httpx) is sent on
        # every request. Left out, an SDK-owned client gets DEFAULT_TIMEOUT and a
        # caller-supplied client keeps its own timeout (nothing is sent).
        if isinstance(timeout, NotGiven) and not custom_client:
            timeout = DEFAULT_TIMEOUT
        self._timeout: TimeoutArg = timeout
        self._max_retries = max_retries
        self._debug = debug
        self._headers = _build_headers(api_key)
        self._owns_client = not custom_client

    def _url(self, path: str) -> httpx.URL:
        """The absolute request URL, or NetworkError when base_url cannot form one."""
        raw = f"{self._base_url}/{path.lstrip('/')}"
        try:
            url = httpx.URL(raw)
        except httpx.InvalidURL as exc:
            raise NetworkError(f"Invalid request URL {raw!r}: {exc}", cause=exc) from exc
        # The path is appended to base_url, so a query or fragment there would swallow it.
        if url.scheme not in ("http", "https") or not url.host or url.query or url.fragment:
            invalid = httpx.InvalidURL(
                "base_url must be an absolute http(s) URL with no query or fragment, "
                f"got {self._base_url!r}"
            )
            raise NetworkError(str(invalid), cause=invalid) from invalid
        return url

    def _request_kwargs(
        self,
        json: Any,
        params: dict[str, Any] | None,
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        headers = dict(self._headers)
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        kwargs: dict[str, Any] = {
            "json": json,
            "params": _clean_params(params),
            "headers": headers,
            # The SDK's Bearer header must win over any `auth=` set on a supplied client.
            "auth": None,
        }
        if not isinstance(self._timeout, NotGiven):
            kwargs["timeout"] = self._timeout
        return kwargs

    def _timeout_error(self, exc: httpx.TimeoutException) -> TimeoutError:
        t = self._timeout
        if isinstance(t, (int, float)) and not isinstance(t, bool):
            message = f"Request timed out after {t}s"
        else:
            # A supplied client's own timeout, or an httpx.Timeout: no single number to name.
            message = "Request timed out"
        err = TimeoutError(message)
        err.__cause__ = exc
        return err

    def _error_for(self, resp: httpx.Response) -> APIError:
        try:
            body = resp.json()
        except Exception:
            body = {}
        error = _parse_error(resp.status_code, body, resp.headers.get("x-request-id"))
        if isinstance(error, RateLimitError):
            error.retry_after = _parse_retry_after(resp.headers.get("retry-after"))
        return error

    def _log(self, method: str, path: str, params: Any) -> None:
        if self._debug:
            logger.debug("[Hookbase] %s %s params=%s", method, path, params)


class SyncTransport(_BaseTransport):
    """Synchronous HTTP transport backed by httpx.Client."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: TimeoutArg = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        debug: bool = False,
        http_client: httpx.Client | None = None,
    ) -> None:
        super().__init__(
            api_key, base_url, timeout, max_retries, debug, custom_client=http_client is not None
        )
        self._client = http_client if http_client is not None else httpx.Client()

    def request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        kwargs = self._request_kwargs(json, params, idempotency_key)
        url = self._url(path)
        repeatable = _may_repeat(method, idempotency_key)
        self._log(method, path, kwargs["params"])

        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = self._client.request(method, url, **kwargs)
            except httpx.TimeoutException as exc:
                last_exc = self._timeout_error(exc)
                if attempt < self._max_retries and (repeatable or _never_sent(exc)):
                    time.sleep(_backoff(attempt))
                    continue
                raise last_exc from exc
            except (httpx.HTTPError, httpx.InvalidURL) as exc:
                last_exc = NetworkError(str(exc), cause=exc)
                if (
                    not _is_config_error(exc)
                    and attempt < self._max_retries
                    and (repeatable or _never_sent(exc))
                ):
                    time.sleep(_backoff(attempt))
                    continue
                raise last_exc from exc

            if resp.status_code == 204:
                return None
            if resp.is_success:
                return _decode_body(resp)

            error = self._error_for(resp)

            # Don't retry client errors (except 429), nor a 5xx on a request
            # that is not safe to repeat (see `_may_repeat`).
            if not _should_retry(resp.status_code):
                raise error
            if not repeatable and not isinstance(error, RateLimitError):
                raise error

            last_exc = error

            if attempt >= self._max_retries or not _worth_waiting(error):
                raise error
            if isinstance(error, RateLimitError):
                time.sleep(error.retry_after)
            else:
                time.sleep(_backoff(attempt))

        if last_exc is not None:
            raise last_exc
        raise NetworkError("Request failed after retries")  # pragma: no cover

    def close(self) -> None:
        """Close the HTTP client if the SDK created it; a caller-supplied one stays open."""
        if self._owns_client:
            self._client.close()


class AsyncTransport(_BaseTransport):
    """Asynchronous HTTP transport backed by httpx.AsyncClient."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: TimeoutArg = NOT_GIVEN,
        max_retries: int = DEFAULT_MAX_RETRIES,
        debug: bool = False,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        super().__init__(
            api_key, base_url, timeout, max_retries, debug, custom_client=http_client is not None
        )
        self._client = http_client if http_client is not None else httpx.AsyncClient()

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

        kwargs = self._request_kwargs(json, params, idempotency_key)
        url = self._url(path)
        repeatable = _may_repeat(method, idempotency_key)
        self._log(method, path, kwargs["params"])

        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            try:
                resp = await self._client.request(method, url, **kwargs)
            except httpx.TimeoutException as exc:
                last_exc = self._timeout_error(exc)
                if attempt < self._max_retries and (repeatable or _never_sent(exc)):
                    await asyncio.sleep(_backoff(attempt))
                    continue
                raise last_exc from exc
            except (httpx.HTTPError, httpx.InvalidURL) as exc:
                last_exc = NetworkError(str(exc), cause=exc)
                if (
                    not _is_config_error(exc)
                    and attempt < self._max_retries
                    and (repeatable or _never_sent(exc))
                ):
                    await asyncio.sleep(_backoff(attempt))
                    continue
                raise last_exc from exc

            if resp.status_code == 204:
                return None
            if resp.is_success:
                return _decode_body(resp)

            error = self._error_for(resp)

            if not _should_retry(resp.status_code):
                raise error
            if not repeatable and not isinstance(error, RateLimitError):
                raise error

            last_exc = error

            if attempt >= self._max_retries or not _worth_waiting(error):
                raise error
            if isinstance(error, RateLimitError):
                await asyncio.sleep(error.retry_after)
            else:
                await asyncio.sleep(_backoff(attempt))

        if last_exc is not None:
            raise last_exc
        raise NetworkError("Request failed after retries")  # pragma: no cover

    async def close(self) -> None:
        """Close the HTTP client if the SDK created it; a caller-supplied one stays open."""
        if self._owns_client:
            await self._client.aclose()
