from __future__ import annotations

from typing import Any, Literal

from ._base import HookbaseModel

DeliveryStatus = str  # API may return: pending, success, failed, retrying, delivered, failed_over, schema_failed, exhausted, etc.


class Delivery(HookbaseModel):
    id: str
    event_id: str
    route_id: str
    destination_id: str
    organization_id: str
    status: DeliveryStatus = "pending"
    status_code: int | None = None
    attempts: int = 0
    max_attempts: int = 3
    response_body: str | None = None
    error: str | None = None
    duration: float | None = None
    created_at: str = ""
    completed_at: str | None = None
    next_retry_at: str | None = None


class DeliveryEvent(HookbaseModel):
    id: str
    event_type: str | None = None
    received_at: str = ""


class DeliveryDestination(HookbaseModel):
    name: str
    url: str


class DeliveryDetail(Delivery):
    event: DeliveryEvent | None = None
    destination: DeliveryDestination | None = None


class ReplayResult(HookbaseModel):
    delivery_id: str
    message: str = ""


class BulkReplayResult(HookbaseModel):
    message: str = ""
    queued: int = 0
    skipped: int = 0
    results: list[dict[str, Any]] = []
