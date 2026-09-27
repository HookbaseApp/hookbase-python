from __future__ import annotations

import pytest
import respx
from pydantic import ValidationError

from hookbase import Hookbase
from hookbase.errors import HookbaseError
from hookbase.models import (
    CreateEndpointParams,
    CustomHeader,
    UpdateEndpointParams,
    WebhookEndpoint,
)

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


# Every key the API's `formatEndpoint` returns
# (api/src/routes/webhook-endpoints.ts), populated with a value no Python
# default would produce -- so a field that fails to decode shows as its default
# rather than passing by coincidence.
ENDPOINT_RESPONSE = {
    "id": "ep_1",
    "applicationId": "app_1",
    "url": "https://acme.test/webhooks",
    "description": "Production endpoint",
    "secretPrefix": "whsec_abcdef...",
    "hasSecret": True,
    "secretVersion": 2,
    "headers": [{"name": "X-Tenant", "value": "acme"}],
    "timeoutSeconds": 45,
    "isDisabled": False,
    "disabledAt": None,
    "disabledReason": None,
    "rateLimitPerSecond": 25,
    "successStatusCodes": [200, 201, "2xx"],
    "backoffType": "linear",
    "retryDelays": [5, 30, 300],
    "ipAllowlistNotes": "egress from 203.0.113.0/24",
    "useStaticIp": True,
    "circuitState": "closed",
    "circuitOpenedAt": None,
    "circuitFailureCount": 1,
    "circuitFailureThreshold": 7,
    "circuitSuccessThreshold": 3,
    "circuitCooldownSeconds": 120,
    "totalMessages": 900,
    "totalSuccesses": 880,
    "totalFailures": 20,
    "avgResponseTimeMs": 143.5,
    "lastSuccessAt": "2026-01-05T00:00:00Z",
    "lastFailureAt": "2026-01-04T00:00:00Z",
    "lastResponseStatus": 200,
    "isVerified": True,
    "verifiedAt": "2026-01-01T00:00:00Z",
    "createdAt": "2026-01-01T00:00:00Z",
    "updatedAt": "2026-01-06T00:00:00Z",
    "createdBy": "u1",
    "apiKeyId": None,
}


def test_endpoint_model_has_a_field_for_every_response_key(mock_api, client):
    """`extra="ignore"` drops a key the model has no field for, silently.

    This model carried fifteen of the API's thirty-six response keys, so most of
    an endpoint's configuration was unreadable from Python and nothing said so.
    Add a key to `formatEndpoint`, add it here, and this fails until the model
    can hold it.
    """
    aliases = {
        field.alias or name
        for name, field in WebhookEndpoint.model_fields.items()
    }
    missing = sorted(key for key in ENDPOINT_RESPONSE if key not in aliases)
    assert missing == [], f"the API returns these and WebhookEndpoint has no field: {missing}"


def test_endpoint_decodes_the_delivery_policy(mock_api, client):
    """The six settings that were accepted, acted on, and in no response."""
    mock_api.get("/api/webhook-endpoints/ep_1").respond(200, json={"data": ENDPOINT_RESPONSE})
    endpoint = client.outbound.endpoints.get("ep_1")
    assert endpoint.rate_limit_per_second == 25
    assert endpoint.success_status_codes == [200, 201, "2xx"]
    assert endpoint.backoff_type == "linear"
    assert endpoint.retry_delays == [5, 30, 300]
    assert endpoint.ip_allowlist_notes == "egress from 203.0.113.0/24"
    assert endpoint.use_static_ip is True


def test_endpoint_decodes_the_rest_of_the_response(mock_api, client):
    mock_api.get("/api/webhook-endpoints/ep_1").respond(200, json={"data": ENDPOINT_RESPONSE})
    endpoint = client.outbound.endpoints.get("ep_1")
    assert endpoint.secret_prefix == "whsec_abcdef..."
    assert endpoint.has_secret is True
    assert endpoint.secret_version == 2
    assert endpoint.timeout_seconds == 45
    assert endpoint.circuit_failure_threshold == 7
    assert endpoint.circuit_cooldown_seconds == 120
    assert endpoint.avg_response_time_ms == 143.5
    assert endpoint.last_response_status == 200
    assert endpoint.is_verified is True
    assert endpoint.verified_at == "2026-01-01T00:00:00Z"
    assert endpoint.created_by == "u1"


def test_use_static_ip_defaults_to_false(mock_api, client):
    """It defaulted to true, which was the opposite of the API's own default.

    `sp_webhook_endpoint_create` stores `input.useStaticIp === true`, so an
    endpoint created without the setting has it off -- and this model reported
    every one of them as routing through the static-IP proxy.
    """
    data = {k: v for k, v in ENDPOINT_RESPONSE.items() if k != "useStaticIp"}
    mock_api.get("/api/webhook-endpoints/ep_1").respond(200, json={"data": data})
    assert client.outbound.endpoints.get("ep_1").use_static_ip is False


def test_endpoint_keeps_the_wire_form_of_headers(mock_api, client):
    """A mapping cannot hold a repeated name, and an update takes the array."""
    data = {**ENDPOINT_RESPONSE, "headers": [
        {"name": "X-Tenant", "value": "acme"},
        {"name": "X-Env", "value": "prod"},
    ]}
    mock_api.get("/api/webhook-endpoints/ep_1").respond(200, json={"data": data})
    endpoint = client.outbound.endpoints.get("ep_1")
    assert endpoint.headers == {"X-Tenant": "acme", "X-Env": "prod"}
    assert [(h.name, h.value) for h in endpoint.header_list] == [
        ("X-Tenant", "acme"), ("X-Env", "prod"),
    ]


def test_endpoint_null_policy_fields_stay_none(mock_api, client):
    """Null means "use the platform default", which is not an empty list."""
    data = {**ENDPOINT_RESPONSE, "successStatusCodes": None, "retryDelays": None,
            "backoffType": None, "ipAllowlistNotes": None}
    mock_api.get("/api/webhook-endpoints/ep_1").respond(200, json={"data": data})
    endpoint = client.outbound.endpoints.get("ep_1")
    assert endpoint.success_status_codes is None
    assert endpoint.retry_delays is None
    assert endpoint.backoff_type is None
    assert endpoint.ip_allowlist_notes is None


# `clear`: the only way to send an explicit null.
#
# Every optional field is `X | None = None` and `dump` excludes `None`, so
# `None` means "leave this alone" and there was nothing left to mean "reset
# this" -- even though the API accepts a null for five of these settings. A
# caller who had set a custom retry schedule could not remove it from Python.

def test_update_endpoint_clear_sends_an_explicit_null(mock_api, client):
    route = mock_api.patch("/api/webhook-endpoints/ep_1").respond(
        200, json={"data": ENDPOINT_RESPONSE}
    )
    client.outbound.endpoints.update(
        "ep_1", UpdateEndpointParams(clear=["retryDelays", "backoffType"]),
    )
    body = sent_body(route)
    # Present AS null, not absent: an absent key leaves the setting alone.
    assert body == {"retryDelays": None, "backoffType": None}


def test_update_endpoint_clear_leaves_the_rest_of_the_patch_alone(mock_api, client):
    route = mock_api.patch("/api/webhook-endpoints/ep_1").respond(
        200, json={"data": ENDPOINT_RESPONSE}
    )
    client.outbound.endpoints.update(
        "ep_1", UpdateEndpointParams(url="https://acme.test/v2", clear=["description"]),
    )
    assert sent_body(route) == {"url": "https://acme.test/v2", "description": None}


def test_update_endpoint_clear_accepts_the_snake_case_spelling(mock_api, client):
    """Every other field takes both spellings; `clear`'s entries do too."""
    route = mock_api.patch("/api/webhook-endpoints/ep_1").respond(
        200, json={"data": ENDPOINT_RESPONSE}
    )
    client.outbound.endpoints.update("ep_1", {"clear": ["success_status_codes"]})
    assert sent_body(route) == {"successStatusCodes": None}


def test_update_endpoint_clear_never_reaches_the_api(mock_api, client):
    """`clear` is an SDK-side instruction; the schema is strict and would 400."""
    route = mock_api.patch("/api/webhook-endpoints/ep_1").respond(
        200, json={"data": ENDPOINT_RESPONSE}
    )
    client.outbound.endpoints.update("ep_1", {"clear": ["description"]})
    body = sent_body(route)
    assert "clear" not in body


def test_update_endpoint_clear_refuses_a_field_also_set(mock_api, client):
    """Set and cleared in one call is a contradiction, not a choice to make."""
    with pytest.raises(HookbaseError, match="also set"):
        client.outbound.endpoints.update(
            "ep_1", UpdateEndpointParams(description="still here", clear=["description"]),
        )


def test_update_endpoint_clear_refuses_a_field_the_api_wont_null(mock_api, client):
    """`url` and `timeoutSeconds` are not nullable; a null for either is a 400.

    Saying which field, here, beats the server's "Invalid input".
    """
    with pytest.raises(HookbaseError, match="url"):
        client.outbound.endpoints.update("ep_1", {"clear": ["url"]})


def test_update_endpoint_clear_rejects_an_unknown_field_at_validation(mock_api, client):
    """The typed path catches it before a request is built at all."""
    with pytest.raises(ValidationError):
        UpdateEndpointParams(clear=["nonsense"])


def test_update_endpoint_without_clear_is_unchanged(mock_api, client):
    """The clear path mutates the body, so the no-clear path must still be bare."""
    route = mock_api.patch("/api/webhook-endpoints/ep_1").respond(
        200, json={"data": ENDPOINT_RESPONSE}
    )
    client.outbound.endpoints.update("ep_1", UpdateEndpointParams(timeout_seconds=45))
    assert sent_body(route) == {"timeoutSeconds": 45}
