"""Inbound resources against the response shapes the API actually sends.

Fixtures are copied from the handlers in api/src/routes/{events,deliveries,
transforms,routes,destinations,cron,tunnels}.ts, so a model that drifts from
the wire fails here rather than coming back empty.
"""

from __future__ import annotations

import httpx
import pytest

from hookbase.models import (
    CircuitStatusInfo,
    CreateCronJobParams,
    CreateTunnelParams,
    Delivery,
    DeliveryDetail,
    EventDetail,
    TransformTestResult,
)

from ..conftest import sent_body

EVENT = {
    "id": "evt_1",
    "organizationId": "org_1",
    "sourceId": "src_1",
    "eventType": "push",
    "payloadHash": "abc",
    "payloadKey": "org_1/evt_1.json",
    "headers": '{"content-type":"application/json"}',
    "ipAddress": "203.0.113.9",
    "signatureValid": True,
    "receivedAt": "2026-10-20T10:00:00.000Z",
    "sourceName": "GitHub",
    "sourceSlug": "github",
    "status": "delivered",
    "method": "POST",
    "deliveryStats": {"total": 1, "delivered": 1, "failed": 0, "pending": 0},
}

# One row of GET /api/deliveries (the list adds eventType; get adds destinationUrl).
DELIVERY = {
    "id": "del_1",
    "organizationId": "org_1",
    "eventId": "evt_1",
    "routeId": "rte_1",
    "destinationId": "dst_1",
    "status": "failed",
    "attemptCount": 3,
    "maxAttempts": 5,
    "nextRetryAt": None,
    "responseStatus": 502,
    "responseKey": None,
    "responseHeaders": '{"server":"nginx"}',
    "responseBody": "Bad Gateway",
    "latencyMs": 812,
    "errorMessage": "HTTP 502",
    "deliveredAt": None,
    "createdAt": "2026-10-20T10:00:01.000Z",
    "updatedAt": "2026-10-20T10:05:00.000Z",
    "destinationName": "Slack",
    "eventType": "push",
}


def _event(n: int) -> dict:
    return {**EVENT, "id": f"evt_{n}"}


def _delivery(n: int) -> dict:
    return {**DELIVERY, "id": f"del_{n}"}


def _events_page(ids: range, *, next_cursor: str | None) -> dict:
    return {
        "events": [_event(n) for n in ids],
        "total": None,
        "limit": 2,
        "hasMore": next_cursor is not None,
        "nextCursor": next_cursor,
    }


# --- 1. events.list follows the cursor ---


def test_events_list_reads_top_level_cursor(mock_api, client):
    mock_api.get("/api/events").respond(200, json=_events_page(range(1, 3), next_cursor="c2"))
    page = client.events.list(limit=2)
    assert [e.id for e in page] == ["evt_1", "evt_2"]
    assert page.has_more is True
    assert page.next_cursor == "c2"
    assert page.data[0].signature_valid == 1
    assert page.data[0].method == "POST"


def test_events_auto_paging_follows_cursor(mock_api, client):
    route = mock_api.get("/api/events").mock(side_effect=[
        httpx.Response(200, json=_events_page(range(1, 3), next_cursor="c2")),
        httpx.Response(200, json=_events_page(range(3, 4), next_cursor=None)),
    ])
    ids = [e.id for e in client.events.list(limit=2, source_id="github").auto_paging_iter()]
    assert ids == ["evt_1", "evt_2", "evt_3"]
    assert route.call_count == 2
    second = route.calls[1].request.url.params
    assert second["cursor"] == "c2"
    assert second["limit"] == "2"
    assert second["sourceId"] == "github"
    assert "offset" not in second


async def test_async_events_auto_paging_follows_cursor(mock_api, async_client):
    route = mock_api.get("/api/events").mock(side_effect=[
        httpx.Response(200, json=_events_page(range(1, 3), next_cursor="c2")),
        httpx.Response(200, json=_events_page(range(3, 4), next_cursor=None)),
    ])
    page = await async_client.events.list(limit=2)
    ids = [e.id async for e in page.auto_paging_iter()]
    assert ids == ["evt_1", "evt_2", "evt_3"]
    assert route.calls[1].request.url.params["cursor"] == "c2"


def test_events_list_passes_cursor(mock_api, client):
    route = mock_api.get("/api/events").respond(
        200, json=_events_page(range(1, 2), next_cursor=None),
    )
    client.events.list(cursor="abc")
    assert route.calls.last.request.url.params["cursor"] == "abc"


# --- 2. events.get carries the payload and deliveries ---


EVENT_GET = {
    "event": {
        k: v for k, v in EVENT.items() if k not in ("sourceSlug", "deliveryStats")
    } | {"encryptFields": None, "maskFields": None},
    "payload": {"ref": "refs/heads/main", "commits": [{"id": "a1"}]},
    "transient": False,
    "deliveries": [{**DELIVERY, "destinationUrl": "https://hooks.slack.com/x"}],
}


def test_events_get_keeps_payload_and_deliveries(mock_api, client):
    mock_api.get("/api/events/evt_1").respond(200, json=EVENT_GET)
    event = client.events.get("evt_1")
    assert isinstance(event, EventDetail)
    assert event.id == "evt_1"
    assert event.payload == {"ref": "refs/heads/main", "commits": [{"id": "a1"}]}
    assert event.transient is False
    assert event.headers == {"content-type": "application/json"}
    assert event.status == "delivered"
    assert len(event.deliveries) == 1
    d = event.deliveries[0]
    assert d.response_status == 502
    assert d.destination_url == "https://hooks.slack.com/x"


async def test_async_events_get_keeps_payload(mock_api, async_client):
    mock_api.get("/api/events/evt_1").respond(200, json=EVENT_GET)
    event = await async_client.events.get("evt_1")
    assert event.payload["ref"] == "refs/heads/main"
    assert event.deliveries[0].attempt_count == 3


def test_events_get_transient_has_no_payload(mock_api, client):
    mock_api.get("/api/events/evt_1").respond(200, json={
        **EVENT_GET, "payload": None, "transient": True, "deliveries": [],
    })
    event = client.events.get("evt_1")
    assert event.payload is None
    assert event.transient is True


# --- 3. Delivery field names ---


def test_delivery_reads_api_field_names():
    d = Delivery.model_validate(DELIVERY)
    assert d.attempt_count == 3
    assert d.max_attempts == 5
    assert d.response_status == 502
    assert d.response_headers == {"server": "nginx"}
    assert d.response_body == "Bad Gateway"
    assert d.latency_ms == 812
    assert d.error_message == "HTTP 502"
    assert d.updated_at == "2026-10-20T10:05:00.000Z"
    assert d.destination_name == "Slack"
    assert d.event_type == "push"


def test_delivery_deprecated_names_mirror_real_fields():
    d = Delivery.model_validate({**DELIVERY, "deliveredAt": "2026-10-20T10:06:00.000Z"})
    assert d.status_code == 502
    assert d.attempts == 3
    assert d.error == "HTTP 502"
    assert d.duration == 812
    assert d.completed_at == "2026-10-20T10:06:00.000Z"


def test_delivery_with_null_counts_validates(mock_api, client):
    # A pending delivery the worker has not counted yet arrives with attemptCount null.
    pending = {**DELIVERY, "attemptCount": None, "maxAttempts": None}
    mock_api.get("/api/deliveries").respond(
        200, json={"deliveries": [pending], "limit": 20, "offset": 0}
    )
    d = client.deliveries.list().data[0]
    assert d.attempt_count == 0
    assert d.max_attempts == 5
    assert d.attempts == 0


def test_deliveries_get(mock_api, client):
    row = {k: v for k, v in DELIVERY.items() if k != "eventType"}
    mock_api.get("/api/deliveries/del_1").respond(200, json={
        "delivery": {**row, "destinationUrl": "https://hooks.slack.com/x"},
    })
    d = client.deliveries.get("del_1")
    assert isinstance(d, DeliveryDetail)
    assert d.response_status == 502
    assert d.destination_url == "https://hooks.slack.com/x"


# --- 10. deliveries pagination advances by rows returned ---


def test_deliveries_auto_paging_advances_by_rows_returned(mock_api, client):
    # Asked for 500; the API clamps to 100 and says so. Advancing by 500 would skip 400 rows.
    route = mock_api.get("/api/deliveries").mock(side_effect=[
        httpx.Response(200, json={
            "deliveries": [_delivery(n) for n in range(100)], "limit": 100, "offset": 0,
        }),
        httpx.Response(200, json={
            "deliveries": [_delivery(n) for n in range(100, 130)], "limit": 100, "offset": 100,
        }),
    ])
    page = client.deliveries.list(limit=500, status="failed")
    assert page.limit == 100 and page.offset == 0
    assert page.has_more is True
    items = list(page.auto_paging_iter())
    assert len(items) == 130
    assert route.call_count == 2
    second = route.calls[1].request.url.params
    assert second["offset"] == "100"
    assert second["status"] == "failed"


def test_deliveries_auto_paging_stops_on_empty_page(mock_api, client):
    route = mock_api.get("/api/deliveries").mock(side_effect=[
        httpx.Response(200, json={
            "deliveries": [_delivery(n) for n in range(2)], "limit": 2, "offset": 10,
        }),
        httpx.Response(200, json={"deliveries": [], "limit": 2, "offset": 12}),
    ])
    items = list(client.deliveries.list(limit=2, offset=10).auto_paging_iter())
    assert len(items) == 2
    assert route.calls[1].request.url.params["offset"] == "12"


async def test_async_deliveries_auto_paging(mock_api, async_client):
    route = mock_api.get("/api/deliveries").mock(side_effect=[
        httpx.Response(200, json={
            "deliveries": [_delivery(n) for n in range(2)], "limit": 2, "offset": 0,
        }),
        httpx.Response(200, json={
            "deliveries": [_delivery(2)], "limit": 2, "offset": 2,
        }),
    ])
    page = await async_client.deliveries.list(limit=2)
    items = [d async for d in page.auto_paging_iter()]
    assert [d.id for d in items] == ["del_0", "del_1", "del_2"]
    assert route.calls[1].request.url.params["offset"] == "2"


# --- deliveries bulk replay request bodies ---


BULK_REPLAY = {
    "message": "1 deliveries queued for replay",
    "queued": 1,
    "skipped": 0,
    "results": [{"originalId": "del_1", "newId": "del_9", "status": "queued"}],
}


def test_bulk_replay_sends_delivery_ids(mock_api, client):
    route = mock_api.post("/api/deliveries/bulk-replay").respond(200, json=BULK_REPLAY)
    result = client.deliveries.bulk_replay(["del_1"])
    assert sent_body(route) == {"deliveryIds": ["del_1"]}
    assert result.queued == 1


async def test_async_bulk_replay_events_hits_events_route(mock_api, async_client):
    route = mock_api.post("/api/deliveries/bulk-replay-events").respond(200, json={
        **BULK_REPLAY,
        "eventsProcessed": 1,
        "overrides": {
            "destinationOverride": None, "transformOverridden": False,
            "headersOverridden": False, "transformPersistedTo": None,
        },
    })
    result = await async_client.deliveries.bulk_replay_events(["evt_1"])
    assert sent_body(route) == {"eventIds": ["evt_1"]}
    assert result.events_processed == 1
    assert result.overrides is not None


def test_bulk_replay_events_hits_events_route(mock_api, client):
    route = mock_api.post("/api/deliveries/bulk-replay-events").respond(200, json=BULK_REPLAY)
    client.deliveries.bulk_replay_events(["evt_1"])
    assert sent_body(route) == {"eventIds": ["evt_1"]}


# --- 4. transforms.test ---


def test_transform_test_reads_result(mock_api, client):
    route = mock_api.post("/api/transforms/test").respond(200, json={
        "success": True, "result": {"name": "Ada"}, "contentType": "application/json",
    })
    result = client.transforms.test(code="{ 'name': name }", payload={"name": "Ada"})
    assert sent_body(route) == {
        "code": "{ 'name': name }", "payload": {"name": "Ada"},
        "transformType": "jsonata", "inputFormat": "json", "outputFormat": "json",
    }
    assert isinstance(result, TransformTestResult)
    assert result.success is True
    assert result.result == {"name": "Ada"}
    assert result.content_type == "application/json"
    assert result.output == {"name": "Ada"}  # deprecated mirror


async def test_async_transform_test_failure(mock_api, async_client):
    mock_api.post("/api/transforms/test").respond(200, json={
        "success": False, "error": "Unexpected token",
    })
    result = await async_client.transforms.test(code="(", payload={})
    assert result.success is False
    assert result.error == "Unexpected token"
    assert result.result is None


# --- 5. cron jobs send `payload` ---


def test_cron_create_and_update_send_payload(mock_api, client):
    job = {
        "id": "cron_1", "name": "Nightly", "url": "https://example.com",
        "cronExpression": "0 0 * * *",
    }
    create = mock_api.post("/api/cron").respond(200, json={"cronJob": job})
    update = mock_api.patch("/api/cron/cron_1").respond(200, json={"success": True})
    client.cron_jobs.create(CreateCronJobParams(
        name="Nightly", url="https://example.com", cron_expression="0 0 * * *",
        method="POST", payload='{"a":1}',
    ))
    client.cron_jobs.update("cron_1", {"payload": "{}"})
    assert sent_body(create)["payload"] == '{"a":1}'
    assert "body" not in sent_body(create)
    assert sent_body(update) == {"payload": "{}"}


# --- 6. tunnels.create sends no localPort ---


def test_tunnel_create_body(mock_api, client):
    route = mock_api.post("/api/tunnels").respond(200, json={"tunnel": {
        "id": "tun_1", "organizationId": "org_1", "name": "dev", "subdomain": "dev-1",
    }})
    client.tunnels.create(CreateTunnelParams(name="dev", subdomain="dev-1"))
    assert sent_body(route) == {"name": "dev", "subdomain": "dev-1"}


# --- 7. route circuit status ---


def test_route_circuit_status(mock_api, client):
    mock_api.get("/api/routes/rte_1/circuit-status").respond(200, json={
        "circuitState": "open",
        "circuitOpenedAt": "2026-10-20T10:00:00.000Z",
        "cooldownSeconds": 300,
        "probeAttempts": 1,
        "probeSuccessThreshold": 2,
        "failureThreshold": 5,
        "consecutiveFailures": 7,
        "timeUntilProbeSeconds": 120,
    })
    info = client.routes.get_circuit_status("rte_1")
    assert isinstance(info, CircuitStatusInfo)
    assert info.circuit_state == "open"
    assert info.cooldown_seconds == 300
    assert info.consecutive_failures == 7
    assert info.time_until_probe_seconds == 120


# --- 8. import results (routes and destinations; sources in test_sources.py) ---


def test_import_routes_result(mock_api, client):
    mock_api.post("/api/routes/import").respond(200, json={
        "success": True,
        "imported": ["a"],
        "skipped": ["b"],
        "errors": [{"name": "c", "error": "Source 'x' not found. Create it first."}],
        "summary": {"total": 3, "imported": 1, "skipped": 1, "errors": 1},
    })
    result = client.routes.import_routes([{"name": "a"}])
    assert result.success is True
    assert result.imported == ["a"]
    assert result.skipped == ["b"]
    assert result.errors[0].name == "c"
    assert result.summary is not None and result.summary.total == 3


def test_import_routes_validate_only(mock_api, client):
    mock_api.post("/api/routes/import").respond(200, json={
        "success": True,
        "validateOnly": True,
        "validationResults": [{
            "index": 0, "name": "a", "status": "rename", "errors": [], "warnings": [],
            "resolvedName": "a (1)",
        }],
        "summary": {"total": 1, "valid": 1, "skipped": 0, "overwrite": 0, "errors": 0},
    })
    result = client.routes.import_routes([{"name": "a"}], validate_only=True)
    assert result.validate_only is True
    assert result.validation_results[0].resolved_name == "a (1)"
    assert result.summary is not None and result.summary.valid == 1


async def test_async_import_destinations_result(mock_api, async_client):
    mock_api.post("/api/destinations/import").respond(200, json={
        "success": True,
        "summary": {"imported": 0, "skipped": 0, "overwritten": 1, "failed": 0},
        "details": {"imported": [], "skipped": [], "overwritten": ["Slack"], "failed": []},
    })
    result = await async_client.destinations.import_destinations([{"name": "Slack"}])
    assert result.details is not None
    assert result.details.overwritten == ["Slack"]
    assert result.summary is not None and result.summary.overwritten == 1


# --- 9. destinations.test (sync in test_destinations.py) ---


async def test_async_destination_test(mock_api, async_client):
    mock_api.post("/api/destinations/dst_1/test").respond(200, json={
        "success": True, "status": 204, "latencyMs": 42, "responseBody": "",
    })
    result = await async_client.destinations.test("dst_1")
    assert result.status == 204
    assert result.latency_ms == 42


@pytest.mark.parametrize("missing", ["status", "latencyMs"])
def test_destination_test_without_optional_fields(mock_api, client, missing):
    body = {"success": False, "status": 500, "latencyMs": 3, "error": "HTTP 500"}
    body.pop(missing)
    mock_api.post("/api/destinations/dst_1/test").respond(200, json=body)
    result = client.destinations.test("dst_1")
    assert result.success is False
    assert result.error == "HTTP 500"
