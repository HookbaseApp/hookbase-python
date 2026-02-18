from __future__ import annotations

from typing import Any

from ..models.common import BulkDeleteResult
from ..models.tunnels import CreateTunnelParams, Tunnel
from ._base import AsyncResource, SyncResource, _to_body


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
        body = _to_body(params)
        resp = self._request("POST", "/api/tunnels", json=body)
        data = resp.get("tunnel", resp.get("data", resp))
        return self._parse(Tunnel, data)

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
        body = _to_body(params)
        resp = await self._request("POST", "/api/tunnels", json=body)
        data = resp.get("tunnel", resp.get("data", resp))
        return self._parse(Tunnel, data)

    async def bulk_delete(self, ids: list[str]) -> BulkDeleteResult:
        resp = await self._request("DELETE", "/api/tunnels/bulk", json={"ids": ids})
        return self._parse(BulkDeleteResult, resp)
