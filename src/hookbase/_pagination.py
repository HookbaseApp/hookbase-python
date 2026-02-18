from __future__ import annotations

from collections.abc import AsyncIterator, Iterator
from typing import Any, Generic, TypeVar

from pydantic import TypeAdapter

from ._client import AsyncTransport, SyncTransport

T = TypeVar("T")


class SyncOffsetPage(Generic[T]):
    """Offset-based paginated response (sync)."""

    data: list[T]
    total: int
    page: int
    page_size: int

    def __init__(
        self,
        data: list[T],
        total: int,
        page: int,
        page_size: int,
        *,
        transport: SyncTransport,
        path: str,
        params: dict[str, Any],
        model: type[T],
    ) -> None:
        self.data = data
        self.total = total
        self.page = page
        self.page_size = page_size
        self._transport = transport
        self._path = path
        self._params = params
        self._model = model

    @property
    def has_more(self) -> bool:
        return self.page * self.page_size < self.total

    def next_page(self) -> SyncOffsetPage[T]:
        return _fetch_offset_page(
            self._transport,
            self._path,
            {**self._params, "page": self.page + 1},
            self._model,
        )

    def auto_paging_iter(self) -> Iterator[T]:
        page = self
        while True:
            yield from page.data
            if not page.has_more:
                break
            page = page.next_page()

    def __iter__(self) -> Iterator[T]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)


class AsyncOffsetPage(Generic[T]):
    """Offset-based paginated response (async)."""

    data: list[T]
    total: int
    page: int
    page_size: int

    def __init__(
        self,
        data: list[T],
        total: int,
        page: int,
        page_size: int,
        *,
        transport: AsyncTransport,
        path: str,
        params: dict[str, Any],
        model: type[T],
    ) -> None:
        self.data = data
        self.total = total
        self.page = page
        self.page_size = page_size
        self._transport = transport
        self._path = path
        self._params = params
        self._model = model

    @property
    def has_more(self) -> bool:
        return self.page * self.page_size < self.total

    async def next_page(self) -> AsyncOffsetPage[T]:
        return await _async_fetch_offset_page(
            self._transport,
            self._path,
            {**self._params, "page": self.page + 1},
            self._model,
        )

    async def auto_paging_iter(self) -> AsyncIterator[T]:
        page = self
        while True:
            for item in page.data:
                yield item
            if not page.has_more:
                break
            page = await page.next_page()

    def __iter__(self) -> Iterator[T]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)


class SyncCursorPage(Generic[T]):
    """Cursor-based paginated response (sync)."""

    data: list[T]
    has_more: bool
    next_cursor: str | None

    def __init__(
        self,
        data: list[T],
        has_more: bool,
        next_cursor: str | None,
        *,
        transport: SyncTransport,
        path: str,
        params: dict[str, Any],
        model: type[T],
    ) -> None:
        self.data = data
        self.has_more = has_more
        self.next_cursor = next_cursor
        self._transport = transport
        self._path = path
        self._params = params
        self._model = model

    def next_page(self) -> SyncCursorPage[T]:
        return _fetch_cursor_page(
            self._transport,
            self._path,
            {**self._params, "cursor": self.next_cursor},
            self._model,
        )

    def auto_paging_iter(self) -> Iterator[T]:
        page = self
        while True:
            yield from page.data
            if not page.has_more:
                break
            page = page.next_page()

    def __iter__(self) -> Iterator[T]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)


class AsyncCursorPage(Generic[T]):
    """Cursor-based paginated response (async)."""

    data: list[T]
    has_more: bool
    next_cursor: str | None

    def __init__(
        self,
        data: list[T],
        has_more: bool,
        next_cursor: str | None,
        *,
        transport: AsyncTransport,
        path: str,
        params: dict[str, Any],
        model: type[T],
    ) -> None:
        self.data = data
        self.has_more = has_more
        self.next_cursor = next_cursor
        self._transport = transport
        self._path = path
        self._params = params
        self._model = model

    async def next_page(self) -> AsyncCursorPage[T]:
        return await _async_fetch_cursor_page(
            self._transport,
            self._path,
            {**self._params, "cursor": self.next_cursor},
            self._model,
        )

    async def auto_paging_iter(self) -> AsyncIterator[T]:
        page = self
        while True:
            for item in page.data:
                yield item
            if not page.has_more:
                break
            page = await page.next_page()

    def __iter__(self) -> Iterator[T]:
        return iter(self.data)

    def __len__(self) -> int:
        return len(self.data)


# --- Helper functions for fetching pages ---


def _parse_list(raw: Any, model: type[T]) -> list[T]:
    adapter = TypeAdapter(list[model])  # type: ignore[valid-type]
    return adapter.validate_python(raw)


def _fetch_offset_page(
    transport: SyncTransport,
    path: str,
    params: dict[str, Any],
    model: type[T],
    *,
    data_key: str | None = None,
) -> SyncOffsetPage[T]:
    resp = transport.request("GET", path, params=params)
    items, total, page, page_size = _extract_offset_data(resp, data_key)
    return SyncOffsetPage(
        data=_parse_list(items, model),
        total=total,
        page=page,
        page_size=page_size,
        transport=transport,
        path=path,
        params=params,
        model=model,
    )


async def _async_fetch_offset_page(
    transport: AsyncTransport,
    path: str,
    params: dict[str, Any],
    model: type[T],
    *,
    data_key: str | None = None,
) -> AsyncOffsetPage[T]:
    resp = await transport.request("GET", path, params=params)
    items, total, page, page_size = _extract_offset_data(resp, data_key)
    return AsyncOffsetPage(
        data=_parse_list(items, model),
        total=total,
        page=page,
        page_size=page_size,
        transport=transport,
        path=path,
        params=params,
        model=model,
    )


def _fetch_cursor_page(
    transport: SyncTransport,
    path: str,
    params: dict[str, Any],
    model: type[T],
) -> SyncCursorPage[T]:
    resp = transport.request("GET", path, params=params)
    items, has_more, next_cursor = _extract_cursor_data(resp)
    return SyncCursorPage(
        data=_parse_list(items, model),
        has_more=has_more,
        next_cursor=next_cursor,
        transport=transport,
        path=path,
        params=params,
        model=model,
    )


async def _async_fetch_cursor_page(
    transport: AsyncTransport,
    path: str,
    params: dict[str, Any],
    model: type[T],
) -> AsyncCursorPage[T]:
    resp = await transport.request("GET", path, params=params)
    items, has_more, next_cursor = _extract_cursor_data(resp)
    return AsyncCursorPage(
        data=_parse_list(items, model),
        has_more=has_more,
        next_cursor=next_cursor,
        transport=transport,
        path=path,
        params=params,
        model=model,
    )


def _extract_offset_data(
    resp: Any, data_key: str | None = None
) -> tuple[list[Any], int, int, int]:
    """Extract items + pagination from an offset-based API response."""
    if not isinstance(resp, dict):
        return [], 0, 1, 20

    pagination = resp.get("pagination", {})
    total = pagination.get("total", 0)
    page = pagination.get("page", 1)
    page_size = pagination.get("pageSize", pagination.get("page_size", 20))

    if data_key and data_key in resp:
        items = resp[data_key]
    elif "data" in resp:
        items = resp["data"]
    else:
        # Try common keys
        for key in ("sources", "destinations", "routes", "events", "deliveries",
                     "transforms", "filters", "schemas", "cronJobs", "tunnels",
                     "apiKeys", "members", "invites"):
            if key in resp:
                items = resp[key]
                break
        else:
            items = []

    return items if isinstance(items, list) else [], total, page, page_size


def _extract_cursor_data(resp: Any) -> tuple[list[Any], bool, str | None]:
    """Extract items + pagination from a cursor-based API response."""
    if not isinstance(resp, dict):
        return [], False, None

    items = resp.get("data", [])
    pagination = resp.get("pagination", {})
    has_more = pagination.get("hasMore", pagination.get("has_more", False))
    next_cursor = pagination.get("nextCursor", pagination.get("next_cursor"))

    return items if isinstance(items, list) else [], has_more, next_cursor
