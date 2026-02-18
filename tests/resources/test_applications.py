from __future__ import annotations

import pytest
import respx

from hookbase import Hookbase
from hookbase.models import Application

from ..conftest import make_cursor_response


@pytest.fixture
def mock_api():
    with respx.mock(base_url="https://api.hookbase.app") as mock:
        yield mock


@pytest.fixture
def client(mock_api):
    c = Hookbase(api_key="whr_test")
    yield c
    c.close()


APP_DATA = {
    "id": "app_1",
    "name": "Acme Corp",
    "organizationId": "org_1",
    "uid": "cust_123",
    "metadata": {"plan": "pro"},
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z",
}


def test_list_applications(mock_api, client):
    mock_api.get("/api/webhook-applications").respond(
        200, json=make_cursor_response([APP_DATA])
    )
    page = client.outbound.applications.list()
    assert len(page) == 1
    app = page.data[0]
    assert isinstance(app, Application)
    assert app.name == "Acme Corp"
    assert app.uid == "cust_123"


def test_get_application(mock_api, client):
    mock_api.get("/api/webhook-applications/app_1").respond(200, json={"data": APP_DATA})
    app = client.outbound.applications.get("app_1")
    assert app.id == "app_1"


def test_create_application(mock_api, client):
    mock_api.post("/api/webhook-applications").respond(200, json={"data": APP_DATA})
    app = client.outbound.applications.create({"name": "Acme Corp", "uid": "cust_123"})
    assert app.name == "Acme Corp"


def test_update_application(mock_api, client):
    updated = {**APP_DATA, "name": "Acme Inc"}
    mock_api.patch("/api/webhook-applications/app_1").respond(200, json={"data": updated})
    app = client.outbound.applications.update("app_1", {"name": "Acme Inc"})
    assert app.name == "Acme Inc"


def test_delete_application(mock_api, client):
    mock_api.delete("/api/webhook-applications/app_1").respond(204)
    client.outbound.applications.delete("app_1")


def test_get_by_external_id(mock_api, client):
    mock_api.get(
        "/api/webhook-applications/by-external-id/cust_123",
    ).respond(200, json={"data": APP_DATA})
    app = client.outbound.applications.get_by_external_id("cust_123")
    assert app.uid == "cust_123"
