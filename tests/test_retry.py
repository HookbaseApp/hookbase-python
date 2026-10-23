"""Retry policy, Retry-After handling and response decoding of both transports.

Policy (shared by every Hookbase SDK):
* 429 is retried for every method, after ``Retry-After``.
* 5xx, read timeouts and dropped connections are retried only when the request is safe to
  repeat: any method but POST, or a POST that carries an idempotency key.
* A connection that was never made is always retried.
* Every other 4xx is never retried.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

import httpx
import pytest

from hookbase import (
    APIError,
    AsyncHookbase,
    ConflictError,
    Hookbase,
    NetworkError,
    NotFoundError,
    RateLimitError,
    TimeoutError,
    ValidationError,
)
from hookbase._client import _backoff, _parse_retry_after

from .conftest import TEST_API_KEY

SOURCES = "/api/sources"
SOURCE = "/api/sources/src_1"
OK_LIST = {"sources": [], "pagination": {"total": 0, "page": 1, "pageSize": 20}}
OK_SOURCE = {"source": {"id": "src_1", "name": "S", "slug": "s"}}


@pytest.fixture
def sleeps(monkeypatch):
    """Record every sleep the transports ask for instead of waiting."""
    recorded: list[float] = []
    monkeypatch.setattr("hookbase._client.time.sleep", recorded.append)

    async def _fast(seconds: float) -> None:
        recorded.append(seconds)

    monkeypatch.setattr(asyncio, "sleep", _fast)
    monkeypatch.setattr("hookbase._client.random.random", lambda: 0.0)
    return recorded


# ----------------------------------------------------------------------------- Retry-After


def test_parse_retry_after_delta_seconds():
    assert _parse_retry_after("7") == 7.0
    assert _parse_retry_after(" 1.5 ") == 1.5


def test_parse_retry_after_http_date():
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    header = format_datetime(now + timedelta(seconds=30), usegmt=True)
    assert _parse_retry_after(header, now=now.timestamp()) == pytest.approx(30.0)


def test_parse_retry_after_past_date_and_negative_are_zero():
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    past = format_datetime(now - timedelta(seconds=30), usegmt=True)
    assert _parse_retry_after(past, now=now.timestamp()) == 0.0
    assert _parse_retry_after("-5") == 0.0


@pytest.mark.parametrize("header", [None, "", "soon", "inf", "nan"])
def test_parse_retry_after_unusable_falls_back_to_60(header):
    assert _parse_retry_after(header) == 60.0


def test_backoff_is_exponential_and_capped(monkeypatch):
    monkeypatch.setattr("hookbase._client.random.random", lambda: 0.5)
    assert [_backoff(a) for a in range(6)] == [1.5, 2.5, 4.5, 8.5, 10.5, 10.5]


# ----------------------------------------------------------------------------- 429


def test_429_waits_retry_after_then_succeeds(mock_api, client, sleeps):
    route = mock_api.get(SOURCES).mock(side_effect=[
        httpx.Response(429, json={"error": "Too many"}, headers={"Retry-After": "3"}),
        httpx.Response(200, json=OK_LIST),
    ])
    client.sources.list()
    assert route.call_count == 2
    assert sleeps == [3.0]


def test_429_without_retry_after_waits_60(mock_api, client, sleeps):
    mock_api.get(SOURCES).mock(side_effect=[
        httpx.Response(429, json={"error": "Too many"}),
        httpx.Response(200, json=OK_LIST),
    ])
    client.sources.list()
    assert sleeps == [60.0]


def test_429_on_post_without_key_is_retried(mock_api, client, sleeps):
    route = mock_api.post(SOURCES).mock(side_effect=[
        httpx.Response(429, json={"error": "Too many"}, headers={"Retry-After": "1"}),
        httpx.Response(201, json=OK_SOURCE),
    ])
    client.sources.create({"name": "S", "provider": "generic"})
    assert route.call_count == 2


def test_429_gives_up_after_max_retries(mock_api, sleeps):
    route = mock_api.get(SOURCES).mock(
        return_value=httpx.Response(429, json={"error": "Slow down", "code": "RATE_LIMITED"},
                                    headers={"Retry-After": "2", "x-request-id": "req_9"}),
    )
    client = Hookbase(api_key=TEST_API_KEY, max_retries=2)
    with pytest.raises(RateLimitError) as exc:
        client.sources.list()
    assert route.call_count == 3
    assert sleeps == [2.0, 2.0]
    assert exc.value.retry_after == 2.0
    assert exc.value.code == "RATE_LIMITED"
    assert exc.value.request_id == "req_9"


# ----------------------------------------------------------------------------- 5xx


@pytest.mark.parametrize("status", [500, 502, 503, 504, 520, 522])
def test_get_retries_every_5xx(mock_api, client, sleeps, status):
    route = mock_api.get(SOURCE).mock(side_effect=[
        httpx.Response(status, json={"error": "boom"}),
        httpx.Response(200, json=OK_SOURCE),
    ])
    assert client.sources.get("src_1").id == "src_1"
    assert route.call_count == 2
    assert sleeps == [1.0]


def test_5xx_backoff_grows_until_max_retries(mock_api, client, sleeps):
    route = mock_api.get(SOURCE).mock(return_value=httpx.Response(503, json={"error": "down"}))
    with pytest.raises(APIError) as exc:
        client.sources.get("src_1")
    assert exc.value.status_code == 503
    assert route.call_count == 4  # first try + 3 retries
    assert sleeps == [1.0, 2.0, 4.0]


@pytest.mark.parametrize("method,call", [
    ("PATCH", lambda c: c.sources.update("src_1", {"name": "x"})),
    ("DELETE", lambda c: c.sources.delete("src_1")),
])
def test_non_post_writes_are_retried_on_5xx(mock_api, client, sleeps, method, call):
    route = mock_api.request(method, SOURCE).mock(side_effect=[
        httpx.Response(500, json={"error": "boom"}),
        httpx.Response(200, json={"success": True}),
    ])
    call(client)
    assert route.call_count == 2


def test_post_without_key_is_not_retried_on_5xx(mock_api, client, sleeps):
    route = mock_api.post(SOURCES).mock(return_value=httpx.Response(502, json={"error": "bad"}))
    with pytest.raises(APIError):
        client.sources.create({"name": "S", "provider": "generic"})
    assert route.call_count == 1
    assert sleeps == []


def test_max_retries_zero_never_retries(mock_api, sleeps):
    route = mock_api.get(SOURCE).mock(return_value=httpx.Response(500, json={"error": "x"}))
    with pytest.raises(APIError):
        Hookbase(api_key=TEST_API_KEY, max_retries=0).sources.get("src_1")
    assert route.call_count == 1


# ----------------------------------------------------------------------------- other 4xx


@pytest.mark.parametrize("status,exc_type", [
    (400, ValidationError), (404, NotFoundError), (409, ConflictError), (422, ValidationError),
    (408, APIError), (418, APIError),
])
def test_other_4xx_are_never_retried(mock_api, client, sleeps, status, exc_type):
    route = mock_api.get(SOURCE).mock(return_value=httpx.Response(status, json={"error": "no"}))
    with pytest.raises(exc_type) as exc:
        client.sources.get("src_1")
    assert exc.value.status_code == status
    assert route.call_count == 1
    assert sleeps == []


# ----------------------------------------------------------------------------- transport errors


def test_get_read_timeout_is_retried_then_raises_timeout_error(mock_api, client, sleeps):
    route = mock_api.get(SOURCE).mock(side_effect=httpx.ReadTimeout("slow"))
    with pytest.raises(TimeoutError, match="timed out after 30.0s"):
        client.sources.get("src_1")
    assert route.call_count == 4


def test_dropped_connection_on_get_is_retried(mock_api, client, sleeps):
    route = mock_api.get(SOURCE).mock(side_effect=[
        httpx.RemoteProtocolError("peer closed"),
        httpx.Response(200, json=OK_SOURCE),
    ])
    client.sources.get("src_1")
    assert route.call_count == 2


def test_connect_error_raises_network_error_after_retries(mock_api, client, sleeps):
    route = mock_api.get(SOURCE).mock(side_effect=httpx.ConnectError("refused"))
    with pytest.raises(NetworkError) as exc:
        client.sources.get("src_1")
    assert isinstance(exc.value.cause, httpx.ConnectError)
    assert route.call_count == 4


# ----------------------------------------------------------------------------- body decoding


def test_empty_2xx_body_is_none(mock_api, client):
    mock_api.delete(SOURCE).mock(
        return_value=httpx.Response(200, content=b"", headers={"content-type": "application/json"})
    )
    assert client.sources.delete("src_1") is None


def test_204_is_none(mock_api, client):
    mock_api.delete(SOURCE).mock(return_value=httpx.Response(204))
    assert client.sources.delete("src_1") is None


def test_invalid_json_2xx_raises_api_error(mock_api, client):
    mock_api.get(SOURCE).mock(return_value=httpx.Response(
        200, content=b"<html>proxy</html>", headers={"content-type": "application/json"},
    ))
    with pytest.raises(APIError) as exc:
        client.sources.get("src_1")
    assert exc.value.code == "invalid_response"
    assert exc.value.status_code == 200


def test_non_json_error_body_still_maps_status(mock_api, client):
    mock_api.get(SOURCE).mock(return_value=httpx.Response(
        404, content=b"not found", headers={"content-type": "text/plain"},
    ))
    with pytest.raises(NotFoundError) as exc:
        client.sources.get("src_1")
    assert str(exc.value) == "API error: 404"


def test_request_headers_and_query(mock_api, client):
    route = mock_api.get(SOURCES).mock(return_value=httpx.Response(200, json=OK_LIST))
    client.sources.list(page=2, page_size=5)
    req = route.calls.last.request
    assert req.headers["authorization"] == f"Bearer {TEST_API_KEY}"
    assert req.headers["accept"] == "application/json"
    assert req.headers["user-agent"].startswith("hookbase-python/")
    assert "idempotency-key" not in req.headers
    assert dict(req.url.params) == {"page": "2", "pageSize": "5"}


def test_none_query_params_are_dropped(mock_api, client):
    route = mock_api.get("/api/deliveries").mock(
        return_value=httpx.Response(200, json={"deliveries": [], "limit": 50, "offset": 0})
    )
    client.deliveries.list(status=None, limit=10)
    assert dict(route.calls.last.request.url.params) == {"limit": "10"}


# ----------------------------------------------------------------------------- async


async def test_async_429_then_success(mock_api, sleeps):
    route = mock_api.get(SOURCES).mock(side_effect=[
        httpx.Response(429, json={"error": "x"}, headers={"Retry-After": "4"}),
        httpx.Response(200, json=OK_LIST),
    ])
    async with AsyncHookbase(api_key=TEST_API_KEY) as client:
        await client.sources.list()
    assert route.call_count == 2
    assert sleeps == [4.0]


async def test_async_5xx_get_backoff_and_give_up(mock_api, sleeps):
    route = mock_api.get(SOURCE).mock(return_value=httpx.Response(520, json={"error": "x"}))
    async with AsyncHookbase(api_key=TEST_API_KEY, max_retries=2) as client:
        with pytest.raises(APIError):
            await client.sources.get("src_1")
    assert route.call_count == 3
    assert sleeps == [1.0, 2.0]


async def test_async_4xx_not_retried(mock_api, sleeps):
    route = mock_api.get(SOURCE).mock(return_value=httpx.Response(409, json={"error": "x"}))
    async with AsyncHookbase(api_key=TEST_API_KEY) as client:
        with pytest.raises(ConflictError):
            await client.sources.get("src_1")
    assert route.call_count == 1


async def test_async_post_without_key_not_retried_on_timeout(mock_api, sleeps):
    route = mock_api.post(SOURCES).mock(side_effect=httpx.ReadTimeout("slow"))
    async with AsyncHookbase(api_key=TEST_API_KEY) as client:
        with pytest.raises(TimeoutError):
            await client.sources.create({"name": "S", "provider": "generic"})
    assert route.call_count == 1


async def test_async_connect_error_on_post_is_retried(mock_api, sleeps):
    route = mock_api.post(SOURCES).mock(side_effect=[
        httpx.ConnectError("refused"),
        httpx.Response(201, json=OK_SOURCE),
    ])
    async with AsyncHookbase(api_key=TEST_API_KEY) as client:
        await client.sources.create({"name": "S", "provider": "generic"})
    assert route.call_count == 2


async def test_async_empty_body_and_invalid_json(mock_api):
    mock_api.delete(SOURCE).mock(return_value=httpx.Response(204))
    mock_api.get(SOURCE).mock(return_value=httpx.Response(
        200, content=b"{", headers={"content-type": "application/json"},
    ))
    async with AsyncHookbase(api_key=TEST_API_KEY) as client:
        assert await client.sources.delete("src_1") is None
        with pytest.raises(APIError):
            await client.sources.get("src_1")
