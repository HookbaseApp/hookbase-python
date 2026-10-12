"""The public provider catalog: GET /api/catalog/providers (no authentication needed).

Every enumerated value here (category, kind, secret_source, secret_format) is a plain string
rather than a Literal, for the reason ``SourceProvider`` is: the catalog grows server-side, and a
value this package has not heard of must not make the whole response fail to parse.
"""

from __future__ import annotations

from typing import Any

from pydantic import field_validator

from ._base import HookbaseModel


class ProviderEventType(HookbaseModel):
    type: str
    description: str = ""


class ProviderVerifyTokenInfo(HookbaseModel):
    """Meta's second, Hookbase-generated credential (see SourceWithSecret.verify_token)."""

    label: str
    instruction: str = ""


class ProviderSignatureVerificationSummary(HookbaseModel):
    """The secret fields a create flow needs, as the catalog list carries them.

    ``secret_source`` says who produces the credential: "provider" (the vendor issues it; paste
    it as signing_secret), "operator" (Hookbase generates it when omitted; paste it into the
    vendor), "public_key" (paste the vendor's public key), "built_in" (nothing to enter; events
    are still verified) or "none" (the vendor does not sign).
    """

    supported: bool = False
    #: The scheme kind: "hmac", "shared_secret", "bespoke" or "asymmetric". None when no scheme.
    kind: str | None = None
    secret_source: str | None = None
    secret_label: str | None = None
    secret_placeholder: str | None = None
    #: The vendor issues the secret only after the source's URL is registered with it.
    secret_after_registration: bool = False


class ProviderSignatureVerification(ProviderSignatureVerificationSummary):
    """The full block from the provider detail call."""

    algorithm: str | None = None
    header_name: str | None = None
    secret_location_hint: str | None = None
    #: One sentence on where the value comes from or goes, in the vendor's own UI wording.
    secret_instruction: str | None = None
    #: "whsec" or "basic_auth" when the value has a required shape.
    secret_format: str | None = None
    #: Present for Meta providers, which also use a verify token.
    verify_token: ProviderVerifyTokenInfo | None = None


class CatalogProvider(HookbaseModel):
    """A provider as the catalog list returns it.

    ``id`` is the catalog's id; ``hookbase_provider`` is the value to use as a source's
    ``provider``. They differ for some entries (catalog "mollie-nextgen" is provider "mollie",
    and several catalog entries map to "custom").
    """

    id: str
    name: str
    category: str = ""
    description: str = ""
    icon: str | None = None
    event_type_count: int = 0
    hookbase_provider: str = ""
    has_signature_verification: bool = False
    has_ip_ranges: bool = False
    #: None when the provider has no verification block, and also from API versions that
    #: predate this summary on list items: fall back to client.providers.get(id) for it.
    signature_verification: ProviderSignatureVerificationSummary | None = None


class ProviderCatalogList(HookbaseModel):
    providers: list[CatalogProvider] = []
    categories: list[str] = []
    total: int = 0


class CatalogProviderDetail(HookbaseModel):
    """One provider in full, from GET /api/catalog/providers/:id."""

    id: str
    name: str
    category: str = ""
    description: str = ""
    website: str | None = None
    docs_url: str | None = None
    icon: str | None = None
    hookbase_provider: str = ""
    signature_verification: ProviderSignatureVerification | None = None
    event_types: list[ProviderEventType] = []
    #: Example payloads keyed by event type.
    sample_payloads: dict[str, Any] = {}
    ip_ranges: list[str] | None = None
    setup_guide: list[str] = []

    @field_validator("event_types", "setup_guide", mode="before")
    @classmethod
    def _none_to_list(cls, v: Any) -> Any:
        return [] if v is None else v


class ProviderEvents(HookbaseModel):
    """GET /api/catalog/providers/:id/events."""

    provider_id: str
    provider_name: str = ""
    event_types: list[ProviderEventType] = []
    sample_payloads: dict[str, Any] = {}
