from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import field_validator

from . import _wire
from ._base import HookbaseModel

# Providers the API accepts for a source today.
#
# Mirrors SUPPORTED_SIGNATURE_PROVIDERS in the API (api/src/utils/signature-schemes.ts): 71
# signature schemes plus the aliases svix, clerk, resend, render, etsy and stytch (all of
# standard-webhooks) and generic (of custom). Regenerate with
# `npx tsx scripts/print-source-enums.ts` in the api package.
#
# This is a list of suggestions, not a constraint. `provider` is typed as a plain string on every
# model, request and response alike, because the API adds providers faster than this package
# ships: when it was a Literal, a single source created with a newer provider (wise, whatsapp...)
# made list(), get() and create() raise a ValidationError for the whole call. The API validates
# the value on create and update and answers an unknown one with a 400 naming it.
KNOWN_SOURCE_PROVIDERS: tuple[str, ...] = (
    "adyen", "airtable", "asana", "auth0", "aws-sns", "bigcommerce", "bitbucket", "braintree",
    "calendly", "chargebee", "circleci", "clerk", "clickup", "cloudflare", "coinbase-commerce",
    "custom", "datadog", "discord", "docusign", "etsy", "freshdesk", "generic", "github",
    "gitlab", "gitlab-signing-token", "gocardless", "grafana", "grafana-hmac",
    "grafana-hmac-timestamped", "heroku", "hubspot", "intercom", "jira", "klaviyo",
    "launchdarkly", "lemonsqueezy", "linear", "mailchimp", "mailgun", "mollie", "netlify",
    "newrelic", "notion", "okta", "paddle", "pagerduty", "paypal", "pipedrive", "postmark",
    "railway", "razorpay", "render", "resend", "segment", "sendgrid", "sentry", "shopify",
    "slack", "square", "standard-webhooks", "stripe", "stytch", "supabase",
    "supabase-auth-hooks", "svix", "telegram", "terraform-cloud", "trello", "twilio",
    "typeform", "vercel", "whatsapp", "wise", "wise-sandbox", "woocommerce", "workos",
    "zendesk", "zoom",
)
#: A source provider id. Any string: see KNOWN_SOURCE_PROVIDERS for the values accepted today.
SourceProvider = str

# Corrected in 2026-09: "header" and "event_id" were never accepted, and the three values the
# API actually defaults to and documents were missing. "auto" is the default.
DedupStrategy = Literal["auto", "provider_id", "payload_hash", "idempotency_key", "none"]
IpFilterMode = Literal["none", "allowlist", "denylist", "both"]
# HTTP verbs an ingest endpoint can be restricted to. OPTIONS is excluded: CORS preflight is
# answered before ingest runs, so it is never gateable.
IngestMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"]

# The settings PATCH /api/sources/:id accepts an explicit null for (`.nullable()` in
# updateSourceSchema). Naming one in `UpdateSourceParams.clear` sends that null. Null signingSecret
# removes the secret; null verifyToken generates a fresh one. `clear` also takes snake_case.
CLEARABLE_SOURCE_FIELDS: tuple[str, ...] = (
    "description",
    "provider",
    "signingSecret",
    "verifyToken",
    "rateLimitPerMinute",
    "ipAllowlist",
    "ipDenylist",
    "encryptFields",
    "maskFields",
    "dedupStrategy",
    "dedupWindowHours",
    "dedupCustomHeader",
    "allowedMethods",
)
ClearableSourceField = Literal[
    "description", "provider", "signingSecret", "verifyToken", "rateLimitPerMinute",
    "ipAllowlist", "ipDenylist", "encryptFields", "maskFields", "dedupStrategy",
    "dedupWindowHours", "dedupCustomHeader", "allowedMethods",
    "signing_secret", "verify_token", "rate_limit_per_minute", "ip_allowlist", "ip_denylist",
    "encrypt_fields", "mask_fields", "dedup_strategy", "dedup_window_hours",
    "dedup_custom_header", "allowed_methods",
]


class Source(HookbaseModel):
    """A source as the API returns it.

    The signing secret is not included. Responses carry ``has_signing_secret`` and the last four
    characters; the full value comes back exactly twice, from :meth:`Sources.create` (which
    returns a :class:`SourceWithSecret`) and from :meth:`Sources.reveal_secret`.

    ``has_signing_secret`` being False is not always a problem. Check the two flags beside it:
    ``verifies_without_secret`` (the provider signs with a key Hookbase already holds, as Wise
    and AWS SNS do, so events are verified with nothing set) and ``awaiting_signing_secret``
    (the vendor issues the secret only after the URL is registered with it, as Asana and Notion
    do, and it has not been set yet).
    """

    id: str
    organization_id: str | None = None
    name: str
    slug: str
    #: Any string; see KNOWN_SOURCE_PROVIDERS. Never validated client-side.
    provider: SourceProvider | None = None
    description: str | None = None
    #: Whether a signing secret is set. The secret itself is not returned here.
    has_signing_secret: bool = False
    #: Last four characters of the signing secret, prefixed with "...", or None if unset.
    signing_secret_last4: str | None = None
    #: The provider verifies with a key Hookbase already holds (wise, wise-sandbox, aws-sns), so
    #: there is no secret to set and has_signing_secret stays False on a fully verified source.
    verifies_without_secret: bool = False
    #: The vendor issues the secret only once this source's URL is registered with it (asana,
    #: notion) and it has not been set yet. Events are not verified until it is. For Notion, see
    #: Sources.get_pending_verification.
    awaiting_signing_secret: bool = False
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
        "verifies_without_secret",
        "awaiting_signing_secret",
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

    #: The signing secret, in full, this once. None when the source has none to show: the
    #: provider verifies without one (verifies_without_secret), the vendor issues it after
    #: registration (awaiting_signing_secret), or the provider does not sign.
    signing_secret: str | None = None
    #: Meta providers (whatsapp) only: the verify token to paste into Meta's webhook setup, in
    #: full, this once. Sources.verify_token reveals it later.
    verify_token: str | None = None


class PendingVerification(HookbaseModel):
    """A verification token a vendor delivered to the ingest URL during registration (Notion).

    The request that carried it was unauthenticated, so it is held rather than adopted: paste
    ``token`` into the vendor's verify form, and once the vendor accepts it, call
    :meth:`Sources.adopt_pending_verification` to make it the source's signing secret.
    """

    provider: str
    token: str
    received_at: str
    client_ip: str | None = None


class CreateSourceParams(HookbaseModel):
    name: str
    #: Required: it forms the ingest URL, /ingest/<org>/<slug>, and cannot be changed later.
    slug: str
    provider: SourceProvider | None = None
    description: str | None = None
    #: What to supply depends on the provider (the catalog's signatureVerification.secretSource,
    #: see client.providers.get):
    #:   - "provider": the vendor issues it. Required for several (standard-webhooks and its
    #:     aliases, airtable, gitlab-signing-token, supabase-auth-hooks, jira, discord, sendgrid);
    #:     a missing or malformed one is a 400.
    #:   - "operator": omit it and the API generates one, returned once on the created source.
    #:   - "public_key": the vendor's public key (PEM or base64).
    #:   - "built_in" (wise, wise-sandbox, aws-sns): send nothing; any secret is a 400.
    signing_secret: str | None = None
    #: Meta providers (whatsapp) only; a 400 for any other. Omit it and the API generates one.
    verify_token: str | None = None
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
    #: Meta providers (whatsapp) only. "" regenerates it, as does clear=["verifyToken"].
    verify_token: str | None = None
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

    clear: list[ClearableSourceField] | None = None
    """Fields to send as an explicit JSON null.

    ``None`` on any field above means "leave it alone", so it cannot also mean "remove it".
    Naming a field here sends null for it, which PATCH /api/sources/:id accepts for the fields in
    ``CLEARABLE_SOURCE_FIELDS``::

        client.sources.update("src_1", UpdateSourceParams(clear=["signingSecret"]))
        client.sources.update("src_1", UpdateSourceParams(clear=["verifyToken"]))  # regenerate

    A field that is also set on this model raises rather than the SDK choosing one silently."""


def update_source_body(params: UpdateSourceParams | dict[str, Any]) -> dict[str, Any]:
    """Build the PATCH /api/sources/:id body, turning ``clear`` into explicit nulls."""
    body = _wire.dump(params)
    _wire.apply_clear(body, CLEARABLE_SOURCE_FIELDS, "source")
    return body
