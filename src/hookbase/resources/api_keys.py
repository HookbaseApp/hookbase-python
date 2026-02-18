from __future__ import annotations

from typing import Any

from ..models.api_keys import ApiKey, ApiKeyWithSecret, CreateApiKeyParams
from ._base import AsyncResource, SyncResource, _to_body


class ApiKeys(SyncResource):
    def list(self) -> list[ApiKey]:
        resp = self._request("GET", "/api/api-keys")
        items = resp.get("apiKeys", resp.get("data", []))
        return self._parse_list(ApiKey, items if isinstance(items, list) else [])

    def create(self, params: CreateApiKeyParams | dict[str, Any]) -> ApiKeyWithSecret:
        body = _to_body(params)
        resp = self._request("POST", "/api/api-keys", json=body)
        data = resp.get("data", resp.get("apiKey", resp))
        return self._parse(ApiKeyWithSecret, data)

    def delete(self, id: str) -> None:
        self._request("DELETE", f"/api/api-keys/{id}")


class AsyncApiKeys(AsyncResource):
    async def list(self) -> list[ApiKey]:
        resp = await self._request("GET", "/api/api-keys")
        items = resp.get("apiKeys", resp.get("data", []))
        return self._parse_list(ApiKey, items if isinstance(items, list) else [])

    async def create(self, params: CreateApiKeyParams | dict[str, Any]) -> ApiKeyWithSecret:
        body = _to_body(params)
        resp = await self._request("POST", "/api/api-keys", json=body)
        data = resp.get("data", resp.get("apiKey", resp))
        return self._parse(ApiKeyWithSecret, data)

    async def delete(self, id: str) -> None:
        await self._request("DELETE", f"/api/api-keys/{id}")
