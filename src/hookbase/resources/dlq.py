from __future__ import annotations

import builtins
from typing import Any

from .._pagination import (
    AsyncCursorPage,
    SyncCursorPage,
    _async_fetch_cursor_page,
    _fetch_cursor_page,
)
from ..models.dlq import (
    DlqBulkDeleteResult,
    DlqBulkRetryResult,
    DlqMessage,
    DlqRetryResult,
    DlqStats,
)
from ._base import AsyncResource, SyncResource


def _unwrap(resp: Any) -> Any:
    """The bulk DLQ routes wrap their result in `data`, like every other route."""
    return resp.get("data", resp) if isinstance(resp, dict) else resp


class DLQ(SyncResource):
    def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        endpoint_id: str | None = None,
        application_id: str | None = None,
        dlq_reason: str | None = None,
        event_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> SyncCursorPage[DlqMessage]:
        params = self._clean_params({
            "limit": limit, "cursor": cursor,
            "endpointId": endpoint_id, "applicationId": application_id,
            "reason": dlq_reason, "eventType": event_type,
            "startDate": start_date, "endDate": end_date,
        })
        path = "/api/outbound-messages/dlq/messages"
        return _fetch_cursor_page(self._transport, path, params, DlqMessage)

    def stats(self) -> DlqStats:
        resp = self._request("GET", "/api/outbound-messages/dlq/stats")
        data = resp.get("data", resp)
        return self._parse(DlqStats, data)

    def retry(self, id: str) -> DlqRetryResult:
        resp = self._request("POST", f"/api/outbound-messages/dlq/{id}/retry")
        data = resp.get("data", resp)
        return self._parse(DlqRetryResult, data)

    def retry_bulk(self, ids: builtins.list[str]) -> DlqBulkRetryResult:
        resp = self._request(
            "POST", "/api/outbound-messages/dlq/retry-bulk", json={"messageIds": ids},
        )
        return self._parse(DlqBulkRetryResult, _unwrap(resp))

    def delete(self, id: str) -> None:
        self._request("DELETE", f"/api/outbound-messages/dlq/{id}")

    def bulk_delete(self, ids: builtins.list[str]) -> DlqBulkDeleteResult:
        resp = self._request(
            "DELETE", "/api/outbound-messages/dlq/bulk", json={"messageIds": ids},
        )
        return self._parse(DlqBulkDeleteResult, _unwrap(resp))


class AsyncDLQ(AsyncResource):
    async def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        endpoint_id: str | None = None,
        application_id: str | None = None,
        dlq_reason: str | None = None,
        event_type: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> AsyncCursorPage[DlqMessage]:
        params = self._clean_params({
            "limit": limit, "cursor": cursor,
            "endpointId": endpoint_id, "applicationId": application_id,
            "reason": dlq_reason, "eventType": event_type,
            "startDate": start_date, "endDate": end_date,
        })
        path = "/api/outbound-messages/dlq/messages"
        return await _async_fetch_cursor_page(self._transport, path, params, DlqMessage)

    async def stats(self) -> DlqStats:
        resp = await self._request("GET", "/api/outbound-messages/dlq/stats")
        data = resp.get("data", resp)
        return self._parse(DlqStats, data)

    async def retry(self, id: str) -> DlqRetryResult:
        resp = await self._request("POST", f"/api/outbound-messages/dlq/{id}/retry")
        data = resp.get("data", resp)
        return self._parse(DlqRetryResult, data)

    async def retry_bulk(self, ids: builtins.list[str]) -> DlqBulkRetryResult:
        path = "/api/outbound-messages/dlq/retry-bulk"
        resp = await self._request("POST", path, json={"messageIds": ids})
        return self._parse(DlqBulkRetryResult, _unwrap(resp))

    async def delete(self, id: str) -> None:
        await self._request("DELETE", f"/api/outbound-messages/dlq/{id}")

    async def bulk_delete(self, ids: builtins.list[str]) -> DlqBulkDeleteResult:
        resp = await self._request(
            "DELETE", "/api/outbound-messages/dlq/bulk", json={"messageIds": ids},
        )
        return self._parse(DlqBulkDeleteResult, _unwrap(resp))
