from __future__ import annotations

import pytest
import respx

from hookbase import Hookbase
from hookbase.models import (
    CreateDestinationParams,
    Destination,
    FieldMapping,
    TestResult,
    Throttle,
    UpdateDestinationParams,
)

from ..conftest import make_paginated_response


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
    "timeout": 30,
    "retryCount": 3,
    "retryInterval": 60,
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
    "timeout": 30,
    "retryCount": 3,
    "retryInterval": 60,
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
    mock_api.post("/api/destinations/dst_1/test").respond(200, json={
        "success": True, "statusCode": 200, "duration": 150.5,
    })
    result = client.destinations.test("dst_1")
    assert isinstance(result, TestResult)
    assert result.success is True
    assert result.status_code == 200
