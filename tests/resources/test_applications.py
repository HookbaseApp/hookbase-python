from __future__ import annotations

import pytest
import respx

from hookbase import Hookbase
from hookbase.models import Application, CreateApplicationParams

from ..conftest import make_cursor_response, sent_body


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
    # The API's own field name — `formatApplicationRow` returns `externalId`
    # and has no `uid` at all.
    "externalId": "cust_123",
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
    assert app.external_id == "cust_123"
    # `uid` is the deprecated spelling of the same field.
    assert app.uid == "cust_123"


def test_get_application(mock_api, client):
    mock_api.get("/api/webhook-applications/app_1").respond(200, json={"data": APP_DATA})
    app = client.outbound.applications.get("app_1")
    assert app.id == "app_1"


def test_create_application(mock_api, client):
    """The deprecated `uid` goes on the wire as `externalId`, the only name the
    API accepts — `uid` was silently stripped, leaving the application with no
    external ID at all."""
    route = mock_api.post("/api/webhook-applications").respond(200, json={"data": APP_DATA})
    app = client.outbound.applications.create({"name": "Acme Corp", "uid": "cust_123"})
    assert app.name == "Acme Corp"
    assert sent_body(route) == {"name": "Acme Corp", "externalId": "cust_123"}


def test_create_application_with_external_id(mock_api, client):
    route = mock_api.post("/api/webhook-applications").respond(200, json={"data": APP_DATA})
    client.outbound.applications.create(
        CreateApplicationParams(name="Acme Corp", external_id="cust_123", metadata={"plan": "pro"})
    )
    assert sent_body(route) == {
        "name": "Acme Corp",
        "externalId": "cust_123",
        "metadata": {"plan": "pro"},
    }


def test_create_application_external_id_wins_over_uid(mock_api, client):
    route = mock_api.post("/api/webhook-applications").respond(200, json={"data": APP_DATA})
    client.outbound.applications.create(
        CreateApplicationParams(name="Acme Corp", uid="old", external_id="cust_123")
    )
    body = sent_body(route)
    assert body["externalId"] == "cust_123"
    assert "uid" not in body


def test_upsert_application_uses_the_upsert_route(mock_api, client):
    """`PUT /api/webhook-applications` is not a route and 404s; upserts live
    at `/upsert`."""
    route = mock_api.put("/api/webhook-applications/upsert").respond(
        200, json={"data": APP_DATA, "created": True}
    )
    app, created = client.outbound.applications.upsert({"name": "Acme Corp", "uid": "cust_123"})
    assert app.id == "app_1"
    assert created is True
    assert route.called
    assert route.calls.last.request.url.path == "/api/webhook-applications/upsert"
    assert sent_body(route) == {"name": "Acme Corp", "externalId": "cust_123"}


def test_upsert_application_requires_an_external_id(mock_api, client):
    """`upsertApplicationSchema` is already `.strict()` and requires a non-empty
    `externalId`; fail before the request rather than on a 400."""
    with pytest.raises(ValueError, match="external_id"):
        client.outbound.applications.upsert({"name": "Acme Corp"})


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
    assert app.external_id == "cust_123"


def test_application_without_an_external_id(mock_api, client):
    """`externalId` is null for applications created without one."""
    mock_api.get("/api/webhook-applications/app_2").respond(200, json={"data": {
        **APP_DATA, "id": "app_2", "externalId": None,
    }})
    app = client.outbound.applications.get("app_2")
    assert app.external_id == ""
    assert app.uid == ""
