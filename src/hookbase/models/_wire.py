"""Normalization of request bodies onto the shapes the API actually accepts.

The SDK has historically put field names on the wire that the API never
accepted (endpoint `filterTypes`/`rateLimitPeriod`/`metadata`, destination
`description`/`retryCount`/`retryInterval`) alongside a few it renamed
(`rateLimit` -> `rateLimitPerSecond`, `timeout` -> `timeoutMs`, `uid` ->
`externalId`). The API validates with `z.object()`, which silently strips
unknown keys, so those requests came back 2xx with the field quietly ignored —
and the resource configured differently from what the caller asked for. Those
schemas are moving to `.strict()`, at which point the same requests become
400s.

Deleting the public fields would break callers, so the models keep them,
document them as deprecated, and these helpers translate them at the wire
boundary. They deliberately operate on the already-serialized body rather than
on the model, so a caller who passes a plain dict — which every resource method
accepts, and which skips model validation entirely — gets the same translation.
"""

from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from ..errors import HookbaseError

# Params models serialize through `to_camel`, but `populate_by_name` means a
# caller may also use the snake_case field name, and a caller passing a plain
# dict can put that spelling straight on the wire.
_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")

# Slug derivation mirrors `deriveDestinationSlug` in
# sdk/node-sdk/src/resources/wire.ts step for step, so all four SDKs derive
# byte-identical slugs from the same name. Keep the two in sync.

_SLUG_SEPARATORS = re.compile(r"[^a-z0-9]+")
_SLUG_EDGE_HYPHENS = re.compile(r"^-+|-+$")
_SLUG_TRAILING_HYPHENS = re.compile(r"-+$")
SLUG_MAX_LENGTH = 50


def dump(params: Any) -> dict[str, Any]:
    """Serialize a params model into a wire body, or copy a caller's dict.

    The copy matters: these helpers mutate the body in place and callers hand
    us dicts they may reuse.
    """
    if hasattr(params, "model_dump"):
        body: dict[str, Any] = params.model_dump(by_alias=True, exclude_none=True)
        return body
    return dict(params or {})


def _spellings(key: str) -> tuple[str, ...]:
    """Every spelling of one wire key a caller may have used."""
    snake = _CAMEL_BOUNDARY.sub("_", key).lower()
    return (key,) if snake == key else (key, snake)


def drop(body: dict[str, Any], *keys: str) -> None:
    """Remove keys the API never accepted."""
    for key in keys:
        for spelling in _spellings(key):
            body.pop(spelling, None)


def canonicalize(body: dict[str, Any], *keys: str) -> None:
    """Move any snake_case spelling of `keys` onto its camelCase wire key."""
    for key in keys:
        for spelling in _spellings(key)[1:]:
            if spelling in body:
                body.setdefault(key, body.pop(spelling))


def rename(body: dict[str, Any], old: str, new: str) -> None:
    """Send `old`'s value under `new`; an explicit `new` wins over `old`."""
    canonicalize(body, new)
    value: Any = None
    found = False
    for spelling in _spellings(old):
        if spelling in body:
            if not found:
                value = body[spelling]
                found = True
            del body[spelling]
    if found and new not in body:
        body[new] = value


def headers_to_pairs(body: dict[str, Any]) -> None:
    """Convert endpoint `headers` from a mapping to the array the API takes.

    `POST`/`PATCH /api/webhook-endpoints` validate headers as
    `z.array({name, value}).max(10)`, so the mapping the SDK has always typed
    here is rejected outright — a 400 today rather than a silently stripped
    field. A mapping is converted in insertion order; an array a caller built
    themselves passes through untouched.
    """
    value = body.get("headers")
    if isinstance(value, dict):
        body["headers"] = [{"name": str(name), "value": str(v)} for name, v in value.items()]


def derive_destination_slug(name: str) -> str:
    """Derive a slug the API accepts (`^[a-z0-9-]+$`, max 50) from a name.

    The API requires `slug` on create; this SDK has always had it optional, so
    every call that left it out was a 400. Deriving one keeps those calls
    working. Accents are folded first, so `Café EU` gives `cafe-eu` rather than
    `caf-eu`.

    Every step mirrors `deriveDestinationSlug` in the Node SDK
    (sdk/node-sdk/src/resources/wire.ts) so all four SDKs agree byte for byte:
    NFKD normalize, drop the combining marks the decomposition leaves behind,
    lowercase, collapse each run of non-alphanumerics to one hyphen, trim the
    ends, then cut to 50 characters. The cut is plain and may land mid-word —
    that is what keeps the implementations identical, so do not trim back to a
    word boundary — and can leave a trailing hyphen to remove.

    Raises:
        HookbaseError: if the name has no alphanumeric characters to derive
            from, rather than sending a slug the API would reject.
    """
    # Drop the whole Mn category, not just the U+0300-U+036F block: a mark outside that block
    # (Arabic, Hebrew, Devanagari) would otherwise survive to become a hyphen separator, and the
    # same name would slug differently depending on which SDK created the destination.
    decomposed = unicodedata.normalize("NFKD", name)
    folded = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn").lower()
    slug = _SLUG_EDGE_HYPHENS.sub("", _SLUG_SEPARATORS.sub("-", folded))
    slug = _SLUG_TRAILING_HYPHENS.sub("", slug[:SLUG_MAX_LENGTH])

    if not slug:
        raise HookbaseError(
            "Cannot derive a destination slug from name "
            f"{json.dumps(name, ensure_ascii=False)}: pass "
            "`slug` explicitly, as a string matching ^[a-z0-9-]+$ (max 50 characters)."
        )

    return slug
