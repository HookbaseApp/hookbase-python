from __future__ import annotations

from typing import Any

from .._pagination import (
    AsyncOffsetPage,
    SyncOffsetPage,
    _async_fetch_offset_page,
    _fetch_offset_page,
)
from ..models.filters import (
    CreateFilterParams,
    Filter,
    FilterCondition,
    FilterTestResult,
    UpdateFilterParams,
)
from ._base import AsyncResource, SyncResource, _to_body


class Filters(SyncResource):
    def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
    ) -> SyncOffsetPage[Filter]:
        params = self._clean_params({"page": page, "pageSize": page_size})
        return _fetch_offset_page(
            self._transport, "/api/filters", params, Filter,
            data_key="filters",
        )

    def get(self, id: str) -> Filter:
        resp = self._request("GET", f"/api/filters/{id}")
        return self._parse(Filter, resp.get("filter", resp))

    def create(self, params: CreateFilterParams | dict[str, Any]) -> Filter:
        body = _to_body(params)
        resp = self._request("POST", "/api/filters", json=body)
        return self._parse(Filter, resp.get("filter", resp))

    def update(self, id: str, params: UpdateFilterParams | dict[str, Any]) -> None:
        body = _to_body(params)
        self._request("PATCH", f"/api/filters/{id}", json=body)

    def delete(self, id: str) -> None:
        self._request("DELETE", f"/api/filters/{id}")

    def test(
        self,
        conditions: list[FilterCondition | dict[str, Any]],
        payload: Any,
        *,
        logic: str | None = None,
    ) -> FilterTestResult:
        conds = [
            c.model_dump(by_alias=True) if hasattr(c, "model_dump") else c
            for c in conditions  # type: ignore[attr-defined]
        ]
        body: dict[str, Any] = {"conditions": conds, "payload": payload}
        if logic is not None:
            body["logic"] = logic
        resp = self._request("POST", "/api/filters/test", json=body)
        return self._parse(FilterTestResult, resp)


class AsyncFilters(AsyncResource):
    async def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
    ) -> AsyncOffsetPage[Filter]:
        params = self._clean_params({"page": page, "pageSize": page_size})
        return await _async_fetch_offset_page(
            self._transport, "/api/filters", params, Filter,
            data_key="filters",
        )

    async def get(self, id: str) -> Filter:
        resp = await self._request("GET", f"/api/filters/{id}")
        return self._parse(Filter, resp.get("filter", resp))

    async def create(self, params: CreateFilterParams | dict[str, Any]) -> Filter:
        body = _to_body(params)
        resp = await self._request("POST", "/api/filters", json=body)
        return self._parse(Filter, resp.get("filter", resp))

    async def update(self, id: str, params: UpdateFilterParams | dict[str, Any]) -> None:
        body = _to_body(params)
        await self._request("PATCH", f"/api/filters/{id}", json=body)

    async def delete(self, id: str) -> None:
        await self._request("DELETE", f"/api/filters/{id}")

    async def test(
        self,
        conditions: list[FilterCondition | dict[str, Any]],
        payload: Any,
        *,
        logic: str | None = None,
    ) -> FilterTestResult:
        conds = [
            c.model_dump(by_alias=True) if hasattr(c, "model_dump") else c
            for c in conditions  # type: ignore[attr-defined]
        ]
        body: dict[str, Any] = {"conditions": conds, "payload": payload}
        if logic is not None:
            body["logic"] = logic
        resp = await self._request("POST", "/api/filters/test", json=body)
        return self._parse(FilterTestResult, resp)
