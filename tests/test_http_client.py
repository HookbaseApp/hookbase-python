"""A caller-supplied ``http_client`` is used as given (absolute URL, per-request headers)."""

from __future__ import annotations

from typing import Any

import httpx
import pytest

from hookbase import (
    AsyncHookbase,
    ForbiddenError,
    Hookbase,
    NetworkError,
    NotFoundError,
    TimeoutError,
    __version__,
)

API_KEY = "whr_custom_client"


class Recorder:
    """httpx MockTransport handler that records each request."""

    def __init__(self, response: httpx.Response | None = None) -> None:
        self.requests: list[httpx.Request] = []
        self.response = response or httpx.Response(200, json={"data": [], "pagination": {}})

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        return self.response


def _timeout_of(request: httpx.Request) -> dict[str, Any]:
    return request.extensions["timeout"]


def _assert_configured(request: httpx.Request, base: str = "https://api.hookbase.app") -> None:
    assert str(request.url).startswith(f"{base}/api/sources")
    assert request.headers["authorization"] == f"Bearer {API_KEY}"
    assert request.headers["user-agent"] == f"hookbase-python/{__version__}"


# --------------------------------------------------------------------------- sync


def test_sync_custom_client_gets_url_auth_and_user_agent():
    rec = Recorder()
    http = httpx.Client(transport=httpx.MockTransport(rec))
    client = Hookbase(api_key=API_KEY, http_client=http)

    client.sources.list()

    assert len(rec.requests) == 1
    _assert_configured(rec.requests[0])


def test_sync_custom_client_honours_base_url():
    rec = Recorder()
    http = httpx.Client(transport=httpx.MockTransport(rec))
    client = Hookbase(api_key=API_KEY, base_url="https://staging.example.test/", http_client=http)

    client.sources.list()

    _assert_configured(rec.requests[0], base="https://staging.example.test")


def test_sync_custom_client_is_not_mutated():
    rec = Recorder()
    http = httpx.Client(transport=httpx.MockTransport(rec), headers={"X-Custom": "1"}, timeout=7.0)
    before_headers = dict(http.headers)
    before_base = http.base_url
    before_timeout = http.timeout

    client = Hookbase(api_key=API_KEY, http_client=http, timeout=12.0)
    client.sources.list()

    assert dict(http.headers) == before_headers
    assert http.base_url == before_base
    assert http.timeout == before_timeout
    # The client's own headers still go out alongside the SDK's.
    assert rec.requests[0].headers["x-custom"] == "1"


def test_sync_explicit_timeout_is_sent_per_request():
    rec = Recorder()
    http = httpx.Client(transport=httpx.MockTransport(rec), timeout=7.0)
    Hookbase(api_key=API_KEY, http_client=http, timeout=12.0).sources.list()
    assert _timeout_of(rec.requests[0])["read"] == 12.0


def test_sync_custom_client_keeps_its_timeout_when_none_given():
    rec = Recorder()
    http = httpx.Client(transport=httpx.MockTransport(rec), timeout=7.0)
    Hookbase(api_key=API_KEY, http_client=http).sources.list()
    assert _timeout_of(rec.requests[0])["read"] == 7.0


def test_sync_owned_client_uses_default_timeout(monkeypatch):
    rec = Recorder()
    client = Hookbase(api_key=API_KEY)
    client._transport._client = httpx.Client(transport=httpx.MockTransport(rec))
    client.sources.list()
    _assert_configured(rec.requests[0])
    assert _timeout_of(rec.requests[0])["read"] == 30.0


def test_sync_close_leaves_custom_client_open():
    http = httpx.Client(transport=httpx.MockTransport(Recorder()))
    client = Hookbase(api_key=API_KEY, http_client=http)
    client.close()
    assert not http.is_closed
    http.close()


def test_sync_close_closes_owned_client():
    client = Hookbase(api_key=API_KEY)
    inner = client._transport._client
    client.close()
    assert inner.is_closed


def test_sync_custom_client_error_body_is_parsed():
    rec = Recorder(httpx.Response(404, json={"error": "Source not found", "code": "NOT_FOUND"}))
    http = httpx.Client(transport=httpx.MockTransport(rec))
    with pytest.raises(NotFoundError) as exc_info:
        Hookbase(api_key=API_KEY, http_client=http, max_retries=0).sources.get("src_1")
    assert exc_info.value.code == "NOT_FOUND"


def test_sync_invalid_base_url_maps_to_hookbase_error():
    rec = Recorder()
    http = httpx.Client(transport=httpx.MockTransport(rec))
    client = Hookbase(api_key=API_KEY, base_url="api.hookbase.app", http_client=http)
    with pytest.raises(NetworkError) as exc_info:
        client.sources.list()
    assert isinstance(exc_info.value.cause, httpx.InvalidURL)
    assert rec.requests == []


def test_sync_malformed_base_url_maps_to_hookbase_error():
    http = httpx.Client(transport=httpx.MockTransport(Recorder()))
    client = Hookbase(api_key=API_KEY, base_url="https://host:abc", http_client=http)
    with pytest.raises(NetworkError) as exc_info:
        client.sources.list()
    assert isinstance(exc_info.value.cause, httpx.InvalidURL)


def test_sync_owned_client_invalid_base_url_maps_to_hookbase_error():
    client = Hookbase(api_key=API_KEY, base_url="ftp://api.hookbase.app")
    with pytest.raises(NetworkError):
        client.sources.list()
    client.close()


def test_sync_custom_client_transport_error_maps_to_network_error(monkeypatch):
    monkeypatch.setattr("hookbase._client.time.sleep", lambda _s: None)

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("refused", request=request)

    http = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(NetworkError):
        Hookbase(api_key=API_KEY, http_client=http, max_retries=1).sources.list()


def test_sync_timeout_message_names_sdk_timeout_only_when_it_applied():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    http = httpx.Client(transport=httpx.MockTransport(handler), timeout=3.0)

    with pytest.raises(TimeoutError) as own:
        Hookbase(api_key=API_KEY, http_client=http, max_retries=0).sources.list()
    assert str(own.value) == "Request timed out"

    with pytest.raises(TimeoutError) as sdk:
        Hookbase(api_key=API_KEY, http_client=http, max_retries=0, timeout=5.0).sources.list()
    assert str(sdk.value) == "Request timed out after 5.0s"


# --------------------------------------------------------------------------- async


async def test_async_custom_client_gets_url_auth_user_agent_and_timeout():
    rec = Recorder()
    http = httpx.AsyncClient(transport=httpx.MockTransport(rec), timeout=7.0)
    client = AsyncHookbase(api_key=API_KEY, http_client=http, timeout=9.0)

    await client.sources.list()

    _assert_configured(rec.requests[0])
    assert _timeout_of(rec.requests[0])["read"] == 9.0
    assert http.timeout.read == 7.0
    await http.aclose()


async def test_async_custom_client_keeps_its_timeout_when_none_given():
    rec = Recorder()
    http = httpx.AsyncClient(transport=httpx.MockTransport(rec), timeout=7.0)
    await AsyncHookbase(api_key=API_KEY, http_client=http).sources.list()
    assert _timeout_of(rec.requests[0])["read"] == 7.0
    await http.aclose()


async def test_async_close_leaves_custom_client_open():
    http = httpx.AsyncClient(transport=httpx.MockTransport(Recorder()))
    client = AsyncHookbase(api_key=API_KEY, http_client=http)
    await client.close()
    assert not http.is_closed
    await http.aclose()


async def test_async_close_closes_owned_client():
    client = AsyncHookbase(api_key=API_KEY)
    inner = client._transport._client
    await client.close()
    assert inner.is_closed


async def test_async_custom_client_error_body_is_parsed():
    rec = Recorder(
        httpx.Response(403, json={"error": "Limit", "code": "LIMIT_EXCEEDED", "max": 5})
    )
    http = httpx.AsyncClient(transport=httpx.MockTransport(rec))
    with pytest.raises(ForbiddenError) as exc_info:
        await AsyncHookbase(api_key=API_KEY, http_client=http).sources.list()
    assert exc_info.value.code == "LIMIT_EXCEEDED"
    assert exc_info.value.details == {"max": 5}
    await http.aclose()


async def test_async_invalid_base_url_maps_to_hookbase_error():
    http = httpx.AsyncClient(transport=httpx.MockTransport(Recorder()))
    client = AsyncHookbase(api_key=API_KEY, base_url="api.hookbase.app", http_client=http)
    with pytest.raises(NetworkError):
        await client.sources.list()
    await http.aclose()


async def test_async_timeout_message_with_client_timeout():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    http = httpx.AsyncClient(transport=httpx.MockTransport(handler))
    with pytest.raises(TimeoutError) as exc_info:
        await AsyncHookbase(api_key=API_KEY, http_client=http, max_retries=0).sources.list()
    assert str(exc_info.value) == "Request timed out"
    await http.aclose()
