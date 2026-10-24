from __future__ import annotations

import builtins
from typing import Any

from .._pagination import (
    AsyncOffsetPage,
    SyncOffsetPage,
    _async_fetch_offset_page,
    _fetch_offset_page,
)
from ..models.common import BulkDeleteResult, ImportResult
from ..models.sources import (
    CreateSourceParams,
    PendingVerification,
    Source,
    SourceWithSecret,
    UpdateSourceParams,
    update_source_body,
)
from ._base import AsyncResource, SyncResource, _to_body, _warn_ignored


class Sources(SyncResource):
    def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        provider: str | None = None,
        is_active: bool | None = None,
    ) -> SyncOffsetPage[Source]:
        _warn_ignored(
            "sources.list()", search=search, provider=provider, is_active=is_active,
        )
        params = self._clean_params({"page": page, "pageSize": page_size})
        return _fetch_offset_page(
            self._transport, "/api/sources", params, Source,
            data_key="sources",
        )

    def get(self, id: str) -> Source:
        resp = self._request("GET", f"/api/sources/{id}")
        return self._parse(Source, resp.get("source", resp))

    def create(self, params: CreateSourceParams | dict[str, Any]) -> SourceWithSecret:
        body = _to_body(params)
        resp = self._request("POST", "/api/sources", json=body)
        return self._parse(SourceWithSecret, resp.get("source", resp))

    def update(self, id: str, params: UpdateSourceParams | dict[str, Any]) -> None:
        """Update a source. Send an explicit null with ``UpdateSourceParams(clear=[...])``."""
        body = update_source_body(params)
        self._request("PATCH", f"/api/sources/{id}", json=body)

    def delete(self, id: str) -> None:
        self._request("DELETE", f"/api/sources/{id}")

    def rotate_secret(self, id: str) -> str:
        """Replace the signing secret with a new Hookbase-generated one and return it.

        Only for providers whose secret Hookbase generates (catalog secretSource "operator" or
        "none"). The API answers 400 (:class:`~hookbase.ValidationError`) when there is nothing
        it can generate: providers that verify without a secret (wise, aws-sns), public-key
        providers (discord, sendgrid...), vendor-issued secrets (stripe, standard-webhooks...)
        and secrets issued after registration (asana, notion). Rotate those at the vendor, then
        set the new value with :meth:`update`.
        """
        resp = self._request("POST", f"/api/sources/{id}/rotate-secret")
        return resp.get("signingSecret", "")

    def reveal_secret(self, id: str) -> str:
        """The source's signing secret in full. 404 when the source has none set."""
        resp = self._request("GET", f"/api/sources/{id}/reveal-secret")
        return resp.get("signingSecret", "")

    def verify_token(self, id: str) -> str:
        """The Meta verify token (whatsapp sources only; 400 for any other provider)."""
        resp = self._request("GET", f"/api/sources/{id}/verify-token")
        return resp.get("verifyToken", "")

    def rotate_verify_token(self, id: str) -> str:
        """Generate a new Meta verify token and return it. Update it in Meta's webhook setup."""
        resp = self._request("POST", f"/api/sources/{id}/rotate-verify-token")
        return resp.get("verifyToken", "")

    def get_pending_verification(self, id: str) -> PendingVerification:
        """The verification token a vendor (Notion) posted to the ingest URL, awaiting adoption.

        Raises :class:`~hookbase.NotFoundError` when no token is waiting (they expire after 24
        hours) as well as when the source does not exist.
        """
        resp = self._request("GET", f"/api/sources/{id}/pending-verification")
        return self._parse(PendingVerification, resp)

    def adopt_pending_verification(self, id: str) -> None:
        """Make the pending verification token this source's signing secret.

        Do this only after the vendor has accepted the token (Notion's Verify form): it arrived
        unauthenticated, and that acceptance is what proves it is genuine. 404 when none is
        waiting.
        """
        self._request("POST", f"/api/sources/{id}/pending-verification/adopt")

    def export(self, *, ids: builtins.list[str] | None = None) -> dict[str, Any]:
        params = {"ids": ",".join(ids)} if ids else None
        return self._request("GET", "/api/sources/export", params=params)

    def import_sources(
        self,
        sources: builtins.list[dict[str, Any]],
        *,
        conflict_strategy: str = "skip",
        validate_only: bool = False,
    ) -> ImportResult:
        resp = self._request("POST", "/api/sources/import", json={
            "sources": sources,
            "conflictStrategy": conflict_strategy,
            "validateOnly": validate_only,
        })
        return self._parse(ImportResult, resp)

    def bulk_delete(self, ids: builtins.list[str]) -> BulkDeleteResult:
        resp = self._request("DELETE", "/api/sources/bulk", json={"ids": ids})
        return self._parse(BulkDeleteResult, resp)


class AsyncSources(AsyncResource):
    async def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        provider: str | None = None,
        is_active: bool | None = None,
    ) -> AsyncOffsetPage[Source]:
        _warn_ignored(
            "sources.list()", search=search, provider=provider, is_active=is_active,
        )
        params = self._clean_params({"page": page, "pageSize": page_size})
        return await _async_fetch_offset_page(
            self._transport, "/api/sources", params, Source,
            data_key="sources",
        )

    async def get(self, id: str) -> Source:
        resp = await self._request("GET", f"/api/sources/{id}")
        return self._parse(Source, resp.get("source", resp))

    async def create(self, params: CreateSourceParams | dict[str, Any]) -> SourceWithSecret:
        body = _to_body(params)
        resp = await self._request("POST", "/api/sources", json=body)
        return self._parse(SourceWithSecret, resp.get("source", resp))

    async def update(self, id: str, params: UpdateSourceParams | dict[str, Any]) -> None:
        """Update a source. Send an explicit null with ``UpdateSourceParams(clear=[...])``."""
        body = update_source_body(params)
        await self._request("PATCH", f"/api/sources/{id}", json=body)

    async def delete(self, id: str) -> None:
        await self._request("DELETE", f"/api/sources/{id}")

    async def rotate_secret(self, id: str) -> str:
        """Replace the signing secret with a new Hookbase-generated one and return it.

        Only for providers whose secret Hookbase generates (catalog secretSource "operator" or
        "none"). The API answers 400 (:class:`~hookbase.ValidationError`) when there is nothing
        it can generate: providers that verify without a secret (wise, aws-sns), public-key
        providers (discord, sendgrid...), vendor-issued secrets (stripe, standard-webhooks...)
        and secrets issued after registration (asana, notion). Rotate those at the vendor, then
        set the new value with :meth:`update`.
        """
        resp = await self._request("POST", f"/api/sources/{id}/rotate-secret")
        return resp.get("signingSecret", "")

    async def reveal_secret(self, id: str) -> str:
        """The source's signing secret in full. 404 when the source has none set."""
        resp = await self._request("GET", f"/api/sources/{id}/reveal-secret")
        return resp.get("signingSecret", "")

    async def verify_token(self, id: str) -> str:
        """The Meta verify token (whatsapp sources only; 400 for any other provider)."""
        resp = await self._request("GET", f"/api/sources/{id}/verify-token")
        return resp.get("verifyToken", "")

    async def rotate_verify_token(self, id: str) -> str:
        """Generate a new Meta verify token and return it. Update it in Meta's webhook setup."""
        resp = await self._request("POST", f"/api/sources/{id}/rotate-verify-token")
        return resp.get("verifyToken", "")

    async def get_pending_verification(self, id: str) -> PendingVerification:
        """The verification token a vendor (Notion) posted to the ingest URL, awaiting adoption.

        Raises :class:`~hookbase.NotFoundError` when no token is waiting (they expire after 24
        hours) as well as when the source does not exist.
        """
        resp = await self._request("GET", f"/api/sources/{id}/pending-verification")
        return self._parse(PendingVerification, resp)

    async def adopt_pending_verification(self, id: str) -> None:
        """Make the pending verification token this source's signing secret.

        Do this only after the vendor has accepted the token (Notion's Verify form): it arrived
        unauthenticated, and that acceptance is what proves it is genuine. 404 when none is
        waiting.
        """
        await self._request("POST", f"/api/sources/{id}/pending-verification/adopt")

    async def export(self, *, ids: builtins.list[str] | None = None) -> dict[str, Any]:
        params = {"ids": ",".join(ids)} if ids else None
        return await self._request("GET", "/api/sources/export", params=params)

    async def import_sources(
        self,
        sources: builtins.list[dict[str, Any]],
        *,
        conflict_strategy: str = "skip",
        validate_only: bool = False,
    ) -> ImportResult:
        resp = await self._request("POST", "/api/sources/import", json={
            "sources": sources,
            "conflictStrategy": conflict_strategy,
            "validateOnly": validate_only,
        })
        return self._parse(ImportResult, resp)

    async def bulk_delete(self, ids: builtins.list[str]) -> BulkDeleteResult:
        resp = await self._request("DELETE", "/api/sources/bulk", json={"ids": ids})
        return self._parse(BulkDeleteResult, resp)
