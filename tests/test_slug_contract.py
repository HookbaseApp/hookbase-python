"""The cross-SDK slug contract.

All four SDKs carry this exact table, so a change to any one implementation shows up as a
failure rather than as two SDKs quietly deriving different slugs from the same destination
name. Keep it identical to:

* ``node-sdk/src/__tests__/wire-format.test.ts``      (cross-SDK contract block)
* ``go-sdk/destinations_test.go``                     (``crossSDKSlugCases``)
* ``dotnet-sdk/tests/.../DestinationSlugTests.cs``    (``CrossSdkSlugCases``)

Note Æ/Ø/Đ/Ł do not decompose under NFKD and so are dropped rather than folded
(``Ærø Ømega`` -> ``r-mega``); that is agreed-upon behaviour, not an accident to fix in one
SDK alone.
"""

from __future__ import annotations

import pytest

from hookbase.errors import HookbaseError
from hookbase.models._wire import derive_destination_slug

CROSS_SDK_SLUG_CASES = [
    ("Café EU", "cafe-eu"),
    ("Acme Orders (EU)", "acme-orders-eu"),
    ("My Backend (EU)", "my-backend-eu"),
    ("  spaced  out  ", "spaced-out"),
    ("UPPER CASE", "upper-case"),
    ("ünïcödé nämes", "unicode-names"),
    (
        "a-very-long-destination-name-that-runs-well-past-the-fifty-character-limit",
        "a-very-long-destination-name-that-runs-well-past-t",
    ),
    ("trailing---hyphens---", "trailing-hyphens"),
    ("123 numeric", "123-numeric"),
    ("Ærø Ømega", "r-mega"),
    ("ﬁle ligature", "file-ligature"),
    ("Mixed 123 ABC xyz", "mixed-123-abc-xyz"),
    ("don't stop", "don-t-stop"),
    ("a", "a"),
    # A combining mark outside the U+0300-U+036F block. This row is why the strip is the whole
    # Mn category: with only the block, Node produced "a-b" here while Python and .NET gave "ab".
    ("a\u064db", "ab"),
    ("\u0939\u093f\u0928\u094d\u0926\u0940 name", "name"),
]


@pytest.mark.parametrize(("name", "expected"), CROSS_SDK_SLUG_CASES)
def test_cross_sdk_slug_contract(name: str, expected: str) -> None:
    assert derive_destination_slug(name) == expected


def test_cross_sdk_slug_contract_rejects_a_name_with_no_alphanumerics() -> None:
    with pytest.raises(HookbaseError):
        derive_destination_slug("☃☃☃")


@pytest.mark.parametrize(("name", "expected"), CROSS_SDK_SLUG_CASES)
def test_derived_slugs_match_the_pattern_the_api_requires(name: str, expected: str) -> None:
    import re

    slug = derive_destination_slug(name)
    assert re.fullmatch(r"[a-z0-9-]+", slug), slug
    assert len(slug) <= 50
