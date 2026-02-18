from __future__ import annotations

from typing import Any

from .._pagination import (
    AsyncOffsetPage,
    SyncOffsetPage,
    _async_fetch_offset_page,
    _fetch_offset_page,
)
from ..models.cron_jobs import (
    CreateCronGroupParams,
    CreateCronJobParams,
    CronGroup,
    CronJob,
    UpdateCronJobParams,
)
from ._base import AsyncResource, SyncResource, _to_body


class CronJobs(SyncResource):
    def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
    ) -> SyncOffsetPage[CronJob]:
        params = self._clean_params({"page": page, "pageSize": page_size})
        return _fetch_offset_page(
            self._transport, "/api/cron", params, CronJob,
            data_key="cronJobs",
        )

    def get(self, id: str) -> CronJob:
        resp = self._request("GET", f"/api/cron/{id}")
        data = resp.get("cronJob", resp.get("data", resp))
        return self._parse(CronJob, data)

    def create(self, params: CreateCronJobParams | dict[str, Any]) -> CronJob:
        body = _to_body(params)
        resp = self._request("POST", "/api/cron", json=body)
        data = resp.get("cronJob", resp.get("data", resp))
        return self._parse(CronJob, data)

    def update(self, id: str, params: UpdateCronJobParams | dict[str, Any]) -> None:
        body = _to_body(params)
        self._request("PATCH", f"/api/cron/{id}", json=body)

    def delete(self, id: str) -> None:
        self._request("DELETE", f"/api/cron/{id}")

    def list_groups(self) -> list[CronGroup]:
        resp = self._request("GET", "/api/cron-groups")
        items = resp.get("groups", resp.get("data", []))
        return self._parse_list(CronGroup, items if isinstance(items, list) else [])

    def create_group(self, params: CreateCronGroupParams | dict[str, Any]) -> CronGroup:
        body = _to_body(params)
        resp = self._request("POST", "/api/cron-groups", json=body)
        data = resp.get("group", resp.get("data", resp))
        return self._parse(CronGroup, data)


class AsyncCronJobs(AsyncResource):
    async def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
    ) -> AsyncOffsetPage[CronJob]:
        params = self._clean_params({"page": page, "pageSize": page_size})
        return await _async_fetch_offset_page(
            self._transport, "/api/cron", params, CronJob,
            data_key="cronJobs",
        )

    async def get(self, id: str) -> CronJob:
        resp = await self._request("GET", f"/api/cron/{id}")
        data = resp.get("cronJob", resp.get("data", resp))
        return self._parse(CronJob, data)

    async def create(self, params: CreateCronJobParams | dict[str, Any]) -> CronJob:
        body = _to_body(params)
        resp = await self._request("POST", "/api/cron", json=body)
        data = resp.get("cronJob", resp.get("data", resp))
        return self._parse(CronJob, data)

    async def update(self, id: str, params: UpdateCronJobParams | dict[str, Any]) -> None:
        body = _to_body(params)
        await self._request("PATCH", f"/api/cron/{id}", json=body)

    async def delete(self, id: str) -> None:
        await self._request("DELETE", f"/api/cron/{id}")

    async def list_groups(self) -> list[CronGroup]:
        resp = await self._request("GET", "/api/cron-groups")
        items = resp.get("groups", resp.get("data", []))
        return self._parse_list(CronGroup, items if isinstance(items, list) else [])

    async def create_group(self, params: CreateCronGroupParams | dict[str, Any]) -> CronGroup:
        body = _to_body(params)
        resp = await self._request("POST", "/api/cron-groups", json=body)
        data = resp.get("group", resp.get("data", resp))
        return self._parse(CronGroup, data)
