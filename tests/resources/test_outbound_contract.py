"""Outbound surface vs the API's wire contract.

Each test pins one request or response shape to the API route it was checked
against (api/src/routes/send-event.ts, outbound-messages.ts,
webhook-endpoints.ts, webhook-subscriptions.ts, event-types.ts,
webhook-applications.ts).
"""

from __future__ import annotations

import asyncio
import json
import uuid
import warnings

import httpx
import pytest
import respx

from hookbase import APIError, AsyncHookbase, Hookbase, NetworkError, TimeoutError
from hookbase.models import (
    Application,
    DlqBulkRetryResult,
    EventType,
    OutboundAttempt,
    OutboundMessage,
)
from hookbase.models.subscriptions import (
    CreateSubscriptionParams,
    Subscription,
    UpdateSubscriptionParams,
)

from ..conftest import make_cursor_response, sent_body

BASE = "https://api.hookbase.app"
SEND_OK = {"data": {"eventId": "evt_1", "messagesQueued": 1, "endpoints": []}}


@pytest.fixture
def mock_api():
    with respx.mock(base_url=BASE) as mock:
        yield mock


@pytest.fixture
def client(mock_api):
    c = Hookbase(api_key="whr_test")
    yield c
    c.close()


@pytest.fixture
def no_sleep(monkeypatch):
    """Skip retry backoff."""
    monkeypatch.setattr("hookbase._client.time.sleep", lambda _s: None)

    async def _fast(_s: float) -> None:
        return None

    monkeypatch.setattr(asyncio, "sleep", _fast)


# --- send-event --------------------------------------------------------------


def test_send_puts_a_generated_idempotency_key_in_body_and_header(mock_api, client):
    route = mock_api.post("/api/send-event").respond(201, json=SEND_OK)
    client.outbound.messages.send("app_1", event_type="order.created", payload={"a": 1})

    body = sent_body(route)
    key = body["idempotencyKey"]
    uuid.UUID(key)  # a fresh UUID per call
    assert route.calls.last.request.headers["Idempotency-Key"] == key
    assert body == {
        "applicationId": "app_1",
        "eventType": "order.created",
        "payload": {"a": 1},
        "idempotencyKey": key,
    }


def test_send_uses_the_callers_idempotency_key(mock_api, client):
    route = mock_api.post("/api/send-event").respond(201, json=SEND_OK)
    client.outbound.messages.send(
        "app_1", event_type="order.created", payload={}, idempotency_key="order-42",
    )
    assert sent_body(route)["idempotencyKey"] == "order-42"
    assert route.calls.last.request.headers["Idempotency-Key"] == "order-42"


def test_send_generates_a_new_key_per_call(mock_api, client):
    route = mock_api.post("/api/send-event").respond(201, json=SEND_OK)
    client.outbound.messages.send("app_1", event_type="a", payload={})
    client.outbound.messages.send("app_1", event_type="a", payload={})
    keys = {json.loads(c.request.content)["idempotencyKey"] for c in route.calls}
    assert len(keys) == 2


def test_send_single_target_also_sends_singular_endpoint_id(mock_api, client):
    route = mock_api.post("/api/send-event").respond(201, json=SEND_OK)
    client.outbound.messages.send(
        "app_1", event_type="a", payload={}, endpoint_ids=["ep_1"],
    )
    body = sent_body(route)
    assert body["endpointIds"] == ["ep_1"]
    assert body["endpointId"] == "ep_1"


def test_send_several_targets_sends_only_the_plural(mock_api, client):
    route = mock_api.post("/api/send-event").respond(201, json=SEND_OK)
    client.outbound.messages.send(
        "app_1", event_type="a", payload={}, endpoint_ids=["ep_1", "ep_2"],
    )
    body = sent_body(route)
    assert body["endpointIds"] == ["ep_1", "ep_2"]
    assert "endpointId" not in body


def test_send_merges_endpoint_id_into_the_targets(mock_api, client):
    route = mock_api.post("/api/send-event").respond(201, json=SEND_OK)
    client.outbound.messages.send("app_1", event_type="a", payload={}, endpoint_id="ep_9")
    body = sent_body(route)
    assert body["endpointIds"] == ["ep_9"]
    assert body["endpointId"] == "ep_9"


def test_send_empty_targets_sends_neither(mock_api, client):
    route = mock_api.post("/api/send-event").respond(201, json=SEND_OK)
    client.outbound.messages.send("app_1", event_type="a", payload={}, endpoint_ids=[])
    body = sent_body(route)
    assert "endpointIds" not in body and "endpointId" not in body


def test_send_labels_priority_metadata_and_no_event_id(mock_api, client):
    route = mock_api.post("/api/send-event").respond(201, json=SEND_OK)
    client.outbound.messages.send(
        "app_1", event_type="a", payload=[1, 2],
        labels={"tenant": "acme"}, priority=1, metadata={"k": "v"}, event_id="ignored",
    )
    body = sent_body(route)
    assert body["labels"] == {"tenant": "acme"}
    assert body["priority"] == 1
    assert body["metadata"] == {"k": "v"}
    assert body["payload"] == [1, 2]
    # `sendEventSchema` has no eventId; the API assigns it.
    assert "eventId" not in body


def test_send_retries_reuse_the_same_idempotency_key(mock_api, client, no_sleep):
    route = mock_api.post("/api/send-event").mock(side_effect=[
        httpx.Response(503, json={"error": "unavailable"}),
        httpx.Response(502, json={"error": "bad gateway"}),
        httpx.Response(201, json=SEND_OK),
    ])
    result = client.outbound.messages.send("app_1", event_type="a", payload={})
    assert result.event_id == "evt_1"
    assert route.call_count == 3
    body_keys = {json.loads(c.request.content)["idempotencyKey"] for c in route.calls}
    header_keys = {c.request.headers["Idempotency-Key"] for c in route.calls}
    assert len(body_keys) == 1
    assert body_keys == header_keys


def test_send_retries_a_read_timeout_with_the_same_key(mock_api, client, no_sleep):
    route = mock_api.post("/api/send-event").mock(side_effect=[
        httpx.ReadTimeout("slow"),
        httpx.Response(201, json=SEND_OK),
    ])
    client.outbound.messages.send("app_1", event_type="a", payload={})
    assert route.call_count == 2
    assert len({c.request.headers["Idempotency-Key"] for c in route.calls}) == 1


async def test_async_send_retries_reuse_the_same_key(mock_api, no_sleep):
    route = mock_api.post("/api/send-event").mock(side_effect=[
        httpx.Response(500, json={"error": "boom"}),
        httpx.Response(201, json=SEND_OK),
    ])
    async with AsyncHookbase(api_key="whr_test") as c:
        await c.outbound.messages.send(
            "app_1", event_type="a", payload={}, endpoint_ids=["ep_1"],
        )
    assert route.call_count == 2
    bodies = [json.loads(call.request.content) for call in route.calls]
    assert bodies[0] == bodies[1]
    assert bodies[0]["endpointId"] == "ep_1"
    assert bodies[0]["idempotencyKey"] == route.calls[0].request.headers["Idempotency-Key"]


# --- retry policy for other POSTs ---------------------------------------------


def test_post_without_key_is_not_retried_on_5xx(mock_api, client, no_sleep):
    route = mock_api.post("/api/outbound-messages/dlq/m_1/retry").respond(
        503, json={"error": "unavailable"},
    )
    with pytest.raises(APIError):
        client.outbound.dlq.retry("m_1")
    assert route.call_count == 1


def test_post_without_key_is_not_retried_on_read_timeout(mock_api, client, no_sleep):
    route = mock_api.post("/api/webhook-endpoints/ep_1/rotate-secret").mock(
        side_effect=httpx.ReadTimeout("slow"),
    )
    with pytest.raises(TimeoutError):
        client.outbound.endpoints.rotate_secret("ep_1")
    assert route.call_count == 1


def test_post_without_key_is_retried_when_the_connection_never_opened(
    mock_api, client, no_sleep,
):
    route = mock_api.post("/api/outbound-messages/m_1/replay").mock(side_effect=[
        httpx.ConnectError("refused"),
        httpx.Response(201, json={"data": {"originalMessageId": "m_1", "newMessageId": "m_2"}}),
    ])
    assert client.outbound.message_log.replay("m_1").new_message_id == "m_2"
    assert route.call_count == 2


def test_post_without_key_is_retried_on_429(mock_api, client, no_sleep):
    route = mock_api.post("/api/outbound-messages/dlq/m_1/retry").mock(side_effect=[
        httpx.Response(429, json={"error": "slow down"}, headers={"retry-after": "0"}),
        httpx.Response(201, json={"data": {"newMessageId": "m_2"}}),
    ])
    assert client.outbound.dlq.retry("m_1").new_message_id == "m_2"
    assert route.call_count == 2


def test_post_without_key_network_error_after_send_is_not_retried(mock_api, client, no_sleep):
    route = mock_api.post("/api/outbound-messages/dlq/retry-bulk").mock(
        side_effect=httpx.RemoteProtocolError("dropped"),
    )
    with pytest.raises(NetworkError):
        client.outbound.dlq.retry_bulk(["m_1"])
    assert route.call_count == 1


def test_get_is_still_retried_on_5xx(mock_api, client, no_sleep):
    route = mock_api.get("/api/outbound-messages/stats/summary").mock(side_effect=[
        httpx.Response(500, json={"error": "boom"}),
        httpx.Response(200, json={"data": {"total": 1}}),
    ])
    assert client.outbound.message_log.stats().total == 1
    assert route.call_count == 2


async def test_async_post_without_key_is_not_retried_on_5xx(mock_api, no_sleep):
    route = mock_api.post("/api/outbound-messages/dlq/m_1/retry").respond(
        500, json={"error": "boom"},
    )
    async with AsyncHookbase(api_key="whr_test") as c:
        with pytest.raises(APIError):
            await c.outbound.dlq.retry("m_1")
    assert route.call_count == 1


# --- pagination ----------------------------------------------------------------


def test_cursor_pages_pass_next_cursor_back_verbatim(mock_api, client):
    opaque = "eyJ0cyI6IjIwMjYtMTAtMTdUMDA6MDA6MDAuMDAwMDAwWiIsImlkIjoiYiJ9"
    route = mock_api.get("/api/outbound-messages").mock(side_effect=[
        httpx.Response(200, json=make_cursor_response(
            [{"id": "a", "eventId": "e"}], has_more=True, next_cursor=opaque,
        )),
        httpx.Response(200, json=make_cursor_response(
            [{"id": "b", "eventId": "e"}], has_more=True, next_cursor="2026-10-17T00:00:00Z",
        )),
        httpx.Response(200, json=make_cursor_response([{"id": "c", "eventId": "e"}])),
    ])
    page = client.outbound.message_log.list(status="failed", limit=1)
    ids = [m.id for m in page.auto_paging_iter()]
    assert ids == ["a", "b", "c"]
    assert route.call_count == 3
    params = [dict(c.request.url.params) for c in route.calls]
    assert "cursor" not in params[0]
    assert params[1] == {"status": "failed", "limit": "1", "cursor": opaque}
    assert params[2]["cursor"] == "2026-10-17T00:00:00Z"


def test_cursor_iteration_stops_when_has_more_lacks_a_cursor(mock_api, client):
    route = mock_api.get("/api/outbound-messages/dlq/messages").respond(
        200, json=make_cursor_response([{"id": "a"}], has_more=True, next_cursor=None),
    )
    assert [m.id for m in client.outbound.dlq.list().auto_paging_iter()] == ["a"]
    assert route.call_count == 1


async def test_async_cursor_pages_go_past_page_one(mock_api):
    route = mock_api.get("/api/webhook-endpoints").mock(side_effect=[
        httpx.Response(200, json=make_cursor_response(
            [{"id": "ep_1", "applicationId": "app", "url": "https://a"}],
            has_more=True, next_cursor="opaque==",
        )),
        httpx.Response(200, json=make_cursor_response(
            [{"id": "ep_2", "applicationId": "app", "url": "https://b"}],
        )),
    ])
    async with AsyncHookbase(api_key="whr_test") as c:
        page = await c.outbound.endpoints.list()
        ids = [ep.id async for ep in page.auto_paging_iter()]
    assert ids == ["ep_1", "ep_2"]
    assert route.calls[1].request.url.params["cursor"] == "opaque=="


# --- messages / attempts / stats / export ------------------------------------

LIST_ITEM = {
    "id": "om_1",
    "eventId": "evt_1",
    "eventType": "order.created",
    "applicationId": "app_1",
    "endpointId": "ep_1",
    "status": "failed",
    "attempts": 2,
    "maxAttempts": 5,
    "lastResponseStatus": 500,
    "lastErrorMessage": "HTTP 500",
    "createdAt": "2026-10-17T00:00:00Z",
    "completedAt": None,
    "endpointUrl": "https://a.example",
    "applicationName": "Acme",
}


@pytest.mark.parametrize("status", [
    "pending", "processing", "success", "failed", "awaiting_retry", "exhausted", "dlq",
    "some_future_status",
])
def test_message_list_accepts_every_status(mock_api, client, status):
    mock_api.get("/api/outbound-messages").respond(
        200, json=make_cursor_response([{**LIST_ITEM, "status": status}]),
    )
    assert client.outbound.message_log.list().data[0].status == status


def test_message_list_maps_the_api_field_names(mock_api, client):
    mock_api.get("/api/outbound-messages").respond(200, json=make_cursor_response([LIST_ITEM]))
    msg = client.outbound.message_log.list().data[0]
    assert isinstance(msg, OutboundMessage)
    assert msg.event_id == "evt_1"
    assert msg.application_id == "app_1"
    assert msg.application_name == "Acme"
    assert msg.last_error_message == "HTTP 500"
    assert msg.endpoint_url == "https://a.example"
    assert msg.completed_at is None
    # Deprecated names mirror the API ones instead of staying empty.
    assert msg.message_id == "evt_1"
    assert msg.last_error == "HTTP 500"


def test_message_list_sends_only_filters_the_api_reads(mock_api, client):
    route = mock_api.get("/api/outbound-messages").respond(200, json=make_cursor_response([]))
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        client.outbound.message_log.list(
            application_id="app_1", endpoint_id="ep_1", status="dlq", event_type="a.b",
            message_id="m", start_date="2026-01-01", end_date="2026-02-01", limit=10,
        )
    assert dict(route.calls.last.request.url.params) == {
        "applicationId": "app_1", "endpointId": "ep_1", "status": "dlq",
        "eventType": "a.b", "limit": "10",
    }
    assert any(issubclass(w.category, DeprecationWarning) for w in caught)


def test_message_get_maps_the_detail_fields(mock_api, client):
    mock_api.get("/api/outbound-messages/om_1").respond(200, json={"data": {
        **LIST_ITEM,
        "status": "success",
        "subscriptionId": "sub_1",
        "eventTypeId": "et_1",
        "lastErrorType": None,
        "payloadKey": "outbound/x.json",
        "payloadSizeBytes": 12,
        "payloadHash": "abc",
        "metadata": {"replayedFrom": "om_0"},
        "priority": 2,
        "completedAt": "2026-10-17T00:00:01Z",
        "endpointDescription": "primary",
        "payload": {"orderId": 1},
    }})
    msg = client.outbound.message_log.get("om_1")
    assert msg.subscription_id == "sub_1"
    assert msg.payload == {"orderId": 1}
    assert msg.metadata == {"replayedFrom": "om_0"}
    assert msg.priority == 2
    assert msg.completed_at == "2026-10-17T00:00:01Z"
    assert msg.delivered_at == "2026-10-17T00:00:01Z"


def test_attempts_map_the_api_field_names(mock_api, client):
    mock_api.get("/api/outbound-messages/om_1/attempts").respond(200, json={"data": [{
        "id": "att_1",
        "messageId": "om_1",
        "attemptNumber": 1,
        "status": "failed",
        "responseStatus": 500,
        "responseHeaders": {"content-type": "text/plain"},
        "responseBody": "nope",
        "responseTimeMs": 123,
        "totalTimeMs": 130,
        "errorType": "http_error",
        "errorMessage": "HTTP 500",
        "errorCode": None,
        "requestUrl": "https://a.example",
        "requestHeaders": {"webhook-id": "evt_1"},
        "requestBodySize": 42,
        "triggeredBy": "system",
        "triggeredByUser": None,
        "createdAt": "2026-10-17T00:00:00Z",
        "completedAt": "2026-10-17T00:00:00.130Z",
    }]})
    [att] = client.outbound.message_log.list_attempts("om_1")
    assert isinstance(att, OutboundAttempt)
    assert att.message_id == "om_1"
    assert att.status == "failed"
    assert att.response_time_ms == 123
    assert att.error_message == "HTTP 500"
    assert att.error_type == "http_error"
    assert att.triggered_by == "system"
    assert att.created_at == "2026-10-17T00:00:00Z"
    # Deprecated mirrors
    assert att.outbound_message_id == "om_1"
    assert att.latency_ms == 123
    assert att.error == "HTTP 500"
    assert att.attempted_at == "2026-10-17T00:00:00Z"


def test_csv_export_returns_the_text(mock_api, client):
    csv = "id,eventType\nevt_1,\"order.created\""
    route = mock_api.get("/api/outbound-messages/export").respond(
        200, text=csv, headers={"content-type": "text/csv"},
    )
    assert client.outbound.message_log.export(format="csv", type="messages") == csv
    assert dict(route.calls.last.request.url.params) == {"format": "csv", "type": "messages"}


def test_json_export_returns_the_object(mock_api, client):
    mock_api.get("/api/outbound-messages/export").respond(
        200, json={"count": 0, "events": []},
    )
    assert client.outbound.message_log.export() == {"count": 0, "events": []}


# --- DLQ -----------------------------------------------------------------------


def test_dlq_list_sends_reason_and_maps_fields(mock_api, client):
    route = mock_api.get("/api/outbound-messages/dlq/messages").respond(
        200, json=make_cursor_response([{
            "id": "om_1", "eventId": "evt_1", "status": "dlq",
            "lastErrorMessage": "HTTP 500", "dlqReason": "max_retries_exceeded",
            "dlqRetryCount": 2,
        }]),
    )
    page = client.outbound.dlq.list(
        dlq_reason="max_retries_exceeded", start_date="2026-01-01", end_date="2026-02-01",
    )
    assert dict(route.calls.last.request.url.params) == {
        "reason": "max_retries_exceeded", "startDate": "2026-01-01", "endDate": "2026-02-01",
    }
    msg = page.data[0]
    assert msg.event_id == "evt_1"
    assert msg.last_error_message == "HTTP 500"
    assert msg.dlq_retry_count == 2
    assert msg.message_id == "evt_1"
    assert msg.last_error == "HTTP 500"


def test_dlq_stats_maps_by_endpoint_and_by_event_type(mock_api, client):
    mock_api.get("/api/outbound-messages/dlq/stats").respond(200, json={"data": {
        "total": 3,
        "byReason": {"max_retries_exceeded": 3},
        "byEndpoint": [{"endpointId": "ep_1", "count": 3}],
        "byEventType": [{"eventType": "order.created", "count": 3}],
    }})
    stats = client.outbound.dlq.stats()
    assert stats.by_endpoint[0].endpoint_id == "ep_1"
    assert stats.by_endpoint[0].count == 3
    assert stats.by_event_type[0].event_type == "order.created"
    assert stats.top_failing_endpoints == stats.by_endpoint


BULK_RETRY_RESPONSE = {"data": {
    "queued": 2,
    "skipped": 1,
    "messages": [
        {"originalMessageId": "m_1", "newMessageId": "n_1"},
        {"originalMessageId": "m_2", "newMessageId": "n_2"},
    ],
}}


def test_dlq_retry_bulk_sends_message_ids_and_unwraps_data(mock_api, client):
    route = mock_api.post("/api/outbound-messages/dlq/retry-bulk").respond(
        201, json=BULK_RETRY_RESPONSE,
    )
    result = client.outbound.dlq.retry_bulk(["m_1", "m_2", "m_3"])
    assert sent_body(route) == {"messageIds": ["m_1", "m_2", "m_3"]}
    assert isinstance(result, DlqBulkRetryResult)
    assert result.queued == 2
    assert result.skipped == 1
    assert [(m.original_message_id, m.new_message_id) for m in result.messages] == [
        ("m_1", "n_1"), ("m_2", "n_2"),
    ]
    # Deprecated names derived from the real ones
    assert (result.total, result.retried, result.failed) == (3, 2, 1)
    assert result.results[0].message_id == "m_1"
    assert result.results[0].status == "queued"


async def test_async_dlq_bulk_routes(mock_api):
    retry = mock_api.post("/api/outbound-messages/dlq/retry-bulk").respond(
        201, json=BULK_RETRY_RESPONSE,
    )
    delete = mock_api.delete("/api/outbound-messages/dlq/bulk").respond(
        200, json={"data": {"deleted": 2}},
    )
    async with AsyncHookbase(api_key="whr_test") as c:
        r = await c.outbound.dlq.retry_bulk(["m_1", "m_2"])
        d = await c.outbound.dlq.bulk_delete(["m_1", "m_2"])
    assert sent_body(retry) == {"messageIds": ["m_1", "m_2"]}
    assert sent_body(delete) == {"messageIds": ["m_1", "m_2"]}
    assert r.queued == 2
    assert d.deleted == 2


# --- endpoints -------------------------------------------------------------------


def test_rotate_secret_maps_the_response(mock_api, client):
    mock_api.post("/api/webhook-endpoints/ep_1/rotate-secret").respond(200, json={
        "secret": "whsec_new",
        "previousSecretExpiresAt": "2026-10-17T01:00:00.000Z",
        "secretVersion": 3,
    })
    result = client.outbound.endpoints.rotate_secret("ep_1")
    assert result.secret == "whsec_new"
    assert result.previous_secret_expires_at == "2026-10-17T01:00:00.000Z"
    assert result.secret_version == 3
    assert result.previous_secret_valid_until == "2026-10-17T01:00:00.000Z"


def test_rotate_secret_on_an_ed25519_endpoint_returns_the_public_keys(mock_api, client):
    # The API never returns the Ed25519 private key, so the response has no `secret`.
    mock_api.post("/api/webhook-endpoints/ep_1/rotate-secret").respond(200, json={
        "signatureScheme": "ed25519",
        "publicKey": "whpk_new",
        "previousPublicKey": "whpk_old",
        "previousSecretExpiresAt": "2026-10-17T01:00:00.000Z",
        "secretVersion": 2,
    })
    result = client.outbound.endpoints.rotate_secret("ep_1")
    assert result.signature_scheme == "ed25519"
    assert result.public_key == "whpk_new"
    assert result.previous_public_key == "whpk_old"
    assert result.secret == ""
    assert result.secret_version == 2


def test_rotate_secret_on_an_hmac_endpoint_reports_the_scheme(mock_api, client):
    mock_api.post("/api/webhook-endpoints/ep_1/rotate-secret").respond(200, json={
        "signatureScheme": "hmac-sha256",
        "secret": "whsec_new",
        "secretVersion": 2,
    })
    result = client.outbound.endpoints.rotate_secret("ep_1")
    assert result.signature_scheme == "hmac-sha256"
    assert result.public_key is None


def test_create_ed25519_endpoint_sends_the_scheme_and_reads_the_public_key(mock_api, client):
    from hookbase.models import CreateEndpointParams

    route = mock_api.post("/api/webhook-endpoints").respond(201, json={"data": {
        "id": "ep_1", "applicationId": "app_1", "url": "https://example.com/hook",
        "signatureScheme": "ed25519", "publicKey": "whpk_abc",
        "secretPrefix": "whsk_...", "hasSecret": True,
    }})
    ep = client.outbound.endpoints.create(
        "app_1",
        CreateEndpointParams(url="https://example.com/hook", signature_scheme="ed25519"),
    )
    assert sent_body(route)["signatureScheme"] == "ed25519"
    assert ep.signature_scheme == "ed25519"
    assert ep.public_key == "whpk_abc"
    assert ep.secret == ""


def test_endpoint_test_sends_event_type_and_payload(mock_api, client):
    route = mock_api.post("/api/webhook-endpoints/ep_1/test").respond(
        200, json={"success": True},
    )
    client.outbound.endpoints.test("ep_1", event_type="order.created", payload={"x": 1})
    assert sent_body(route) == {"eventType": "order.created", "payload": {"x": 1}}


def test_endpoint_test_without_options_sends_no_body(mock_api, client):
    route = mock_api.post("/api/webhook-endpoints/ep_1/test").respond(
        200, json={"success": True},
    )
    client.outbound.endpoints.test("ep_1")
    assert route.calls.last.request.content == b""


def test_endpoint_verify_is_deprecated(mock_api, client):
    mock_api.post("/api/webhook-endpoints/ep_1/verify").respond(404, json={"error": "nf"})
    with pytest.warns(DeprecationWarning), pytest.raises(APIError):
        client.outbound.endpoints.verify("ep_1")


# --- subscriptions ------------------------------------------------------------


def test_subscription_bulk_create_reads_subscriptions(mock_api, client):
    route = mock_api.post("/api/webhook-subscriptions/bulk").respond(201, json={
        "created": 1,
        "skipped": 1,
        "subscriptions": [{
            "id": "sub_1", "endpointId": "ep_1", "eventTypeId": "et_1",
            "labelFilters": None, "labelFilterMode": "all", "isEnabled": True,
            "createdAt": "2026-10-17T00:00:00Z",
        }],
    })
    subs = client.outbound.subscriptions.bulk_create("ep_1", ["et_1", "et_2"])
    assert sent_body(route) == {"endpointId": "ep_1", "eventTypeIds": ["et_1", "et_2"]}
    assert [s.id for s in subs] == ["sub_1"]
    assert subs[0].label_filter_mode == "all"


def test_subscription_bulk_create_when_all_exist(mock_api, client):
    mock_api.post("/api/webhook-subscriptions/bulk").respond(200, json={
        "created": 0, "skipped": 2, "message": "All event types are already subscribed",
    })
    assert client.outbound.subscriptions.bulk_create("ep_1", ["et_1", "et_2"]) == []


def test_subscription_get_flattens_nested_objects(mock_api, client):
    mock_api.get("/api/webhook-subscriptions/sub_1").respond(200, json={"data": {
        "id": "sub_1", "endpointId": "ep_1", "eventTypeId": "et_1",
        "filterExpression": "$.amount > 10", "labelFilters": {"tier": ["gold"]},
        "labelFilterMode": "any", "transformId": None, "priorityOverride": 1,
        "isEnabled": True, "createdAt": "2026-10-17T00:00:00Z",
        "endpoint": {"id": "ep_1", "url": "https://a.example"},
        "eventType": {"id": "et_1", "name": "order.created", "displayName": "Order Created"},
        "application": {"id": "app_1", "name": "Acme"},
    }})
    sub = client.outbound.subscriptions.get("sub_1")
    assert isinstance(sub, Subscription)
    assert sub.event_type_name == "order.created"
    assert sub.event_type_display_name == "Order Created"
    assert sub.endpoint_url == "https://a.example"
    assert sub.application_id == "app_1"
    assert sub.filter_expression == "$.amount > 10"
    assert sub.priority_override == 1


def test_subscription_create_and_update_bodies(mock_api, client):
    sub = {"id": "s", "endpointId": "ep_1", "eventTypeId": "et_1"}
    create = mock_api.post("/api/webhook-subscriptions").respond(201, json={"data": sub})
    update = mock_api.patch("/api/webhook-subscriptions/s").respond(200, json={"data": sub})
    client.outbound.subscriptions.create(CreateSubscriptionParams(
        endpoint_id="ep_1", event_type_id="et_1", label_filters={"tier": "gold"},
        label_filter_mode="any", priority_override=0,
    ))
    client.outbound.subscriptions.update("s", UpdateSubscriptionParams(
        filter_expression="$.a", is_enabled=False,
    ))
    assert sent_body(create) == {
        "endpointId": "ep_1", "eventTypeId": "et_1", "labelFilters": {"tier": "gold"},
        "labelFilterMode": "any", "priorityOverride": 0,
    }
    assert sent_body(update) == {"filterExpression": "$.a", "isEnabled": False}


def test_subscription_list_application_filter(mock_api, client):
    route = mock_api.get("/api/webhook-subscriptions").respond(200, json=make_cursor_response([]))
    client.outbound.subscriptions.list(application_id="app_1")
    assert dict(route.calls.last.request.url.params) == {"applicationId": "app_1"}


# --- event types ------------------------------------------------------------------

EVENT_TYPE = {
    "id": "et_1", "organizationId": "org_1", "name": "order.created",
    "schema": {"type": "object"}, "examplePayload": {"id": 1},
    "isDeprecated": False, "isPublic": True, "defaultPriority": 2, "schemaVersion": 1,
}


def test_event_type_create_serializes_schema_to_a_json_string(mock_api, client):
    route = mock_api.post("/api/event-types").respond(201, json={"data": EVENT_TYPE})
    from hookbase.models import CreateEventTypeParams

    et = client.outbound.event_types.create(CreateEventTypeParams(
        name="order.created",
        schema={"type": "object"},
        example_payload={"id": 1},
        documentation_url="https://docs.example/order",
        default_priority=1,
    ))
    body = sent_body(route)
    assert body == {
        "name": "order.created",
        "schema": '{"type": "object"}',
        "examplePayload": '{"id": 1}',
        "documentationUrl": "https://docs.example/order",
        "defaultPriority": 1,
    }
    assert json.loads(body["schema"]) == {"type": "object"}
    assert isinstance(et, EventType)
    assert et.schema_ == {"type": "object"}
    assert et.is_public is True
    assert et.default_priority == 2


def test_event_type_dict_params_with_dict_schema(mock_api, client):
    route = mock_api.patch("/api/event-types/et_1").respond(200, json={"data": EVENT_TYPE})
    client.outbound.event_types.update("et_1", {
        "schema": {"type": "object"}, "example_payload": [1], "isDeprecated": True,
    })
    assert sent_body(route) == {
        "schema": '{"type": "object"}', "examplePayload": "[1]", "isDeprecated": True,
    }


def test_event_type_string_schema_passes_through(mock_api, client):
    route = mock_api.patch("/api/event-types/et_1").respond(200, json={"data": EVENT_TYPE})
    from hookbase.models import UpdateEventTypeParams

    client.outbound.event_types.update("et_1", UpdateEventTypeParams(
        schema='{"type":"object"}', is_public=True, deprecated_message="use v2",
    ))
    assert sent_body(route) == {
        "schema": '{"type":"object"}', "isPublic": True, "deprecatedMessage": "use v2",
    }


def test_event_type_response_decodes_json_text(mock_api, client):
    mock_api.get("/api/event-types/et_1").respond(200, json={"data": {
        **EVENT_TYPE, "schema": '{"type":"object"}', "examplePayload": '{"id":1}',
    }})
    et = client.outbound.event_types.get("et_1")
    assert et.schema_ == {"type": "object"}
    assert et.example_payload == {"id": 1}


# --- applications -------------------------------------------------------------------


def test_application_decodes_rate_limits_and_disabled_state(mock_api, client):
    mock_api.get("/api/webhook-applications/app_1").respond(200, json={"data": {
        "id": "app_1", "organizationId": "org_1", "name": "Acme", "externalId": None,
        "rateLimitPerSecond": 10, "rateLimitPerMinute": None, "rateLimitPerHour": None,
        "isDisabled": True, "disabledReason": "abuse", "totalEndpoints": 2,
        "sendEventUrl": "https://api.hookbase.app/api/send-event",
    }})
    app = client.outbound.applications.get("app_1")
    assert isinstance(app, Application)
    assert app.rate_limit_per_second == 10
    assert app.is_disabled is True
    assert app.disabled_reason == "abuse"
    assert app.total_endpoints == 2


def test_application_update_sends_rate_limits_and_disable(mock_api, client):
    route = mock_api.patch("/api/webhook-applications/app_1").respond(200, json={"data": {
        "id": "app_1", "organizationId": "org_1", "name": "Acme",
    }})
    from hookbase.models import UpdateApplicationParams

    client.outbound.applications.update("app_1", UpdateApplicationParams(
        rate_limit_per_minute=600, is_disabled=True, disabled_reason="paused",
    ))
    assert sent_body(route) == {
        "rateLimitPerMinute": 600, "isDisabled": True, "disabledReason": "paused",
    }

