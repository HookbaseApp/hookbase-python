from __future__ import annotations

from typing import Any

from .._pagination import (
    AsyncOffsetPage,
    SyncOffsetPage,
    _async_fetch_offset_page,
    _fetch_offset_page,
)
from ..models.common import BulkDeleteResult, ImportResult
from ..models.destinations import (
    CreateDestinationParams,
    Destination,
    TestResult,
    UpdateDestinationParams,
)
from ._base import AsyncResource, SyncResource, _to_body


class Destinations(SyncResource):
    def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> SyncOffsetPage[Destination]:
        params = self._clean_params({
            "page": page, "pageSize": page_size,
            "search": search, "isActive": is_active,
        })
        return _fetch_offset_page(
            self._transport, "/api/destinations", params, Destination, data_key="destinations"
        )

    def get(self, id: str) -> Destination:
        resp = self._request("GET", f"/api/destinations/{id}")
        return self._parse(Destination, resp.get("destination", resp))

    def create(self, params: CreateDestinationParams | dict[str, Any]) -> Destination:
        body = _to_body(params)
        resp = self._request("POST", "/api/destinations", json=body)
        return self._parse(Destination, resp.get("destination", resp))

    def update(self, id: str, params: UpdateDestinationParams | dict[str, Any]) -> None:
        body = _to_body(params)
        self._request("PATCH", f"/api/destinations/{id}", json=body)

    def delete(self, id: str) -> None:
        self._request("DELETE", f"/api/destinations/{id}")

    def test(self, id: str) -> TestResult:
        resp = self._request("POST", f"/api/destinations/{id}/test")
        return self._parse(TestResult, resp)

    def export(self, *, ids: list[str] | None = None) -> dict[str, Any]:
        params = {"ids": ",".join(ids)} if ids else None
        return self._request("GET", "/api/destinations/export", params=params)

    def import_destinations(
        self,
        destinations: list[dict[str, Any]],
        *,
        conflict_strategy: str = "skip",
        validate_only: bool = False,
    ) -> ImportResult:
        resp = self._request("POST", "/api/destinations/import", json={
            "destinations": destinations,
            "conflictStrategy": conflict_strategy,
            "validateOnly": validate_only,
        })
        return self._parse(ImportResult, resp)

    def bulk_delete(self, ids: list[str]) -> BulkDeleteResult:
        resp = self._request("DELETE", "/api/destinations/bulk", json={"ids": ids})
        return self._parse(BulkDeleteResult, resp)


class AsyncDestinations(AsyncResource):
    async def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> AsyncOffsetPage[Destination]:
        params = self._clean_params({
            "page": page, "pageSize": page_size,
            "search": search, "isActive": is_active,
        })
        return await _async_fetch_offset_page(
            self._transport, "/api/destinations", params, Destination, data_key="destinations"
        )

    async def get(self, id: str) -> Destination:
        resp = await self._request("GET", f"/api/destinations/{id}")
        return self._parse(Destination, resp.get("destination", resp))

    async def create(self, params: CreateDestinationParams | dict[str, Any]) -> Destination:
        body = _to_body(params)
        resp = await self._request("POST", "/api/destinations", json=body)
        return self._parse(Destination, resp.get("destination", resp))

    async def update(self, id: str, params: UpdateDestinationParams | dict[str, Any]) -> None:
        body = _to_body(params)
        await self._request("PATCH", f"/api/destinations/{id}", json=body)

    async def delete(self, id: str) -> None:
        await self._request("DELETE", f"/api/destinations/{id}")

    async def test(self, id: str) -> TestResult:
        resp = await self._request("POST", f"/api/destinations/{id}/test")
        return self._parse(TestResult, resp)

    async def export(self, *, ids: list[str] | None = None) -> dict[str, Any]:
        params = {"ids": ",".join(ids)} if ids else None
        return await self._request("GET", "/api/destinations/export", params=params)

    async def import_destinations(
        self,
        destinations: list[dict[str, Any]],
        *,
        conflict_strategy: str = "skip",
        validate_only: bool = False,
    ) -> ImportResult:
        resp = await self._request("POST", "/api/destinations/import", json={
            "destinations": destinations,
            "conflictStrategy": conflict_strategy,
            "validateOnly": validate_only,
        })
        return self._parse(ImportResult, resp)

    async def bulk_delete(self, ids: list[str]) -> BulkDeleteResult:
        resp = await self._request("DELETE", "/api/destinations/bulk", json={"ids": ids})
        return self._parse(BulkDeleteResult, resp)
