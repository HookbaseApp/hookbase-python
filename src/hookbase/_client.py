from __future__ import annotations

import logging
import random
import time
from typing import Any

import httpx

from ._constants import DEFAULT_BASE_URL, DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT, RETRY_STATUS_CODES
from ._version import __version__
from .errors import APIError, NetworkError, RateLimitError, TimeoutError

logger = logging.getLogger("hookbase")


def _parse_error(status_code: int, body: Any, request_id: str | None) -> APIError:
    return APIError.from_response(status_code, body, request_id)


def _build_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "User-Agent": f"hookbase-python/{__version__}",
        "Accept": "application/json",
    }


def _should_retry(status_code: int) -> bool:
    return status_code in RETRY_STATUS_CODES


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
    """JSON for JSON responses; the text for anything else (e.g. a CSV export)."""
    content_type = resp.headers.get("content-type", "")
    if content_type and "json" not in content_type.lower():
        return resp.text
    return resp.json()


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
        timeout: float | None,
        max_retries: int,
        debug: bool,
        custom_client: bool,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url.rstrip("/")
        # With a caller-supplied client and no explicit `timeout`, the client's own timeout
        # applies; otherwise the SDK's timeout is sent on every request.
        if timeout is None and not custom_client:
            timeout = DEFAULT_TIMEOUT
        self._timeout = timeout
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
        if url.scheme not in ("http", "https") or not url.host:
            invalid = httpx.InvalidURL(
                f"base_url must be an absolute http(s) URL, got {self._base_url!r}"
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
        }
        if self._timeout is not None:
            kwargs["timeout"] = self._timeout
        return kwargs

    def _timeout_error(self, exc: httpx.TimeoutException) -> TimeoutError:
        if self._timeout is not None:
            message = f"Request timed out after {self._timeout}s"
        else:
            # The caller's http_client timeout was in effect, not one the SDK set.
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
            retry_after_header = resp.headers.get("retry-after")
            if retry_after_header:
                try:
                    error.retry_after = float(retry_after_header)
                except ValueError:
                    pass
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
        timeout: float | None = None,
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
        """Close the HTTP client if the SDK created it; a caller-supplied one stays open."""
        if self._owns_client:
            self._client.close()


class AsyncTransport(_BaseTransport):
    """Asynchronous HTTP transport backed by httpx.AsyncClient."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float | None = None,
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
        """Close the HTTP client if the SDK created it; a caller-supplied one stays open."""
        if self._owns_client:
            await self._client.aclose()
