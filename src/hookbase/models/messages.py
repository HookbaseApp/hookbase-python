from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import model_validator

from ._base import HookbaseModel

# Every status `outbound_messages.status` takes. The field accepts any string so a status the
# API adds later does not make a whole list page fail to decode, which a closed Literal did for
# `processing`, `awaiting_retry` and `dlq`.
MessageStatus = Union[
    Literal[
        "pending", "processing", "success", "failed", "awaiting_retry", "exhausted", "dlq",
    ],
    str,
]


def _mirror(data: Any, pairs: dict[str, str]) -> Any:
    """Fill each deprecated field (key) from the API field it was a misspelling of (value)."""
    if not isinstance(data, dict):
        return data
    out = dict(data)
    for old, new in pairs.items():
        if out.get(new) is not None and out.get(old) is None:
            out[old] = out[new]
    return out


class SendEventParams(HookbaseModel):
    event_type: str
    payload: Any
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
    """An outbound message as `GET /api/outbound-messages[/:id]` returns it.

    `list` returns the summary fields; `get` adds the subscription, payload and
    error-type fields, which are `None` on list items.
    """

    id: str
    event_id: str = ""
    event_type: str = ""
    application_id: str = ""
    application_name: str | None = None
    endpoint_id: str = ""
    endpoint_url: str | None = ""
    status: MessageStatus = "pending"
    attempts: int = 0
    max_attempts: int = 5
    last_response_status: int | None = None
    last_error_message: str | None = None
    created_at: str = ""
    completed_at: str | None = None

    # `get` only.
    subscription_id: str | None = None
    event_type_id: str | None = None
    last_error_type: str | None = None
    payload_key: str | None = None
    payload_size_bytes: int | None = None
    payload_hash: str | None = None
    metadata: Any = None
    priority: int | None = None
    endpoint_description: str | None = None
    payload: Any = None

    # Deprecated: names the API never sent. The three with an API equivalent mirror it.
    message_id: str = ""
    """Deprecated: read `event_id`."""
    last_error: str | None = None
    """Deprecated: read `last_error_message`."""
    delivered_at: str | None = None
    """Deprecated: read `completed_at`."""
    last_attempt_at: str | None = None
    """Deprecated: not returned by the API; always `None`."""
    next_attempt_at: str | None = None
    """Deprecated: not returned by the API; always `None`."""
    last_response_body: str | None = None
    """Deprecated: not returned by the API; read the attempts instead."""
    updated_at: str = ""
    """Deprecated: not returned by the API; always empty."""

    @model_validator(mode="before")
    @classmethod
    def _fill_deprecated(cls, data: Any) -> Any:
        return _mirror(data, {
            "messageId": "eventId",
            "lastError": "lastErrorMessage",
            "deliveredAt": "completedAt",
        })


class OutboundAttempt(HookbaseModel):
    """One delivery attempt, as `GET /api/outbound-messages/:id/attempts` returns it."""

    id: str
    message_id: str = ""
    attempt_number: int = 0
    status: str = ""
    response_status: int | None = None
    response_headers: dict[str, Any] | None = None
    response_body: str | None = None
    response_time_ms: int | None = None
    total_time_ms: int | None = None
    error_type: str | None = None
    error_message: str | None = None
    error_code: str | None = None
    request_url: str | None = None
    request_headers: dict[str, Any] | None = None
    request_body_size: int | None = None
    triggered_by: str | None = None
    triggered_by_user: str | None = None
    created_at: str = ""
    completed_at: str | None = None

    # Deprecated: names the API never sent, each mirroring its API equivalent.
    outbound_message_id: str = ""
    """Deprecated: read `message_id`."""
    error: str | None = None
    """Deprecated: read `error_message`."""
    latency_ms: float | None = None
    """Deprecated: read `response_time_ms`."""
    attempted_at: str = ""
    """Deprecated: read `created_at`."""

    @model_validator(mode="before")
    @classmethod
    def _fill_deprecated(cls, data: Any) -> Any:
        return _mirror(data, {
            "outboundMessageId": "messageId",
            "error": "errorMessage",
            "latencyMs": "responseTimeMs",
            "attemptedAt": "createdAt",
        })


class StatsSummary(HookbaseModel):
    pending: int = 0
    processing: int = 0
    success: int = 0
    failed: int = 0
    awaiting_retry: int = 0
    exhausted: int = 0
    dlq: int = 0
    total: int = 0


class ReplayResult(HookbaseModel):
    original_message_id: str = ""
    new_message_id: str = ""
    status: str = ""
