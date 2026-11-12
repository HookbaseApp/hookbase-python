from __future__ import annotations

import re

import pytest
import respx

from hookbase import AsyncHookbase, Hookbase
from hookbase.errors import HookbaseError
from hookbase.models import (
    BridgeConfig,
    CreateDestinationParams,
    Destination,
    DestinationSecret,
    DestinationWithSecret,
    FieldMapping,
    TestResult,
    Throttle,
    UpdateDestinationParams,
)

from ..conftest import make_paginated_response, sent_body


@pytest.fixture
def mock_api():
    with respx.mock(base_url="https://api.hookbase.app") as mock:
        yield mock


@pytest.fixture
def client(mock_api):
    c = Hookbase(api_key="whr_test")
    yield c
    c.close()


DEST_DATA = {
    "id": "dst_1",
    "organizationId": "org_1",
    "name": "Backend",
    "slug": "backend",
    "type": "http",
    "url": "https://example.com/webhooks",
    "method": "POST",
    "authType": "none",
    "timeoutMs": 30000,
    "isActive": True,
    "config": None,
    "fieldMapping": None,
    "deliveryCount": 100,
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z",
}

S3_DEST_DATA = {
    "id": "dst_s3",
    "organizationId": "org_1",
    "name": "S3 Archive",
    "slug": "s3-archive",
    "type": "s3",
    "url": "",
    "method": "POST",
    "authType": "none",
    "timeoutMs": 30000,
    "isActive": True,
    "config": {
        "bucket": "my-webhooks",
        "region": "us-east-1",
        "accessKeyId": "AKIAIOSFODNN7EXAMPLE",
        "secretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "prefix": "events/",
        "fileFormat": "jsonl",
        "partitionBy": "date",
    },
    "fieldMapping": [
        {"source": "$.id", "target": "event_id", "type": "string"},
        {"source": "$.payload", "target": "data", "type": "json"},
        {"source": "$.timestamp", "target": "received_at", "type": "timestamp", "default": "now()"},
    ],
    "deliveryCount": 0,
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z",
}


def test_list_destinations(mock_api, client):
    mock_api.get("/api/destinations").respond(200, json=make_paginated_response(
        [DEST_DATA], data_key="destinations", total=1,
    ))
    page = client.destinations.list()
    assert len(page) == 1
    assert page.data[0].name == "Backend"


def test_get_destination(mock_api, client):
    mock_api.get("/api/destinations/dst_1").respond(200, json={"destination": DEST_DATA})
    dest = client.destinations.get("dst_1")
    assert isinstance(dest, Destination)
    assert dest.url == "https://example.com/webhooks"
    assert dest.type == "http"
    assert dest.config is None
    assert dest.field_mapping is None


def test_get_warehouse_destination(mock_api, client):
    mock_api.get("/api/destinations/dst_s3").respond(200, json={"destination": S3_DEST_DATA})
    dest = client.destinations.get("dst_s3")
    assert isinstance(dest, Destination)
    assert dest.type == "s3"
    assert dest.config is not None
    assert dest.config["bucket"] == "my-webhooks"
    assert dest.config["region"] == "us-east-1"
    assert dest.field_mapping is not None
    assert len(dest.field_mapping) == 3
    assert dest.field_mapping[0].source == "$.id"
    assert dest.field_mapping[0].target == "event_id"
    assert dest.field_mapping[0].type == "string"
    assert dest.field_mapping[2].default == "now()"


def test_create_destination(mock_api, client):
    mock_api.post("/api/destinations").respond(200, json={"destination": DEST_DATA})
    dest = client.destinations.create({"name": "Backend", "url": "https://example.com/webhooks"})
    assert dest.id == "dst_1"
    assert dest.type == "http"


def test_create_warehouse_destination(mock_api, client):
    mock_api.post("/api/destinations").respond(200, json={"destination": S3_DEST_DATA})
    dest = client.destinations.create({
        "name": "S3 Archive",
        "type": "s3",
        "config": {
            "bucket": "my-webhooks",
            "region": "us-east-1",
            "accessKeyId": "AKIAIOSFODNN7EXAMPLE",
            "secretAccessKey": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        },
        "fieldMapping": [
            {"source": "$.id", "target": "event_id", "type": "string"},
        ],
    })
    assert dest.id == "dst_s3"
    assert dest.type == "s3"
    assert dest.config is not None
    assert dest.field_mapping is not None


def test_update_warehouse_destination_config(mock_api, client):
    updated = {**S3_DEST_DATA, "config": {**S3_DEST_DATA["config"], "bucket": "new-bucket"}}
    mock_api.patch("/api/destinations/dst_s3").respond(200, json={"destination": updated})
    client.destinations.update("dst_s3", {
        "config": {
            "bucket": "new-bucket",
            "region": "us-east-1",
            "accessKeyId": "AKIA",
            "secretAccessKey": "secret",
        },
        "fieldMapping": [
            {"source": "$.body", "target": "payload", "type": "json"},
        ],
    })


def test_field_mapping_model():
    fm = FieldMapping(source="$.id", target="event_id", type="string")
    assert fm.source == "$.id"
    assert fm.target == "event_id"
    assert fm.type == "string"
    assert fm.default is None

    fm_with_default = FieldMapping(
        source="$.ts", target="timestamp", type="timestamp", default="now()",
    )
    assert fm_with_default.default == "now()"


def test_destination_without_type_defaults():
    """Destinations without type field should default to http."""
    data = {
        "id": "dst_old",
        "name": "Old Dest",
        "slug": "old-dest",
        "url": "https://example.com",
        "method": "POST",
        "isActive": True,
    }
    dest = Destination(**data)
    assert dest.type == "http"
    assert dest.config is None
    assert dest.field_mapping is None


def test_throttle_model():
    throttle = Throttle(mode="rate", rate_limit=10, rate_unit="minute")
    assert throttle.mode == "rate"
    assert throttle.rate_limit == 10
    assert throttle.rate_unit == "minute"
    assert throttle.max_concurrency is None
    assert throttle.queue_limit is None

    default_throttle = Throttle()
    assert default_throttle.mode == "off"


def test_create_destination_response_nests_throttle(mock_api, client):
    """POST /api/destinations nests throttle fields under `throttle`."""
    data = {
        **DEST_DATA,
        "throttle": {
            "mode": "rate",
            "rateLimit": 100,
            "rateUnit": "minute",
            "maxConcurrency": None,
            "queueLimit": 50,
        },
    }
    mock_api.post("/api/destinations").respond(200, json={"destination": data})
    dest = client.destinations.create({"name": "Backend", "url": "https://example.com/webhooks"})
    assert dest.throttle is not None
    assert dest.throttle.mode == "rate"
    assert dest.throttle.rate_limit == 100
    assert dest.throttle.rate_unit == "minute"
    assert dest.throttle.max_concurrency is None
    assert dest.throttle.queue_limit == 50


def test_get_destination_response_has_flat_throttle_fields(mock_api, client):
    """GET /api/destinations/:id returns throttle fields flat (spread from the
    DB row) rather than nested under `throttle`; the model must normalize
    this into the same `throttle` field used by the create/export shape."""
    data = {
        **DEST_DATA,
        "throttleMode": "concurrency",
        "throttleRateLimit": None,
        "throttleRateUnit": None,
        "throttleMaxConcurrency": 5,
        "throttleQueueLimit": None,
    }
    mock_api.get("/api/destinations/dst_1").respond(200, json={"destination": data})
    dest = client.destinations.get("dst_1")
    assert dest.throttle is not None
    assert dest.throttle.mode == "concurrency"
    assert dest.throttle.max_concurrency == 5
    assert dest.throttle.rate_limit is None


def test_destination_without_throttle_data():
    dest = Destination(**DEST_DATA)
    assert dest.throttle is None


def test_create_destination_params_throttle_serializes_camelcase():
    params = CreateDestinationParams(
        name="Backend",
        url="https://example.com/webhooks",
        throttle=Throttle(mode="rate", rate_limit=10, rate_unit="minute"),
    )
    body = params.model_dump(by_alias=True, exclude_none=True)
    assert body["throttle"] == {"mode": "rate", "rateLimit": 10, "rateUnit": "minute"}


def test_update_destination_params_throttle_serializes_camelcase():
    params = UpdateDestinationParams(
        throttle=Throttle(mode="concurrency", max_concurrency=25, queue_limit=100),
    )
    body = params.model_dump(by_alias=True, exclude_none=True)
    assert body["throttle"] == {
        "mode": "concurrency",
        "maxConcurrency": 25,
        "queueLimit": 100,
    }


def test_test_destination(mock_api, client):
    # The API answers with `status`/`latencyMs` (api/src/routes/destinations.ts); the
    # model reads them under those names and mirrors them onto the deprecated
    # `status_code`/`duration`.
    mock_api.post("/api/destinations/dst_1/test").respond(200, json={
        "success": True, "status": 200, "latencyMs": 150, "responseBody": "OK",
    })
    result = client.destinations.test("dst_1")
    assert isinstance(result, TestResult)
    assert result.success is True
    assert result.status == 200
    assert result.latency_ms == 150
    assert result.response_body == "OK"
    assert result.status_code == 200
    assert result.duration == 150


def test_test_destination_failure_surfaces_error(mock_api, client):
    mock_api.post("/api/destinations/dst_1/test").respond(200, json={
        "success": False, "error": "Network error",
    })
    result = client.destinations.test("dst_1")
    assert result.success is False
    assert result.error == "Network error"
    assert result.status is None
    assert result.status_code is None


# The API requires `slug` (`^[a-z0-9-]+$`, max 50); the SDK leaves it optional
# and derives one from `name` rather than letting the request 400.
SLUG_PATTERN = re.compile(r"^[a-z0-9-]+$")


def test_create_destination_derives_a_slug_from_the_name(mock_api, client):
    route = mock_api.post("/api/destinations").respond(200, json={"destination": DEST_DATA})
    client.destinations.create({"name": "My  Backend (EU)!", "url": "https://example.com/hooks"})
    slug = sent_body(route)["slug"]
    assert slug == "my-backend-eu"
    assert SLUG_PATTERN.fullmatch(slug)


def test_create_destination_derived_slug_folds_accents(mock_api, client):
    """NFKD-fold first, so `Café EU` gives `cafe-eu`, not `caf-eu`. This is one
    of the two places the four SDKs' slug derivations drift apart."""
    route = mock_api.post("/api/destinations").respond(200, json={"destination": DEST_DATA})
    client.destinations.create({"name": "Café EU", "url": "https://example.com/hooks"})
    slug = sent_body(route)["slug"]
    assert slug == "cafe-eu"
    assert SLUG_PATTERN.fullmatch(slug)


def test_create_destination_derived_slug_truncates_mid_word(mock_api, client):
    """Truncation to 50 is a plain cut and may land mid-word. Word-wrapping or
    trimming back to a boundary would make this SDK disagree with the others,
    so the cut stays plain — the other place the derivations drift."""
    route = mock_api.post("/api/destinations").respond(200, json={"destination": DEST_DATA})
    client.destinations.create({
        "name": "Warehouse archive for the EU region running well past the fifty character limit",
        "url": "https://example.com/hooks",
    })
    slug = sent_body(route)["slug"]
    assert slug == "warehouse-archive-for-the-eu-region-running-well-p"
    assert len(slug) == 50
    assert SLUG_PATTERN.fullmatch(slug)


def test_create_destination_derived_slug_drops_a_hyphen_left_by_truncation(mock_api, client):
    route = mock_api.post("/api/destinations").respond(200, json={"destination": DEST_DATA})
    client.destinations.create({
        "name": "Warehouse archive for the EU region well past the limit",
        "url": "https://example.com/hooks",
    })
    slug = sent_body(route)["slug"]
    assert slug == "warehouse-archive-for-the-eu-region-well-past-the"
    assert not slug.endswith("-")
    assert SLUG_PATTERN.fullmatch(slug)


def test_create_destination_derived_slug_fits_the_api_limit(mock_api, client):
    route = mock_api.post("/api/destinations").respond(200, json={"destination": DEST_DATA})
    client.destinations.create({"name": "A" * 80, "url": "https://example.com/hooks"})
    slug = sent_body(route)["slug"]
    assert len(slug) == 50
    assert SLUG_PATTERN.fullmatch(slug)


def test_create_destination_with_an_underivable_name(mock_api, client):
    """A name with no alphanumerics cannot produce a valid slug; say so instead
    of sending one the API would reject."""
    with pytest.raises(HookbaseError, match="pass `slug` explicitly"):
        client.destinations.create({"name": "\u2603\u2603\u2603", "url": "https://example.com/hooks"})
    # No route is registered: the failure has to come before the request.
    assert not mock_api.calls


def test_create_destination_derives_a_slug_over_a_blank_one(mock_api, client):
    route = mock_api.post("/api/destinations").respond(200, json={"destination": DEST_DATA})
    client.destinations.create({
        "name": "My Backend", "slug": "   ", "url": "https://example.com/hooks",
    })
    assert sent_body(route)["slug"] == "my-backend"


def test_create_destination_keeps_an_explicit_slug(mock_api, client):
    route = mock_api.post("/api/destinations").respond(200, json={"destination": DEST_DATA})
    client.destinations.create(CreateDestinationParams(
        name="My Backend", slug="chosen-slug", url="https://example.com/hooks",
    ))
    assert sent_body(route)["slug"] == "chosen-slug"


def test_create_destination_drops_deprecated_fields(mock_api, client):
    """`description`, `retryCount` and `retryInterval` were never accepted."""
    route = mock_api.post("/api/destinations").respond(200, json={"destination": DEST_DATA})
    client.destinations.create(CreateDestinationParams(
        name="Backend",
        slug="backend",
        url="https://example.com/hooks",
        description="Forwards to the monolith",
        retry_count=3,
        retry_interval=60,
    ))
    assert sent_body(route) == {
        "name": "Backend",
        "slug": "backend",
        "url": "https://example.com/hooks",
    }


def test_create_destination_renames_timeout(mock_api, client):
    route = mock_api.post("/api/destinations").respond(200, json={"destination": DEST_DATA})
    client.destinations.create({
        "name": "Backend", "slug": "backend", "url": "https://example.com/hooks",
        "timeout": 5000,
    })
    body = sent_body(route)
    assert body["timeoutMs"] == 5000
    assert "timeout" not in body


def test_create_destination_timeout_ms_wins_over_timeout(mock_api, client):
    route = mock_api.post("/api/destinations").respond(200, json={"destination": DEST_DATA})
    client.destinations.create(CreateDestinationParams(
        name="Backend", slug="backend", url="https://example.com/hooks",
        timeout=5000, timeout_ms=12000,
    ))
    body = sent_body(route)
    assert body["timeoutMs"] == 12000
    assert "timeout" not in body


def test_create_destination_full_body(mock_api, client):
    route = mock_api.post("/api/destinations").respond(200, json={"destination": DEST_DATA})
    client.destinations.create(CreateDestinationParams(
        name="Backend",
        slug="backend",
        url="https://example.com/hooks",
        method="POST",
        headers={"X-Api-Key": "secret"},
        auth_type="bearer",
        auth_config={"token": "t"},
        timeout_ms=15000,
        throttle=Throttle(mode="rate", rate_limit=10, rate_unit="minute"),
        use_static_ip=True,
        batch_size=10,
        batch_window_seconds=5,
    ))
    assert sent_body(route) == {
        "name": "Backend",
        "slug": "backend",
        "url": "https://example.com/hooks",
        "method": "POST",
        # Destination headers really are a mapping here, unlike endpoint headers.
        "headers": {"X-Api-Key": "secret"},
        "authType": "bearer",
        "authConfig": {"token": "t"},
        "timeoutMs": 15000,
        "throttle": {"mode": "rate", "rateLimit": 10, "rateUnit": "minute"},
        "useStaticIp": True,
        "batchSize": 10,
        "batchWindowSeconds": 5,
    }


def test_update_destination_applies_the_same_fixups(mock_api, client):
    route = mock_api.patch("/api/destinations/dst_1").respond(200, json={"destination": DEST_DATA})
    client.destinations.update("dst_1", UpdateDestinationParams(
        name="Backend v2",
        description="ignored",
        timeout=9000,
        retry_count=5,
        retry_interval=30,
        is_active=False,
    ))
    assert sent_body(route) == {
        "name": "Backend v2",
        "timeoutMs": 9000,
        "isActive": False,
    }


def test_update_destination_sends_no_slug(mock_api, client):
    """A destination's slug cannot be changed, and PATCH does not read one."""
    route = mock_api.patch("/api/destinations/dst_1").respond(200, json={"destination": DEST_DATA})
    client.destinations.update("dst_1", {"name": "Backend v2"})
    assert sent_body(route) == {"name": "Backend v2"}


def test_destination_response_exposes_timeout_ms(mock_api, client):
    mock_api.get("/api/destinations/dst_1").respond(200, json={"destination": {
        **DEST_DATA, "timeoutMs": 45000,
    }})
    dest = client.destinations.get("dst_1")
    assert dest.timeout_ms == 45000
    # The deprecated field mirrors it rather than sitting at a stale default.
    assert dest.timeout == 45000


# --- signing secrets (HTTP destinations) ---


def test_create_destination_keeps_the_one_time_signing_secret(mock_api, client):
    mock_api.post("/api/destinations").respond(200, json={"destination": {
        **DEST_DATA, "hasSigningSecret": True, "signingSecret": "whsec_abc",
    }})
    dest = client.destinations.create({"name": "Backend", "url": "https://example.com/webhooks"})
    assert isinstance(dest, DestinationWithSecret)
    assert dest.signing_secret == "whsec_abc"
    assert dest.has_signing_secret is True


def test_create_storage_destination_has_no_signing_secret(mock_api, client):
    mock_api.post("/api/destinations").respond(200, json={"destination": {
        **S3_DEST_DATA, "hasSigningSecret": False, "signingSecret": None,
    }})
    dest = client.destinations.create({"name": "S3 Archive", "type": "s3", "config": {}})
    assert dest.signing_secret is None
    assert dest.has_signing_secret is False


def test_get_and_list_report_has_signing_secret(mock_api, client):
    mock_api.get("/api/destinations/dst_1").respond(200, json={"destination": {
        **DEST_DATA, "hasSigningSecret": True,
    }})
    mock_api.get("/api/destinations").respond(200, json=make_paginated_response(
        [{**DEST_DATA, "hasSigningSecret": True}], data_key="destinations",
    ))
    assert client.destinations.get("dst_1").has_signing_secret is True
    assert client.destinations.list().data[0].has_signing_secret is True
    # Older responses without the key read as unsigned.
    assert Destination.model_validate(DEST_DATA).has_signing_secret is False


def test_reveal_secret(mock_api, client):
    route = mock_api.get("/api/destinations/dst_1/reveal-secret").respond(200, json={
        "signingSecret": "whsec_abc", "previousSecretExpiresAt": None,
    })
    secret = client.destinations.reveal_secret("dst_1")
    assert isinstance(secret, DestinationSecret)
    assert secret.signing_secret == "whsec_abc"
    assert secret.previous_secret_expires_at is None
    assert route.calls.last.request.content == b""


def test_rotate_secret_without_grace_period_sends_no_body(mock_api, client):
    route = mock_api.post("/api/destinations/dst_1/rotate-secret").respond(200, json={
        "signingSecret": "whsec_new", "previousSecretExpiresAt": "2026-11-12T01:00:00Z",
    })
    secret = client.destinations.rotate_secret("dst_1")
    assert secret.signing_secret == "whsec_new"
    assert secret.previous_secret_expires_at == "2026-11-12T01:00:00Z"
    # No body: the API applies its 3600 s default.
    assert route.calls.last.request.content == b""


@pytest.mark.parametrize("grace", [0, 600])
def test_rotate_secret_sends_grace_period_seconds(mock_api, client, grace):
    route = mock_api.post("/api/destinations/dst_1/rotate-secret").respond(200, json={
        "signingSecret": "whsec_new", "previousSecretExpiresAt": None,
    })
    client.destinations.rotate_secret("dst_1", grace_period_seconds=grace)
    assert sent_body(route) == {"gracePeriodSeconds": grace}


async def test_async_destination_secrets(mock_api):
    mock_api.post("/api/destinations").respond(200, json={"destination": {
        **DEST_DATA, "hasSigningSecret": True, "signingSecret": "whsec_abc",
    }})
    mock_api.get("/api/destinations/dst_1/reveal-secret").respond(200, json={
        "signingSecret": "whsec_abc", "previousSecretExpiresAt": None,
    })
    rotate = mock_api.post("/api/destinations/dst_1/rotate-secret").respond(200, json={
        "signingSecret": "whsec_new", "previousSecretExpiresAt": "2026-11-12T01:00:00Z",
    })
    async with AsyncHookbase(api_key="whr_test") as c:
        created = await c.destinations.create({"name": "Backend", "url": "https://x.test"})
        assert isinstance(created, DestinationWithSecret)
        assert created.signing_secret == "whsec_abc"
        assert (await c.destinations.reveal_secret("dst_1")).signing_secret == "whsec_abc"
        rotated = await c.destinations.rotate_secret("dst_1", grace_period_seconds=60)
    assert rotated.previous_secret_expires_at == "2026-11-12T01:00:00Z"
    assert sent_body(rotate) == {"gracePeriodSeconds": 60}


# --- bridge destinations ---

BRIDGE_DEST_DATA = {
    "id": "dst_br",
    "name": "Orders bridge",
    "slug": "orders-bridge",
    "type": "bridge",
    "url": "",
    "method": "POST",
    "isActive": True,
    "hasSigningSecret": False,
    "config": {"eventTypeSource": "field", "eventTypeField": "type", "eventTypePrefix": "order."},
}


def test_create_bridge_destination_with_a_bridge_config(mock_api, client):
    route = mock_api.post("/api/destinations").respond(200, json={"destination": {
        **BRIDGE_DEST_DATA, "signingSecret": None,
    }})
    dest = client.destinations.create(CreateDestinationParams(
        name="Orders bridge",
        type="bridge",
        config=BridgeConfig(
            event_type_source="field", event_type_field="type", event_type_prefix="order.",
        ),
    ))
    # camelCase keys, unset fields left out: the API's bridge schema is strict.
    assert sent_body(route) == {
        "name": "Orders bridge",
        "slug": "orders-bridge",
        "type": "bridge",
        "config": {
            "eventTypeSource": "field", "eventTypeField": "type", "eventTypePrefix": "order.",
        },
    }
    assert dest.type == "bridge"
    assert dest.url == ""
    assert dest.signing_secret is None


def test_bridge_config_in_a_plain_dict_is_serialized(mock_api, client):
    route = mock_api.post("/api/destinations").respond(200, json={"destination": BRIDGE_DEST_DATA})
    client.destinations.create({
        "name": "Fixed bridge",
        "type": "bridge",
        "config": BridgeConfig(
            event_type_source="fixed", event_type="order.created", allow_unverified_sources=True,
        ),
    })
    assert sent_body(route)["config"] == {
        "eventTypeSource": "fixed", "eventType": "order.created", "allowUnverifiedSources": True,
    }


def test_update_bridge_config(mock_api, client):
    route = mock_api.patch("/api/destinations/dst_br").respond(200, json={"success": True})
    client.destinations.update("dst_br", UpdateDestinationParams(
        config=BridgeConfig(
            event_type_source="fixed", event_type="order.paid", application_id="app_1",
        ),
    ))
    assert sent_body(route) == {"config": {
        "eventTypeSource": "fixed", "eventType": "order.paid", "applicationId": "app_1",
    }}


def test_destination_bridge_config_property(mock_api, client):
    mock_api.get("/api/destinations/dst_br").respond(200, json={"destination": BRIDGE_DEST_DATA})
    dest = client.destinations.get("dst_br")
    cfg = dest.bridge_config
    assert isinstance(cfg, BridgeConfig)
    assert (cfg.event_type_source, cfg.event_type_field, cfg.event_type_prefix) == (
        "field", "type", "order.",
    )
    assert cfg.application_id is None
    assert Destination.model_validate(DEST_DATA).bridge_config is None


def test_test_bridge_destination_sends_the_sample_payload(mock_api, client):
    route = mock_api.post("/api/destinations/dst_br/test").respond(200, json={
        "success": True, "dryRun": True, "eventType": "order.created",
        "eventTypeExists": True, "matchingEndpoints": 2,
    })
    result = client.destinations.test("dst_br", payload={"type": "created"})
    assert sent_body(route) == {"payload": {"type": "created"}}
    assert result.success is True
    assert result.dry_run is True
    assert result.event_type == "order.created"
    assert result.event_type_exists is True
    assert result.matching_endpoints == 2
    assert result.status is None


def test_test_bridge_destination_with_an_unresolvable_event_type(mock_api, client):
    mock_api.post("/api/destinations/dst_br/test").respond(200, json={
        "success": False, "dryRun": True, "eventType": None, "eventTypeExists": False,
        "matchingEndpoints": 0, "error": "Payload field 'type' is missing",
    })
    result = client.destinations.test("dst_br", payload={})
    assert result.success is False
    assert result.event_type is None
    assert result.matching_endpoints == 0
    assert result.error == "Payload field 'type' is missing"


def test_test_destination_without_payload_sends_no_body(mock_api, client):
    route = mock_api.post("/api/destinations/dst_1/test").respond(200, json={"success": True})
    result = client.destinations.test("dst_1")
    assert route.calls.last.request.content == b""
    # Not a bridge: the dry-run fields are absent.
    assert result.dry_run is None
    assert result.event_type_exists is None
    # None is no payload too: a bridge answers 400 to payload null.
    client.destinations.test("dst_1", payload=None)
    assert route.calls.last.request.content == b""


async def test_async_test_destination_with_payload_none_sends_no_body(mock_api, async_client):
    route = mock_api.post("/api/destinations/dst_br/test").respond(200, json={
        "success": True, "dryRun": True, "eventType": "order.created",
        "eventTypeExists": True, "matchingEndpoints": 0,
    })
    result = await async_client.destinations.test("dst_br", payload=None)
    assert route.calls.last.request.content == b""
    assert result.dry_run is True


async def test_async_test_bridge_destination(mock_api):
    route = mock_api.post("/api/destinations/dst_br/test").respond(200, json={
        "success": True, "dryRun": True, "eventType": "order.created",
        "eventTypeExists": True, "matchingEndpoints": 1,
    })
    async with AsyncHookbase(api_key="whr_test") as c:
        result = await c.destinations.test("dst_br", payload={"type": "created"})
    assert sent_body(route) == {"payload": {"type": "created"}}
    assert result.dry_run is True
    assert result.matching_endpoints == 1
