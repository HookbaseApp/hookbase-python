from __future__ import annotations

from typing import Any

from pydantic import Field

from ._base import HookbaseModel


class EventType(HookbaseModel):
    id: str
    organization_id: str
    name: str
    display_name: str | None = None
    description: str | None = None
    category: str | None = None
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")
    is_enabled: bool = True
    is_archived: bool = False
    created_at: str = ""
    updated_at: str = ""


class CreateEventTypeParams(HookbaseModel):
    name: str
    display_name: str | None = None
    description: str | None = None
    category: str | None = None
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")


class UpdateEventTypeParams(HookbaseModel):
    display_name: str | None = None
    description: str | None = None
    category: str | None = None
    schema_: dict[str, Any] | None = Field(default=None, alias="schema")
    is_enabled: bool | None = None
