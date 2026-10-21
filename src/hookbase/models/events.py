from __future__ import annotations

import json
from typing import Any

from pydantic import field_validator

from ._base import HookbaseModel
from .deliveries import Delivery

InboundEventStatus = str  # API may return: delivered, failed, pending, partial, schema_failed, etc.


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
    payload: Any = None
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


class EventDebugInfo(HookbaseModel):
    event: EventDebugEvent
    curl_command: str = ""
