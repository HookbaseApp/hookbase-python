from __future__ import annotations

from typing import Any

from ._base import HookbaseModel


class DashboardData(HookbaseModel):
    events_received: int = 0
    deliveries_completed: int = 0
    delivery_success_rate: float = 0.0
    active_sources: int = 0
    active_destinations: int = 0
    active_routes: int = 0
    timeline: list[dict[str, Any]] = []


class AnalyticsTimeline(HookbaseModel):
    data: list[dict[str, Any]] = []
    range: str = "7d"
    start_date: str | None = None
    end_date: str | None = None
