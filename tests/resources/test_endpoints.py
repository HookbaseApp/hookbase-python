from __future__ import annotations

import pytest
import respx

from hookbase import Hookbase
from hookbase.models import CreateEndpointParams, CustomHeader, UpdateEndpointParams

from ..conftest import sent_body


@pytest.fixture
def mock_api():
    with respx.mock(base_url="https://api.hookbase.app") as mock:
        yield mock


@pytest.fixture
def client(mock_api):
    c = Hookbase(api_key="whr_test")
    yield c
    c.close()


# Shaped like the real response: headers arrive as an array of name/value
# objects (`[]` when the endpoint has none), never as a mapping.
ENDPOINT_DATA = {
    "id": "ep_1",
    "applicationId": "app_1",
    "url": "https://acme.test/webhooks",
    "description": "Production endpoint",
    "secret": "whsec_abc",
    "headers": [],
    "timeoutSeconds": 30,
    "isDisabled": False,
    "circuitState": "closed",
    "totalMessages": 0,
    "totalSuccesses": 0,
    "totalFailures": 0,
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z",
}


def test_create_endpoint(mock_api, client):
    route = mock_api.post("/api/webhook-endpoints").respond(200, json={"data": ENDPOINT_DATA})
    endpoint = client.outbound.endpoints.create("app_1", {"url": "https://acme.test/webhooks"})
    assert endpoint.id == "ep_1"
    assert sent_body(route) == {
        "applicationId": "app_1",
        "url": "https://acme.test/webhooks",
    }


def test_create_endpoint_sends_every_accepted_field(mock_api, client):
    route = mock_api.post("/api/webhook-endpoints").respond(200, json={"data": ENDPOINT_DATA})
    client.outbound.endpoints.create("app_1", CreateEndpointParams(
        url="https://acme.test/webhooks",
        description="Production endpoint",
        headers={"X-Tenant": "acme"},
        timeout_seconds=45,
        rate_limit_per_second=20,
        success_status_codes=[200, 201, "2xx"],
        backoff_type="exponential",
        retry_delays=[5, 30, 300],
        ip_allowlist_notes="Allow 203.0.113.0/24",
        use_static_ip=True,
        circuit_failure_threshold=10,
        circuit_success_threshold=3,
        circuit_cooldown_seconds=120,
    ))
    assert sent_body(route) == {
        "applicationId": "app_1",
        "url": "https://acme.test/webhooks",
        "description": "Production endpoint",
        "headers": [{"name": "X-Tenant", "value": "acme"}],
        "timeoutSeconds": 45,
        "rateLimitPerSecond": 20,
        "successStatusCodes": [200, 201, "2xx"],
        "backoffType": "exponential",
        "retryDelays": [5, 30, 300],
        "ipAllowlistNotes": "Allow 203.0.113.0/24",
        "useStaticIp": True,
        "circuitFailureThreshold": 10,
        "circuitSuccessThreshold": 3,
        "circuitCooldownSeconds": 120,
    }


def test_create_endpoint_drops_deprecated_fields(mock_api, client):
    """`filterTypes`, `rateLimitPeriod` and `metadata` were never accepted."""
    route = mock_api.post("/api/webhook-endpoints").respond(200, json={"data": ENDPOINT_DATA})
    client.outbound.endpoints.create("app_1", CreateEndpointParams(
        url="https://acme.test/webhooks",
        filter_types=["order.created"],
        rate_limit_period=60,
        metadata={"team": "payments"},
    ))
    body = sent_body(route)
    assert body == {"applicationId": "app_1", "url": "https://acme.test/webhooks"}
    for stale in ("filterTypes", "filter_types", "rateLimitPeriod", "rate_limit_period",
                  "metadata"):
        assert stale not in body


def test_create_endpoint_drops_deprecated_fields_from_a_dict(mock_api, client):
    """A caller passing a plain dict skips model validation but not the fixup."""
    route = mock_api.post("/api/webhook-endpoints").respond(200, json={"data": ENDPOINT_DATA})
    client.outbound.endpoints.create("app_1", {
        "url": "https://acme.test/webhooks",
        "filterTypes": ["order.created"],
        "rateLimitPeriod": 60,
        "metadata": {"team": "payments"},
    })
    assert sent_body(route) == {"applicationId": "app_1", "url": "https://acme.test/webhooks"}


def test_create_endpoint_renames_rate_limit(mock_api, client):
    route = mock_api.post("/api/webhook-endpoints").respond(200, json={"data": ENDPOINT_DATA})
    client.outbound.endpoints.create("app_1", {
        "url": "https://acme.test/webhooks", "rateLimit": 25,
    })
    body = sent_body(route)
    assert body["rateLimitPerSecond"] == 25
    assert "rateLimit" not in body


def test_create_endpoint_rate_limit_per_second_wins_over_rate_limit(mock_api, client):
    route = mock_api.post("/api/webhook-endpoints").respond(200, json={"data": ENDPOINT_DATA})
    client.outbound.endpoints.create("app_1", CreateEndpointParams(
        url="https://acme.test/webhooks", rate_limit=25, rate_limit_per_second=50,
    ))
    body = sent_body(route)
    assert body["rateLimitPerSecond"] == 50
    assert "rateLimit" not in body


def test_create_endpoint_converts_mapping_headers_to_pairs(mock_api, client):
    """The API takes `[{"name": .., "value": ..}]`; a mapping 400s outright."""
    route = mock_api.post("/api/webhook-endpoints").respond(200, json={"data": ENDPOINT_DATA})
    client.outbound.endpoints.create("app_1", CreateEndpointParams(
        url="https://acme.test/webhooks",
        headers={"X-Tenant": "acme", "X-Region": "eu", "Authorization": "Bearer t"},
    ))
    # Insertion order is preserved so the array reads back the way it was built.
    assert sent_body(route)["headers"] == [
        {"name": "X-Tenant", "value": "acme"},
        {"name": "X-Region", "value": "eu"},
        {"name": "Authorization", "value": "Bearer t"},
    ]


def test_create_endpoint_leaves_pair_headers_alone(mock_api, client):
    route = mock_api.post("/api/webhook-endpoints").respond(200, json={"data": ENDPOINT_DATA})
    client.outbound.endpoints.create("app_1", CreateEndpointParams(
        url="https://acme.test/webhooks",
        headers=[CustomHeader(name="X-Tenant", value="acme")],
    ))
    assert sent_body(route)["headers"] == [{"name": "X-Tenant", "value": "acme"}]


def test_create_endpoint_leaves_raw_pair_headers_alone(mock_api, client):
    route = mock_api.post("/api/webhook-endpoints").respond(200, json={"data": ENDPOINT_DATA})
    client.outbound.endpoints.create("app_1", {
        "url": "https://acme.test/webhooks",
        "headers": [{"name": "X-Tenant", "value": "acme"}],
    })
    assert sent_body(route)["headers"] == [{"name": "X-Tenant", "value": "acme"}]


def test_update_endpoint_applies_the_same_fixups(mock_api, client):
    route = mock_api.patch("/api/webhook-endpoints/ep_1").respond(
        200, json={"data": ENDPOINT_DATA}
    )
    client.outbound.endpoints.update("ep_1", UpdateEndpointParams(
        is_disabled=True,
        disabled_reason="Too many failures",
        rate_limit=10,
        rate_limit_period=60,
        filter_types=["order.created"],
        metadata={"team": "payments"},
        headers={"X-Tenant": "acme"},
        timeout_seconds=15,
    ))
    assert sent_body(route) == {
        "isDisabled": True,
        "disabledReason": "Too many failures",
        "rateLimitPerSecond": 10,
        "headers": [{"name": "X-Tenant", "value": "acme"}],
        "timeoutSeconds": 15,
    }


def test_rotate_secret_sends_grace_period_seconds(mock_api, client):
    """The API reads `gracePeriodSeconds`; `gracePeriod` was silently ignored."""
    route = mock_api.post("/api/webhook-endpoints/ep_1/rotate-secret").respond(
        200, json={"data": {"secret": "whsec_new"}}
    )
    result = client.outbound.endpoints.rotate_secret("ep_1", grace_period=3600)
    assert result.secret == "whsec_new"
    assert sent_body(route) == {"gracePeriodSeconds": 3600}


def test_endpoint_response_headers_become_a_mapping(mock_api, client):
    """Responses carry headers as an array; the model exposes a mapping."""
    data = {**ENDPOINT_DATA, "headers": [
        {"name": "X-Tenant", "value": "acme"},
        {"name": "X-Region", "value": "eu"},
    ]}
    mock_api.get("/api/webhook-endpoints/ep_1").respond(200, json={"data": data})
    endpoint = client.outbound.endpoints.get("ep_1")
    assert endpoint.headers == {"X-Tenant": "acme", "X-Region": "eu"}


def test_endpoint_response_without_headers(mock_api, client):
    mock_api.get("/api/webhook-endpoints/ep_1").respond(200, json={"data": ENDPOINT_DATA})
    endpoint = client.outbound.endpoints.get("ep_1")
    assert endpoint.headers == {}
