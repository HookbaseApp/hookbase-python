"""Every resource method, run through both Hookbase and AsyncHookbase against the same mock.

Each case is (call, HTTP method, path, response JSON, expected request body or None, check).
The sync and async variants must put the same request on the wire and parse the same result,
which is what catches an async method that drifted from its sync twin.
"""

from __future__ import annotations

import inspect
import json
from typing import Any, Callable

import httpx
import pytest

from hookbase import AsyncHookbase, Hookbase

from ..conftest import TEST_API_KEY

ROUTE = {"id": "rte_1", "name": "R", "sourceId": "src_1", "destinationId": "dst_1"}
DEST = {"id": "dst_1", "name": "D", "slug": "d", "url": "https://x.test"}
ET = {"id": "et_1", "organizationId": "org_1", "name": "order.created"}
SUB = {"id": "sub_1", "endpointId": "ep_1", "eventTypeId": "et_1"}
EP = {"id": "ep_1", "applicationId": "app_1", "url": "https://x.test"}
APP = {"id": "app_1", "name": "A", "organizationId": "org_1", "externalId": "cust_1"}
DELIVERY = {"id": "dlv_1", "eventId": "evt_1", "routeId": "rte_1", "destinationId": "dst_1",
            "organizationId": "org_1", "status": "success"}
EVENT = {"id": "evt_1", "sourceId": "src_1", "organizationId": "org_1"}
MSG = {"id": "msg_1"}
CURSOR = {"hasMore": False, "nextCursor": None}
OFFSET = {"total": 1, "page": 1, "pageSize": 20}

Case = tuple[Callable[[Any], Any], str, str, Any, Any, Callable[[Any], bool]]

CASES: dict[str, Case] = {
    # routes
    "routes.list": (lambda c: c.routes.list(page=1), "GET", "/api/routes",
                    {"routes": [ROUTE], "pagination": OFFSET}, None,
                    lambda r: r.data[0].source_id == "src_1"),
    "routes.get": (lambda c: c.routes.get("rte_1"), "GET", "/api/routes/rte_1",
                   {"route": ROUTE}, None, lambda r: r.destination_id == "dst_1"),
    "routes.create": (lambda c: c.routes.create({"name": "R", "sourceId": "src_1",
                                                 "destinationId": "dst_1"}),
                      "POST", "/api/routes", {"route": ROUTE},
                      {"name": "R", "sourceId": "src_1", "destinationId": "dst_1"},
                      lambda r: r.id == "rte_1"),
    "routes.update": (lambda c: c.routes.update("rte_1", {"isActive": False}), "PATCH",
                      "/api/routes/rte_1", {"success": True}, {"isActive": False},
                      lambda r: r is None),
    "routes.delete": (lambda c: c.routes.delete("rte_1"), "DELETE", "/api/routes/rte_1",
                      {"success": True}, None, lambda r: r is None),
    "routes.get_circuit_status": (lambda c: c.routes.get_circuit_status("rte_1"), "GET",
                                  "/api/routes/rte_1/circuit-status",
                                  {"circuitState": "open"}, None,
                                  lambda r: r.circuit_state == "open"),
    "routes.reset_circuit": (lambda c: c.routes.reset_circuit("rte_1"), "POST",
                             "/api/routes/rte_1/reset-circuit", {"success": True}, None,
                             lambda r: r is None),
    "routes.bulk_delete": (lambda c: c.routes.bulk_delete(["rte_1"]), "DELETE",
                           "/api/routes/bulk", {"success": True, "deleted": 1}, {"ids": ["rte_1"]},
                           lambda r: r.deleted == 1),
    "routes.export": (lambda c: c.routes.export(ids=["rte_1", "rte_2"]), "GET",
                      "/api/routes/export", {"routes": []}, None, lambda r: r == {"routes": []}),
    # destinations
    "destinations.get": (lambda c: c.destinations.get("dst_1"), "GET", "/api/destinations/dst_1",
                         {"destination": DEST}, None, lambda r: r.slug == "d"),
    "destinations.delete": (lambda c: c.destinations.delete("dst_1"), "DELETE",
                            "/api/destinations/dst_1", {"success": True}, None,
                            lambda r: r is None),
    "destinations.test": (lambda c: c.destinations.test("dst_1"), "POST",
                          "/api/destinations/dst_1/test",
                          {"success": True, "status": 200, "latencyMs": 12}, None,
                          lambda r: r.success is True),
    "destinations.export": (lambda c: c.destinations.export(), "GET", "/api/destinations/export",
                            {"destinations": []}, None, lambda r: "destinations" in r),
    "destinations.import": (lambda c: c.destinations.import_destinations([{"name": "D"}]), "POST",
                            "/api/destinations/import",
                            {"success": True, "summary": {"total": 1, "imported": 1}},
                            {"destinations": [{"name": "D"}], "conflictStrategy": "skip",
                             "validateOnly": False},
                            lambda r: r.success is True),
    "destinations.bulk_delete": (lambda c: c.destinations.bulk_delete(["dst_1"]), "DELETE",
                                 "/api/destinations/bulk", {"success": True, "deleted": 1},
                                 {"ids": ["dst_1"]}, lambda r: r.deleted == 1),
    # sources
    "sources.export": (lambda c: c.sources.export(ids=["src_1"]), "GET", "/api/sources/export",
                       {"sources": []}, None, lambda r: "sources" in r),
    "sources.import": (lambda c: c.sources.import_sources([{"name": "S"}], validate_only=True),
                       "POST", "/api/sources/import", {"valid": True, "summary": {"total": 1}},
                       {"sources": [{"name": "S"}], "conflictStrategy": "skip",
                        "validateOnly": True}, lambda r: r.valid is True),
    "sources.bulk_delete": (lambda c: c.sources.bulk_delete(["src_1"]), "DELETE",
                            "/api/sources/bulk", {"success": True, "deleted": 1},
                            {"ids": ["src_1"]}, lambda r: r.deleted == 1),
    "sources.reveal_secret": (lambda c: c.sources.reveal_secret("src_1"), "GET",
                              "/api/sources/src_1/reveal-secret", {"signingSecret": "s3"}, None,
                              lambda r: r == "s3"),
    "sources.verify_token": (lambda c: c.sources.verify_token("src_1"), "GET",
                             "/api/sources/src_1/verify-token", {"verifyToken": "vt"}, None,
                             lambda r: r == "vt"),
    "sources.rotate_verify_token": (lambda c: c.sources.rotate_verify_token("src_1"), "POST",
                                    "/api/sources/src_1/rotate-verify-token",
                                    {"verifyToken": "vt2"}, None, lambda r: r == "vt2"),
    # event types
    "event_types.list": (lambda c: c.event_types.list(limit=10), "GET", "/api/event-types",
                         {"data": [ET], "pagination": CURSOR}, None,
                         lambda r: r.data[0].name == "order.created"),
    "event_types.get": (lambda c: c.event_types.get("et_1"), "GET", "/api/event-types/et_1",
                        {"data": ET}, None, lambda r: r.id == "et_1"),
    "event_types.create": (lambda c: c.event_types.create({"name": "order.created"}), "POST",
                           "/api/event-types", {"data": ET}, {"name": "order.created"},
                           lambda r: r.id == "et_1"),
    "event_types.update": (lambda c: c.event_types.update("et_1", {"description": "x"}), "PATCH",
                           "/api/event-types/et_1", {"data": ET}, {"description": "x"},
                           lambda r: r.id == "et_1"),
    "event_types.delete": (lambda c: c.event_types.delete("et_1"), "DELETE",
                           "/api/event-types/et_1", {"success": True}, None, lambda r: r is None),
    # subscriptions
    "subscriptions.list": (lambda c: c.subscriptions.list(), "GET", "/api/webhook-subscriptions",
                           {"data": [SUB], "pagination": CURSOR}, None,
                           lambda r: r.data[0].endpoint_id == "ep_1"),
    "subscriptions.get": (lambda c: c.subscriptions.get("sub_1"), "GET",
                          "/api/webhook-subscriptions/sub_1", {"data": SUB}, None,
                          lambda r: r.event_type_id == "et_1"),
    "subscriptions.create": (lambda c: c.subscriptions.create({"endpointId": "ep_1",
                                                               "eventTypeId": "et_1"}),
                             "POST", "/api/webhook-subscriptions", {"data": SUB},
                             {"endpointId": "ep_1", "eventTypeId": "et_1"},
                             lambda r: r.id == "sub_1"),
    "subscriptions.update": (lambda c: c.subscriptions.update("sub_1", {"isEnabled": False}),
                             "PATCH", "/api/webhook-subscriptions/sub_1", {"data": SUB},
                             {"isEnabled": False}, lambda r: r.id == "sub_1"),
    "subscriptions.delete": (lambda c: c.subscriptions.delete("sub_1"), "DELETE",
                             "/api/webhook-subscriptions/sub_1", {"success": True}, None,
                             lambda r: r is None),
    "subscriptions.bulk_create": (lambda c: c.subscriptions.bulk_create("ep_1", ["et_1"]), "POST",
                                  "/api/webhook-subscriptions/bulk", {"data": [SUB]},
                                  {"endpointId": "ep_1", "eventTypeIds": ["et_1"]},
                                  lambda r: r[0].id == "sub_1"),
    # endpoints
    "endpoints.list": (lambda c: c.endpoints.list(), "GET", "/api/webhook-endpoints",
                       {"data": [EP], "pagination": CURSOR}, None,
                       lambda r: r.data[0].url == "https://x.test"),
    "endpoints.get": (lambda c: c.endpoints.get("ep_1"), "GET", "/api/webhook-endpoints/ep_1",
                      {"data": EP}, None, lambda r: r.application_id == "app_1"),
    "endpoints.update": (lambda c: c.endpoints.update("ep_1", {"description": "x"}), "PATCH",
                         "/api/webhook-endpoints/ep_1", {"data": EP}, {"description": "x"},
                         lambda r: r.id == "ep_1"),
    "endpoints.delete": (lambda c: c.endpoints.delete("ep_1"), "DELETE",
                         "/api/webhook-endpoints/ep_1", {"success": True}, None,
                         lambda r: r is None),
    "endpoints.reset_circuit": (lambda c: c.endpoints.reset_circuit("ep_1"), "POST",
                                "/api/webhook-endpoints/ep_1/reset-circuit", {"success": True},
                                None, lambda r: r is None),
    # applications
    "applications.get": (lambda c: c.applications.get("app_1"), "GET",
                         "/api/webhook-applications/app_1", {"data": APP}, None,
                         lambda r: r.external_id == "cust_1"),
    "applications.get_by_external_id": (lambda c: c.applications.get_by_external_id("cust_1"),
                                        "GET", "/api/webhook-applications/by-external-id/cust_1",
                                        {"data": APP}, None, lambda r: r.id == "app_1"),
    "applications.create": (lambda c: c.applications.create({"name": "A"}), "POST",
                            "/api/webhook-applications", {"data": APP}, {"name": "A"},
                            lambda r: r.id == "app_1"),
    "applications.update": (lambda c: c.applications.update("app_1", {"name": "B"}), "PATCH",
                            "/api/webhook-applications/app_1", {"data": APP}, {"name": "B"},
                            lambda r: r.id == "app_1"),
    "applications.delete": (lambda c: c.applications.delete("app_1"), "DELETE",
                            "/api/webhook-applications/app_1", {"success": True}, None,
                            lambda r: r is None),
    # deliveries and events
    "deliveries.get": (lambda c: c.deliveries.get("dlv_1"), "GET", "/api/deliveries/dlv_1",
                       {"delivery": DELIVERY}, None, lambda r: r.status == "success"),
    "deliveries.replay": (lambda c: c.deliveries.replay("dlv_1"), "POST",
                          "/api/deliveries/dlv_1/replay", {"deliveryId": "dlv_2"}, None,
                          lambda r: r.delivery_id == "dlv_2"),
    "deliveries.bulk_replay": (lambda c: c.deliveries.bulk_replay(["dlv_1"]), "POST",
                               "/api/deliveries/bulk-replay", {"replayed": 1},
                               {"deliveryIds": ["dlv_1"]}, lambda r: r is not None),
    "deliveries.bulk_replay_events": (lambda c: c.deliveries.bulk_replay_events(["evt_1"]),
                                      "POST", "/api/deliveries/bulk-replay-events",
                                      {"replayed": 1}, {"eventIds": ["evt_1"]},
                                      lambda r: r is not None),
    "events.get": (lambda c: c.events.get("evt_1"), "GET", "/api/events/evt_1",
                   {"event": EVENT, "deliveries": []}, None, lambda r: r.id == "evt_1"),
    "events.debug": (lambda c: c.events.debug("evt_1"), "GET", "/api/events/evt_1/debug",
                     {"event": EVENT}, None, lambda r: r is not None),
    # outbound message log and DLQ
    "message_log.get": (lambda c: c.message_log.get("msg_1"), "GET",
                        "/api/outbound-messages/msg_1", {"data": MSG}, None,
                        lambda r: r.id == "msg_1"),
    "message_log.list_attempts": (lambda c: c.message_log.list_attempts("msg_1"), "GET",
                                  "/api/outbound-messages/msg_1/attempts",
                                  {"data": [{"id": "att_1"}]}, None,
                                  lambda r: r[0].id == "att_1"),
    "message_log.stats": (lambda c: c.message_log.stats(), "GET",
                          "/api/outbound-messages/stats/summary", {"data": {}}, None,
                          lambda r: r is not None),
    "dlq.stats": (lambda c: c.dlq.stats(), "GET", "/api/outbound-messages/dlq/stats",
                  {"data": {}}, None, lambda r: r is not None),
    "dlq.retry": (lambda c: c.dlq.retry("msg_1"), "POST", "/api/outbound-messages/dlq/msg_1/retry",
                  {"data": {}}, None, lambda r: r is not None),
    "dlq.delete": (lambda c: c.dlq.delete("msg_1"), "DELETE", "/api/outbound-messages/dlq/msg_1",
                   {"success": True}, None, lambda r: r is None),
    "dlq.retry_bulk": (lambda c: c.dlq.retry_bulk(["msg_1"]), "POST",
                       "/api/outbound-messages/dlq/retry-bulk", {"data": {}},
                       {"messageIds": ["msg_1"]}, lambda r: r is not None),
    "dlq.bulk_delete": (lambda c: c.dlq.bulk_delete(["msg_1"]), "DELETE",
                        "/api/outbound-messages/dlq/bulk", {"data": {}},
                        {"messageIds": ["msg_1"]}, lambda r: r is not None),
}

CRON = {"id": "crn_1", "name": "C", "url": "https://x.test", "cronExpression": "0 * * * *"}
FLT = {"id": "flt_1", "name": "F", "slug": "f", "conditions": [], "logic": "AND"}
SCH = {"id": "sch_1", "name": "S", "slug": "s", "jsonSchema": {"type": "object"}}
TRN = {"id": "trn_1", "name": "T", "slug": "t", "code": "$"}
TUN = {"id": "tun_1", "organizationId": "org_1", "name": "dev", "subdomain": "abc"}
ORG = {"id": "org_1", "name": "Acme", "slug": "acme"}

CASES.update({
    # cron jobs
    "cron_jobs.list": (lambda c: c.cron_jobs.list(), "GET", "/api/cron", {"cronJobs": [CRON]},
                       None, lambda r: r.total == 1 and r.data[0].id == "crn_1"),
    "cron_jobs.get": (lambda c: c.cron_jobs.get("crn_1"), "GET", "/api/cron/crn_1",
                      {"cronJob": CRON}, None, lambda r: r.id == "crn_1"),
    "cron_jobs.create": (lambda c: c.cron_jobs.create({"name": "C", "url": "https://x.test",
                                                       "cronExpression": "0 * * * *"}),
                         "POST", "/api/cron", {"cronJob": CRON},
                         {"name": "C", "url": "https://x.test", "cronExpression": "0 * * * *"},
                         lambda r: r.id == "crn_1"),
    "cron_jobs.update": (lambda c: c.cron_jobs.update("crn_1", {"isActive": False}), "PATCH",
                         "/api/cron/crn_1", {"success": True}, {"isActive": False},
                         lambda r: r is None),
    "cron_jobs.delete": (lambda c: c.cron_jobs.delete("crn_1"), "DELETE", "/api/cron/crn_1",
                         {"success": True}, None, lambda r: r is None),
    "cron_jobs.create_group": (lambda c: c.cron_jobs.create_group({"name": "G"}), "POST",
                               "/api/cron-groups", {"group": {"id": "grp_1", "name": "G"}},
                               {"name": "G"}, lambda r: r.id == "grp_1"),
    # api keys
    "api_keys.create": (lambda c: c.api_keys.create({"name": "K"}), "POST", "/api/api-keys",
                        {"apiKey": {"id": "key_1", "name": "K", "key": "whr_x"}}, {"name": "K"},
                        lambda r: r.key == "whr_x"),
    "api_keys.delete": (lambda c: c.api_keys.delete("key_1"), "DELETE", "/api/api-keys/key_1",
                        {"success": True}, None, lambda r: r is None),
    # filters
    "filters.list": (lambda c: c.filters.list(), "GET", "/api/filters",
                     {"filters": [FLT], "pagination": OFFSET}, None,
                     lambda r: r.data[0].id == "flt_1"),
    "filters.get": (lambda c: c.filters.get("flt_1"), "GET", "/api/filters/flt_1",
                    {"filter": FLT}, None, lambda r: r.logic == "AND"),
    "filters.update": (lambda c: c.filters.update("flt_1", {"logic": "or"}), "PATCH",
                       "/api/filters/flt_1", {"success": True}, {"logic": "OR"},
                       lambda r: r is None),
    "filters.delete": (lambda c: c.filters.delete("flt_1"), "DELETE", "/api/filters/flt_1",
                       {"success": True}, None, lambda r: r is None),
    # schemas
    "schemas.get": (lambda c: c.schemas.get("sch_1"), "GET", "/api/schemas/sch_1",
                    {"schema": SCH}, None, lambda r: r.json_schema == {"type": "object"}),
    "schemas.create": (lambda c: c.schemas.create({"name": "S", "jsonSchema": {}}), "POST",
                       "/api/schemas", {"schema": SCH}, {"name": "S", "jsonSchema": {}},
                       lambda r: r.id == "sch_1"),
    "schemas.update": (lambda c: c.schemas.update("sch_1", {"name": "S2"}), "PUT",
                       "/api/schemas/sch_1", {"success": True}, {"name": "S2"},
                       lambda r: r is None),
    "schemas.delete": (lambda c: c.schemas.delete("sch_1"), "DELETE", "/api/schemas/sch_1",
                       {"success": True}, None, lambda r: r is None),
    # transforms
    "transforms.list": (lambda c: c.transforms.list(), "GET", "/api/transforms",
                        {"transforms": [TRN], "pagination": OFFSET}, None,
                        lambda r: r.data[0].id == "trn_1"),
    "transforms.get": (lambda c: c.transforms.get("trn_1"), "GET", "/api/transforms/trn_1",
                       {"transform": TRN}, None, lambda r: r.code == "$"),
    "transforms.create": (lambda c: c.transforms.create({"name": "T", "code": "$"}), "POST",
                          "/api/transforms", {"transform": TRN}, {"name": "T", "code": "$"},
                          lambda r: r.id == "trn_1"),
    "transforms.delete": (lambda c: c.transforms.delete("trn_1"), "DELETE",
                          "/api/transforms/trn_1", {"success": True}, None, lambda r: r is None),
    "transforms.test": (lambda c: c.transforms.test(code="$", payload={}), "POST",
                        "/api/transforms/test", {"success": True, "output": {}},
                        {"code": "$", "payload": {}, "transformType": "jsonata",
                         "inputFormat": "json", "outputFormat": "json"},
                        lambda r: r.success is True),
    # tunnels
    "tunnels.list": (lambda c: c.tunnels.list(), "GET", "/api/tunnels", {"tunnels": [TUN]},
                     None, lambda r: r[0].subdomain == "abc"),
    "tunnels.get": (lambda c: c.tunnels.get("tun_1"), "GET", "/api/tunnels/tun_1",
                    {"tunnel": TUN}, None, lambda r: r.id == "tun_1"),
    "tunnels.bulk_delete": (lambda c: c.tunnels.bulk_delete(["tun_1"]), "DELETE",
                            "/api/tunnels/bulk", {"success": True, "deleted": 1},
                            {"ids": ["tun_1"]}, lambda r: r.deleted == 1),
    # organizations
    "organizations.get": (lambda c: c.organizations.get("org_1"), "GET",
                          "/api/organizations/org_1", {"organization": ORG}, None,
                          lambda r: r.slug == "acme"),
    "organizations.create": (lambda c: c.organizations.create("Acme", "acme"), "POST",
                             "/api/organizations", {"organization": ORG},
                             {"name": "Acme", "slug": "acme"}, lambda r: r.id == "org_1"),
    "organizations.update_member": (lambda c: c.organizations.update_member("org_1", "usr_1",
                                                                            "admin"),
                                    "PATCH", "/api/organizations/org_1/members/usr_1",
                                    {"success": True}, {"role": "admin"}, lambda r: r is None),
    "organizations.remove_member": (lambda c: c.organizations.remove_member("org_1", "usr_1"),
                                    "DELETE", "/api/organizations/org_1/members/usr_1",
                                    {"success": True}, None, lambda r: r is None),
    "organizations.invite": (lambda c: c.organizations.invite("org_1", "a@b.test"), "POST",
                             "/api/organizations/org_1/invites",
                             {"invite": {"id": "inv_1", "email": "a@b.test", "role": "member"}},
                             {"email": "a@b.test", "role": "member"},
                             lambda r: r.id == "inv_1"),
    "organizations.list_invites": (lambda c: c.organizations.list_invites("org_1"), "GET",
                                   "/api/organizations/org_1/invites",
                                   {"invites": [{"id": "inv_1", "email": "a@b.test"}]}, None,
                                   lambda r: r[0].email == "a@b.test"),
    "organizations.cancel_invite": (lambda c: c.organizations.cancel_invite("org_1", "inv_1"),
                                    "DELETE", "/api/organizations/org_1/invites/inv_1",
                                    {"success": True}, None, lambda r: r is None),
    # portal tokens, providers
    "portal_tokens.create": (lambda c: c.portal_tokens.create("app_1", {"name": "N"}), "POST",
                             "/api/portal/webhook-applications/app_1/tokens",
                             {"data": {"id": "ptk_1", "token": "whpt_x"}}, {"name": "N"},
                             lambda r: r.token == "whpt_x"),
    "providers.get": (lambda c: c.providers.get("stripe"), "GET", "/api/catalog/providers/stripe",
                      {"provider": {"id": "stripe", "name": "Stripe"}}, None,
                      lambda r: r.name == "Stripe"),
    "providers.events": (lambda c: c.providers.events("stripe"), "GET",
                         "/api/catalog/providers/stripe/events",
                         {"providerId": "stripe", "events": []}, None,
                         lambda r: r.provider_id == "stripe"),
    # endpoints
    "endpoints.create": (lambda c: c.endpoints.create("app_1", {"url": "https://x.test"}), "POST",
                         "/api/webhook-endpoints", {"data": {**EP, "secret": "whsec_x"}},
                         {"url": "https://x.test", "applicationId": "app_1"},
                         lambda r: r.secret == "whsec_x"),
    "endpoints.rotate_secret": (lambda c: c.endpoints.rotate_secret("ep_1", grace_period=60),
                                "POST", "/api/webhook-endpoints/ep_1/rotate-secret",
                                {"data": {"secret": "whsec_new"}}, {"gracePeriodSeconds": 60},
                                lambda r: r is not None),
    "endpoints.test": (lambda c: c.endpoints.test("ep_1"), "POST",
                       "/api/webhook-endpoints/ep_1/test", {"success": True}, None,
                       lambda r: r == {"success": True}),
    # destinations, events, message log
    "destinations.list": (lambda c: c.destinations.list(page_size=5), "GET", "/api/destinations",
                          {"destinations": [DEST], "pagination": OFFSET}, None,
                          lambda r: r.data[0].id == "dst_1"),
    "destinations.update": (lambda c: c.destinations.update("dst_1", {"name": "D2"}), "PATCH",
                            "/api/destinations/dst_1", {"success": True}, {"name": "D2"},
                            lambda r: r is None),
    "events.export": (lambda c: c.events.export(source_id="src_1"), "GET", "/api/events/export",
                      {"events": []}, None, lambda r: r == {"events": []}),
    "message_log.replay": (lambda c: c.message_log.replay("msg_1"), "POST",
                           "/api/outbound-messages/msg_1/replay",
                           {"data": {"originalMessageId": "msg_1", "newMessageId": "msg_2",
                                     "status": "pending"}}, None,
                           lambda r: r.new_message_id == "msg_2"),
    "message_log.export": (lambda c: c.message_log.export(), "GET",
                           "/api/outbound-messages/export", {"data": []}, None,
                           lambda r: r == {"data": []}),
})



def _sync(client: Hookbase, call: Callable[[Any], Any]) -> Any:
    return call(_Ns(client))


async def _async(client: AsyncHookbase, call: Callable[[Any], Any]) -> Any:
    result = call(_Ns(client))
    return await result if inspect.isawaitable(result) else result


class _Ns:
    """Expose the outbound resources (client.outbound.endpoints...) at the top level."""

    _OUTBOUND = {"event_types", "subscriptions", "endpoints", "applications", "message_log",
                 "dlq", "portal_tokens", "messages"}

    def __init__(self, client: Any) -> None:
        self._client = client

    def __getattr__(self, name: str) -> Any:
        if name in self._OUTBOUND:
            return getattr(self._client.outbound, name)
        return getattr(self._client, name)


def _check_request(route: Any, method: str, body: Any) -> None:
    req = route.calls.last.request
    assert req.method == method
    if body is None:
        assert req.content in (b"", b"null")
    else:
        assert json.loads(req.content) == body


@pytest.mark.parametrize("name", list(CASES))
def test_sync(mock_api, name):
    call, method, path, resp, body, check = CASES[name]
    route = mock_api.request(method, path).mock(return_value=httpx.Response(200, json=resp))
    with Hookbase(api_key=TEST_API_KEY) as client:
        assert check(_sync(client, call))
    _check_request(route, method, body)


@pytest.mark.parametrize("name", list(CASES))
async def test_async(mock_api, name):
    call, method, path, resp, body, check = CASES[name]
    route = mock_api.request(method, path).mock(return_value=httpx.Response(200, json=resp))
    async with AsyncHookbase(api_key=TEST_API_KEY) as client:
        assert check(await _async(client, call))
    _check_request(route, method, body)


def test_export_ids_are_comma_joined(mock_api):
    route = mock_api.get("/api/routes/export").mock(return_value=httpx.Response(200, json={}))
    with Hookbase(api_key=TEST_API_KEY) as client:
        client.routes.export(ids=["rte_1", "rte_2"])
    assert dict(route.calls.last.request.url.params) == {"ids": "rte_1,rte_2"}
