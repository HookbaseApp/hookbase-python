from __future__ import annotations

from typing import Any

from .._pagination import (
    AsyncCursorPage,
    SyncCursorPage,
    _async_fetch_cursor_page,
    _fetch_cursor_page,
)
from ..models.messages import OutboundAttempt, OutboundMessage, ReplayResult, StatsSummary
from ._base import AsyncResource, SyncResource


class MessageLog(SyncResource):
    """Track outbound message delivery status."""

    def list(
        self,
        *,
        application_id: str | None = None,
        endpoint_id: str | None = None,
        message_id: str | None = None,
        status: str | None = None,
        event_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> SyncCursorPage[OutboundMessage]:
        params = self._clean_params({
            "applicationId": application_id, "endpointId": endpoint_id,
            "messageId": message_id, "status": status, "eventType": event_type,
            "startDate": start_date, "endDate": end_date,
            "limit": limit, "cursor": cursor,
        })
        return _fetch_cursor_page(
            self._transport, "/api/outbound-messages",
            params, OutboundMessage,
        )

    def get(self, id: str) -> OutboundMessage:
        resp = self._request("GET", f"/api/outbound-messages/{id}")
        data = resp.get("data", resp)
        return self._parse(OutboundMessage, data)

    def list_attempts(self, id: str) -> list[OutboundAttempt]:
        resp = self._request("GET", f"/api/outbound-messages/{id}/attempts")
        data = resp.get("data", resp)
        return self._parse_list(OutboundAttempt, data if isinstance(data, list) else [])

    def replay(self, id: str) -> ReplayResult:
        resp = self._request("POST", f"/api/outbound-messages/{id}/replay")
        data = resp.get("data", resp)
        return self._parse(ReplayResult, data)

    def stats(self) -> StatsSummary:
        resp = self._request("GET", "/api/outbound-messages/stats/summary")
        data = resp.get("data", resp)
        return self._parse(StatsSummary, data)

    def export(
        self,
        *,
        format: str = "json",
        type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        status: str | None = None,
        event_type: str | None = None,
        application_id: str | None = None,
        limit: int | None = None,
    ) -> Any:
        params = self._clean_params({
            "format": format, "type": type,
            "startDate": start_date, "endDate": end_date,
            "status": status, "eventType": event_type,
            "applicationId": application_id, "limit": limit,
        })
        return self._request("GET", "/api/outbound-messages/export", params=params)


class AsyncMessageLog(AsyncResource):
    """Track outbound message delivery status (async)."""

    async def list(
        self,
        *,
        application_id: str | None = None,
        endpoint_id: str | None = None,
        message_id: str | None = None,
        status: str | None = None,
        event_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> AsyncCursorPage[OutboundMessage]:
        params = self._clean_params({
            "applicationId": application_id, "endpointId": endpoint_id,
            "messageId": message_id, "status": status, "eventType": event_type,
            "startDate": start_date, "endDate": end_date,
            "limit": limit, "cursor": cursor,
        })
        return await _async_fetch_cursor_page(
            self._transport, "/api/outbound-messages",
            params, OutboundMessage,
        )

    async def get(self, id: str) -> OutboundMessage:
        resp = await self._request("GET", f"/api/outbound-messages/{id}")
        data = resp.get("data", resp)
        return self._parse(OutboundMessage, data)

    async def list_attempts(self, id: str) -> list[OutboundAttempt]:
        resp = await self._request("GET", f"/api/outbound-messages/{id}/attempts")
        data = resp.get("data", resp)
        return self._parse_list(OutboundAttempt, data if isinstance(data, list) else [])

    async def replay(self, id: str) -> ReplayResult:
        resp = await self._request("POST", f"/api/outbound-messages/{id}/replay")
        data = resp.get("data", resp)
        return self._parse(ReplayResult, data)

    async def stats(self) -> StatsSummary:
        resp = await self._request("GET", "/api/outbound-messages/stats/summary")
        data = resp.get("data", resp)
        return self._parse(StatsSummary, data)

    async def export(
        self,
        *,
        format: str = "json",
        type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        status: str | None = None,
        event_type: str | None = None,
        application_id: str | None = None,
        limit: int | None = None,
    ) -> Any:
        params = self._clean_params({
            "format": format, "type": type,
            "startDate": start_date, "endDate": end_date,
            "status": status, "eventType": event_type,
            "applicationId": application_id, "limit": limit,
        })
        return await self._request("GET", "/api/outbound-messages/export", params=params)
