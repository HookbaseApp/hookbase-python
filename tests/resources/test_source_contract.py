"""The 2026-10 source contract: open provider strings, null secrets, verify tokens, pending
verification, and the provider catalog."""

from __future__ import annotations

import pytest
import respx

from hookbase import AsyncHookbase, Hookbase, NotFoundError, ValidationError
from hookbase.models import (
    CatalogProviderDetail,
    PendingVerification,
    ProviderCatalogList,
    SourceWithSecret,
)

from ..conftest import make_paginated_response, sent_body


@pytest.fixture
def mock_api():
    with respx.mock(base_url="https://api.hookbase.app") as mock:
        yield mock


@pytest.fixture
def client(mock_api):
    c = Hookbase(api_key="whr_test")
    yield c
    c.close()


WISE_SOURCE = {
    "id": "src_wise",
    "organizationId": "org_1",
    "name": "Wise",
    "slug": "wise",
    "provider": "wise",
    "isActive": True,
    "hasSigningSecret": False,
    "signingSecretLast4": None,
    "verifiesWithoutSecret": True,
    "awaitingSigningSecret": False,
    "createdAt": "2026-10-01T00:00:00Z",
    "updatedAt": "2026-10-01T00:00:00Z",
}


# --- regressions: responses that used to raise ---------------------------------------------


def test_list_parses_a_source_with_a_newer_provider(mock_api, client):
    mock_api.get("/api/sources").respond(200, json=make_paginated_response(
        [WISE_SOURCE, {**WISE_SOURCE, "id": "src_x", "slug": "x", "provider": "not-yet-known"}],
        data_key="sources",
    ))
    page = client.sources.list()
    assert [s.provider for s in page.data] == ["wise", "not-yet-known"]
    assert page.data[0].verifies_without_secret is True
    assert page.data[0].awaiting_signing_secret is False


def test_create_parses_a_null_signing_secret(mock_api, client):
    mock_api.post("/api/sources").respond(201, json={
        "source": {**WISE_SOURCE, "signingSecret": None},
    })
    src = client.sources.create({"name": "Wise", "slug": "wise", "provider": "wise"})
    assert isinstance(src, SourceWithSecret)
    assert src.signing_secret is None
    assert src.verifies_without_secret is True


def test_create_reports_a_secret_awaiting_registration(mock_api, client):
    mock_api.post("/api/sources").respond(201, json={"source": {
        **WISE_SOURCE, "provider": "notion", "slug": "notion",
        "verifiesWithoutSecret": False, "awaitingSigningSecret": True, "signingSecret": None,
    }})
    src = client.sources.create({"name": "Notion", "slug": "notion", "provider": "notion"})
    assert src.awaiting_signing_secret is True
    assert src.signing_secret is None


def test_whatsapp_create_returns_and_sends_the_verify_token(mock_api, client):
    route = mock_api.post("/api/sources").respond(201, json={"source": {
        **WISE_SOURCE, "id": "src_wa", "provider": "whatsapp", "slug": "wa",
        "verifiesWithoutSecret": False, "hasSigningSecret": True, "signingSecretLast4": "...beef",
        "signingSecret": "app-secret-beef", "verifyToken": "vt_123",
    }})
    src = client.sources.create({
        "name": "WhatsApp", "slug": "wa", "provider": "whatsapp", "verifyToken": "vt_123",
    })
    assert src.verify_token == "vt_123"
    assert src.signing_secret == "app-secret-beef"
    assert sent_body(route)["verifyToken"] == "vt_123"


def test_update_sends_clear_as_null(mock_api, client):
    route = mock_api.patch("/api/sources/src_wa").respond(200, json={"success": True})
    client.sources.update("src_wa", {"clear": ["verifyToken"]})
    assert sent_body(route) == {"verifyToken": None}


# --- new source endpoints --------------------------------------------------------------------


def test_verify_token(mock_api, client):
    mock_api.get("/api/sources/src_wa/verify-token").respond(200, json={"verifyToken": "vt_1"})
    assert client.sources.verify_token("src_wa") == "vt_1"


def test_verify_token_for_a_non_meta_source_is_a_400(mock_api, client):
    mock_api.get("/api/sources/src_1/verify-token").respond(400, json={
        "error": "stripe has no verify token; only Meta providers (WhatsApp) use one",
    })
    with pytest.raises(ValidationError):
        client.sources.verify_token("src_1")


def test_rotate_verify_token(mock_api, client):
    route = mock_api.post("/api/sources/src_wa/rotate-verify-token").respond(
        200, json={"verifyToken": "vt_2"},
    )
    assert client.sources.rotate_verify_token("src_wa") == "vt_2"
    assert route.called


def test_get_pending_verification(mock_api, client):
    mock_api.get("/api/sources/notion/pending-verification").respond(200, json={
        "provider": "notion", "token": "secret_abc",
        "receivedAt": "2026-10-11T12:00:00Z", "clientIp": None,
    })
    pending = client.sources.get_pending_verification("notion")
    assert isinstance(pending, PendingVerification)
    assert pending.token == "secret_abc"
    assert pending.received_at == "2026-10-11T12:00:00Z"
    assert pending.client_ip is None


def test_get_pending_verification_when_none_is_waiting(mock_api, client):
    mock_api.get("/api/sources/notion/pending-verification").respond(404, json={
        "error": "No verification token is waiting for this source",
    })
    with pytest.raises(NotFoundError):
        client.sources.get_pending_verification("notion")


def test_adopt_pending_verification(mock_api, client):
    route = mock_api.post("/api/sources/notion/pending-verification/adopt").respond(
        200, json={"success": True},
    )
    assert client.sources.adopt_pending_verification("notion") is None
    assert route.called


def test_rotate_secret_for_a_built_in_provider_is_a_400(mock_api, client):
    mock_api.post("/api/sources/src_wise/rotate-secret").respond(400, json={
        "error": "wise signs with a public key it publishes, so this source has no secret.",
    })
    with pytest.raises(ValidationError):
        client.sources.rotate_secret("src_wise")


def test_reveal_secret(mock_api, client):
    mock_api.get("/api/sources/src_1/reveal-secret").respond(200, json={"signingSecret": "s3cret"})
    assert client.sources.reveal_secret("src_1") == "s3cret"


def test_events_source_id_slug_unknown_is_a_404(mock_api, client):
    mock_api.get("/api/events", params={"sourceId": "nope"}).respond(
        404, json={"error": "Source not found"},
    )
    with pytest.raises(NotFoundError):
        client.events.list(source_id="nope")


async def test_async_new_endpoints(mock_api):
    mock_api.get("/api/sources/src_wa/verify-token").respond(200, json={"verifyToken": "vt_1"})
    mock_api.post("/api/sources/src_wa/rotate-verify-token").respond(
        200, json={"verifyToken": "vt_2"},
    )
    mock_api.get("/api/sources/n/pending-verification").respond(200, json={
        "provider": "notion", "token": "secret_x", "receivedAt": "2026-10-11T00:00:00Z",
        "clientIp": "203.0.113.9",
    })
    adopt = mock_api.post("/api/sources/n/pending-verification/adopt").respond(
        200, json={"success": True},
    )
    async with AsyncHookbase(api_key="whr_test") as c:
        assert await c.sources.verify_token("src_wa") == "vt_1"
        assert await c.sources.rotate_verify_token("src_wa") == "vt_2"
        pending = await c.sources.get_pending_verification("n")
        assert pending.client_ip == "203.0.113.9"
        await c.sources.adopt_pending_verification("n")
    assert adopt.called


# --- provider catalog ------------------------------------------------------------------------

CATALOG_LIST = {
    "providers": [
        {
            "id": "stripe", "name": "Stripe", "category": "payments",
            "description": "Payments", "icon": "x", "eventTypeCount": 12,
            "hookbaseProvider": "stripe", "hasSignatureVerification": True, "hasIpRanges": True,
            "signatureVerification": {
                "supported": True, "kind": "hmac", "secretSource": "provider",
                "secretLabel": "Signing secret", "secretPlaceholder": "whsec_...",
            },
        },
        {
            "id": "mollie-nextgen", "name": "Mollie", "category": "payments",
            "description": "", "icon": "m", "eventTypeCount": 3,
            "hookbaseProvider": "mollie", "hasSignatureVerification": True, "hasIpRanges": False,
            # An API version that predates the list summary omits the field entirely.
        },
        {
            "id": "notion", "name": "Notion", "category": "brand-new-category",
            "description": "", "icon": "n", "eventTypeCount": 4,
            "hookbaseProvider": "notion", "hasSignatureVerification": True, "hasIpRanges": False,
            "signatureVerification": {
                "supported": True, "kind": "hmac", "secretSource": "a-future-source",
                "secretLabel": "Verification token", "secretAfterRegistration": True,
            },
        },
    ],
    "categories": ["payments", "productivity"],
    "total": 3,
}


def test_catalog_list(mock_api, client):
    route = mock_api.get("/api/catalog/providers").respond(200, json=CATALOG_LIST)
    result = client.providers.list(category="payments", search="str")
    assert isinstance(result, ProviderCatalogList)
    assert route.calls.last.request.url.params["category"] == "payments"
    assert route.calls.last.request.url.params["search"] == "str"
    stripe, mollie, notion = result.providers
    assert stripe.signature_verification is not None
    assert stripe.signature_verification.secret_source == "provider"
    assert stripe.event_type_count == 12
    assert mollie.hookbase_provider == "mollie"
    assert mollie.signature_verification is None
    assert notion.signature_verification is not None
    assert notion.signature_verification.secret_after_registration is True
    assert result.total == 3


def test_catalog_list_without_filters_sends_no_query(mock_api, client):
    route = mock_api.get("/api/catalog/providers").respond(200, json=CATALOG_LIST)
    client.providers.list()
    assert not route.calls.last.request.url.params


def test_catalog_get(mock_api, client):
    mock_api.get("/api/catalog/providers/whatsapp").respond(200, json={"provider": {
        "id": "whatsapp", "name": "WhatsApp", "category": "communication", "description": "",
        "website": "https://w", "docsUrl": "https://d", "icon": "w",
        "hookbaseProvider": "whatsapp",
        "signatureVerification": {
            "supported": True, "algorithm": "HMAC-SHA256", "headerName": "X-Hub-Signature-256",
            "secretLocationHint": "App settings", "kind": "hmac", "secretLabel": "App secret",
            "secretSource": "provider", "secretInstruction": "Copy the App secret.",
            "verifyToken": {"label": "Verify token", "instruction": "Paste it into Meta."},
        },
        "eventTypes": [{"type": "messages", "description": "Inbound messages"}],
        "samplePayloads": {"messages": {"object": "whatsapp_business_account"}},
        "ipRanges": None,
        "setupGuide": ["Step one"],
    }})
    detail = client.providers.get("whatsapp")
    assert isinstance(detail, CatalogProviderDetail)
    sv = detail.signature_verification
    assert sv is not None and sv.verify_token is not None
    assert sv.verify_token.label == "Verify token"
    assert sv.header_name == "X-Hub-Signature-256"
    assert detail.event_types[0].type == "messages"
    assert detail.ip_ranges is None


def test_catalog_get_unknown_is_a_404(mock_api, client):
    mock_api.get("/api/catalog/providers/nope").respond(404, json={"error": "Provider not found"})
    with pytest.raises(NotFoundError):
        client.providers.get("nope")


def test_catalog_events(mock_api, client):
    mock_api.get("/api/catalog/providers/stripe/events").respond(200, json={
        "providerId": "stripe", "providerName": "Stripe",
        "eventTypes": [{"type": "charge.succeeded", "description": "A charge succeeded"}],
        "samplePayloads": {"charge.succeeded": {"id": "evt_1"}},
    })
    events = client.providers.events("stripe")
    assert events.provider_id == "stripe"
    assert events.event_types[0].type == "charge.succeeded"
    assert events.sample_payloads["charge.succeeded"] == {"id": "evt_1"}


async def test_async_catalog(mock_api):
    mock_api.get("/api/catalog/providers").respond(200, json=CATALOG_LIST)
    async with AsyncHookbase(api_key="whr_test") as c:
        result = await c.providers.list()
    assert len(result.providers) == 3
