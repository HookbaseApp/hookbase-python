from __future__ import annotations

from .._pagination import (
    AsyncOffsetPage,
    SyncOffsetPage,
    _async_fetch_offset_page,
    _fetch_offset_page,
)
from ..models.deliveries import BulkReplayResult, Delivery, DeliveryDetail, ReplayResult
from ._base import AsyncResource, SyncResource


class Deliveries(SyncResource):
    def list(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        event_id: str | None = None,
        route_id: str | None = None,
        destination_id: str | None = None,
        status: str | None = None,
    ) -> SyncOffsetPage[Delivery]:
        params = self._clean_params({
            "limit": limit, "offset": offset, "eventId": event_id,
            "routeId": route_id, "destinationId": destination_id, "status": status,
        })
        return _fetch_offset_page(self._transport, "/api/deliveries", params, Delivery)

    def get(self, id: str) -> DeliveryDetail:
        resp = self._request("GET", f"/api/deliveries/{id}")
        return self._parse(DeliveryDetail, resp.get("delivery", resp))

    def replay(self, id: str) -> ReplayResult:
        resp = self._request("POST", f"/api/deliveries/{id}/replay")
        return self._parse(ReplayResult, resp)

    def bulk_replay(self, ids: list[str]) -> BulkReplayResult:
        resp = self._request("POST", "/api/deliveries/bulk-replay", json={"ids": ids})
        return self._parse(BulkReplayResult, resp)

    def bulk_replay_events(self, event_ids: list[str]) -> BulkReplayResult:
        resp = self._request("POST", "/api/deliveries/bulk-replay", json={"eventIds": event_ids})
        return self._parse(BulkReplayResult, resp)


class AsyncDeliveries(AsyncResource):
    async def list(
        self,
        *,
        limit: int | None = None,
        offset: int | None = None,
        event_id: str | None = None,
        route_id: str | None = None,
        destination_id: str | None = None,
        status: str | None = None,
    ) -> AsyncOffsetPage[Delivery]:
        params = self._clean_params({
            "limit": limit, "offset": offset, "eventId": event_id,
            "routeId": route_id, "destinationId": destination_id, "status": status,
        })
        return await _async_fetch_offset_page(self._transport, "/api/deliveries", params, Delivery)

    async def get(self, id: str) -> DeliveryDetail:
        resp = await self._request("GET", f"/api/deliveries/{id}")
        return self._parse(DeliveryDetail, resp.get("delivery", resp))

    async def replay(self, id: str) -> ReplayResult:
        resp = await self._request("POST", f"/api/deliveries/{id}/replay")
        return self._parse(ReplayResult, resp)

    async def bulk_replay(self, ids: list[str]) -> BulkReplayResult:
        resp = await self._request("POST", "/api/deliveries/bulk-replay", json={"ids": ids})
        return self._parse(BulkReplayResult, resp)

    async def bulk_replay_events(self, event_ids: list[str]) -> BulkReplayResult:
        resp = await self._request(
            "POST", "/api/deliveries/bulk-replay",
            json={"eventIds": event_ids},
        )
        return self._parse(BulkReplayResult, resp)
