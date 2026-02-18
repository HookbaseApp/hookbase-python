from __future__ import annotations

import pytest
import respx

from hookbase import Hookbase
from hookbase.models import Source, SourceWithSecret

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


SOURCE_DATA = {
    "id": "src_1",
    "organizationId": "org_1",
    "name": "GitHub",
    "slug": "github",
    "provider": "github",
    "isActive": True,
    "verifySignature": True,
    "dedupStrategy": "none",
    "ipFilterMode": "none",
    "eventCount": 42,
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z",
}


def test_list_sources(mock_api, client):
    mock_api.get("/api/sources").respond(200, json=make_paginated_response(
        [SOURCE_DATA], data_key="sources", total=1,
    ))
    page = client.sources.list()
    assert len(page) == 1
    src = page.data[0]
    assert isinstance(src, Source)
    assert src.id == "src_1"
    assert src.name == "GitHub"
    assert src.provider == "github"


def test_get_source(mock_api, client):
    mock_api.get("/api/sources/src_1").respond(200, json={"source": SOURCE_DATA})
    src = client.sources.get("src_1")
    assert src.id == "src_1"
    assert src.event_count == 42


def test_create_source(mock_api, client):
    resp_data = {**SOURCE_DATA, "signingSecret": "whsec_abc123"}
    mock_api.post("/api/sources").respond(200, json={"source": resp_data})
    src = client.sources.create({"name": "GitHub", "slug": "github", "provider": "github"})
    assert isinstance(src, SourceWithSecret)
    assert src.signing_secret == "whsec_abc123"


def test_update_source(mock_api, client):
    mock_api.patch("/api/sources/src_1").respond(204)
    client.sources.update("src_1", {"name": "Updated"})


def test_delete_source(mock_api, client):
    mock_api.delete("/api/sources/src_1").respond(204)
    client.sources.delete("src_1")


def test_rotate_secret(mock_api, client):
    mock_api.post("/api/sources/src_1/rotate-secret").respond(
        200, json={"signingSecret": "whsec_new"}
    )
    secret = client.sources.rotate_secret("src_1")
    assert secret == "whsec_new"


def test_reveal_secret(mock_api, client):
    mock_api.get("/api/sources/src_1/reveal-secret").respond(
        200, json={"signingSecret": "whsec_existing"}
    )
    secret = client.sources.reveal_secret("src_1")
    assert secret == "whsec_existing"


def test_bulk_delete(mock_api, client):
    mock_api.delete("/api/sources/bulk").respond(200, json={"success": True, "deleted": 2})
    result = client.sources.bulk_delete(["src_1", "src_2"])
    assert result.deleted == 2


def test_export_sources(mock_api, client):
    mock_api.get("/api/sources/export").respond(200, json={"sources": [SOURCE_DATA]})
    result = client.sources.export()
    assert "sources" in result


def test_import_sources(mock_api, client):
    mock_api.post("/api/sources/import").respond(200, json={
        "success": True, "imported": 1, "skipped": 0, "errors": 0, "results": [],
    })
    result = client.sources.import_sources([SOURCE_DATA])
    assert result.imported == 1
