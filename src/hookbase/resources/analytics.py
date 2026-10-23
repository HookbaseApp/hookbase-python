from __future__ import annotations

from typing import Any

from ..models.analytics import DashboardData
from ._base import AsyncResource, SyncResource, _warn_ignored


def _dashboard_params(
    range: str | None,
    start_date: str | None,
    end_date: str | None,
    tz: str | None,
    source_id: str | None,
    destination_id: str | None,
) -> dict[str, Any]:
    return SyncResource._clean_params({
        "range": range, "startDate": start_date, "endDate": end_date, "tz": tz,
        "sourceId": source_id, "destinationId": destination_id,
    })


class Analytics(SyncResource):
    def dashboard(
        self,
        *,
        range: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        tz: str | None = None,
        source_id: str | None = None,
        destination_id: str | None = None,
    ) -> DashboardData:
        """Dashboard analytics for a time range.

        Args:
            range: ``1h``, ``24h``, ``7d`` (the default) or ``30d``; ``custom`` together with
                ``start_date`` and ``end_date`` (ISO-8601).
            tz: IANA time zone the timeline buckets are aligned to (default ``UTC``).
            source_id: Only events from this source.
            destination_id: Only deliveries to this destination.
        """
        params = _dashboard_params(range, start_date, end_date, tz, source_id, destination_id)
        resp = self._request("GET", "/api/analytics/dashboard", params=params)
        return self._parse(DashboardData, resp)

    def overview(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """All-time totals: ``{"stats": {"total_events", "successful_deliveries", ...}}``.

        The API has no date filter here; ``start_date``/``end_date`` are ignored (use
        ``dashboard(range="custom", ...)`` for a range).
        """
        _warn_ignored("analytics.overview()", start_date=start_date, end_date=end_date)
        return self._request("GET", "/api/analytics/overview")


class AsyncAnalytics(AsyncResource):
    async def dashboard(
        self,
        *,
        range: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
        tz: str | None = None,
        source_id: str | None = None,
        destination_id: str | None = None,
    ) -> DashboardData:
        """Dashboard analytics for a time range. See :meth:`Analytics.dashboard`."""
        params = _dashboard_params(range, start_date, end_date, tz, source_id, destination_id)
        resp = await self._request("GET", "/api/analytics/dashboard", params=params)
        return self._parse(DashboardData, resp)

    async def overview(
        self,
        *,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, Any]:
        """All-time totals. ``start_date``/``end_date`` are ignored, as the API has no filter."""
        _warn_ignored("analytics.overview()", start_date=start_date, end_date=end_date)
        return await self._request("GET", "/api/analytics/overview")
