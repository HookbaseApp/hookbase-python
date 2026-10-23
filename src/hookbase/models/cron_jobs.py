from __future__ import annotations

import json
from typing import Literal

from pydantic import field_validator

from ._base import HookbaseModel

CronJobExecutionStatus = Literal["success", "failed", "running"]


class CronJob(HookbaseModel):
    id: str
    organization_id: str | None = None
    name: str
    description: str | None = None
    url: str = ""
    method: str = "GET"
    headers: dict[str, str] | None = None
    payload: str | None = None
    cron_expression: str = ""
    timezone: str = "UTC"
    timeout_ms: int = 30000
    is_active: bool = True
    use_static_ip: bool = True
    group_id: str | None = None
    last_run_at: str | None = None
    next_run_at: str | None = None
    consecutive_failures: int = 0
    notify_on_failure: bool = False
    notify_on_success: bool = False
    notify_emails: str | None = None
    created_at: str = ""
    updated_at: str = ""

    @field_validator("headers", mode="before")
    @classmethod
    def _parse_headers(cls, v: object) -> object:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return None
        if isinstance(v, list) and len(v) == 0:
            return None
        return v


class CronJobExecution(HookbaseModel):
    """One run of a cron job: a ``trigger()`` result or an entry of ``list_executions()``."""

    id: str
    status: CronJobExecutionStatus = "success"
    response_status: int | None = None
    latency_ms: int | None = 0
    error: str | None = None
    """Why a ``trigger()`` failed (no response, DNS failure, timeout...)."""
    error_message: str | None = None
    """The same, as stored on a past execution (``list_executions()``)."""
    cron_job_id: str | None = None
    response_body: str | None = None
    response_headers: str | None = None
    started_at: str | None = None
    completed_at: str | None = None


class CreateCronJobParams(HookbaseModel):
    name: str
    description: str | None = None
    url: str
    method: str | None = None
    headers: dict[str, str] | None = None
    payload: str | None = None
    cron_expression: str
    timezone: str | None = None
    timeout_ms: int | None = None
    is_active: bool | None = None
    use_static_ip: bool | None = None
    group_id: str | None = None
    notify_on_failure: bool | None = None
    notify_on_success: bool | None = None
    notify_emails: str | None = None


class UpdateCronJobParams(HookbaseModel):
    name: str | None = None
    description: str | None = None
    url: str | None = None
    method: str | None = None
    headers: dict[str, str] | None = None
    payload: str | None = None
    cron_expression: str | None = None
    timezone: str | None = None
    timeout_ms: int | None = None
    is_active: bool | None = None
    use_static_ip: bool | None = None
    group_id: str | None = None
    notify_on_failure: bool | None = None
    notify_on_success: bool | None = None
    notify_emails: str | None = None


class CronGroup(HookbaseModel):
    id: str
    organization_id: str | None = None
    name: str
    description: str | None = None
    created_at: str = ""


class CreateCronGroupParams(HookbaseModel):
    name: str
    description: str | None = None
