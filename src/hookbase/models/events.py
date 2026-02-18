from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import field_validator

from ._base import HookbaseModel

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
    delivery_stats: DeliveryStats | None = None


class EventDelivery(HookbaseModel):
    id: str
    destination_id: str
    destination_name: str = ""
    destination_url: str = ""
    status: str = ""
    status_code: int | None = None
    attempts: int = 0
    created_at: str = ""
    completed_at: str | None = None


class EventDetail(HookbaseModel):
    id: str
    source_id: str
    event_type: str | None = None
    payload: Any = None
    headers: dict[str, str] = {}
    signature_valid: int | None = None
    received_at: str = ""
    ip_address: str | None = None
    source_name: str = ""
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
