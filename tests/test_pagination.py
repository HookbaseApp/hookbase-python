from __future__ import annotations

import httpx
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


def test_offset_next_page_keeps_the_data_key(mock_api, client):
    from hookbase._pagination import _fetch_offset_page
    from hookbase.models import Source

    route = mock_api.get("/api/widgets").mock(side_effect=[
        httpx.Response(200, json={"widgets": [{"id": "w1", "name": "W", "slug": "w"}],
                                  "pagination": {"total": 2, "page": 1, "pageSize": 1}}),
        httpx.Response(200, json={"widgets": [{"id": "w2", "name": "W", "slug": "w"}],
                                  "pagination": {"total": 2, "page": 2, "pageSize": 1}}),
    ])
    page = _fetch_offset_page(
        client._transport, "/api/widgets", {"pageSize": 1}, Source, data_key="widgets",
    )
    assert [w.id for w in page.auto_paging_iter()] == ["w1", "w2"]
    assert route.calls[1].request.url.params["page"] == "2"


async def test_async_offset_auto_paging(mock_api, async_client):
    mock_api.get("/api/sources").mock(side_effect=[
        httpx.Response(200, json=make_paginated_response(
            [{"id": "src_1", "name": "S1", "slug": "s1"}],
            data_key="sources", total=2, page=1, page_size=1,
        )),
        httpx.Response(200, json=make_paginated_response(
            [{"id": "src_2", "name": "S2", "slug": "s2"}],
            data_key="sources", total=2, page=2, page_size=1,
        )),
    ])
    page = await async_client.sources.list(page_size=1)
    assert page.has_more and len(page) == 1 and [s.id for s in page] == ["src_1"]
    assert [s.id async for s in page.auto_paging_iter()] == ["src_1", "src_2"]


async def test_async_cursor_auto_paging(mock_api, async_client):
    route = mock_api.get("/api/webhook-applications").mock(side_effect=[
        httpx.Response(200, json=make_cursor_response(
            [{"id": "app_1", "name": "A", "organizationId": "org_1"}],
            has_more=True, next_cursor="c1",
        )),
        httpx.Response(200, json=make_cursor_response(
            [{"id": "app_2", "name": "B", "organizationId": "org_1"}],
            has_more=False, next_cursor=None,
        )),
    ])
    page = await async_client.outbound.applications.list(limit=1)
    assert [a.id async for a in page.auto_paging_iter()] == ["app_1", "app_2"]
    assert route.calls[1].request.url.params["cursor"] == "c1"
