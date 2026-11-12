from __future__ import annotations

import json
from typing import Any

from pydantic import field_validator, model_validator

from ._base import HookbaseModel
from .deliveries import Delivery, DeliveryStatus

# The API derives it from the event's deliveries: delivered, failed, partial (some delivered),
# pending, no_routes (no route matched) or duplicate. Any string, so a later one still parses.
InboundEventStatus = str


class DeliveryStats(HookbaseModel):
    total: int = 0
    delivered: int = 0
    failed: int = 0
    pending: int = 0


class Event(HookbaseModel):
    id: str
    source_id: str
    organization_id: str
    event_type: str | None = None
    payload_hash: str | None = None
    signature_valid: int | None = None
    received_at: str = ""
    ip_address: str | None = None
    source_name: str = ""
    source_slug: str = ""
    status: InboundEventStatus = "pending"
    method: str | None = None
    delivery_stats: DeliveryStats | None = None


class EventDelivery(Delivery):
    """A delivery of this event, as listed on `events.get`.

    The same shape as :class:`~hookbase.models.Delivery`, with `destination_name`
    and `destination_url` set.
    """


class EventDetail(HookbaseModel):
    id: str
    organization_id: str | None = None
    source_id: str
    event_type: str | None = None
    payload: Any = None
    """The stored payload; None for transient events or when it has expired."""
    payload_hash: str | None = None
    payload_key: str | None = None
    headers: dict[str, str] = {}
    signature_valid: int | None = None
    received_at: str = ""
    ip_address: str | None = None
    source_name: str = ""
    status: InboundEventStatus | None = None
    method: str | None = None
    encrypt_fields: Any = None
    mask_fields: Any = None
    transient: bool = False
    deliveries: list[EventDelivery] = []

    @field_validator("headers", mode="before")
    @classmethod
    def parse_headers(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return {}
        return v if v is not None else {}


def event_detail_data(resp: Any) -> Any:
    """Flatten a `GET /api/events/:id` response into one :class:`EventDetail`.

    The API returns the event's fields under `event`, with `payload`,
    `transient` and `deliveries` beside it at the top level, so parsing `event`
    alone loses the payload and the deliveries.
    """
    if not isinstance(resp, dict) or not isinstance(resp.get("event"), dict):
        return resp
    data = dict(resp["event"])
    for key in ("payload", "transient", "deliveries"):
        if key in resp:
            data[key] = resp[key]
    return data


class EventDebugEvent(HookbaseModel):
    id: str
    source_id: str
    event_type: str | None = None
    headers: dict[str, str] = {}
    """The request headers as stored (`request.headers` in the response)."""
    payload: Any = None
    """The stored payload (`payload` in the response); None for a transient event."""
    signature_valid: int | None = None
    received_at: str = ""
    ip_address: str | None = None

    @field_validator("headers", mode="before")
    @classmethod
    def parse_headers(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return {}
        return v if v is not None else {}


class EventDebugDestination(HookbaseModel):
    name: str = ""
    url: str = ""
    method: str = ""


class EventDebugPatternHint(HookbaseModel):
    """A known failure pattern the delivery's response matched, with a likely fix."""

    id: str
    category: str = ""
    title: str = ""
    hypothesis: str = ""
    suggested_fix: str = ""


class EventDebugRouteCircuit(HookbaseModel):
    """The circuit breaker of the delivery's route, as it is now."""

    state: str = "closed"
    """closed, open or half_open."""
    opened_at: str | None = None
    cooldown_seconds: int | None = None
    failure_threshold: int | None = None
    consecutive_failures: int = 0


class EventDebugDelivery(HookbaseModel):
    """One delivery of the event, as `events.debug` reports it.

    Not the :class:`~hookbase.models.Delivery` shape: the debug view names the fields for
    reading (`status_code`, `duration_ms`, `attempt`) and adds what is useful when tracing a
    failure.
    """

    id: str
    status: DeliveryStatus = "pending"
    status_code: int | None = None
    """The HTTP status the destination answered with."""
    duration_ms: int | None = None
    attempt: int | None = None
    """Attempts made so far."""
    max_attempts: int | None = None
    next_retry_at: str | None = None
    """When the next retry is due; None when none is scheduled, and for a held delivery."""
    hold_expires_at: str | None = None
    """For a `held` delivery: when the hold ends. None for every other status."""
    error: str | None = None
    response_body: str | None = None
    response_headers: dict[str, Any] = {}
    transformed_payload: Any = None
    """The payload after the route's transform, when one ran and its output is stored."""
    route_id: str | None = None
    destination_id: str | None = None
    destination: EventDebugDestination | None = None
    started_at: str | None = None
    completed_at: str | None = None
    failover_index: int = 0
    """0 for the original delivery; 1 and up for the failover backups that followed it."""
    parent_delivery_id: str | None = None
    """For a failover backup: the chain's first delivery."""
    fingerprint: str | None = None
    """Groups failures with the same cause; see `cluster_count`."""
    retry_after: str | None = None
    """The destination's Retry-After header, if it sent one."""
    cluster_count: int | None = None
    """How many deliveries in the organization share this delivery's failure fingerprint."""
    pattern_hints: list[EventDebugPatternHint] = []
    route_circuit: EventDebugRouteCircuit | None = None

    @field_validator("response_headers", "pattern_hints", mode="before")
    @classmethod
    def _null_to_empty(cls, v: Any, info: Any) -> Any:
        if v is None:
            return {} if info.field_name == "response_headers" else []
        return v

    @field_validator("failover_index", mode="before")
    @classmethod
    def _null_index_to_zero(cls, v: Any) -> Any:
        return 0 if v is None else v


class EventDebugInfo(HookbaseModel):
    """The result of `events.debug`."""

    event: EventDebugEvent
    payload: Any = None
    """The stored payload; None for a transient event or one whose payload has expired."""
    transient: bool = False
    deliveries: list[EventDebugDelivery] = []
    curl_command: str = ""
    """A curl command that re-sends the event to its source. Empty for a transient event, whose
    payload is not stored."""

    @model_validator(mode="before")
    @classmethod
    def _lift_debug_fields(cls, data: Any) -> Any:
        """Read the fields the API sends outside `event`.

        `curlCommand` is under `debug` (null for a transient event), and the request headers
        and payload sit beside `event`; reading only the top level left `curl_command`,
        `event.headers` and `event.payload` always empty.
        """
        if not isinstance(data, dict):
            return data
        out = dict(data)
        debug = out.get("debug")
        if "curlCommand" not in out and "curl_command" not in out and isinstance(debug, dict):
            out["curlCommand"] = debug.get("curlCommand") or ""
        elif out.get("curlCommand") is None and "curlCommand" in out:
            out["curlCommand"] = ""
        event = out.get("event")
        if isinstance(event, dict):
            event = dict(event)
            request = out.get("request")
            if "headers" not in event and isinstance(request, dict):
                event["headers"] = request.get("headers")
            if "payload" not in event and "payload" in out:
                event["payload"] = out["payload"]
            out["event"] = event
        return out
