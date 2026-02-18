from __future__ import annotations

import json
from typing import Any

from pydantic import field_validator

from ._base import HookbaseModel


class FilterCondition(HookbaseModel):
    field: str
    operator: str
    value: Any = None


class Filter(HookbaseModel):
    id: str
    organization_id: str | None = None
    name: str
    slug: str
    description: str | None = None
    conditions: list[FilterCondition] = []
    logic: str = "and"
    created_at: str = ""
    updated_at: str = ""

    @field_validator("conditions", mode="before")
    @classmethod
    def _parse_conditions(cls, v: Any) -> Any:
        if isinstance(v, str):
            return json.loads(v)
        return v


class CreateFilterParams(HookbaseModel):
    name: str
    slug: str | None = None
    description: str | None = None
    conditions: list[FilterCondition]
    logic: str | None = None


class UpdateFilterParams(HookbaseModel):
    name: str | None = None
    description: str | None = None
    conditions: list[FilterCondition] | None = None
    logic: str | None = None


class FilterTestInput(HookbaseModel):
    conditions: list[FilterCondition]
    logic: str | None = None
    payload: Any = None


class FilterTestResult(HookbaseModel):
    matches: bool
    results: list[dict[str, Any]] = []
    logic: str = "and"
