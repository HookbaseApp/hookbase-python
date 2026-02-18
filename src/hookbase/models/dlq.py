from __future__ import annotations

from ._base import HookbaseModel


class DlqMessage(HookbaseModel):
    id: str
    message_id: str = ""
    endpoint_id: str = ""
    endpoint_url: str | None = None
    application_id: str = ""
    application_name: str | None = None
    event_type: str = ""
    status: str = ""
    dlq_reason: str | None = None
    dlq_moved_at: str | None = None
    attempts: int = 0
    max_attempts: int = 5
    last_attempt_at: str | None = None
    last_response_status: int | None = None
    last_error: str | None = None
    created_at: str = ""
    updated_at: str = ""


class DlqEndpointStat(HookbaseModel):
    endpoint_id: str
    endpoint_url: str = ""
    count: int = 0


class DlqStats(HookbaseModel):
    total: int = 0
    by_reason: dict[str, int] = {}
    top_failing_endpoints: list[DlqEndpointStat] = []


class DlqRetryResult(HookbaseModel):
    original_message_id: str = ""
    new_message_id: str = ""
    status: str = ""


class DlqBulkRetryResultItem(HookbaseModel):
    message_id: str = ""
    status: str = ""
    new_message_id: str | None = None
    error: str | None = None


class DlqBulkRetryResult(HookbaseModel):
    total: int = 0
    retried: int = 0
    failed: int = 0
    results: list[DlqBulkRetryResultItem] = []


class DlqBulkDeleteResult(HookbaseModel):
    total: int = 0
    deleted: int = 0
