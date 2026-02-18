from __future__ import annotations

from typing import Any

from .._pagination import (
    AsyncOffsetPage,
    SyncOffsetPage,
    _async_fetch_offset_page,
    _fetch_offset_page,
)
from ..models.transforms import (
    CreateTransformParams,
    Transform,
    TransformTestResult,
    UpdateTransformParams,
)
from ._base import AsyncResource, SyncResource, _to_body


class Transforms(SyncResource):
    def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
    ) -> SyncOffsetPage[Transform]:
        params = self._clean_params({"page": page, "pageSize": page_size})
        return _fetch_offset_page(
            self._transport, "/api/transforms", params, Transform,
            data_key="transforms",
        )

    def get(self, id: str) -> Transform:
        resp = self._request("GET", f"/api/transforms/{id}")
        return self._parse(Transform, resp.get("transform", resp))

    def create(self, params: CreateTransformParams | dict[str, Any]) -> Transform:
        body = _to_body(params)
        resp = self._request("POST", "/api/transforms", json=body)
        return self._parse(Transform, resp.get("transform", resp))

    def update(self, id: str, params: UpdateTransformParams | dict[str, Any]) -> Transform:
        body = _to_body(params)
        resp = self._request("PATCH", f"/api/transforms/{id}", json=body)
        return self._parse(Transform, resp.get("transform", resp))

    def delete(self, id: str) -> None:
        self._request("DELETE", f"/api/transforms/{id}")

    def test(
        self,
        *,
        code: str,
        payload: Any,
        transform_type: str = "jsonata",
        input_format: str = "json",
        output_format: str = "json",
    ) -> TransformTestResult:
        body: dict[str, Any] = {
            "code": code,
            "payload": payload,
            "transformType": transform_type,
            "inputFormat": input_format,
            "outputFormat": output_format,
        }
        resp = self._request("POST", "/api/transforms/test", json=body)
        return self._parse(TransformTestResult, resp)


class AsyncTransforms(AsyncResource):
    async def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
    ) -> AsyncOffsetPage[Transform]:
        params = self._clean_params({"page": page, "pageSize": page_size})
        return await _async_fetch_offset_page(
            self._transport, "/api/transforms", params, Transform,
            data_key="transforms",
        )

    async def get(self, id: str) -> Transform:
        resp = await self._request("GET", f"/api/transforms/{id}")
        return self._parse(Transform, resp.get("transform", resp))

    async def create(self, params: CreateTransformParams | dict[str, Any]) -> Transform:
        body = _to_body(params)
        resp = await self._request("POST", "/api/transforms", json=body)
        return self._parse(Transform, resp.get("transform", resp))

    async def update(self, id: str, params: UpdateTransformParams | dict[str, Any]) -> Transform:
        body = _to_body(params)
        resp = await self._request("PATCH", f"/api/transforms/{id}", json=body)
        return self._parse(Transform, resp.get("transform", resp))

    async def delete(self, id: str) -> None:
        await self._request("DELETE", f"/api/transforms/{id}")

    async def test(
        self,
        *,
        code: str,
        payload: Any,
        transform_type: str = "jsonata",
        input_format: str = "json",
        output_format: str = "json",
    ) -> TransformTestResult:
        body: dict[str, Any] = {
            "code": code,
            "payload": payload,
            "transformType": transform_type,
            "inputFormat": input_format,
            "outputFormat": output_format,
        }
        resp = await self._request(
            "POST", "/api/transforms/test", json=body,
        )
        return self._parse(TransformTestResult, resp)
