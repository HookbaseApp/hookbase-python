from __future__ import annotations

from typing import Any

from ..models.portal_tokens import CreatePortalTokenParams, PortalToken
from ._base import AsyncResource, SyncResource, _to_body


class PortalTokens(SyncResource):
    def create(
        self,
        application_id: str,
        params: CreatePortalTokenParams | dict[str, Any] | None = None,
    ) -> PortalToken:
        body = _to_body(params) if params else {}
        resp = self._request(
            "POST",
            f"/api/portal/webhook-applications/{application_id}/tokens",
            json=body,
        )
        data = resp.get("data", resp)
        return self._parse(PortalToken, data)

    def list(self, application_id: str) -> list[PortalToken]:
        resp = self._request(
            "GET",
            f"/api/portal/webhook-applications/{application_id}/tokens",
        )
        items = resp.get("data", [])
        return self._parse_list(PortalToken, items if isinstance(items, list) else [])

    def revoke(self, token_id: str) -> None:
        self._request("DELETE", f"/api/portal/tokens/{token_id}")


class AsyncPortalTokens(AsyncResource):
    async def create(
        self,
        application_id: str,
        params: CreatePortalTokenParams | dict[str, Any] | None = None,
    ) -> PortalToken:
        body = _to_body(params) if params else {}
        resp = await self._request(
            "POST",
            f"/api/portal/webhook-applications/{application_id}/tokens",
            json=body,
        )
        data = resp.get("data", resp)
        return self._parse(PortalToken, data)

    async def list(self, application_id: str) -> list[PortalToken]:
        resp = await self._request(
            "GET",
            f"/api/portal/webhook-applications/{application_id}/tokens",
        )
        items = resp.get("data", [])
        return self._parse_list(PortalToken, items if isinstance(items, list) else [])

    async def revoke(self, token_id: str) -> None:
        await self._request("DELETE", f"/api/portal/tokens/{token_id}")
