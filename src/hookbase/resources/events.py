from __future__ import annotations

from typing import Any

from .._pagination import (
    AsyncOffsetPage,
    SyncOffsetPage,
    _async_fetch_offset_page,
    _fetch_offset_page,
)
from ..models.events import Event, EventDebugInfo, EventDetail
from ._base import AsyncResource, SyncResource


class Events(SyncResource):
    def list(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        source_id: str | None = None,
        event_type: str | None = None,
        search: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        signature_valid: str | None = None,
        status: str | None = None,
    ) -> SyncOffsetPage[Event]:
        params = self._clean_params({
            "limit": limit, "offset": offset, "sourceId": source_id,
            "eventType": event_type, "search": search,
            "fromDate": from_date, "toDate": to_date,
            "signatureValid": signature_valid, "status": status,
        })
        return _fetch_offset_page(self._transport, "/api/events", params, Event)

    def get(self, id: str) -> EventDetail:
        resp = self._request("GET", f"/api/events/{id}")
        return self._parse(EventDetail, resp.get("event", resp))

    def debug(self, id: str) -> EventDebugInfo:
        resp = self._request("GET", f"/api/events/{id}/debug")
        return self._parse(EventDebugInfo, resp)

    def export(
        self,
        *,
        format: str = "json",
        source_id: str | None = None,
        event_type: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        status: str | None = None,
    ) -> Any:
        params = self._clean_params({
            "format": format, "sourceId": source_id,
            "eventType": event_type,
            "fromDate": from_date, "toDate": to_date, "status": status,
        })
        return self._request("GET", "/api/events/export", params=params)


class AsyncEvents(AsyncResource):
    async def list(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        source_id: str | None = None,
        event_type: str | None = None,
        search: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        signature_valid: str | None = None,
        status: str | None = None,
    ) -> AsyncOffsetPage[Event]:
        params = self._clean_params({
            "limit": limit, "offset": offset, "sourceId": source_id,
            "eventType": event_type, "search": search,
            "fromDate": from_date, "toDate": to_date,
            "signatureValid": signature_valid, "status": status,
        })
        return await _async_fetch_offset_page(self._transport, "/api/events", params, Event)

    async def get(self, id: str) -> EventDetail:
        resp = await self._request("GET", f"/api/events/{id}")
        return self._parse(EventDetail, resp.get("event", resp))

    async def debug(self, id: str) -> EventDebugInfo:
        resp = await self._request("GET", f"/api/events/{id}/debug")
        return self._parse(EventDebugInfo, resp)

    async def export(
        self,
        *,
        format: str = "json",
        source_id: str | None = None,
        event_type: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        status: str | None = None,
    ) -> Any:
        params = self._clean_params({
            "format": format, "sourceId": source_id,
            "eventType": event_type,
            "fromDate": from_date, "toDate": to_date, "status": status,
        })
        return await self._request("GET", "/api/events/export", params=params)
