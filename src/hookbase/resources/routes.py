from __future__ import annotations

from typing import Any

from .._pagination import (
    AsyncOffsetPage,
    SyncOffsetPage,
    _async_fetch_offset_page,
    _fetch_offset_page,
)
from ..models.common import BulkDeleteResult, ImportResult
from ..models.routes import (
    CircuitBreakerConfig,
    CircuitStatusInfo,
    CreateRouteParams,
    Route,
    UpdateRouteParams,
)
from ._base import AsyncResource, SyncResource, _to_body


class Routes(SyncResource):
    def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        source_id: str | None = None,
        destination_id: str | None = None,
        is_active: bool | None = None,
    ) -> SyncOffsetPage[Route]:
        params = self._clean_params({
            "page": page, "pageSize": page_size,
            "sourceId": source_id, "destinationId": destination_id, "isActive": is_active,
        })
        return _fetch_offset_page(
            self._transport, "/api/routes", params, Route,
            data_key="routes",
        )

    def get(self, id: str) -> Route:
        resp = self._request("GET", f"/api/routes/{id}")
        return self._parse(Route, resp.get("route", resp))

    def create(self, params: CreateRouteParams | dict[str, Any]) -> Route:
        body = _to_body(params)
        resp = self._request("POST", "/api/routes", json=body)
        return self._parse(Route, resp.get("route", resp))

    def update(self, id: str, params: UpdateRouteParams | dict[str, Any]) -> None:
        body = _to_body(params)
        self._request("PATCH", f"/api/routes/{id}", json=body)

    def delete(self, id: str) -> None:
        self._request("DELETE", f"/api/routes/{id}")

    def get_circuit_status(self, id: str) -> CircuitStatusInfo:
        resp = self._request("GET", f"/api/routes/{id}/circuit-status")
        return self._parse(CircuitStatusInfo, resp)

    def reset_circuit(self, id: str) -> None:
        self._request("POST", f"/api/routes/{id}/reset-circuit")

    def update_circuit_config(
        self, id: str, params: CircuitBreakerConfig | dict[str, Any],
    ) -> None:
        body = _to_body(params)
        self._request("PATCH", f"/api/routes/{id}/circuit-config", json=body)

    def bulk_update(
        self, ids: list[str], is_active: bool,
    ) -> dict[str, Any]:
        return self._request(
            "PATCH", "/api/routes/bulk",
            json={"ids": ids, "isActive": is_active},
        )

    def bulk_delete(self, ids: list[str]) -> BulkDeleteResult:
        resp = self._request("DELETE", "/api/routes/bulk", json={"ids": ids})
        return self._parse(BulkDeleteResult, resp)

    def export(self, *, ids: list[str] | None = None) -> dict[str, Any]:
        params = {"ids": ",".join(ids)} if ids else None
        return self._request("GET", "/api/routes/export", params=params)

    def import_routes(
        self,
        routes: list[dict[str, Any]],
        *,
        conflict_strategy: str = "skip",
        validate_only: bool = False,
    ) -> ImportResult:
        resp = self._request("POST", "/api/routes/import", json={
            "routes": routes,
            "conflictStrategy": conflict_strategy,
            "validateOnly": validate_only,
        })
        return self._parse(ImportResult, resp)


class AsyncRoutes(AsyncResource):
    async def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        source_id: str | None = None,
        destination_id: str | None = None,
        is_active: bool | None = None,
    ) -> AsyncOffsetPage[Route]:
        params = self._clean_params({
            "page": page, "pageSize": page_size,
            "sourceId": source_id, "destinationId": destination_id, "isActive": is_active,
        })
        return await _async_fetch_offset_page(
            self._transport, "/api/routes", params, Route,
            data_key="routes",
        )

    async def get(self, id: str) -> Route:
        resp = await self._request("GET", f"/api/routes/{id}")
        return self._parse(Route, resp.get("route", resp))

    async def create(self, params: CreateRouteParams | dict[str, Any]) -> Route:
        body = _to_body(params)
        resp = await self._request("POST", "/api/routes", json=body)
        return self._parse(Route, resp.get("route", resp))

    async def update(self, id: str, params: UpdateRouteParams | dict[str, Any]) -> None:
        body = _to_body(params)
        await self._request("PATCH", f"/api/routes/{id}", json=body)

    async def delete(self, id: str) -> None:
        await self._request("DELETE", f"/api/routes/{id}")

    async def get_circuit_status(self, id: str) -> CircuitStatusInfo:
        resp = await self._request("GET", f"/api/routes/{id}/circuit-status")
        return self._parse(CircuitStatusInfo, resp)

    async def reset_circuit(self, id: str) -> None:
        await self._request("POST", f"/api/routes/{id}/reset-circuit")

    async def update_circuit_config(
        self, id: str, params: CircuitBreakerConfig | dict[str, Any],
    ) -> None:
        body = _to_body(params)
        await self._request("PATCH", f"/api/routes/{id}/circuit-config", json=body)

    async def bulk_update(
        self, ids: list[str], is_active: bool,
    ) -> dict[str, Any]:
        return await self._request(
            "PATCH", "/api/routes/bulk",
            json={"ids": ids, "isActive": is_active},
        )

    async def bulk_delete(self, ids: list[str]) -> BulkDeleteResult:
        resp = await self._request("DELETE", "/api/routes/bulk", json={"ids": ids})
        return self._parse(BulkDeleteResult, resp)

    async def export(self, *, ids: list[str] | None = None) -> dict[str, Any]:
        params = {"ids": ",".join(ids)} if ids else None
        return await self._request("GET", "/api/routes/export", params=params)

    async def import_routes(
        self,
        routes: list[dict[str, Any]],
        *,
        conflict_strategy: str = "skip",
        validate_only: bool = False,
    ) -> ImportResult:
        resp = await self._request("POST", "/api/routes/import", json={
            "routes": routes,
            "conflictStrategy": conflict_strategy,
            "validateOnly": validate_only,
        })
        return self._parse(ImportResult, resp)
