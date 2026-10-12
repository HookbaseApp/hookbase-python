from __future__ import annotations

from ..models.catalog import CatalogProviderDetail, ProviderCatalogList, ProviderEvents
from ._base import AsyncResource, SyncResource


class Providers(SyncResource):
    """The public provider catalog: what each provider signs with and which secret it needs."""

    def list(
        self,
        *,
        category: str | None = None,
        search: str | None = None,
    ) -> ProviderCatalogList:
        """List catalog providers, optionally narrowed by category or a name/description search."""
        params = self._clean_params({"category": category, "search": search})
        resp = self._request("GET", "/api/catalog/providers", params=params or None)
        return self._parse(ProviderCatalogList, resp)

    def get(self, id: str) -> CatalogProviderDetail:
        """One provider in full, by catalog id. 404 for an unknown id."""
        resp = self._request("GET", f"/api/catalog/providers/{id}")
        return self._parse(CatalogProviderDetail, resp.get("provider", resp))

    def events(self, id: str) -> ProviderEvents:
        """The provider's event types and sample payloads. 404 for an unknown id."""
        resp = self._request("GET", f"/api/catalog/providers/{id}/events")
        return self._parse(ProviderEvents, resp)


class AsyncProviders(AsyncResource):
    """The public provider catalog: what each provider signs with and which secret it needs."""

    async def list(
        self,
        *,
        category: str | None = None,
        search: str | None = None,
    ) -> ProviderCatalogList:
        """List catalog providers, optionally narrowed by category or a name/description search."""
        params = self._clean_params({"category": category, "search": search})
        resp = await self._request("GET", "/api/catalog/providers", params=params or None)
        return self._parse(ProviderCatalogList, resp)

    async def get(self, id: str) -> CatalogProviderDetail:
        """One provider in full, by catalog id. 404 for an unknown id."""
        resp = await self._request("GET", f"/api/catalog/providers/{id}")
        return self._parse(CatalogProviderDetail, resp.get("provider", resp))

    async def events(self, id: str) -> ProviderEvents:
        """The provider's event types and sample payloads. 404 for an unknown id."""
        resp = await self._request("GET", f"/api/catalog/providers/{id}/events")
        return self._parse(ProviderEvents, resp)
