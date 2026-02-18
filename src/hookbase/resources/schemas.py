from __future__ import annotations

from typing import Any

from .._pagination import (
    AsyncOffsetPage,
    SyncOffsetPage,
    _async_fetch_offset_page,
    _fetch_offset_page,
)
from ..models.schemas import CreateSchemaParams, Schema, UpdateSchemaParams
from ._base import AsyncResource, SyncResource, _to_body


class Schemas(SyncResource):
    def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
    ) -> SyncOffsetPage[Schema]:
        params = self._clean_params({"page": page, "pageSize": page_size})
        return _fetch_offset_page(
            self._transport, "/api/schemas", params, Schema,
            data_key="schemas",
        )

    def get(self, id: str) -> Schema:
        resp = self._request("GET", f"/api/schemas/{id}")
        return self._parse(Schema, resp.get("schema", resp))

    def create(self, params: CreateSchemaParams | dict[str, Any]) -> Schema:
        body = _to_body(params)
        resp = self._request("POST", "/api/schemas", json=body)
        return self._parse(Schema, resp.get("schema", resp))

    def update(self, id: str, params: UpdateSchemaParams | dict[str, Any]) -> None:
        body = _to_body(params)
        self._request("PUT", f"/api/schemas/{id}", json=body)

    def delete(self, id: str) -> None:
        self._request("DELETE", f"/api/schemas/{id}")


class AsyncSchemas(AsyncResource):
    async def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
    ) -> AsyncOffsetPage[Schema]:
        params = self._clean_params({"page": page, "pageSize": page_size})
        return await _async_fetch_offset_page(
            self._transport, "/api/schemas", params, Schema,
            data_key="schemas",
        )

    async def get(self, id: str) -> Schema:
        resp = await self._request("GET", f"/api/schemas/{id}")
        return self._parse(Schema, resp.get("schema", resp))

    async def create(self, params: CreateSchemaParams | dict[str, Any]) -> Schema:
        body = _to_body(params)
        resp = await self._request("POST", "/api/schemas", json=body)
        return self._parse(Schema, resp.get("schema", resp))

    async def update(self, id: str, params: UpdateSchemaParams | dict[str, Any]) -> None:
        body = _to_body(params)
        await self._request("PUT", f"/api/schemas/{id}", json=body)

    async def delete(self, id: str) -> None:
        await self._request("DELETE", f"/api/schemas/{id}")
