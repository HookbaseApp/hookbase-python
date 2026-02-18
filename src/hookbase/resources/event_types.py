from __future__ import annotations

from typing import Any

from .._pagination import (
    AsyncCursorPage,
    SyncCursorPage,
    _async_fetch_cursor_page,
    _fetch_cursor_page,
)
from ..models.event_types import (
    CreateEventTypeParams,
    EventType,
    UpdateEventTypeParams,
)
from ._base import AsyncResource, SyncResource, _to_body


class EventTypes(SyncResource):
    def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        category: str | None = None,
        is_enabled: bool | None = None,
        search: str | None = None,
    ) -> SyncCursorPage[EventType]:
        params = self._clean_params({
            "limit": limit, "cursor": cursor,
            "category": category, "isEnabled": is_enabled, "search": search,
        })
        return _fetch_cursor_page(self._transport, "/api/event-types", params, EventType)

    def get(self, id: str) -> EventType:
        resp = self._request("GET", f"/api/event-types/{id}")
        data = resp.get("data", resp)
        return self._parse(EventType, data)

    def create(self, params: CreateEventTypeParams | dict[str, Any]) -> EventType:
        body = _to_body(params)
        resp = self._request("POST", "/api/event-types", json=body)
        data = resp.get("data", resp)
        return self._parse(EventType, data)

    def update(self, id: str, params: UpdateEventTypeParams | dict[str, Any]) -> EventType:
        body = _to_body(params)
        resp = self._request("PATCH", f"/api/event-types/{id}", json=body)
        data = resp.get("data", resp)
        return self._parse(EventType, data)

    def delete(self, id: str) -> None:
        self._request("DELETE", f"/api/event-types/{id}")


class AsyncEventTypes(AsyncResource):
    async def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        category: str | None = None,
        is_enabled: bool | None = None,
        search: str | None = None,
    ) -> AsyncCursorPage[EventType]:
        params = self._clean_params({
            "limit": limit, "cursor": cursor,
            "category": category, "isEnabled": is_enabled, "search": search,
        })
        return await _async_fetch_cursor_page(
            self._transport, "/api/event-types", params, EventType,
        )

    async def get(self, id: str) -> EventType:
        resp = await self._request("GET", f"/api/event-types/{id}")
        data = resp.get("data", resp)
        return self._parse(EventType, data)

    async def create(self, params: CreateEventTypeParams | dict[str, Any]) -> EventType:
        body = _to_body(params)
        resp = await self._request("POST", "/api/event-types", json=body)
        data = resp.get("data", resp)
        return self._parse(EventType, data)

    async def update(self, id: str, params: UpdateEventTypeParams | dict[str, Any]) -> EventType:
        body = _to_body(params)
        resp = await self._request("PATCH", f"/api/event-types/{id}", json=body)
        data = resp.get("data", resp)
        return self._parse(EventType, data)

    async def delete(self, id: str) -> None:
        await self._request("DELETE", f"/api/event-types/{id}")
