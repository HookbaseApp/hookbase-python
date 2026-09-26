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

# Which characters count as combining marks is a function of the Unicode version the *runtime*
# ships, and the four SDKs' runtimes do not agree: CPython 3.12's `unicodedata` is Unicode 15.0,
# while the reference implementation's `\p{Mn}` (V8) is a version ahead. Reading the category alone
# therefore makes the same name slug differently depending on which SDK created the destination,
# which is the thing this derivation exists to prevent.
#
# These two tables close that gap, generated from the reference runtime's own `\p{Mn}` compared
# against Unicode 15.0's. Both self-heal: once this interpreter's tables cover the additions, the
# set is redundant but harmless, and `test_slug_contract.py` says so when that happens.
#
# 75 code points in 21 ranges, the same table `slugMarkAdditions` carries in
# sdk/go-sdk/slug_fold.go. Change one and you change both.
_SLUG_MARK_ADDITIONS: frozenset[str] = frozenset(
    chr(cp)
    for lo, hi in (
        ("\u0897", "\u0897"),
        ("\u1acf", "\u1add"),
        ("\u1ae0", "\u1aeb"),
        ("\U00010d69", "\U00010d6d"),
        ("\U00010efa", "\U00010efc"),
        ("\U000113bb", "\U000113c0"),
        ("\U000113ce", "\U000113ce"),
        ("\U000113d0", "\U000113d0"),
        ("\U000113d2", "\U000113d2"),
        ("\U000113e1", "\U000113e2"),
        ("\U00011b60", "\U00011b60"),
        ("\U00011b62", "\U00011b64"),
        ("\U00011b66", "\U00011b66"),
        ("\U00011f5a", "\U00011f5a"),
        ("\U0001611e", "\U00016129"),
        ("\U0001612d", "\U0001612f"),
        ("\U0001e5ee", "\U0001e5ef"),
        ("\U0001e6e3", "\U0001e6e3"),
        ("\U0001e6e6", "\U0001e6e6"),
        ("\U0001e6ee", "\U0001e6ef"),
        ("\U0001e6f5", "\U0001e6f5"),
    )
    for cp in range(ord(lo), ord(hi) + 1)
)

# The correction in the other direction: AHOM CONSONANT SIGN MEDIAL RA was Mn in Unicode 15.0 and
# is Mc (a *spacing* mark) from 15.1, so the reference does not strip it and neither may this
# SDK -- it has to separate, the way any other non-alphanumeric does.
_SLUG_MARK_RECLASSIFIED = "\U0001171e"


# The same version skew, one layer down: NFKD itself. These characters are unassigned in Unicode
# 15.0, so this interpreter leaves them alone and they become hyphen separators, while the
# reference runtime decomposes them to ASCII letters and digits. Folding them first makes NFKD's
# answer the same on both. Every mapping is the reference's own NFKD output, not a guess at the
# character's meaning; a later interpreter that knows them decomposes them identically, so this
# stays a no-op rather than a divergence of its own.
#
#   U+A7F1              Latin Extended-D, decomposes to "S"
#   U+1CCD6 - U+1CCF9   36 contiguous additions in Symbols for Legacy Computing Supplement,
#                       decomposing to A-Z and then 0-9 in order
_SLUG_FOLD_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
_SLUG_FOLD_ADDITIONS = {
    0xA7F1: "S",
    **{0x1CCD6 + offset: char for offset, char in enumerate(_SLUG_FOLD_ALPHABET)},
}


def _is_slug_mark(char: str) -> bool:
    """Whether `char` is a combining mark the slug fold drops. See the tables above."""
    if char == _SLUG_MARK_RECLASSIFIED:
        return False
    return unicodedata.category(char) == "Mn" or char in _SLUG_MARK_ADDITIONS


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
    # `_is_slug_mark` rather than the category alone, because the category answer depends on this
    # interpreter's Unicode version -- see the tables above it.
    decomposed = unicodedata.normalize("NFKD", name.translate(_SLUG_FOLD_ADDITIONS))
    folded = "".join(ch for ch in decomposed if not _is_slug_mark(ch)).lower()
    slug = _SLUG_EDGE_HYPHENS.sub("", _SLUG_SEPARATORS.sub("-", folded))
    slug = _SLUG_TRAILING_HYPHENS.sub("", slug[:SLUG_MAX_LENGTH])

    if not slug:
        raise HookbaseError(
            "Cannot derive a destination slug from name "
            f"{json.dumps(name, ensure_ascii=False)}: pass "
            "`slug` explicitly, as a string matching ^[a-z0-9-]+$ (max 50 characters)."
        )

    return slug
