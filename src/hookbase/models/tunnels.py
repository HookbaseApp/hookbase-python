from __future__ import annotations

import json
from typing import Any

from pydantic import field_validator

from ._base import HookbaseModel


class Tunnel(HookbaseModel):
    id: str
    organization_id: str = ""
    name: str
    subdomain: str = ""
    status: str = "disconnected"
    direction: str = "inbound"
    """``inbound`` or ``bidirectional``."""
    allowed_hosts: list[str] | None = None
    user_id: str | None = None
    user_name: str | None = None
    local_port: int | None = None
    total_requests: int = 0
    last_connected_at: str | None = None
    last_request_at: str | None = None
    tunnel_url: str | None = None
    """Public URL. Only ``tunnels.create()`` returns it."""
    ws_url: str | None = None
    """WebSocket URL the CLI connects to, with the token in it. Only on create/regenerate."""
    auth_token: str | None = None
    """The tunnel's auth token in full. Only ``create()`` returns it, once; it is not stored."""
    created_at: str = ""
    updated_at: str = ""

    @field_validator("allowed_hosts", mode="before")
    @classmethod
    def _decode_hosts(cls, value: Any) -> Any:
        # The API stores and returns allowed hosts as a JSON-encoded string.
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except ValueError:
                return [value]
        return value


class CreateTunnelParams(HookbaseModel):
    name: str
    subdomain: str | None = None
    direction: str | None = None
    """``inbound`` (default) or ``bidirectional`` (Pro and Business plans)."""
    allowed_hosts: list[str] | None = None
    """Up to 20 hosts a bidirectional tunnel may forward to."""


class UpdateTunnelParams(HookbaseModel):
    name: str | None = None
    direction: str | None = None
    allowed_hosts: list[str] | None = None
    """An empty list clears the allowed hosts."""


class TunnelToken(HookbaseModel):
    """``tunnels.regenerate_token()``: the new token, shown once, and the URL that uses it."""

    auth_token: str
    ws_url: str | None = None
