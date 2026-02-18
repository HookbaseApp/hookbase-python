from __future__ import annotations

from typing import Any

from .._pagination import (
    AsyncCursorPage,
    SyncCursorPage,
    _async_fetch_cursor_page,
    _fetch_cursor_page,
)
from ..models.endpoints import (
    CreateEndpointParams,
    EndpointWithSecret,
    RotateSecretResult,
    UpdateEndpointParams,
    WebhookEndpoint,
)
from ._base import AsyncResource, SyncResource, _to_body


class Endpoints(SyncResource):
    def list(
        self,
        *,
        application_id: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        is_disabled: bool | None = None,
    ) -> SyncCursorPage[WebhookEndpoint]:
        params = self._clean_params({
            "applicationId": application_id, "limit": limit,
            "cursor": cursor, "isDisabled": is_disabled,
        })
        return _fetch_cursor_page(
            self._transport, "/api/webhook-endpoints",
            params, WebhookEndpoint,
        )

    def get(self, id: str) -> WebhookEndpoint:
        resp = self._request("GET", f"/api/webhook-endpoints/{id}")
        data = resp.get("data", resp)
        return self._parse(WebhookEndpoint, data)

    def create(
        self, application_id: str, params: CreateEndpointParams | dict[str, Any]
    ) -> EndpointWithSecret:
        body = dict(_to_body(params))
        body["applicationId"] = application_id
        resp = self._request("POST", "/api/webhook-endpoints", json=body)
        data = resp.get("data", resp)
        return self._parse(EndpointWithSecret, data)

    def update(self, id: str, params: UpdateEndpointParams | dict[str, Any]) -> WebhookEndpoint:
        body = _to_body(params)
        resp = self._request("PATCH", f"/api/webhook-endpoints/{id}", json=body)
        data = resp.get("data", resp)
        return self._parse(WebhookEndpoint, data)

    def delete(self, id: str) -> None:
        self._request("DELETE", f"/api/webhook-endpoints/{id}")

    def rotate_secret(self, id: str, *, grace_period: int | None = None) -> RotateSecretResult:
        body: dict[str, Any] = {}
        if grace_period is not None:
            body["gracePeriod"] = grace_period
        resp = self._request(
            "POST", f"/api/webhook-endpoints/{id}/rotate-secret",
            json=body or None,
        )
        data = resp.get("data", resp)
        return self._parse(RotateSecretResult, data)

    def reset_circuit(self, id: str) -> None:
        self._request("POST", f"/api/webhook-endpoints/{id}/reset-circuit")

    def test(self, id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/webhook-endpoints/{id}/test")

    def verify(self, id: str) -> dict[str, Any]:
        return self._request("POST", f"/api/webhook-endpoints/{id}/verify")


class AsyncEndpoints(AsyncResource):
    async def list(
        self,
        *,
        application_id: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        is_disabled: bool | None = None,
    ) -> AsyncCursorPage[WebhookEndpoint]:
        params = self._clean_params({
            "applicationId": application_id, "limit": limit,
            "cursor": cursor, "isDisabled": is_disabled,
        })
        return await _async_fetch_cursor_page(
            self._transport, "/api/webhook-endpoints",
            params, WebhookEndpoint,
        )

    async def get(self, id: str) -> WebhookEndpoint:
        resp = await self._request("GET", f"/api/webhook-endpoints/{id}")
        data = resp.get("data", resp)
        return self._parse(WebhookEndpoint, data)

    async def create(
        self, application_id: str, params: CreateEndpointParams | dict[str, Any]
    ) -> EndpointWithSecret:
        body = dict(_to_body(params))
        body["applicationId"] = application_id
        resp = await self._request("POST", "/api/webhook-endpoints", json=body)
        data = resp.get("data", resp)
        return self._parse(EndpointWithSecret, data)

    async def update(
        self, id: str, params: UpdateEndpointParams | dict[str, Any],
    ) -> WebhookEndpoint:
        body = _to_body(params)
        resp = await self._request("PATCH", f"/api/webhook-endpoints/{id}", json=body)
        data = resp.get("data", resp)
        return self._parse(WebhookEndpoint, data)

    async def delete(self, id: str) -> None:
        await self._request("DELETE", f"/api/webhook-endpoints/{id}")

    async def rotate_secret(
        self, id: str, *, grace_period: int | None = None,
    ) -> RotateSecretResult:
        body: dict[str, Any] = {}
        if grace_period is not None:
            body["gracePeriod"] = grace_period
        resp = await self._request(
            "POST", f"/api/webhook-endpoints/{id}/rotate-secret",
            json=body or None,
        )
        data = resp.get("data", resp)
        return self._parse(RotateSecretResult, data)

    async def reset_circuit(self, id: str) -> None:
        await self._request("POST", f"/api/webhook-endpoints/{id}/reset-circuit")

    async def test(self, id: str) -> dict[str, Any]:
        return await self._request("POST", f"/api/webhook-endpoints/{id}/test")

    async def verify(self, id: str) -> dict[str, Any]:
        return await self._request("POST", f"/api/webhook-endpoints/{id}/verify")
