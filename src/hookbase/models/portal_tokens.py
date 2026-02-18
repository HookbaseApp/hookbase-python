from __future__ import annotations

from typing import Any

from ._base import HookbaseModel


class PortalToken(HookbaseModel):
    id: str
    application_id: str = ""
    token: str | None = None
    token_prefix: str | None = None
    name: str | None = None
    scopes: list[str] = []
    expires_at: str = ""
    created_at: str = ""
    is_expired: bool | None = None
    is_revoked: bool | None = None


class CreatePortalTokenParams(HookbaseModel):
    name: str | None = None
    scopes: list[str] | None = None
    expires_in_days: int | None = None
    allowed_ips: list[str] | None = None
