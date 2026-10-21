from __future__ import annotations

from typing import Any

from .._pagination import (
    AsyncCursorPage,
    SyncCursorPage,
    _async_fetch_cursor_page,
    _fetch_cursor_page,
)
from ..models.events import Event, EventDebugInfo, EventDetail, event_detail_data
from ._base import AsyncResource, SyncResource


class Events(SyncResource):
    def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        source_id: str | None = None,
        event_type: str | None = None,
        search: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        signature_valid: str | None = None,
        status: str | None = None,
    ) -> SyncCursorPage[Event]:
        """List inbound events, newest first.

        Cursor-paginated: pass ``next_cursor`` from the previous page as ``cursor``,
        or iterate ``auto_paging_iter()``. ``limit`` is capped at 100 by the API.
        ``source_id`` takes a source id or its slug; one that matches no source raises
        :class:`~hookbase.NotFoundError` rather than returning an empty page.
        """
        params = self._clean_params({
            "limit": limit, "cursor": cursor, "sourceId": source_id,
            "eventType": event_type, "search": search,
            "fromDate": from_date, "toDate": to_date,
            "signatureValid": signature_valid, "status": status,
        })
        return _fetch_cursor_page(
            self._transport, "/api/events", params, Event, data_key="events",
        )

    def get(self, id: str) -> EventDetail:
        resp = self._request("GET", f"/api/events/{id}")
        return self._parse(EventDetail, event_detail_data(resp))

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
        """Export inbound events as JSON or CSV.

        ``source_id`` takes a source id or its slug; one that matches no source raises
        :class:`~hookbase.NotFoundError`.
        """
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
        cursor: str | None = None,
        source_id: str | None = None,
        event_type: str | None = None,
        search: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        signature_valid: str | None = None,
        status: str | None = None,
    ) -> AsyncCursorPage[Event]:
        """List inbound events, newest first.

        Cursor-paginated: pass ``next_cursor`` from the previous page as ``cursor``,
        or iterate ``auto_paging_iter()``. ``limit`` is capped at 100 by the API.
        ``source_id`` takes a source id or its slug; one that matches no source raises
        :class:`~hookbase.NotFoundError` rather than returning an empty page.
        """
        params = self._clean_params({
            "limit": limit, "cursor": cursor, "sourceId": source_id,
            "eventType": event_type, "search": search,
            "fromDate": from_date, "toDate": to_date,
            "signatureValid": signature_valid, "status": status,
        })
        return await _async_fetch_cursor_page(
            self._transport, "/api/events", params, Event, data_key="events",
        )

    async def get(self, id: str) -> EventDetail:
        resp = await self._request("GET", f"/api/events/{id}")
        return self._parse(EventDetail, event_detail_data(resp))

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
        """Export inbound events as JSON or CSV.

        ``source_id`` takes a source id or its slug; one that matches no source raises
        :class:`~hookbase.NotFoundError`.
        """
        params = self._clean_params({
            "format": format, "sourceId": source_id,
            "eventType": event_type,
            "fromDate": from_date, "toDate": to_date, "status": status,
        })
        return await self._request("GET", "/api/events/export", params=params)
