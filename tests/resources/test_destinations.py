from __future__ import annotations

import pytest
import respx

from hookbase import Hookbase
from hookbase.models import Destination, TestResult

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
    "url": "https://example.com/webhooks",
    "method": "POST",
    "authType": "none",
    "timeout": 30,
    "retryCount": 3,
    "retryInterval": 60,
    "isActive": True,
    "deliveryCount": 100,
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


def test_create_destination(mock_api, client):
    mock_api.post("/api/destinations").respond(200, json={"destination": DEST_DATA})
    dest = client.destinations.create({"name": "Backend", "url": "https://example.com/webhooks"})
    assert dest.id == "dst_1"


def test_test_destination(mock_api, client):
    mock_api.post("/api/destinations/dst_1/test").respond(200, json={
        "success": True, "statusCode": 200, "duration": 150.5,
    })
    result = client.destinations.test("dst_1")
    assert isinstance(result, TestResult)
    assert result.success is True
    assert result.status_code == 200
