"""The field names this SDK puts on the wire, as POST/PATCH /api/sources accept them.

These lists exist because they were wrong for months and nothing said so. The models named
``verify_signature``, ``dedup_window``, ``dedup_header_name``, ``rate_limit`` and
``rate_limit_window``, which the camelCase alias generator sent as ``verifySignature`` and
friends. The API's create schema was a plain zod object, which strips unknown keys rather than
refusing them, so every one of those calls returned 201 having quietly dropped the setting: a
source created with ``verify_signature=True`` came back with verification off and raised no error.

The create schema is strict now, so a stale name is a 400 rather than a silent drop — which is why
a rename here has to be deliberate.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from hookbase.models.sources import (
    CreateSourceParams,
    Source,
    SourceWithSecret,
    UpdateSourceParams,
)

CREATE_FIELDS = {
    "name", "slug", "provider", "description", "signingSecret",
    "rejectInvalidSignatures", "rateLimitPerMinute", "ipFilterMode", "ipAllowlist",
    "ipDenylist", "encryptFields", "maskFields", "dedupEnabled", "dedupStrategy",
    "dedupWindowHours", "dedupCustomHeader", "transientMode", "allowedMethods",
}

UPDATE_FIELDS = (CREATE_FIELDS - {"slug"}) | {"isActive"}


def _aliases(model: type) -> set[str]:
    return {f.alias or name for name, f in model.model_fields.items()}


def test_create_params_send_exactly_the_accepted_fields() -> None:
    assert _aliases(CreateSourceParams) == CREATE_FIELDS


def test_update_params_send_exactly_the_accepted_fields() -> None:
    assert _aliases(UpdateSourceParams) == UPDATE_FIELDS


def test_create_and_update_differ_only_by_slug_and_is_active() -> None:
    create, update = _aliases(CreateSourceParams), _aliases(UpdateSourceParams)
    assert create - update == {"slug"}
    assert update - create == {"isActive"}


def test_slug_is_required_on_create() -> None:
    """slug forms the ingest URL and cannot be changed afterwards, so create demands it."""
    with pytest.raises(ValidationError, match="slug"):
        CreateSourceParams(name="No slug")


def test_a_full_create_serializes_every_field_under_its_wire_name() -> None:
    params = CreateSourceParams(
        name="Stripe Production",
        slug="stripe",
        provider="stripe",
        description="Live charge events",
        signing_secret="whsec_abc",
        reject_invalid_signatures=True,
        rate_limit_per_minute=600,
        ip_filter_mode="allowlist",
        ip_allowlist=["203.0.113.0/24"],
        ip_denylist=[],
        encrypt_fields=["$.data.object.customer_email"],
        mask_fields=["$.data.object.last4"],
        dedup_enabled=True,
        dedup_strategy="provider_id",
        dedup_window_hours=24,
        dedup_custom_header="X-Idempotency-Key",
        transient_mode=False,
        allowed_methods=["POST"],
    )
    assert set(params.model_dump(by_alias=True, exclude_none=True)) == CREATE_FIELDS


def test_a_listed_source_carries_the_masked_pair_not_the_secret() -> None:
    src = Source(
        id="src_1", name="Stripe", slug="stripe",
        hasSigningSecret=True, signingSecretLast4="...c123",
        rejectInvalidSignatures=True, dedupWindowHours=24, routeCount=3,
    )
    assert src.has_signing_secret is True
    assert src.signing_secret_last4 == "...c123"
    assert src.reject_invalid_signatures is True
    assert src.dedup_window_hours == 24
    assert src.route_count == 3
    assert not hasattr(src, "signing_secret")


def test_a_created_source_carries_the_secret_and_the_ingest_url() -> None:
    created = SourceWithSecret(
        id="src_1", name="Stripe", slug="stripe",
        signingSecret="whsec_abc",
        ingestUrl="https://api.hookbase.app/ingest/acme/stripe",
    )
    assert created.signing_secret == "whsec_abc"
    assert created.ingest_url is not None and "/ingest/" in created.ingest_url
