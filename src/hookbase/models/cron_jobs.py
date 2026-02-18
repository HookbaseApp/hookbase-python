from __future__ import annotations

import json

from pydantic import field_validator

from ._base import HookbaseModel


class CronJob(HookbaseModel):
    id: str
    organization_id: str | None = None
    name: str
    description: str | None = None
    url: str = ""
    method: str = "GET"
    headers: dict[str, str] | None = None
    body: str | None = None
    schedule: str = ""
    timezone: str = "UTC"
    is_active: bool = True
    group_id: str | None = None
    last_run_at: str | None = None
    next_run_at: str | None = None
    last_status: str | None = None
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


class CreateCronJobParams(HookbaseModel):
    name: str
    description: str | None = None
    url: str
    method: str | None = None
    headers: dict[str, str] | None = None
    body: str | None = None
    schedule: str
    timezone: str | None = None
    is_active: bool | None = None
    group_id: str | None = None


class UpdateCronJobParams(HookbaseModel):
    name: str | None = None
    description: str | None = None
    url: str | None = None
    method: str | None = None
    headers: dict[str, str] | None = None
    body: str | None = None
    schedule: str | None = None
    timezone: str | None = None
    is_active: bool | None = None
    group_id: str | None = None


class CronGroup(HookbaseModel):
    id: str
    organization_id: str | None = None
    name: str
    description: str | None = None
    created_at: str = ""


class CreateCronGroupParams(HookbaseModel):
    name: str
    description: str | None = None
