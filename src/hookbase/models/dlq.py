from __future__ import annotations

from typing import Any

from pydantic import model_validator

from ._base import HookbaseModel
from .messages import _mirror


class DlqMessage(HookbaseModel):
    """A dead-lettered message, as `GET /api/outbound-messages/dlq/messages` returns it."""

    id: str
    event_id: str = ""
    endpoint_id: str = ""
    endpoint_url: str | None = None
    application_id: str = ""
    application_name: str | None = None
    event_type: str = ""
    status: str = ""
    dlq_reason: str | None = None
    dlq_moved_at: str | None = None
    dlq_retry_count: int | None = None
    dlq_last_retry_at: str | None = None
    attempts: int = 0
    max_attempts: int = 5
    last_response_status: int | None = None
    last_error_type: str | None = None
    last_error_message: str | None = None
    created_at: str = ""
    completed_at: str | None = None

    # Deprecated: names the API never sent.
    message_id: str = ""
    """Deprecated: read `event_id`."""
    last_error: str | None = None
    """Deprecated: read `last_error_message`."""
    last_attempt_at: str | None = None
    """Deprecated: not returned by the API; always `None`."""
    updated_at: str = ""
    """Deprecated: not returned by the API; always empty."""

    @model_validator(mode="before")
    @classmethod
    def _fill_deprecated(cls, data: Any) -> Any:
        return _mirror(data, {"messageId": "eventId", "lastError": "lastErrorMessage"})


class DlqEndpointStat(HookbaseModel):
    endpoint_id: str
    endpoint_url: str | None = ""
    count: int = 0


class DlqEventTypeStat(HookbaseModel):
    event_type: str
    count: int = 0


class DlqStats(HookbaseModel):
    total: int = 0
    by_reason: dict[str, int] = {}
    by_endpoint: list[DlqEndpointStat] = []
    """The ten endpoints with the most dead-lettered messages."""
    by_event_type: list[DlqEventTypeStat] = []
    """The ten event types with the most dead-lettered messages."""

    top_failing_endpoints: list[DlqEndpointStat] = []
    """Deprecated: read `by_endpoint`; this mirrors it."""

    @model_validator(mode="before")
    @classmethod
    def _fill_deprecated(cls, data: Any) -> Any:
        return _mirror(data, {"topFailingEndpoints": "byEndpoint"})


class DlqRetryResult(HookbaseModel):
    original_message_id: str = ""
    new_message_id: str = ""
    status: str = ""


class DlqBulkRetryResultItem(HookbaseModel):
    original_message_id: str = ""
    new_message_id: str | None = None

    message_id: str = ""
    """Deprecated: read `original_message_id`; this mirrors it."""
    status: str = ""
    """Deprecated: the API returns only the messages it queued, so this is always `"queued"`."""
    error: str | None = None
    """Deprecated: not returned by the API; always `None`."""

    @model_validator(mode="before")
    @classmethod
    def _fill_deprecated(cls, data: Any) -> Any:
        data = _mirror(data, {"messageId": "originalMessageId"})
        if isinstance(data, dict) and not data.get("status"):
            data["status"] = "queued"
        return data


class DlqBulkRetryResult(HookbaseModel):
    """The result of `POST /api/outbound-messages/dlq/retry-bulk`."""

    queued: int = 0
    """Messages re-queued for delivery."""
    skipped: int = 0
    """Requested IDs that were not in the DLQ (or not found)."""
    messages: list[DlqBulkRetryResultItem] = []

    # Deprecated: names the API never sent, derived from the fields above.
    total: int = 0
    """Deprecated: `queued + skipped`."""
    retried: int = 0
    """Deprecated: read `queued`."""
    failed: int = 0
    """Deprecated: read `skipped`."""
    results: list[DlqBulkRetryResultItem] = []
    """Deprecated: read `messages`."""

    @model_validator(mode="before")
    @classmethod
    def _fill_deprecated(cls, data: Any) -> Any:
        data = _mirror(data, {"retried": "queued", "failed": "skipped", "results": "messages"})
        if isinstance(data, dict) and data.get("total") is None:
            data["total"] = int(data.get("queued") or 0) + int(data.get("skipped") or 0)
        return data


class DlqBulkDeleteResult(HookbaseModel):
    deleted: int = 0
    """How many of the IDs were in the DLQ and were removed. Unknown IDs are not counted."""

    total: int = 0
    """Deprecated: mirrors `deleted`."""

    @model_validator(mode="before")
    @classmethod
    def _fill_deprecated(cls, data: Any) -> Any:
        return _mirror(data, {"total": "deleted"})
