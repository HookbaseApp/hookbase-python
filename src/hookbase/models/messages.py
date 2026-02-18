from __future__ import annotations

from typing import Any, Literal

from ._base import HookbaseModel

MessageStatus = Literal["pending", "success", "failed", "exhausted"]


class SendEventParams(HookbaseModel):
    event_type: str
    payload: dict[str, Any]
    event_id: str | None = None
    metadata: dict[str, Any] | None = None
    endpoint_ids: list[str] | None = None


class SendEventEndpoint(HookbaseModel):
    id: str
    url: str = ""


class SendEventResponse(HookbaseModel):
    event_id: str = ""
    messages_queued: int = 0
    endpoints: list[SendEventEndpoint] = []


class OutboundMessage(HookbaseModel):
    id: str
    message_id: str = ""
    endpoint_id: str = ""
    endpoint_url: str = ""
    event_type: str = ""
    status: MessageStatus = "pending"
    attempts: int = 0
    max_attempts: int = 5
    last_attempt_at: str | None = None
    next_attempt_at: str | None = None
    last_response_status: int | None = None
    last_response_body: str | None = None
    last_error: str | None = None
    delivered_at: str | None = None
    created_at: str = ""
    updated_at: str = ""


class OutboundAttempt(HookbaseModel):
    id: str
    outbound_message_id: str = ""
    attempt_number: int = 0
    response_status: int | None = None
    response_body: str | None = None
    response_headers: dict[str, str] | None = None
    error: str | None = None
    latency_ms: float | None = None
    attempted_at: str = ""


class StatsSummary(HookbaseModel):
    pending: int = 0
    processing: int = 0
    success: int = 0
    failed: int = 0
    exhausted: int = 0
    dlq: int = 0
    total: int = 0


class ReplayResult(HookbaseModel):
    original_message_id: str = ""
    new_message_id: str = ""
    status: str = ""
