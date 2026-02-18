from __future__ import annotations

import pytest

from hookbase import AsyncHookbase, Hookbase


def test_requires_api_key():
    with pytest.raises(ValueError, match="api_key is required"):
        Hookbase(api_key="")


def test_async_requires_api_key():
    with pytest.raises(ValueError, match="api_key is required"):
        AsyncHookbase(api_key="")


def test_has_inbound_resources():
    client = Hookbase(api_key="whr_test")
    for attr in ("sources", "destinations", "routes", "events",
                 "deliveries", "transforms", "filters", "schemas"):
        assert hasattr(client, attr), f"Missing inbound resource: {attr}"
    client.close()


def test_has_outbound_resources():
    client = Hookbase(api_key="whr_test")
    outbound = client.outbound
    for attr in ("applications", "endpoints", "event_types", "subscriptions",
                 "messages", "message_log", "dlq"):
        assert hasattr(outbound, attr), f"Missing outbound resource: {attr}"
    client.close()


def test_has_admin_resources():
    client = Hookbase(api_key="whr_test")
    for attr in ("organizations", "api_keys", "analytics", "cron_jobs", "tunnels"):
        assert hasattr(client, attr), f"Missing admin resource: {attr}"
    client.close()


def test_context_manager():
    with Hookbase(api_key="whr_test") as client:
        assert client.sources is not None


@pytest.mark.asyncio
async def test_async_context_manager():
    async with AsyncHookbase(api_key="whr_test") as client:
        assert client.sources is not None


def test_async_has_all_resources():
    client = AsyncHookbase(api_key="whr_test")
    # Inbound
    for attr in ("sources", "destinations", "routes", "events",
                 "deliveries", "transforms", "filters", "schemas"):
        assert hasattr(client, attr)
    # Outbound
    for attr in ("applications", "endpoints", "event_types", "subscriptions",
                 "messages", "message_log", "dlq"):
        assert hasattr(client.outbound, attr)
    # Admin
    for attr in ("organizations", "api_keys", "analytics", "cron_jobs", "tunnels"):
        assert hasattr(client, attr)
