from __future__ import annotations

from typing import Any

from ._base import HookbaseModel


class Application(HookbaseModel):
    id: str
    name: str
    organization_id: str
    uid: str = ""
    metadata: dict[str, Any] | None = None
    created_at: str = ""
    updated_at: str = ""


class CreateApplicationParams(HookbaseModel):
    name: str
    uid: str | None = None
    metadata: dict[str, Any] | None = None


class UpdateApplicationParams(HookbaseModel):
    name: str | None = None
    metadata: dict[str, Any] | None = None
