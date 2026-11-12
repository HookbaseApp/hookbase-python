from __future__ import annotations

import builtins
from typing import Any

from .._pagination import (
    AsyncLimitOffsetPage,
    SyncLimitOffsetPage,
    _async_fetch_limit_offset_page,
    _fetch_limit_offset_page,
)
from ..models.deliveries import BulkReplayResult, Delivery, DeliveryDetail, ReplayResult
from ._base import AsyncResource, SyncResource


def _replay_body(
    *,
    modified_payload: Any | None,
    payload_patch: dict[str, Any] | None,
    destination_override: str | None,
    transform_override: dict[str, Any] | None,
    headers_override: dict[str, str] | None,
    persist_transform: bool | None,
) -> dict[str, Any] | None:
    """Build the replay body from the arguments given. None, the API's plain replay, if none is.

    None leaves an argument out. The API takes any value that is present as an edit, so sending
    `modifiedPayload: null` would replay a literal JSON null instead of the stored payload.
    """
    if modified_payload is not None and payload_patch is not None:
        # The API answers 400 PAYLOAD_EDIT_AMBIGUOUS; fail before the request.
        raise ValueError("Pass modified_payload or payload_patch, not both")
    fields = {
        "modifiedPayload": modified_payload,
        "payloadPatch": payload_patch,
        "destinationOverride": destination_override,
        "transformOverride": transform_override,
        "headersOverride": headers_override,
        "persistTransform": persist_transform,
    }
    body = {k: v for k, v in fields.items() if v is not None}
    return body or None


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
    ) -> SyncLimitOffsetPage[Delivery]:
        """List inbound deliveries, newest first.

        ``limit`` defaults to 50 and is capped at 100 by the API. The response has
        no total; ``auto_paging_iter()`` keeps fetching until a page comes back short.
        ``status`` is one of pending, delivered, failed, failed_over, schema_failed,
        throttled, awaiting_retry or held. ``status="pending"`` also returns awaiting_retry
        and held rows, since all three are still waiting to be delivered.
        """
        params = self._clean_params({
            "limit": limit, "offset": offset, "eventId": event_id,
            "routeId": route_id, "destinationId": destination_id, "status": status,
        })
        return _fetch_limit_offset_page(
            self._transport, "/api/deliveries", params, Delivery, data_key="deliveries",
        )

    def get(self, id: str) -> DeliveryDetail:
        resp = self._request("GET", f"/api/deliveries/{id}")
        return self._parse(DeliveryDetail, resp.get("delivery", resp))

    def replay(
        self,
        id: str,
        *,
        modified_payload: Any | None = None,
        payload_patch: dict[str, Any] | None = None,
        destination_override: str | None = None,
        transform_override: dict[str, Any] | None = None,
        headers_override: dict[str, str] | None = None,
        persist_transform: bool | None = None,
    ) -> ReplayResult:
        """Replay a delivery as a new delivery, optionally edited. With no arguments the request
        has no body and the stored payload goes to the same destination.

        Every argument defaults to None, which leaves it out of the request.

        Args:
            modified_payload: Replaces the stored payload. Any JSON value but null, which None
                can't send.
            payload_patch: An RFC 7386 JSON merge patch applied to the *stored* payload: keys
                set to None are removed, the rest replace or add. Use it for a source that masks
                or encrypts fields, since you only see the masked view; it may not touch an
                encrypted field. Exclusive with ``modified_payload`` (ValueError).
            destination_override: A destination id or slug in the same organization.
            transform_override: A one-shot transform: ``{"code": ..., "type": ...,
                "inputFormat": ..., "outputFormat": ...}`` (``code`` required).
            headers_override: Headers to add or replace on this delivery. Framing and signature
                headers are refused.
            persist_transform: With ``transform_override``, also save it as the route's
                transform. The route must already have one.
        """
        body = _replay_body(
            modified_payload=modified_payload, payload_patch=payload_patch,
            destination_override=destination_override, transform_override=transform_override,
            headers_override=headers_override, persist_transform=persist_transform,
        )
        resp = self._request("POST", f"/api/deliveries/{id}/replay", json=body)
        return self._parse(ReplayResult, resp)

    def bulk_replay(self, ids: builtins.list[str]) -> BulkReplayResult:
        resp = self._request("POST", "/api/deliveries/bulk-replay", json={"deliveryIds": ids})
        return self._parse(BulkReplayResult, resp)

    def bulk_replay_events(self, event_ids: builtins.list[str]) -> BulkReplayResult:
        resp = self._request(
            "POST", "/api/deliveries/bulk-replay-events", json={"eventIds": event_ids},
        )
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
    ) -> AsyncLimitOffsetPage[Delivery]:
        """List inbound deliveries, newest first.

        ``limit`` defaults to 50 and is capped at 100 by the API. The response has
        no total; ``auto_paging_iter()`` keeps fetching until a page comes back short.
        ``status`` is one of pending, delivered, failed, failed_over, schema_failed,
        throttled, awaiting_retry or held. ``status="pending"`` also returns awaiting_retry
        and held rows, since all three are still waiting to be delivered.
        """
        params = self._clean_params({
            "limit": limit, "offset": offset, "eventId": event_id,
            "routeId": route_id, "destinationId": destination_id, "status": status,
        })
        return await _async_fetch_limit_offset_page(
            self._transport, "/api/deliveries", params, Delivery, data_key="deliveries",
        )

    async def get(self, id: str) -> DeliveryDetail:
        resp = await self._request("GET", f"/api/deliveries/{id}")
        return self._parse(DeliveryDetail, resp.get("delivery", resp))

    async def replay(
        self,
        id: str,
        *,
        modified_payload: Any | None = None,
        payload_patch: dict[str, Any] | None = None,
        destination_override: str | None = None,
        transform_override: dict[str, Any] | None = None,
        headers_override: dict[str, str] | None = None,
        persist_transform: bool | None = None,
    ) -> ReplayResult:
        """Replay a delivery as a new delivery, optionally edited. See `Deliveries.replay`."""
        body = _replay_body(
            modified_payload=modified_payload, payload_patch=payload_patch,
            destination_override=destination_override, transform_override=transform_override,
            headers_override=headers_override, persist_transform=persist_transform,
        )
        resp = await self._request("POST", f"/api/deliveries/{id}/replay", json=body)
        return self._parse(ReplayResult, resp)

    async def bulk_replay(self, ids: builtins.list[str]) -> BulkReplayResult:
        resp = await self._request("POST", "/api/deliveries/bulk-replay", json={"deliveryIds": ids})
        return self._parse(BulkReplayResult, resp)

    async def bulk_replay_events(self, event_ids: builtins.list[str]) -> BulkReplayResult:
        resp = await self._request(
            "POST", "/api/deliveries/bulk-replay-events",
            json={"eventIds": event_ids},
        )
        return self._parse(BulkReplayResult, resp)
