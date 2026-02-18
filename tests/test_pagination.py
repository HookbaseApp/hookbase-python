from __future__ import annotations

import pytest
import respx

from hookbase import Hookbase

from .conftest import make_cursor_response, make_paginated_response


@pytest.fixture
def mock_api():
    with respx.mock(base_url="https://api.hookbase.app") as mock:
        yield mock


@pytest.fixture
def client(mock_api):
    c = Hookbase(api_key="whr_test")
    yield c
    c.close()


def test_offset_page_properties(mock_api, client):
    mock_api.get("/api/sources").respond(200, json=make_paginated_response(
        [{"id": "src_1", "organizationId": "org_1", "name": "Test", "slug": "test", "url": ""}],
        data_key="sources", total=30, page=1, page_size=20,
    ))
    page = client.sources.list()
    assert len(page) == 1
    assert page.total == 30
    assert page.page == 1
    assert page.page_size == 20
    assert page.has_more is True


def test_offset_page_no_more(mock_api, client):
    mock_api.get("/api/sources").respond(200, json=make_paginated_response(
        [{"id": "src_1", "organizationId": "org_1", "name": "Test", "slug": "test"}],
        data_key="sources", total=1, page=1, page_size=20,
    ))
    page = client.sources.list()
    assert page.has_more is False


def test_offset_page_auto_paging(mock_api, client):
    # Page 1
    mock_api.get("/api/sources").respond(200, json=make_paginated_response(
        [{"id": "src_1", "organizationId": "org_1", "name": "S1", "slug": "s1"}],
        data_key="sources", total=2, page=1, page_size=1,
    ))
    page = client.sources.list(page_size=1)

    # Page 2 - need to set up mock for next page request
    mock_api.get("/api/sources").respond(200, json=make_paginated_response(
        [{"id": "src_2", "organizationId": "org_1", "name": "S2", "slug": "s2"}],
        data_key="sources", total=2, page=2, page_size=1,
    ))

    items = list(page.auto_paging_iter())
    assert len(items) == 2
    assert items[0].id == "src_1"
    assert items[1].id == "src_2"


def test_cursor_page_properties(mock_api, client):
    mock_api.get("/api/webhook-applications").respond(200, json=make_cursor_response(
        [{"id": "app_1", "name": "App1", "organizationId": "org_1", "uid": "u1"}],
        has_more=True, next_cursor="cursor_abc",
    ))
    page = client.outbound.applications.list()
    assert len(page) == 1
    assert page.has_more is True
    assert page.next_cursor == "cursor_abc"


def test_cursor_page_no_more(mock_api, client):
    mock_api.get("/api/webhook-applications").respond(200, json=make_cursor_response(
        [{"id": "app_1", "name": "App1", "organizationId": "org_1", "uid": "u1"}],
        has_more=False,
    ))
    page = client.outbound.applications.list()
    assert page.has_more is False
    assert page.next_cursor is None
