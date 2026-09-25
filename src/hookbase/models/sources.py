from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import field_validator

from ._base import HookbaseModel

# Providers the API will accept for a source.
#
# Mirrors SUPPORTED_SIGNATURE_PROVIDERS in the API (api/src/utils/signature-schemes.ts), which
# is derived from the signature scheme table rather than restated. Regenerate with
# `npx tsx scripts/print-source-enums.ts` in the api package; do not hand-extend this Literal,
# because a value the API does not accept is a 400 the type promised would not happen.
#
# Removed in the 2026-09 correction: "sendgrid", "mailgun" and "linear". All three were
# advertised here from the beginning and none was ever accepted by the API. SendGrid signs with
# ECDSA and Mailgun puts the signature in the POST body, so neither fits this scheme model;
# Linear's scheme is real but unverified against its docs. Use "custom" for all three.
#
# "svix" is an alias of "standard-webhooks"; both resolve to the same scheme server-side.
SourceProvider = Literal[
    "airtable", "asana", "bitbucket", "calendly", "custom", "generic",
    "github", "gitlab", "heroku", "intercom", "lemonsqueezy", "notion",
    "paddle", "razorpay", "sentry", "shopify", "slack", "standard-webhooks",
    "stripe", "svix", "twilio", "typeform", "workos", "zoom",
]
# Corrected alongside SourceProvider: "header" and "event_id" were never accepted, and the three
# values the API actually defaults to and documents were missing. "auto" is the default.
DedupStrategy = Literal["auto", "provider_id", "payload_hash", "idempotency_key", "none"]
IpFilterMode = Literal["none", "allowlist", "denylist", "both"]
# HTTP verbs an ingest endpoint can be restricted to. OPTIONS is excluded: CORS preflight is
# answered before ingest runs, so it is never gateable.
IngestMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]


class Source(HookbaseModel):
    """A source as the API returns it.

    The signing secret is not included. Responses carry ``has_signing_secret`` and the last four
    characters; the full value comes back exactly twice, from :meth:`Sources.create` (which
    returns a :class:`SourceWithSecret`) and from :meth:`Sources.reveal_secret`.
    """

    id: str
    organization_id: str | None = None
    name: str
    slug: str
    provider: SourceProvider | None = None
    description: str | None = None
    #: Whether a signing secret is set. The secret itself is not returned here.
    has_signing_secret: bool = False
    #: Last four characters of the signing secret, prefixed with "...", or None if unset.
    signing_secret_last4: str | None = None
    #: Reject events whose signature fails verification. Defaults to False, in which case a
    #: failing event is flagged with signature_valid=False and delivered anyway.
    reject_invalid_signatures: bool = False
    rate_limit_per_minute: int | None = None
    is_active: bool = True
    custom_domain_id: str | None = None
    ip_filter_mode: IpFilterMode = "none"
    ip_allowlist: list[str] = []
    ip_denylist: list[str] = []
    #: JSONPath expressions whose values are encrypted at rest.
    encrypt_fields: list[str] = []
    #: JSONPath expressions whose values are masked in stored payloads.
    mask_fields: list[str] = []
    dedup_enabled: bool = False
    dedup_strategy: DedupStrategy = "auto"
    dedup_window_hours: int = 24
    dedup_custom_header: str | None = None
    transient_mode: bool = False
    #: HTTP verbs the ingest endpoint accepts. Empty list means any method.
    allowed_methods: list[str] = []
    event_count: int = 0
    route_count: int = 0
    #: Returned by get() and create(). Not included in list() responses.
    ingest_url: str | None = None
    created_at: str = ""
    updated_at: str = ""

    @field_validator(
        "is_active",
        "reject_invalid_signatures",
        "has_signing_secret",
        "dedup_enabled",
        "transient_mode",
        mode="before",
    )
    @classmethod
    def parse_bool_from_int(cls, v: Any) -> Any:
        if isinstance(v, int):
            return bool(v)
        return v

    @field_validator(
        "ip_allowlist", "ip_denylist", "encrypt_fields", "mask_fields", mode="before"
    )
    @classmethod
    def parse_json_list(cls, v: Any) -> Any:
        if v is None:
            return []
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, ValueError):
                return []
        return v

    @field_validator("allowed_methods", mode="before")
    @classmethod
    def parse_allowed_methods(cls, v: Any) -> Any:
        """Coerce null/JSON-string forms to a list; both mean "any method" when empty."""
        if v is None:
            return []
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else []
            except (json.JSONDecodeError, ValueError):
                return []
        return v


class SourceWithSecret(Source):
    """What create() returns: a source plus the one look at its signing secret you get."""

    signing_secret: str = ""


class CreateSourceParams(HookbaseModel):
    name: str
    #: Required: it forms the ingest URL, /ingest/<org>/<slug>, and cannot be changed later.
    slug: str
    provider: SourceProvider | None = None
    description: str | None = None
    #: Supply your own secret to match what the provider is already configured with. Omit it and
    #: the API generates one, returned once on the created source.
    signing_secret: str | None = None
    #: Reject events whose signature fails verification. Defaults to False.
    reject_invalid_signatures: bool | None = None
    rate_limit_per_minute: int | None = None
    ip_filter_mode: IpFilterMode | None = None
    ip_allowlist: list[str] | None = None
    ip_denylist: list[str] | None = None
    encrypt_fields: list[str] | None = None
    mask_fields: list[str] | None = None
    dedup_enabled: bool | None = None
    dedup_strategy: DedupStrategy | None = None
    #: Deduplication window in hours, 1 to 168.
    dedup_window_hours: int | None = None
    #: Header to deduplicate on when dedup_strategy is "idempotency_key".
    dedup_custom_header: str | None = None
    transient_mode: bool | None = None
    #: Restrict the ingest endpoint to these verbs. None/[] accepts any method.
    allowed_methods: list[IngestMethod] | None = None


class UpdateSourceParams(HookbaseModel):
    name: str | None = None
    description: str | None = None
    provider: SourceProvider | None = None
    is_active: bool | None = None
    signing_secret: str | None = None
    reject_invalid_signatures: bool | None = None
    rate_limit_per_minute: int | None = None
    ip_filter_mode: IpFilterMode | None = None
    ip_allowlist: list[str] | None = None
    ip_denylist: list[str] | None = None
    encrypt_fields: list[str] | None = None
    mask_fields: list[str] | None = None
    dedup_enabled: bool | None = None
    dedup_strategy: DedupStrategy | None = None
    dedup_window_hours: int | None = None
    dedup_custom_header: str | None = None
    transient_mode: bool | None = None
    #: Restrict the ingest endpoint to these verbs. Pass [] to accept any method again.
    allowed_methods: list[IngestMethod] | None = None
