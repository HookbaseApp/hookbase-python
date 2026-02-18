from __future__ import annotations

from typing import Any

from ..models.analytics import DashboardData
from ._base import AsyncResource, SyncResource


class Analytics(SyncResource):
    def dashboard(
        self,
        *,
        range: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> DashboardData:
        params = self._clean_params({
            "range": range, "startDate": start_date, "endDate": end_date,
        })
        resp = self._request("GET", "/api/analytics/dashboard", params=params)
        data = resp.get("data", resp)
        return self._parse(DashboardData, data)

    def overview(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        params = self._clean_params({"startDate": start_date, "endDate": end_date})
        return self._request("GET", "/api/analytics/overview", params=params)


class AsyncAnalytics(AsyncResource):
    async def dashboard(
        self,
        *,
        range: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> DashboardData:
        params = self._clean_params({
            "range": range, "startDate": start_date, "endDate": end_date,
        })
        resp = await self._request("GET", "/api/analytics/dashboard", params=params)
        data = resp.get("data", resp)
        return self._parse(DashboardData, data)

    async def overview(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        params = self._clean_params({"startDate": start_date, "endDate": end_date})
        return await self._request("GET", "/api/analytics/overview", params=params)
