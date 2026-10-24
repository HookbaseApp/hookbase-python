"""Request and response contracts of the resources that had no tests of their own.

Every response mocked here has the shape the route in api/src/routes/ sends, so a test failing
means the SDK no longer reads what the API actually returns.
"""

from __future__ import annotations

import warnings

import httpx
import pytest

from hookbase import AsyncHookbase
from hookbase.models import (
    CreateTunnelParams,
    UpdateTunnelParams,
)

from ..conftest import TEST_API_KEY, sent_body

# --------------------------------------------------------------------------- analytics

DASHBOARD = {
    "overview": {
        "total_events": 120, "successful_deliveries": 90, "failed_deliveries": 10,
        "avg_latency": 42.5, "source_count": 3, "destination_count": 2,
    },
    "timeline": [{"period": "2026-10-01T00:00:00Z", "events": 5, "successful": 4, "failed": 1}],
    "latency": {
        "percentiles": {"p50": 10, "p75": 20, "p90": 30, "p95": 40, "p99": 50},
        "min": 1, "max": 99, "avg": 12.5, "count": 100,
    },
    "latencyDistribution": [{"bucket": "<100ms", "count": 80}],
    "latencyTrends": [{"period": "2026-10-01", "p50": 10, "p95": 40, "p99": 50, "count": 7}],
    "errors": {
        "byDestination": [{
            "destination_id": "dst_1", "destination_name": "D", "error_count": 4,
            "avg_attempts": 2.5,
        }],
        "byStatusCode": [{"status_code": 503, "count": 4}],
        "trend": [{"date": "2026-10-01", "success": 9, "failed": 1}],
    },
    "retries": {
        "stats": {
            "total_deliveries": 100, "retried_count": 7, "retry_success": 5,
            "avg_attempts_to_success": 1.2, "max_attempts": 5,
        },
        "distribution": [{"category": "1 attempt", "count": 93}],
    },
    "sources": [{
        "id": "src_1", "name": "S", "slug": "s", "event_count": 120,
        "successful_deliveries": 90, "failed_deliveries": 10, "avg_latency": None,
    }],
    "destinations": [{
        "id": "dst_1", "name": "D", "url": "https://x.test", "total_deliveries": 100,
        "successful": 90, "failed": 10, "success_rate": 90, "avg_latency": 40,
        "min_latency": 1, "max_latency": 99,
    }],
    "routes": [{
        "id": "rte_1", "name": "R", "priority": 0, "source_name": "S", "source_slug": "s",
        "destination_name": "D", "destination_url": "https://x.test", "total_deliveries": 100,
        "successful": 90, "failed": 10, "success_rate": 90, "avg_latency": 40,
        "max_latency": 99, "min_latency": 1,
    }],
    "payloadSizes": {"distribution": [{"bucket": "<1KB", "count": 3}], "sample_size": 3,
                     "total_events": 3},
    "range": "7d",
    "interval": "day",
}


def test_analytics_dashboard_parses_the_real_shape(mock_api, client):
    route = mock_api.get("/api/analytics/dashboard").mock(
        return_value=httpx.Response(200, json=DASHBOARD)
    )
    data = client.analytics.dashboard(
        range="custom", start_date="2026-10-01", end_date="2026-10-07", tz="Europe/Berlin",
        source_id="src_1", destination_id="dst_1",
    )
    assert dict(route.calls.last.request.url.params) == {
        "range": "custom", "startDate": "2026-10-01", "endDate": "2026-10-07",
        "tz": "Europe/Berlin", "sourceId": "src_1", "destinationId": "dst_1",
    }
    assert data.overview.total_events == 120
    assert data.latency.percentiles.p99 == 50
    assert data.latency_distribution[0].bucket == "<100ms"
    assert data.latency_trends[0].p95 == 40
    assert data.errors.by_destination[0].error_count == 4
    assert data.errors.by_status_code[0].status_code == 503
    assert data.retries.stats.retried_count == 7
    assert data.sources[0].event_count == 120
    assert data.destinations[0].success_rate == 90
    assert data.routes[0].source_slug == "s"
    assert data.payload_sizes is not None and data.payload_sizes.sample_size == 3
    assert data.timeline[0]["events"] == 5
    assert (data.range, data.interval) == ("7d", "day")


def test_analytics_dashboard_legacy_properties_read_overview(mock_api, client):
    mock_api.get("/api/analytics/dashboard").mock(return_value=httpx.Response(200, json=DASHBOARD))
    data = client.analytics.dashboard()
    assert data.events_received == 120
    assert data.deliveries_completed == 90
    assert data.delivery_success_rate == pytest.approx(90.0)
    assert (data.active_sources, data.active_destinations, data.active_routes) == (3, 2, 1)


def test_analytics_dashboard_empty_org(mock_api, client):
    mock_api.get("/api/analytics/dashboard").mock(return_value=httpx.Response(200, json={
        "overview": {"total_events": 0, "successful_deliveries": 0, "failed_deliveries": 0,
                     "avg_latency": None, "source_count": 0, "destination_count": 0},
        "timeline": [], "payloadSizes": None, "range": "24h", "interval": "hour",
    }))
    data = client.analytics.dashboard(range="24h")
    assert data.delivery_success_rate == 0.0
    assert data.payload_sizes is None


def test_analytics_overview_warns_on_ignored_dates(mock_api, client):
    route = mock_api.get("/api/analytics/overview").mock(
        return_value=httpx.Response(200, json={"stats": {"total_events": 1}})
    )
    with pytest.warns(DeprecationWarning, match="start_date"):
        assert client.analytics.overview(start_date="2026-01-01") == {"stats": {"total_events": 1}}
    assert route.calls.last.request.url.params == httpx.QueryParams()


async def test_async_analytics(mock_api, async_client):
    mock_api.get("/api/analytics/dashboard").mock(return_value=httpx.Response(200, json=DASHBOARD))
    mock_api.get("/api/analytics/overview").mock(
        return_value=httpx.Response(200, json={"stats": {}})
    )
    data = await async_client.analytics.dashboard(tz="UTC")
    assert data.overview.failed_deliveries == 10
    assert await async_client.analytics.overview() == {"stats": {}}


# --------------------------------------------------------------------------- transforms

TRANSFORM = {"id": "trn_1", "name": "T", "slug": "t", "code": "$", "transformType": "jsonata"}


def test_transforms_crud(mock_api, client):
    mock_api.get("/api/transforms").mock(return_value=httpx.Response(200, json={
        "transforms": [TRANSFORM], "pagination": {"total": 1, "page": 1, "pageSize": 20},
    }))
    created = mock_api.post("/api/transforms").mock(return_value=httpx.Response(200, json={
        "transform": {**TRANSFORM, "transform_type": "jsonata", "input_format": "json"},
    }))
    patch = mock_api.patch("/api/transforms/trn_1").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    mock_api.get("/api/transforms/trn_1").mock(
        return_value=httpx.Response(200, json={"transform": {**TRANSFORM, "name": "T2"}})
    )
    delete = mock_api.delete("/api/transforms/trn_1").mock(
        return_value=httpx.Response(200, json={"success": True})
    )

    page = client.transforms.list()
    assert [t.id for t in page.data] == ["trn_1"]
    t = client.transforms.create({"name": "T", "code": "$", "transformType": "jsonata"})
    assert t.id == "trn_1"
    assert sent_body(created)["transformType"] == "jsonata"
    updated = client.transforms.update("trn_1", {"name": "T2"})
    assert updated.name == "T2"
    assert sent_body(patch) == {"name": "T2"}
    client.transforms.delete("trn_1")
    assert delete.called


def test_transforms_test_body(mock_api, client):
    route = mock_api.post("/api/transforms/test").mock(return_value=httpx.Response(200, json={
        "success": True, "output": {"a": 1},
    }))
    result = client.transforms.test(code="{ 'a': 1 }", payload={"x": 1}, transform_type="jsonata")
    assert result.success is True
    assert sent_body(route) == {
        "code": "{ 'a': 1 }", "payload": {"x": 1}, "transformType": "jsonata",
        "inputFormat": "json", "outputFormat": "json",
    }


async def test_async_transforms_update_reads_back(mock_api, async_client):
    mock_api.patch("/api/transforms/trn_1").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    mock_api.get("/api/transforms/trn_1").mock(
        return_value=httpx.Response(200, json={"transform": TRANSFORM})
    )
    assert (await async_client.transforms.update("trn_1", {"code": "$"})).id == "trn_1"


# --------------------------------------------------------------------------- organizations

ORG = {"id": "org_1", "name": "Acme", "slug": "acme", "plan": "pro"}


def test_organizations_list_reads_organizations_key(mock_api, client):
    mock_api.get("/api/organizations").mock(return_value=httpx.Response(200, json={
        "organizations": [{**ORG, "role": "owner", "memberCount": 3, "sourceCount": 2,
                           "createdAt": "2026-01-01"}],
    }))
    orgs = client.organizations.list()
    assert [(o.id, o.role, o.member_count) for o in orgs] == [("org_1", "owner", 3)]


def test_organizations_get_create_update(mock_api, client):
    mock_api.get("/api/organizations/org_1").mock(return_value=httpx.Response(200, json={
        "organization": {**ORG, "billingEmail": "b@acme.test", "userRole": "admin",
                         "dataRegion": "us", "dataRegionLabel": "United States"},
        "limits": {}, "usage": {},
    }))
    create = mock_api.post("/api/organizations").mock(return_value=httpx.Response(200, json={
        "organization": {"id": "org_2", "name": "New", "slug": "new", "plan": "free",
                         "dataRegion": "us"},
    }))
    patch = mock_api.patch("/api/organizations/org_1").mock(
        return_value=httpx.Response(200, json={"success": True})
    )

    org = client.organizations.get("org_1")
    assert (org.billing_email, org.user_role, org.data_region) == ("b@acme.test", "admin", "us")
    assert client.organizations.create("New", "new").id == "org_2"
    assert sent_body(create) == {"name": "New", "slug": "new"}
    assert client.organizations.update("org_1", {"name": "Acme"}).id == "org_1"
    assert sent_body(patch) == {"name": "Acme"}


def test_organization_members_and_invites(mock_api, client):
    mock_api.get("/api/organizations/org_1/members").mock(return_value=httpx.Response(200, json={
        "members": [{
            "id": "usr_1", "email": "a@acme.test", "displayName": "Ann", "avatarUrl": None,
            "role": "owner", "createdAt": "2026-01-01", "membershipId": "mem_1",
        }],
    }))
    role = mock_api.patch("/api/organizations/org_1/members/usr_1").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    remove = mock_api.delete("/api/organizations/org_1/members/usr_1").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    invite = mock_api.post("/api/organizations/org_1/invites").mock(
        return_value=httpx.Response(200, json={"invite": {
            "id": "inv_1", "email": "b@acme.test", "role": "admin",
            "expiresAt": "2026-11-01", "emailSent": True,
        }})
    )
    mock_api.get("/api/organizations/org_1/invites").mock(return_value=httpx.Response(200, json={
        "invites": [{"id": "inv_1", "email": "b@acme.test", "role": "admin",
                     "expiresAt": "2026-11-01", "createdAt": "2026-10-01",
                     "invitedByName": "Ann"}],
    }))
    cancel = mock_api.delete("/api/organizations/org_1/invites/inv_1").mock(
        return_value=httpx.Response(200, json={"success": True})
    )

    [member] = client.organizations.list_members("org_1")
    assert (member.user_id, member.name, member.membership_id) == ("usr_1", "Ann", "mem_1")
    client.organizations.update_member("org_1", member.user_id, "admin")
    assert sent_body(role) == {"role": "admin"}
    client.organizations.remove_member("org_1", "usr_1")
    assert remove.called
    inv = client.organizations.invite("org_1", "b@acme.test", role="admin")
    assert (inv.id, inv.email_sent, inv.organization_id) == ("inv_1", True, None)
    assert sent_body(invite) == {"email": "b@acme.test", "role": "admin"}
    [listed] = client.organizations.list_invites("org_1")
    assert listed.invited_by_name == "Ann"
    client.organizations.cancel_invite("org_1", "inv_1")
    assert cancel.called


async def test_async_organizations(mock_api, async_client):
    mock_api.get("/api/organizations").mock(
        return_value=httpx.Response(200, json={"organizations": [ORG]})
    )
    mock_api.patch("/api/organizations/org_1").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    mock_api.get("/api/organizations/org_1").mock(
        return_value=httpx.Response(200, json={"organization": ORG})
    )
    mock_api.get("/api/organizations/org_1/members").mock(
        return_value=httpx.Response(200, json={"members": [{"id": "usr_1", "role": "owner"}]})
    )
    assert [o.slug for o in await async_client.organizations.list()] == ["acme"]
    assert (await async_client.organizations.update("org_1", {"name": "A"})).slug == "acme"
    assert (await async_client.organizations.list_members("org_1"))[0].user_id == "usr_1"


# --------------------------------------------------------------------------- tunnels

TUNNEL_ROW = {
    "id": "tun_1", "organizationId": "org_1", "userId": None, "name": "dev", "subdomain": "abc",
    "localPort": None, "status": "disconnected", "createdAt": "2026-10-01",
    "lastConnectedAt": None, "lastRequestAt": None, "totalRequests": 0,
    "direction": "bidirectional", "allowedHosts": '["localhost","api.internal"]',
    "userName": None,
}


def test_tunnel_create_keeps_the_one_time_token_and_urls(mock_api, client):
    route = mock_api.post("/api/tunnels").mock(return_value=httpx.Response(201, json={
        "tunnel": {**TUNNEL_ROW, "auth_token": "tok_secret"},
        "tunnelUrl": "https://api.hookbase.app/t/abc",
        "wsUrl": "wss://api.hookbase.app/tunnels/abc/ws?tunnelId=tun_1&token=tok_secret",
        "message": "Tunnel created. Use the CLI to connect.",
    }))
    t = client.tunnels.create(CreateTunnelParams(
        name="dev", direction="bidirectional", allowed_hosts=["localhost", "api.internal"],
    ))
    assert sent_body(route) == {
        "name": "dev", "direction": "bidirectional", "allowedHosts": ["localhost", "api.internal"],
    }
    assert t.auth_token == "tok_secret"
    assert t.tunnel_url == "https://api.hookbase.app/t/abc"
    assert t.ws_url is not None and t.ws_url.startswith("wss://")
    assert t.allowed_hosts == ["localhost", "api.internal"]
    assert t.direction == "bidirectional"


def test_tunnel_list_get_update_delete_token_disconnect(mock_api, client):
    mock_api.get("/api/tunnels").mock(
        return_value=httpx.Response(200, json={"tunnels": [{**TUNNEL_ROW, "allowedHosts": None}]})
    )
    mock_api.get("/api/tunnels/tun_1").mock(
        return_value=httpx.Response(200, json={"tunnel": TUNNEL_ROW})
    )
    patch = mock_api.patch("/api/tunnels/tun_1").mock(
        return_value=httpx.Response(200, json={"tunnel": {**TUNNEL_ROW, "name": "dev2",
                                                          "allowedHosts": None}})
    )
    delete = mock_api.delete("/api/tunnels/tun_1").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    regen = mock_api.post("/api/tunnels/tun_1/regenerate-token").mock(
        return_value=httpx.Response(200, json={
            "auth_token": "tok_new", "authToken": "tok_new", "wsUrl": "wss://x/ws",
            "message": "Token regenerated.",
        })
    )
    disconnect = mock_api.post("/api/tunnels/tun_1/disconnect").mock(
        return_value=httpx.Response(200, json={"success": True, "message": "Tunnel disconnected"})
    )
    bulk = mock_api.delete("/api/tunnels/bulk").mock(
        return_value=httpx.Response(200, json={"success": True, "deleted": 2})
    )

    [listed] = client.tunnels.list()
    assert listed.allowed_hosts is None and listed.auth_token is None
    assert client.tunnels.get("tun_1").total_requests == 0
    updated = client.tunnels.update("tun_1", UpdateTunnelParams(name="dev2", allowed_hosts=[]))
    assert updated.name == "dev2"
    assert sent_body(patch) == {"name": "dev2", "allowedHosts": []}
    token = client.tunnels.regenerate_token("tun_1")
    assert (token.auth_token, token.ws_url) == ("tok_new", "wss://x/ws")
    assert regen.called
    client.tunnels.disconnect("tun_1")
    assert disconnect.called
    client.tunnels.delete("tun_1")
    assert delete.called
    assert client.tunnels.bulk_delete(["tun_1", "tun_2"]).deleted == 2
    assert sent_body(bulk) == {"ids": ["tun_1", "tun_2"]}


async def test_async_tunnels(mock_api, async_client):
    mock_api.post("/api/tunnels").mock(return_value=httpx.Response(201, json={
        "tunnel": {**TUNNEL_ROW, "auth_token": "t"}, "tunnelUrl": "https://u", "wsUrl": "wss://w",
    }))
    mock_api.patch("/api/tunnels/tun_1").mock(
        return_value=httpx.Response(200, json={"tunnel": TUNNEL_ROW})
    )
    mock_api.post("/api/tunnels/tun_1/regenerate-token").mock(
        return_value=httpx.Response(200, json={"authToken": "n", "wsUrl": "wss://n"})
    )
    mock_api.post("/api/tunnels/tun_1/disconnect").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    mock_api.delete("/api/tunnels/tun_1").mock(return_value=httpx.Response(200, json={}))
    t = await async_client.tunnels.create({"name": "dev"})
    assert (t.auth_token, t.tunnel_url, t.ws_url) == ("t", "https://u", "wss://w")
    assert (await async_client.tunnels.update("tun_1", {"name": "x"})).id == "tun_1"
    assert (await async_client.tunnels.regenerate_token("tun_1")).auth_token == "n"
    await async_client.tunnels.disconnect("tun_1")
    await async_client.tunnels.delete("tun_1")


# --------------------------------------------------------------------------- ignored list filters


@pytest.mark.parametrize("call,path,match", [
    (lambda c: c.sources.list(search="x", provider="stripe"), "/api/sources", "search, provider"),
    (lambda c: c.destinations.list(is_active=True), "/api/destinations", "is_active"),
    (lambda c: c.routes.list(source_id="src_1"), "/api/routes", "source_id"),
])
def test_list_filters_the_api_ignores_warn_and_are_not_sent(mock_api, client, call, path, match):
    key = path.rsplit("/", 1)[1]
    route = mock_api.get(path).mock(return_value=httpx.Response(200, json={
        key: [], "pagination": {"total": 0, "page": 1, "pageSize": 20},
    }))
    with pytest.warns(DeprecationWarning, match=match):
        call(client)
    assert route.calls.last.request.url.params == httpx.QueryParams()


def test_list_without_filters_does_not_warn(mock_api, client):
    mock_api.get("/api/sources").mock(return_value=httpx.Response(200, json={
        "sources": [], "pagination": {"total": 0, "page": 1, "pageSize": 20},
    }))
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        client.sources.list(page=1)


async def test_async_list_filter_warning(mock_api, async_client):
    mock_api.get("/api/routes").mock(return_value=httpx.Response(200, json={
        "routes": [], "pagination": {"total": 0, "page": 1, "pageSize": 20},
    }))
    with pytest.warns(DeprecationWarning, match="destination_id"):
        await async_client.routes.list(destination_id="dst_1")


# --------------------------------------------------------------------------- filters

FILTER = {
    "id": "flt_1", "name": "F", "slug": "f", "logic": "AND",
    "conditions": '[{"field":"type","operator":"equals","value":"x"}]',
}


def test_filters_crud_uppercases_logic(mock_api, client):
    mock_api.get("/api/filters").mock(return_value=httpx.Response(200, json={
        "filters": [FILTER], "pagination": {"total": 1, "page": 1, "pageSize": 20},
    }))
    mock_api.get("/api/filters/flt_1").mock(
        return_value=httpx.Response(200, json={"filter": FILTER})
    )
    create = mock_api.post("/api/filters").mock(
        return_value=httpx.Response(200, json={"filter": FILTER})
    )
    patch = mock_api.patch("/api/filters/flt_1").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    delete = mock_api.delete("/api/filters/flt_1").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    conds = [{"field": "type", "operator": "equals", "value": "x"}]

    [listed] = client.filters.list().data
    assert listed.conditions[0].field == "type"
    assert client.filters.get("flt_1").logic == "AND"
    client.filters.create({"name": "F", "conditions": conds, "logic": "or"})
    assert sent_body(create)["logic"] == "OR"
    client.filters.update("flt_1", {"logic": "and"})
    assert sent_body(patch) == {"logic": "AND"}
    client.filters.delete("flt_1")
    assert delete.called


def test_filters_test_sends_uppercase_logic(mock_api, client):
    route = mock_api.post("/api/filters/test").mock(return_value=httpx.Response(200, json={
        "matches": True, "results": [{"field": "type", "matched": True}], "logic": "OR",
    }))
    result = client.filters.test(
        [{"field": "type", "operator": "equals", "value": "x"}], {"type": "x"}, logic="or",
    )
    assert result.matches is True
    assert sent_body(route) == {
        "conditions": [{"field": "type", "operator": "equals", "value": "x"}],
        "payload": {"type": "x"}, "logic": "OR",
    }


async def test_async_filters(mock_api, async_client):
    create = mock_api.post("/api/filters").mock(
        return_value=httpx.Response(200, json={"filter": FILTER})
    )
    test = mock_api.post("/api/filters/test").mock(
        return_value=httpx.Response(200, json={"matches": False, "results": [], "logic": "AND"})
    )
    await async_client.filters.create({"name": "F", "conditions": [], "logic": "and"})
    assert sent_body(create)["logic"] == "AND"
    await async_client.filters.test([], {}, logic="and")
    assert sent_body(test)["logic"] == "AND"


# --------------------------------------------------------------------------- schemas


def test_schemas_list_is_one_unpaginated_page(mock_api, client):
    schemas = [{"id": f"sch_{i}", "name": f"S{i}", "slug": f"s{i}"} for i in range(25)]
    route = mock_api.get("/api/schemas").mock(
        return_value=httpx.Response(200, json={"schemas": schemas})
    )
    page = client.schemas.list()
    assert page.total == 25
    assert not page.has_more
    assert len(list(page.auto_paging_iter())) == 25
    assert route.call_count == 1


def test_schemas_crud_and_validate(mock_api, client):
    mock_api.get("/api/schemas/sch_1").mock(return_value=httpx.Response(200, json={
        "schema": {"id": "sch_1", "name": "S", "slug": "s", "jsonSchema": {"type": "object"},
                   "routes": [{"id": "rte_1", "name": "R"}]},
    }))
    create = mock_api.post("/api/schemas").mock(return_value=httpx.Response(201, json={
        "schema": {"id": "sch_1", "name": "S", "slug": "s", "json_schema": {"type": "object"}},
    }))
    put = mock_api.put("/api/schemas/sch_1").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    mock_api.delete("/api/schemas/sch_1").mock(return_value=httpx.Response(200, json={}))
    validate = mock_api.post("/api/schemas/sch_1/validate").mock(
        return_value=httpx.Response(200, json={
            "valid": False, "errors": [{"path": "email", "message": "Required field missing"}],
        })
    )

    assert client.schemas.get("sch_1").routes[0].id == "rte_1"  # type: ignore[index]
    created = client.schemas.create({"name": "S", "jsonSchema": {"type": "object"}})
    assert created.json_schema == {"type": "object"}
    assert sent_body(create) == {"name": "S", "jsonSchema": {"type": "object"}}
    client.schemas.update("sch_1", {"name": "S2"})
    assert sent_body(put) == {"name": "S2"}
    client.schemas.delete("sch_1")
    result = client.schemas.validate("sch_1", {"name": "x"})
    assert result.valid is False
    assert (result.errors[0].path, result.errors[0].message) == ("email", "Required field missing")
    assert sent_body(validate) == {"payload": {"name": "x"}}


async def test_async_schemas(mock_api, async_client):
    mock_api.get("/api/schemas").mock(return_value=httpx.Response(200, json={"schemas": []}))
    mock_api.post("/api/schemas/sch_1/validate").mock(
        return_value=httpx.Response(200, json={"valid": True, "errors": []})
    )
    assert (await async_client.schemas.list()).total == 0
    assert (await async_client.schemas.validate("sch_1", {})).valid is True


# --------------------------------------------------------------------------- cron jobs


def test_cron_trigger_failure_carries_error(mock_api, client):
    mock_api.post("/api/cron/crn_1/trigger").mock(return_value=httpx.Response(200, json={
        "execution": {"id": "exe_1", "status": "failed", "error": "DNS lookup failed",
                      "latencyMs": 12},
    }))
    ex = client.cron_jobs.trigger("crn_1")
    assert (ex.status, ex.error, ex.response_status) == ("failed", "DNS lookup failed", None)


def test_cron_list_executions(mock_api, client):
    route = mock_api.get("/api/cron/crn_1/executions").mock(
        return_value=httpx.Response(200, json={"executions": [
            {"id": "exe_1", "organizationId": "org_1", "cronJobId": "crn_1", "status": "running",
             "responseStatus": None, "responseBody": None, "responseHeaders": None,
             "errorMessage": None, "latencyMs": None, "startedAt": "2026-10-01T00:00:00Z",
             "completedAt": None},
            {"id": "exe_0", "cronJobId": "crn_1", "status": "failed", "errorMessage": "timeout",
             "latencyMs": 30000, "startedAt": "2026-09-30T00:00:00Z"},
        ]})
    )
    running, failed = client.cron_jobs.list_executions("crn_1", limit=5)
    assert dict(route.calls.last.request.url.params) == {"limit": "5"}
    assert (running.status, running.latency_ms) == ("running", None)
    assert failed.error_message == "timeout"


def test_cron_list_is_unpaginated(mock_api, client):
    mock_api.get("/api/cron").mock(return_value=httpx.Response(200, json={"cronJobs": [
        {"id": "crn_1", "name": "C", "url": "https://x.test", "cronExpression": "* * * * *"},
    ]}))
    page = client.cron_jobs.list()
    assert page.total == 1 and not page.has_more


def test_cron_groups(mock_api, client):
    mock_api.get("/api/cron-groups").mock(return_value=httpx.Response(200, json={
        "groups": [{"id": "grp_1", "name": "G", "slug": "g"}],
    }))
    create = mock_api.post("/api/cron-groups").mock(return_value=httpx.Response(201, json={
        "group": {"id": "grp_2", "name": "H", "slug": "h"},
    }))
    assert client.cron_jobs.list_groups()[0].id == "grp_1"
    assert client.cron_jobs.create_group({"name": "H"}).id == "grp_2"
    assert sent_body(create) == {"name": "H"}


async def test_async_cron(mock_api, async_client):
    mock_api.get("/api/cron/crn_1/executions").mock(
        return_value=httpx.Response(200, json={"executions": []})
    )
    mock_api.post("/api/cron/crn_1/trigger").mock(return_value=httpx.Response(200, json={
        "execution": {"id": "e", "status": "success", "responseStatus": 200, "latencyMs": 3},
    }))
    mock_api.get("/api/cron-groups").mock(return_value=httpx.Response(200, json={"groups": []}))
    assert await async_client.cron_jobs.list_executions("crn_1") == []
    assert (await async_client.cron_jobs.trigger("crn_1")).response_status == 200
    assert await async_client.cron_jobs.list_groups() == []


# --------------------------------------------------------------------------- routes


def test_route_expected_response_is_any_json(mock_api, client):
    mock_api.get("/api/routes/rte_1").mock(return_value=httpx.Response(200, json={"route": {
        "id": "rte_1", "name": "R", "sourceId": "src_1", "destinationId": "dst_1",
        "expectedResponse": {"statusCodes": [200, 202], "bodyContains": "ok"},
    }}))
    route = client.routes.get("rte_1")
    assert route.expected_response == {"statusCodes": [200, 202], "bodyContains": "ok"}


# --------------------------------------------------------------------------- portal tokens


def test_portal_tokens(mock_api, client):
    create = mock_api.post("/api/portal/webhook-applications/app_1/tokens").mock(
        return_value=httpx.Response(201, json={"data": {
            "id": "ptk_1", "token": "whpt_secret", "tokenPrefix": "whpt_sec", "name": "N",
            "scopes": ["read"], "expiresAt": "2026-11-01", "createdAt": "2026-10-01",
            "applicationId": "app_1", "apiKeyId": "key_1",
        }})
    )
    mock_api.get("/api/portal/webhook-applications/app_1/tokens").mock(
        return_value=httpx.Response(200, json={"data": [{
            "id": "ptk_1", "name": "N", "tokenPrefix": "whpt_sec", "scopes": ["read"],
            "expiresAt": "2026-11-01", "lastUsedAt": "2026-10-02", "useCount": 4,
            "createdAt": "2026-10-01", "revokedAt": None, "isExpired": False,
            "isRevoked": False, "apiKeyId": "key_1", "revokedByApiKeyId": None,
        }]})
    )
    revoke = mock_api.delete("/api/portal/tokens/ptk_1").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    tok = client.outbound.portal_tokens.create("app_1", {"name": "N", "scopes": ["read"]})
    assert (tok.token, tok.api_key_id) == ("whpt_secret", "key_1")
    assert sent_body(create) == {"name": "N", "scopes": ["read"]}
    [listed] = client.outbound.portal_tokens.list("app_1")
    assert (listed.use_count, listed.last_used_at, listed.is_revoked) == (4, "2026-10-02", False)
    client.outbound.portal_tokens.revoke("ptk_1")
    assert revoke.called


def test_portal_token_create_without_params_sends_empty_object(mock_api, client):
    route = mock_api.post("/api/portal/webhook-applications/app_1/tokens").mock(
        return_value=httpx.Response(201, json={"data": {"id": "ptk_1"}})
    )
    client.outbound.portal_tokens.create("app_1")
    assert sent_body(route) == {}


async def test_async_portal_tokens(mock_api, async_client):
    mock_api.get("/api/portal/webhook-applications/app_1/tokens").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    mock_api.delete("/api/portal/tokens/ptk_1").mock(return_value=httpx.Response(200, json={}))
    assert await async_client.outbound.portal_tokens.list("app_1") == []
    await async_client.outbound.portal_tokens.revoke("ptk_1")


# --------------------------------------------------------------------------- api keys


def test_api_keys(mock_api, client):
    mock_api.get("/api/api-keys").mock(return_value=httpx.Response(200, json={"apiKeys": [{
        "id": "key_1", "name": "CI", "keyPrefix": "whr_abc", "scopes": '["read","write"]',
        "lastUsedAt": None, "expiresAt": None, "createdAt": "2026-10-01",
    }]}))
    create = mock_api.post("/api/api-keys").mock(return_value=httpx.Response(200, json={
        "apiKey": {"id": "key_2", "name": "CI2", "key": "whr_full", "keyPrefix": "whr_ful",
                   "scopes": ["read"], "expiresAt": None},
    }))
    delete = mock_api.delete("/api/api-keys/key_1").mock(
        return_value=httpx.Response(200, json={"success": True})
    )
    [key] = client.api_keys.list()
    assert key.scopes == ["read", "write"]
    new = client.api_keys.create({"name": "CI2", "scopes": ["read"]})
    assert (new.key, new.key_prefix) == ("whr_full", "whr_ful")
    assert sent_body(create) == {"name": "CI2", "scopes": ["read"]}
    client.api_keys.delete("key_1")
    assert delete.called


async def test_async_api_keys(mock_api):
    mock_api.get("/api/api-keys").mock(return_value=httpx.Response(200, json={"apiKeys": []}))
    async with AsyncHookbase(api_key=TEST_API_KEY) as c:
        assert await c.api_keys.list() == []
