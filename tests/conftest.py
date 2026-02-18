from __future__ import annotations

from typing import Any

import pytest
import respx

from hookbase import AsyncHookbase, Hookbase

TEST_API_KEY = "whr_test_key_123"
TEST_BASE_URL = "https://api.hookbase.app"


@pytest.fixture
def mock_api():
    """Set up respx mock for sync client tests."""
    with respx.mock(base_url=TEST_BASE_URL) as mock:
        yield mock


@pytest.fixture
def client(mock_api):
    """Create a sync Hookbase client with mocked transport."""
    c = Hookbase(api_key=TEST_API_KEY)
    yield c
    c.close()


@pytest.fixture
def async_client(mock_api):
    """Create an async Hookbase client with mocked transport."""
    c = AsyncHookbase(api_key=TEST_API_KEY)
    yield c


def make_paginated_response(
    items: list[dict[str, Any]],
    *,
    data_key: str = "data",
    total: int | None = None,
    page: int = 1,
    page_size: int = 20,
) -> dict[str, Any]:
    """Helper to create a paginated API response."""
    return {
        data_key: items,
        "pagination": {
            "total": total if total is not None else len(items),
            "page": page,
            "pageSize": page_size,
        },
    }


def make_cursor_response(
    items: list[dict[str, Any]],
    *,
    has_more: bool = False,
    next_cursor: str | None = None,
) -> dict[str, Any]:
    """Helper to create a cursor-paginated API response."""
    return {
        "data": items,
        "pagination": {
            "hasMore": has_more,
            "nextCursor": next_cursor,
        },
    }
