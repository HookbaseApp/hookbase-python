from __future__ import annotations

from typing import Any

import httpx

from ._client import AsyncTransport, SyncTransport
from ._constants import DEFAULT_BASE_URL, DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT
from .resources import (
    DLQ,
    Analytics,
    ApiKeys,
    Applications,
    AsyncAnalytics,
    AsyncApiKeys,
    AsyncApplications,
    AsyncCronJobs,
    AsyncDeliveries,
    AsyncDestinations,
    AsyncDLQ,
    AsyncEndpoints,
    AsyncEvents,
    AsyncEventTypes,
    AsyncFilters,
    AsyncMessageLog,
    AsyncMessages,
    AsyncOrganizations,
    AsyncPortalTokens,
    AsyncRoutes,
    AsyncSchemas,
    AsyncSources,
    AsyncSubscriptions,
    AsyncTransforms,
    AsyncTunnels,
    CronJobs,
    Deliveries,
    Destinations,
    Endpoints,
    Events,
    EventTypes,
    Filters,
    MessageLog,
    Messages,
    Organizations,
    PortalTokens,
    Routes,
    Schemas,
    Sources,
    Subscriptions,
    Transforms,
    Tunnels,
)


class _OutboundNamespace:
    """Namespace for outbound webhook resources."""

    __slots__ = (
        "applications", "endpoints", "event_types", "subscriptions",
        "messages", "message_log", "portal_tokens", "dlq",
    )

    def __init__(self, transport: SyncTransport) -> None:
        self.applications = Applications(transport)
        self.endpoints = Endpoints(transport)
        self.event_types = EventTypes(transport)
        self.subscriptions = Subscriptions(transport)
        self.messages = Messages(transport)
        self.message_log = MessageLog(transport)
        self.portal_tokens = PortalTokens(transport)
        self.dlq = DLQ(transport)


class _AsyncOutboundNamespace:
    """Namespace for outbound webhook resources (async)."""

    __slots__ = (
        "applications", "endpoints", "event_types", "subscriptions",
        "messages", "message_log", "portal_tokens", "dlq",
    )

    def __init__(self, transport: AsyncTransport) -> None:
        self.applications = AsyncApplications(transport)
        self.endpoints = AsyncEndpoints(transport)
        self.event_types = AsyncEventTypes(transport)
        self.subscriptions = AsyncSubscriptions(transport)
        self.messages = AsyncMessages(transport)
        self.message_log = AsyncMessageLog(transport)
        self.portal_tokens = AsyncPortalTokens(transport)
        self.dlq = AsyncDLQ(transport)


class Hookbase:
    """Synchronous Hookbase API client.

    Args:
        api_key: Your Hookbase API key (e.g. ``whr_...``).
        base_url: API base URL (default: ``https://api.hookbase.app``).
        timeout: Request timeout in seconds (default: 30).
        max_retries: Max retry attempts for transient failures (default: 3).
        debug: Enable debug logging of requests.
        http_client: Optional custom ``httpx.Client`` instance.

    Example::

        from hookbase import Hookbase

        client = Hookbase(api_key="whr_...")
        sources = client.sources.list()
    """

    # Inbound
    sources: Sources
    destinations: Destinations
    routes: Routes
    events: Events
    deliveries: Deliveries
    transforms: Transforms
    filters: Filters
    schemas: Schemas

    # Outbound
    outbound: _OutboundNamespace

    # Admin
    organizations: Organizations
    api_keys: ApiKeys
    analytics: Analytics
    cron_jobs: CronJobs
    tunnels: Tunnels

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        debug: bool = False,
        http_client: httpx.Client | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")

        self._transport = SyncTransport(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            debug=debug,
            http_client=http_client,
        )

        # Inbound resources
        self.sources = Sources(self._transport)
        self.destinations = Destinations(self._transport)
        self.routes = Routes(self._transport)
        self.events = Events(self._transport)
        self.deliveries = Deliveries(self._transport)
        self.transforms = Transforms(self._transport)
        self.filters = Filters(self._transport)
        self.schemas = Schemas(self._transport)

        # Outbound namespace
        self.outbound = _OutboundNamespace(self._transport)

        # Admin resources
        self.organizations = Organizations(self._transport)
        self.api_keys = ApiKeys(self._transport)
        self.analytics = Analytics(self._transport)
        self.cron_jobs = CronJobs(self._transport)
        self.tunnels = Tunnels(self._transport)

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._transport.close()

    def __enter__(self) -> Hookbase:
        return self

    def __exit__(self, *args: Any) -> None:
        self.close()


class AsyncHookbase:
    """Asynchronous Hookbase API client.

    Args:
        api_key: Your Hookbase API key (e.g. ``whr_...``).
        base_url: API base URL (default: ``https://api.hookbase.app``).
        timeout: Request timeout in seconds (default: 30).
        max_retries: Max retry attempts for transient failures (default: 3).
        debug: Enable debug logging of requests.
        http_client: Optional custom ``httpx.AsyncClient`` instance.

    Example::

        from hookbase import AsyncHookbase

        async with AsyncHookbase(api_key="whr_...") as client:
            sources = await client.sources.list()
    """

    # Inbound
    sources: AsyncSources
    destinations: AsyncDestinations
    routes: AsyncRoutes
    events: AsyncEvents
    deliveries: AsyncDeliveries
    transforms: AsyncTransforms
    filters: AsyncFilters
    schemas: AsyncSchemas

    # Outbound
    outbound: _AsyncOutboundNamespace

    # Admin
    organizations: AsyncOrganizations
    api_keys: AsyncApiKeys
    analytics: AsyncAnalytics
    cron_jobs: AsyncCronJobs
    tunnels: AsyncTunnels

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        debug: bool = False,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")

        self._transport = AsyncTransport(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
            debug=debug,
            http_client=http_client,
        )

        # Inbound resources
        self.sources = AsyncSources(self._transport)
        self.destinations = AsyncDestinations(self._transport)
        self.routes = AsyncRoutes(self._transport)
        self.events = AsyncEvents(self._transport)
        self.deliveries = AsyncDeliveries(self._transport)
        self.transforms = AsyncTransforms(self._transport)
        self.filters = AsyncFilters(self._transport)
        self.schemas = AsyncSchemas(self._transport)

        # Outbound namespace
        self.outbound = _AsyncOutboundNamespace(self._transport)

        # Admin resources
        self.organizations = AsyncOrganizations(self._transport)
        self.api_keys = AsyncApiKeys(self._transport)
        self.analytics = AsyncAnalytics(self._transport)
        self.cron_jobs = AsyncCronJobs(self._transport)
        self.tunnels = AsyncTunnels(self._transport)

    async def close(self) -> None:
        """Close the underlying async HTTP client."""
        await self._transport.close()

    async def __aenter__(self) -> AsyncHookbase:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
