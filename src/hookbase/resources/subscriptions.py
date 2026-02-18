from __future__ import annotations

from typing import Any

from .._pagination import (
    AsyncCursorPage,
    SyncCursorPage,
    _async_fetch_cursor_page,
    _fetch_cursor_page,
)
from ..models.subscriptions import (
    CreateSubscriptionParams,
    Subscription,
    UpdateSubscriptionParams,
)
from ._base import AsyncResource, SyncResource, _to_body


class Subscriptions(SyncResource):
    def list(
        self,
        *,
        endpoint_id: str | None = None,
        event_type_id: str | None = None,
        is_enabled: bool | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> SyncCursorPage[Subscription]:
        params = self._clean_params({
            "endpointId": endpoint_id, "eventTypeId": event_type_id,
            "isEnabled": is_enabled, "limit": limit, "cursor": cursor,
        })
        return _fetch_cursor_page(
            self._transport, "/api/webhook-subscriptions",
            params, Subscription,
        )

    def get(self, id: str) -> Subscription:
        resp = self._request("GET", f"/api/webhook-subscriptions/{id}")
        data = resp.get("data", resp)
        return self._parse(Subscription, data)

    def create(self, params: CreateSubscriptionParams | dict[str, Any]) -> Subscription:
        body = _to_body(params)
        resp = self._request("POST", "/api/webhook-subscriptions", json=body)
        data = resp.get("data", resp)
        return self._parse(Subscription, data)

    def update(self, id: str, params: UpdateSubscriptionParams | dict[str, Any]) -> Subscription:
        body = _to_body(params)
        resp = self._request("PATCH", f"/api/webhook-subscriptions/{id}", json=body)
        data = resp.get("data", resp)
        return self._parse(Subscription, data)

    def delete(self, id: str) -> None:
        self._request("DELETE", f"/api/webhook-subscriptions/{id}")

    def bulk_create(self, endpoint_id: str, event_type_ids: list[str]) -> list[Subscription]:
        resp = self._request("POST", "/api/webhook-subscriptions/bulk", json={
            "endpointId": endpoint_id,
            "eventTypeIds": event_type_ids,
        })
        items = resp.get("data", resp) if isinstance(resp, dict) else resp
        return self._parse_list(Subscription, items)


class AsyncSubscriptions(AsyncResource):
    async def list(
        self,
        *,
        endpoint_id: str | None = None,
        event_type_id: str | None = None,
        is_enabled: bool | None = None,
        limit: int | None = None,
        cursor: str | None = None,
    ) -> AsyncCursorPage[Subscription]:
        params = self._clean_params({
            "endpointId": endpoint_id, "eventTypeId": event_type_id,
            "isEnabled": is_enabled, "limit": limit, "cursor": cursor,
        })
        return await _async_fetch_cursor_page(
            self._transport, "/api/webhook-subscriptions",
            params, Subscription,
        )

    async def get(self, id: str) -> Subscription:
        resp = await self._request("GET", f"/api/webhook-subscriptions/{id}")
        data = resp.get("data", resp)
        return self._parse(Subscription, data)

    async def create(self, params: CreateSubscriptionParams | dict[str, Any]) -> Subscription:
        body = _to_body(params)
        resp = await self._request("POST", "/api/webhook-subscriptions", json=body)
        data = resp.get("data", resp)
        return self._parse(Subscription, data)

    async def update(
        self, id: str, params: UpdateSubscriptionParams | dict[str, Any],
    ) -> Subscription:
        body = _to_body(params)
        resp = await self._request("PATCH", f"/api/webhook-subscriptions/{id}", json=body)
        data = resp.get("data", resp)
        return self._parse(Subscription, data)

    async def delete(self, id: str) -> None:
        await self._request("DELETE", f"/api/webhook-subscriptions/{id}")

    async def bulk_create(self, endpoint_id: str, event_type_ids: list[str]) -> list[Subscription]:
        resp = await self._request("POST", "/api/webhook-subscriptions/bulk", json={
            "endpointId": endpoint_id,
            "eventTypeIds": event_type_ids,
        })
        items = resp.get("data", resp) if isinstance(resp, dict) else resp
        return self._parse_list(Subscription, items)
