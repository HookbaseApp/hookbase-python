from __future__ import annotations

from typing import Any

from .._pagination import (
    AsyncOffsetPage,
    SyncOffsetPage,
    _async_fetch_offset_page,
    _fetch_offset_page,
)
from ..models.common import BulkDeleteResult, ImportResult
from ..models.sources import (
    CreateSourceParams,
    Source,
    SourceWithSecret,
    UpdateSourceParams,
)
from ._base import AsyncResource, SyncResource, _to_body


class Sources(SyncResource):
    def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        provider: str | None = None,
        is_active: bool | None = None,
    ) -> SyncOffsetPage[Source]:
        params = self._clean_params({
            "page": page, "pageSize": page_size,
            "search": search, "provider": provider, "isActive": is_active,
        })
        return _fetch_offset_page(
            self._transport, "/api/sources", params, Source,
            data_key="sources",
        )

    def get(self, id: str) -> Source:
        resp = self._request("GET", f"/api/sources/{id}")
        return self._parse(Source, resp.get("source", resp))

    def create(self, params: CreateSourceParams | dict[str, Any]) -> SourceWithSecret:
        body = _to_body(params)
        resp = self._request("POST", "/api/sources", json=body)
        return self._parse(SourceWithSecret, resp.get("source", resp))

    def update(self, id: str, params: UpdateSourceParams | dict[str, Any]) -> None:
        body = _to_body(params)
        self._request("PATCH", f"/api/sources/{id}", json=body)

    def delete(self, id: str) -> None:
        self._request("DELETE", f"/api/sources/{id}")

    def rotate_secret(self, id: str) -> str:
        resp = self._request("POST", f"/api/sources/{id}/rotate-secret")
        return resp.get("signingSecret", "")

    def reveal_secret(self, id: str) -> str:
        resp = self._request("GET", f"/api/sources/{id}/reveal-secret")
        return resp.get("signingSecret", "")

    def export(self, *, ids: list[str] | None = None) -> dict[str, Any]:
        params = {"ids": ",".join(ids)} if ids else None
        return self._request("GET", "/api/sources/export", params=params)

    def import_sources(
        self,
        sources: list[dict[str, Any]],
        *,
        conflict_strategy: str = "skip",
        validate_only: bool = False,
    ) -> ImportResult:
        resp = self._request("POST", "/api/sources/import", json={
            "sources": sources,
            "conflictStrategy": conflict_strategy,
            "validateOnly": validate_only,
        })
        return self._parse(ImportResult, resp)

    def bulk_delete(self, ids: list[str]) -> BulkDeleteResult:
        resp = self._request("DELETE", "/api/sources/bulk", json={"ids": ids})
        return self._parse(BulkDeleteResult, resp)


class AsyncSources(AsyncResource):
    async def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        provider: str | None = None,
        is_active: bool | None = None,
    ) -> AsyncOffsetPage[Source]:
        params = self._clean_params({
            "page": page, "pageSize": page_size,
            "search": search, "provider": provider, "isActive": is_active,
        })
        return await _async_fetch_offset_page(
            self._transport, "/api/sources", params, Source,
            data_key="sources",
        )

    async def get(self, id: str) -> Source:
        resp = await self._request("GET", f"/api/sources/{id}")
        return self._parse(Source, resp.get("source", resp))

    async def create(self, params: CreateSourceParams | dict[str, Any]) -> SourceWithSecret:
        body = _to_body(params)
        resp = await self._request("POST", "/api/sources", json=body)
        return self._parse(SourceWithSecret, resp.get("source", resp))

    async def update(self, id: str, params: UpdateSourceParams | dict[str, Any]) -> None:
        body = _to_body(params)
        await self._request("PATCH", f"/api/sources/{id}", json=body)

    async def delete(self, id: str) -> None:
        await self._request("DELETE", f"/api/sources/{id}")

    async def rotate_secret(self, id: str) -> str:
        resp = await self._request("POST", f"/api/sources/{id}/rotate-secret")
        return resp.get("signingSecret", "")

    async def reveal_secret(self, id: str) -> str:
        resp = await self._request("GET", f"/api/sources/{id}/reveal-secret")
        return resp.get("signingSecret", "")

    async def export(self, *, ids: list[str] | None = None) -> dict[str, Any]:
        params = {"ids": ",".join(ids)} if ids else None
        return await self._request("GET", "/api/sources/export", params=params)

    async def import_sources(
        self,
        sources: list[dict[str, Any]],
        *,
        conflict_strategy: str = "skip",
        validate_only: bool = False,
    ) -> ImportResult:
        resp = await self._request("POST", "/api/sources/import", json={
            "sources": sources,
            "conflictStrategy": conflict_strategy,
            "validateOnly": validate_only,
        })
        return self._parse(ImportResult, resp)

    async def bulk_delete(self, ids: list[str]) -> BulkDeleteResult:
        resp = await self._request("DELETE", "/api/sources/bulk", json={"ids": ids})
        return self._parse(BulkDeleteResult, resp)
