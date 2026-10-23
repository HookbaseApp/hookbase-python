from __future__ import annotations

from typing import Any

from ..models.common import BulkDeleteResult
from ..models.tunnels import CreateTunnelParams, Tunnel, TunnelToken, UpdateTunnelParams
from ._base import AsyncResource, SyncResource, _to_body


def _created(resp: Any) -> dict[str, Any]:
    """Fold the top-level ``tunnelUrl``/``wsUrl`` of a create response into the tunnel."""
    data = dict(resp.get("tunnel", resp.get("data", resp)))
    for key in ("tunnelUrl", "wsUrl"):
        if resp.get(key) is not None:
            data[key] = resp[key]
    return data


def _update_body(params: UpdateTunnelParams | dict[str, Any]) -> dict[str, Any]:
    if isinstance(params, UpdateTunnelParams):
        # exclude_none would drop an empty allowed_hosts, which is how hosts are cleared.
        return params.model_dump(by_alias=True, exclude_unset=True)
    return dict(params)


class Tunnels(SyncResource):
    def list(self) -> list[Tunnel]:
        resp = self._request("GET", "/api/tunnels")
        items = resp.get("tunnels", resp.get("data", []))
        return self._parse_list(Tunnel, items if isinstance(items, list) else [])

    def get(self, id: str) -> Tunnel:
        resp = self._request("GET", f"/api/tunnels/{id}")
        data = resp.get("tunnel", resp.get("data", resp))
        return self._parse(Tunnel, data)

    def create(self, params: CreateTunnelParams | dict[str, Any]) -> Tunnel:
        """Create a tunnel. The result carries ``auth_token``, ``tunnel_url`` and ``ws_url``.

        Keep the auth token: this is the only response that contains it.
        """
        body = _to_body(params)
        resp = self._request("POST", "/api/tunnels", json=body)
        return self._parse(Tunnel, _created(resp))

    def update(self, id: str, params: UpdateTunnelParams | dict[str, Any]) -> Tunnel:
        """Rename a tunnel or change its direction or allowed hosts."""
        resp = self._request("PATCH", f"/api/tunnels/{id}", json=_update_body(params))
        return self._parse(Tunnel, resp.get("tunnel", resp))

    def delete(self, id: str) -> None:
        self._request("DELETE", f"/api/tunnels/{id}")

    def regenerate_token(self, id: str) -> TunnelToken:
        """Issue a new auth token and disconnect any client using the old one."""
        resp = self._request("POST", f"/api/tunnels/{id}/regenerate-token")
        return self._parse(TunnelToken, resp)

    def disconnect(self, id: str) -> None:
        """Close the tunnel's active connection, if any."""
        self._request("POST", f"/api/tunnels/{id}/disconnect")

    def bulk_delete(self, ids: list[str]) -> BulkDeleteResult:
        resp = self._request("DELETE", "/api/tunnels/bulk", json={"ids": ids})
        return self._parse(BulkDeleteResult, resp)


class AsyncTunnels(AsyncResource):
    async def list(self) -> list[Tunnel]:
        resp = await self._request("GET", "/api/tunnels")
        items = resp.get("tunnels", resp.get("data", []))
        return self._parse_list(Tunnel, items if isinstance(items, list) else [])

    async def get(self, id: str) -> Tunnel:
        resp = await self._request("GET", f"/api/tunnels/{id}")
        data = resp.get("tunnel", resp.get("data", resp))
        return self._parse(Tunnel, data)

    async def create(self, params: CreateTunnelParams | dict[str, Any]) -> Tunnel:
        """Create a tunnel. See :meth:`Tunnels.create`."""
        body = _to_body(params)
        resp = await self._request("POST", "/api/tunnels", json=body)
        return self._parse(Tunnel, _created(resp))

    async def update(self, id: str, params: UpdateTunnelParams | dict[str, Any]) -> Tunnel:
        resp = await self._request("PATCH", f"/api/tunnels/{id}", json=_update_body(params))
        return self._parse(Tunnel, resp.get("tunnel", resp))

    async def delete(self, id: str) -> None:
        await self._request("DELETE", f"/api/tunnels/{id}")

    async def regenerate_token(self, id: str) -> TunnelToken:
        """Issue a new auth token and disconnect any client using the old one."""
        resp = await self._request("POST", f"/api/tunnels/{id}/regenerate-token")
        return self._parse(TunnelToken, resp)

    async def disconnect(self, id: str) -> None:
        await self._request("POST", f"/api/tunnels/{id}/disconnect")

    async def bulk_delete(self, ids: list[str]) -> BulkDeleteResult:
        resp = await self._request("DELETE", "/api/tunnels/bulk", json={"ids": ids})
        return self._parse(BulkDeleteResult, resp)
