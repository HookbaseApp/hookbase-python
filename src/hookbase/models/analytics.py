from __future__ import annotations

from typing import Any

from ._base import HookbaseModel

# GET /api/analytics/dashboard returns its nested objects with snake_case keys (the rest of the
# API is camelCase). Every model here takes either spelling: the alias generator reads camelCase,
# and `populate_by_name` reads the snake_case field names.


class DashboardOverview(HookbaseModel):
    total_events: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    avg_latency: float | None = None
    source_count: int = 0
    destination_count: int = 0


class LatencyPercentiles(HookbaseModel):
    p50: float = 0
    p75: float = 0
    p90: float = 0
    p95: float = 0
    p99: float = 0


class LatencyStats(HookbaseModel):
    percentiles: LatencyPercentiles = LatencyPercentiles()
    min: float = 0
    max: float = 0
    avg: float = 0
    count: int = 0


class LatencyBucket(HookbaseModel):
    bucket: str
    count: int = 0


class LatencyTrendPoint(HookbaseModel):
    period: str
    p50: float = 0
    p95: float = 0
    p99: float = 0
    count: int = 0


class DestinationErrorCount(HookbaseModel):
    destination_id: str | None = None
    destination_name: str | None = None
    error_count: int = 0
    avg_attempts: float = 0


class StatusCodeCount(HookbaseModel):
    status_code: int = 0
    count: int = 0


class ErrorTrendPoint(HookbaseModel):
    date: str
    success: int = 0
    failed: int = 0


class ErrorBreakdown(HookbaseModel):
    by_destination: list[DestinationErrorCount] = []
    by_status_code: list[StatusCodeCount] = []
    trend: list[ErrorTrendPoint] = []


class RetryCounts(HookbaseModel):
    total_deliveries: int = 0
    retried_count: int = 0
    retry_success: int = 0
    avg_attempts_to_success: float = 1
    max_attempts: int = 1


class RetryBucket(HookbaseModel):
    category: str
    count: int = 0


class RetryStats(HookbaseModel):
    stats: RetryCounts = RetryCounts()
    distribution: list[RetryBucket] = []


class SourcePerformance(HookbaseModel):
    id: str
    name: str = ""
    slug: str = ""
    event_count: int = 0
    successful_deliveries: int = 0
    failed_deliveries: int = 0
    avg_latency: float | None = None


class DestinationPerformance(HookbaseModel):
    id: str
    name: str = ""
    url: str | None = None
    total_deliveries: int = 0
    successful: int = 0
    failed: int = 0
    success_rate: float = 0
    avg_latency: float | None = None
    min_latency: float | None = None
    max_latency: float | None = None


class RoutePerformance(HookbaseModel):
    id: str
    name: str = ""
    priority: int = 0
    source_name: str | None = None
    source_slug: str | None = None
    destination_name: str | None = None
    destination_url: str | None = None
    total_deliveries: int = 0
    successful: int = 0
    failed: int = 0
    success_rate: float = 0
    avg_latency: float | None = None
    min_latency: float | None = None
    max_latency: float | None = None


class PayloadSizeDistribution(HookbaseModel):
    distribution: list[LatencyBucket] = []
    sample_size: int = 0
    total_events: int = 0


class DashboardData(HookbaseModel):
    """`GET /api/analytics/dashboard`: everything the analytics dashboard shows, in one call."""

    overview: DashboardOverview = DashboardOverview()
    timeline: list[dict[str, Any]] = []
    """One ``{"period", "events", "successful", "failed"}`` dict per time bucket."""
    latency: LatencyStats = LatencyStats()
    latency_distribution: list[LatencyBucket] = []
    latency_trends: list[LatencyTrendPoint] = []
    errors: ErrorBreakdown = ErrorBreakdown()
    retries: RetryStats = RetryStats()
    sources: list[SourcePerformance] = []
    destinations: list[DestinationPerformance] = []
    routes: list[RoutePerformance] = []
    payload_sizes: PayloadSizeDistribution | None = None
    range: str = "24h"
    interval: str | None = None

    # Before 4.1 these were model fields the API never sent, so they always read 0. They are
    # now derived from `overview`, which holds the real numbers.

    @property
    def events_received(self) -> int:
        """Deprecated: use ``overview.total_events``."""
        return self.overview.total_events

    @property
    def deliveries_completed(self) -> int:
        """Deprecated: use ``overview.successful_deliveries``."""
        return self.overview.successful_deliveries

    @property
    def delivery_success_rate(self) -> float:
        """Deprecated: successful / (successful + failed) deliveries, as a percentage."""
        done = self.overview.successful_deliveries + self.overview.failed_deliveries
        return (self.overview.successful_deliveries / done * 100.0) if done else 0.0

    @property
    def active_sources(self) -> int:
        """Deprecated: use ``overview.source_count``."""
        return self.overview.source_count

    @property
    def active_destinations(self) -> int:
        """Deprecated: use ``overview.destination_count``."""
        return self.overview.destination_count

    @property
    def active_routes(self) -> int:
        """Deprecated: the number of routes with deliveries in the range (``len(routes)``)."""
        return len(self.routes)


class AnalyticsTimeline(HookbaseModel):
    data: list[dict[str, Any]] = []
    range: str = "7d"
    start_date: str | None = None
    end_date: str | None = None
