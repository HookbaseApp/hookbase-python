from __future__ import annotations

from ._base import HookbaseModel


class Tunnel(HookbaseModel):
    id: str
    organization_id: str
    name: str
    subdomain: str = ""
    status: str = "disconnected"
    tunnel_url: str | None = None
    created_at: str = ""
    updated_at: str = ""


class CreateTunnelParams(HookbaseModel):
    name: str
    subdomain: str | None = None
