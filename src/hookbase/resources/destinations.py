from __future__ import annotations

import builtins
from typing import Any

from .._constants import NOT_GIVEN, NotGiven
from .._pagination import (
    AsyncOffsetPage,
    SyncOffsetPage,
    _async_fetch_offset_page,
    _fetch_offset_page,
)
from ..models.common import BulkDeleteResult, ImportResult
from ..models.destinations import (
    CreateDestinationParams,
    Destination,
    DestinationSecret,
    DestinationWithSecret,
    TestResult,
    UpdateDestinationParams,
    create_destination_body,
    update_destination_body,
)
from ._base import AsyncResource, SyncResource, _warn_ignored


def _rotate_body(grace_period_seconds: int | None) -> dict[str, Any] | None:
    """`rotateSigningSecretSchema`: an optional gracePeriodSeconds, 0-86400 (API default 3600)."""
    if grace_period_seconds is None:
        return None
    return {"gracePeriodSeconds": grace_period_seconds}


def _test_body(payload: dict[str, Any] | NotGiven) -> dict[str, Any] | None:
    """Only a bridge reads a body here: `payload` is the sample its dry run resolves."""
    if isinstance(payload, NotGiven):
        return None
    return {"payload": payload}


class Destinations(SyncResource):
    def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> SyncOffsetPage[Destination]:
        _warn_ignored("destinations.list()", search=search, is_active=is_active)
        params = self._clean_params({"page": page, "pageSize": page_size})
        return _fetch_offset_page(
            self._transport, "/api/destinations", params, Destination, data_key="destinations"
        )

    def get(self, id: str) -> Destination:
        resp = self._request("GET", f"/api/destinations/{id}")
        return self._parse(Destination, resp.get("destination", resp))

    def create(
        self, params: CreateDestinationParams | dict[str, Any],
    ) -> DestinationWithSecret:
        """Create a destination. An HTTP destination's `signing_secret` is in this response
        only; afterwards it takes `reveal_secret`."""
        body = create_destination_body(params)
        resp = self._request("POST", "/api/destinations", json=body)
        return self._parse(DestinationWithSecret, resp.get("destination", resp))

    def update(self, id: str, params: UpdateDestinationParams | dict[str, Any]) -> None:
        body = update_destination_body(params)
        self._request("PATCH", f"/api/destinations/{id}", json=body)

    def delete(self, id: str) -> None:
        self._request("DELETE", f"/api/destinations/{id}")

    def reveal_secret(self, id: str) -> DestinationSecret:
        """Return an HTTP destination's signing secret. Needs the `write` scope; a non-HTTP
        destination is a 400."""
        resp = self._request("GET", f"/api/destinations/{id}/reveal-secret")
        return self._parse(DestinationSecret, resp)

    def rotate_secret(
        self, id: str, *, grace_period_seconds: int | None = None,
    ) -> DestinationSecret:
        """Issue a new signing secret for an HTTP destination.

        For `grace_period_seconds` (0-86400; the API defaults to 3600) deliveries are signed with
        both the old and the new secret, so receivers can switch without rejecting any. 0 drops
        the old secret at once.
        """
        resp = self._request(
            "POST", f"/api/destinations/{id}/rotate-secret",
            json=_rotate_body(grace_period_seconds),
        )
        return self._parse(DestinationSecret, resp)

    def test(
        self, id: str, *, payload: dict[str, Any] | NotGiven = NOT_GIVEN,
    ) -> TestResult:
        """Send a test delivery to the destination.

        For a bridge destination this is a dry run that publishes nothing: it resolves the event
        type from `payload` (a JSON object; the API's test payload when omitted) and reports it
        in `event_type`, `event_type_exists` and `matching_endpoints`. Other types ignore
        `payload`.
        """
        resp = self._request("POST", f"/api/destinations/{id}/test", json=_test_body(payload))
        return self._parse(TestResult, resp)

    def export(self, *, ids: builtins.list[str] | None = None) -> dict[str, Any]:
        params = {"ids": ",".join(ids)} if ids else None
        return self._request("GET", "/api/destinations/export", params=params)

    def import_destinations(
        self,
        destinations: builtins.list[dict[str, Any]],
        *,
        conflict_strategy: str = "skip",
        validate_only: bool = False,
    ) -> ImportResult:
        resp = self._request("POST", "/api/destinations/import", json={
            "destinations": destinations,
            "conflictStrategy": conflict_strategy,
            "validateOnly": validate_only,
        })
        return self._parse(ImportResult, resp)

    def bulk_delete(self, ids: builtins.list[str]) -> BulkDeleteResult:
        resp = self._request("DELETE", "/api/destinations/bulk", json={"ids": ids})
        return self._parse(BulkDeleteResult, resp)


class AsyncDestinations(AsyncResource):
    async def list(
        self,
        *,
        page: int | None = None,
        page_size: int | None = None,
        search: str | None = None,
        is_active: bool | None = None,
    ) -> AsyncOffsetPage[Destination]:
        _warn_ignored("destinations.list()", search=search, is_active=is_active)
        params = self._clean_params({"page": page, "pageSize": page_size})
        return await _async_fetch_offset_page(
            self._transport, "/api/destinations", params, Destination, data_key="destinations"
        )

    async def get(self, id: str) -> Destination:
        resp = await self._request("GET", f"/api/destinations/{id}")
        return self._parse(Destination, resp.get("destination", resp))

    async def create(
        self, params: CreateDestinationParams | dict[str, Any],
    ) -> DestinationWithSecret:
        """Create a destination. See `Destinations.create`."""
        body = create_destination_body(params)
        resp = await self._request("POST", "/api/destinations", json=body)
        return self._parse(DestinationWithSecret, resp.get("destination", resp))

    async def update(self, id: str, params: UpdateDestinationParams | dict[str, Any]) -> None:
        body = update_destination_body(params)
        await self._request("PATCH", f"/api/destinations/{id}", json=body)

    async def delete(self, id: str) -> None:
        await self._request("DELETE", f"/api/destinations/{id}")

    async def reveal_secret(self, id: str) -> DestinationSecret:
        """Return an HTTP destination's signing secret. See `Destinations.reveal_secret`."""
        resp = await self._request("GET", f"/api/destinations/{id}/reveal-secret")
        return self._parse(DestinationSecret, resp)

    async def rotate_secret(
        self, id: str, *, grace_period_seconds: int | None = None,
    ) -> DestinationSecret:
        """Issue a new signing secret. See `Destinations.rotate_secret`."""
        resp = await self._request(
            "POST", f"/api/destinations/{id}/rotate-secret",
            json=_rotate_body(grace_period_seconds),
        )
        return self._parse(DestinationSecret, resp)

    async def test(
        self, id: str, *, payload: dict[str, Any] | NotGiven = NOT_GIVEN,
    ) -> TestResult:
        """Send a test delivery, or dry-run a bridge. See `Destinations.test`."""
        resp = await self._request(
            "POST", f"/api/destinations/{id}/test", json=_test_body(payload),
        )
        return self._parse(TestResult, resp)

    async def export(self, *, ids: builtins.list[str] | None = None) -> dict[str, Any]:
        params = {"ids": ",".join(ids)} if ids else None
        return await self._request("GET", "/api/destinations/export", params=params)

    async def import_destinations(
        self,
        destinations: builtins.list[dict[str, Any]],
        *,
        conflict_strategy: str = "skip",
        validate_only: bool = False,
    ) -> ImportResult:
        resp = await self._request("POST", "/api/destinations/import", json={
            "destinations": destinations,
            "conflictStrategy": conflict_strategy,
            "validateOnly": validate_only,
        })
        return self._parse(ImportResult, resp)

    async def bulk_delete(self, ids: builtins.list[str]) -> BulkDeleteResult:
        resp = await self._request("DELETE", "/api/destinations/bulk", json={"ids": ids})
        return self._parse(BulkDeleteResult, resp)
