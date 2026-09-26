"""The cross-SDK slug contract.

All four SDKs carry this exact table, so a change to any one implementation shows up as a
failure rather than as two SDKs quietly deriving different slugs from the same destination
name. Keep it identical to:

* ``node-sdk/src/__tests__/wire-format.test.ts``  (cross-SDK contract block)
* ``go-sdk/destinations_fields_test.go``          (``crossSDKSlugCases``)
* ``dotnet-sdk/tests/Hookbase.Tests/DestinationRequestSerializationTests.cs``
  (``CrossSdkSlugCases``)

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
    ("\u05d0\u05b8 hebrew", "hebrew"),
    # The rows below are the cases where the four implementations can disagree for reasons that
    # have nothing to do with the algorithm, so they are the ones worth pinning. Each was run
    # against all four before being written down.
    #
    # Not marks themselves (both are Lm) but their NFKD is one, so decomposing before stripping
    # makes them vanish rather than separate. Go folds per rune and needed an explicit empty fold
    # to match.
    ("a\uff9eb", "ab"),
    ("a\uff9fb", "ab"),
    # Mn only from Unicode 16, so an interpreter on 15.0 does not strip it without
    # _SLUG_MARK_ADDITIONS.
    ("a\u1acfb", "ab"),
    # The same, outside the BMP: .NET read this as two surrogate halves, neither of them a mark.
    ("a\U0001e5eeb", "ab"),
    # The other direction: Mn in Unicode 15.0 and Mc from 15.1. A spacing mark separates.
    ("a\U0001171eb", "a-b"),
    # Unassigned before Unicode 16, where it decomposes to "A". Without _SLUG_FOLD_ADDITIONS an
    # older interpreter leaves it alone and it separates instead.
    ("a\U0001ccd6b", "aab"),
    # A noncharacter: separates, and must not raise. .NET's Normalize rejects these outright.
    ("a\ufffeb", "a-b"),
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


# The 75 marks the reference runtime strips that Unicode 15.0 does not know, spelled out
# independently of the implementation's own table so a typo in one range shows up as a failure
# rather than as a slug that quietly differs from the other SDKs'. Same list, same order as
# ``_SLUG_MARK_ADDITIONS``, ``slugMarkAdditions`` (Go), ``SlugMarkAdditions`` (.NET) and
# ``SLUG_MARKS``' explicit half (Node).
NEWER_UNICODE_MARKS = (
    "0897 1ACF-1ADD 1AE0-1AEB 10D69-10D6D 10EFA-10EFC 113BB-113C0 113CE 113D0 113D2 "
    "113E1-113E2 11B60 11B62-11B64 11B66 11F5A 1611E-16129 1612D-1612F 1E5EE-1E5EF 1E6E3 "
    "1E6E6 1E6EE-1E6EF 1E6F5"
)


def _newer_unicode_marks() -> list[str]:
    marks = []
    for span in NEWER_UNICODE_MARKS.split():
        low, _, high = span.partition("-")
        for code_point in range(int(low, 16), int(high or low, 16) + 1):
            marks.append(chr(code_point))
    return marks


def test_marks_a_newer_unicode_added_are_still_stripped() -> None:
    """A mark this interpreter's tables predate has to fold away, not become a separator."""
    marks = _newer_unicode_marks()
    assert len(marks) == 75, len(marks)
    for mark in marks:
        assert derive_destination_slug(f"a{mark}b") == "ab", f"U+{ord(mark):04X}"


def test_the_mark_table_reports_when_it_becomes_redundant() -> None:
    """Once this interpreter's own category data covers every addition, the table can go."""
    import unicodedata

    uncovered = [m for m in _newer_unicode_marks() if unicodedata.category(m) != "Mn"]
    if not uncovered:
        pytest.fail(
            "unicodedata is now "
            f"{unicodedata.unidata_version} and classifies all 75 additions as Mn: "
            "_SLUG_MARK_ADDITIONS is redundant and can be deleted, here and in the other SDKs"
        )


def test_characters_a_newer_unicode_decomposes_to_ascii_fold_the_same_way() -> None:
    """U+A7F1 and the 36 contiguous additions from U+1CCD6, which older tables do not know.

    Spelled out here rather than read off ``_SLUG_FOLD_ADDITIONS`` so an off-by-one in the
    alphabet is a failure instead of a slug that differs from the other SDKs'.
    """
    assert derive_destination_slug("a꟱b") == "asb"

    alphabet = "abcdefghijklmnopqrstuvwxyz0123456789"
    for offset, expected in enumerate(alphabet):
        char = chr(0x1CCD6 + offset)
        assert derive_destination_slug(f"a{char}b") == f"a{expected}b", f"U+{ord(char):04X}"
