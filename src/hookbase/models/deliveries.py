from __future__ import annotations

import json
from typing import Any

from pydantic import field_validator, model_validator
from pydantic.alias_generators import to_camel

from ._base import HookbaseModel

# API may return: pending, success, failed, retrying, delivered,
# failed_over, schema_failed, exhausted, etc.
DeliveryStatus = str


class Delivery(HookbaseModel):
    id: str
    event_id: str
    route_id: str
    destination_id: str
    organization_id: str
    status: DeliveryStatus = "pending"
    attempt_count: int = 0
    max_attempts: int = 5
    next_retry_at: str | None = None
    response_status: int | None = None
    response_key: str | None = None
    response_headers: dict[str, Any] | None = None
    response_body: str | None = None
    latency_ms: int | None = None
    error_message: str | None = None
    delivered_at: str | None = None
    created_at: str = ""
    updated_at: str | None = None
    destination_name: str | None = None
    destination_url: str | None = None
    """Set by `deliveries.get` and on `events.get` deliveries; not by `deliveries.list`."""
    event_type: str | None = None
    """Set by `deliveries.list` only."""

    # Deprecated: the SDK's older names for fields the API returns as
    # `responseStatus`, `attemptCount`, `errorMessage`, `latencyMs` and
    # `deliveredAt`. Never sent by the API, so they used to be always empty;
    # now kept in step with the real fields so existing attribute access works.
    status_code: int | None = None
    """Deprecated: read `response_status`."""
    attempts: int = 0
    """Deprecated: read `attempt_count`."""
    error: str | None = None
    """Deprecated: read `error_message`."""
    duration: float | None = None
    """Deprecated: read `latency_ms`."""
    completed_at: str | None = None
    """Deprecated: read `delivered_at`."""

    @field_validator("attempt_count", "max_attempts", mode="before")
    @classmethod
    def _null_counts_to_default(cls, v: Any, info: Any) -> Any:
        # The API sends null for a delivery the worker has not counted yet; a field default only
        # covers a missing key, so without this every list/get containing one failed to validate.
        if v is None:
            return cls.model_fields[info.field_name].default
        return v

    @field_validator("response_headers", mode="before")
    @classmethod
    def _parse_response_headers(cls, v: Any) -> Any:
        # Stored as JSON text, so the API usually sends a string.
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return None
            return parsed if isinstance(parsed, dict) else None
        return v

    @model_validator(mode="before")
    @classmethod
    def _mirror_deprecated(cls, data: Any) -> Any:
        """Copy each real field onto its deprecated name, whichever spelling it came in."""
        if not isinstance(data, dict):
            return data
        out = dict(data)
        for new, old in _DEPRECATED_DELIVERY_FIELDS:
            value = out.get(to_camel(new))
            if value is None:
                value = out.get(new)
            if value is not None:
                out.pop(old, None)
                out[to_camel(old)] = value
        return out


# (current field, deprecated field kept in step with it)
_DEPRECATED_DELIVERY_FIELDS = (
    ("response_status", "status_code"),
    ("attempt_count", "attempts"),
    ("error_message", "error"),
    ("latency_ms", "duration"),
    ("delivered_at", "completed_at"),
)


class DeliveryEvent(HookbaseModel):
    id: str
    event_type: str | None = None
    received_at: str = ""


class DeliveryDestination(HookbaseModel):
    name: str
    url: str


class DeliveryDetail(Delivery):
    # Deprecated: `GET /api/deliveries/:id` has never returned nested `event` or
    # `destination` objects, so these are always None. Read `event_id`,
    # `destination_name` and `destination_url` instead.
    event: DeliveryEvent | None = None
    destination: DeliveryDestination | None = None


class ReplayResult(HookbaseModel):
    delivery_id: str
    message: str = ""


class BulkReplayResult(HookbaseModel):
    message: str = ""
    queued: int = 0
    skipped: int = 0
    events_processed: int | None = None
    """Set by `bulk_replay_events` only."""
    overrides: dict[str, Any] | None = None
    """Set by `bulk_replay_events` only."""
    results: list[dict[str, Any]] = []
