from __future__ import annotations

from typing import Any

from .._pagination import (
    AsyncCursorPage,
    SyncCursorPage,
    _async_fetch_cursor_page,
    _fetch_cursor_page,
)
from ..models.applications import (
    Application,
    CreateApplicationParams,
    UpdateApplicationParams,
)
from ._base import AsyncResource, SyncResource, _to_body


class Applications(SyncResource):
    def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        search: str | None = None,
    ) -> SyncCursorPage[Application]:
        params = self._clean_params({"limit": limit, "cursor": cursor, "search": search})
        return _fetch_cursor_page(
            self._transport, "/api/webhook-applications",
            params, Application,
        )

    def get(self, id: str) -> Application:
        resp = self._request("GET", f"/api/webhook-applications/{id}")
        data = resp.get("data", resp)
        return self._parse(Application, data)

    def get_by_external_id(self, external_id: str) -> Application:
        resp = self._request("GET", f"/api/webhook-applications/by-external-id/{external_id}")
        data = resp.get("data", resp)
        return self._parse(Application, data)

    def create(self, params: CreateApplicationParams | dict[str, Any]) -> Application:
        body = _to_body(params)
        resp = self._request("POST", "/api/webhook-applications", json=body)
        data = resp.get("data", resp)
        return self._parse(Application, data)

    def upsert(self, params: CreateApplicationParams | dict[str, Any]) -> tuple[Application, bool]:
        body = _to_body(params)
        resp = self._request("PUT", "/api/webhook-applications", json=body)
        data = resp.get("data", resp)
        created = resp.get("created", False)
        return self._parse(Application, data), created

    def update(self, id: str, params: UpdateApplicationParams | dict[str, Any]) -> Application:
        body = _to_body(params)
        resp = self._request("PATCH", f"/api/webhook-applications/{id}", json=body)
        data = resp.get("data", resp)
        return self._parse(Application, data)

    def delete(self, id: str) -> None:
        self._request("DELETE", f"/api/webhook-applications/{id}")


class AsyncApplications(AsyncResource):
    async def list(
        self,
        *,
        limit: int | None = None,
        cursor: str | None = None,
        search: str | None = None,
    ) -> AsyncCursorPage[Application]:
        params = self._clean_params({"limit": limit, "cursor": cursor, "search": search})
        return await _async_fetch_cursor_page(
            self._transport, "/api/webhook-applications",
            params, Application,
        )

    async def get(self, id: str) -> Application:
        resp = await self._request("GET", f"/api/webhook-applications/{id}")
        data = resp.get("data", resp)
        return self._parse(Application, data)

    async def get_by_external_id(self, external_id: str) -> Application:
        resp = await self._request(
            "GET", f"/api/webhook-applications/by-external-id/{external_id}",
        )
        data = resp.get("data", resp)
        return self._parse(Application, data)

    async def create(self, params: CreateApplicationParams | dict[str, Any]) -> Application:
        body = _to_body(params)
        resp = await self._request("POST", "/api/webhook-applications", json=body)
        data = resp.get("data", resp)
        return self._parse(Application, data)

    async def upsert(
        self, params: CreateApplicationParams | dict[str, Any],
    ) -> tuple[Application, bool]:
        body = _to_body(params)
        resp = await self._request("PUT", "/api/webhook-applications", json=body)
        data = resp.get("data", resp)
        created = resp.get("created", False)
        return self._parse(Application, data), created

    async def update(
        self, id: str, params: UpdateApplicationParams | dict[str, Any],
    ) -> Application:
        body = _to_body(params)
        resp = await self._request("PATCH", f"/api/webhook-applications/{id}", json=body)
        data = resp.get("data", resp)
        return self._parse(Application, data)

    async def delete(self, id: str) -> None:
        await self._request("DELETE", f"/api/webhook-applications/{id}")
