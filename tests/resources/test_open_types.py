"""Destination and transform types the API adds later must not break list() and get().

`DestinationType`, `TransformType` and `ContentFormat` were closed Literals, so one sqs or bridge
destination, or one transform in a language newer than this package, made the whole page fail to
validate. They now accept any string, the way `MessageStatus` does.
"""

from __future__ import annotations

from typing import get_args

import pytest

from hookbase.models import (
    ContentFormat,
    Destination,
    DestinationType,
    Transform,
    TransformType,
)

from ..conftest import make_paginated_response

# DESTINATION_TYPES in api/src/routes/destinations.ts.
DESTINATION_TYPES = [
    "http", "sqs", "eventbridge", "servicebus", "pubsub", "oci_queue",
    "s3", "r2", "gcs", "azure_blob", "bridge",
]
# TRANSFORM_CATALOG in api/src/transforms/catalog.ts.
TRANSFORM_TYPES = [
    "jsonata", "javascript", "typescript", "liquid", "xslt", "jmespath", "jsonlogic", "jq",
]
FUTURE = "some_future_type"


def _dest(i: int, dest_type: str) -> dict[str, object]:
    return {"id": f"dst_{i}", "name": f"D{i}", "slug": f"d{i}", "type": dest_type,
            "url": "" if dest_type != "http" else "https://x.test"}


def _transform(i: int, transform_type: str, fmt: str = "json") -> dict[str, object]:
    return {"id": f"trn_{i}", "name": f"T{i}", "slug": f"t{i}", "code": "$",
            "transformType": transform_type, "inputFormat": fmt, "outputFormat": fmt}


@pytest.mark.parametrize("dest_type", [*DESTINATION_TYPES, FUTURE])
def test_destination_of_every_type_parses(dest_type):
    assert Destination.model_validate(_dest(1, dest_type)).type == dest_type


@pytest.mark.parametrize("transform_type", [*TRANSFORM_TYPES, FUTURE])
def test_transform_of_every_type_parses(transform_type):
    assert Transform.model_validate(_transform(1, transform_type)).transform_type == transform_type


def test_destinations_list_with_every_type(mock_api, client):
    types = [*DESTINATION_TYPES, FUTURE]
    mock_api.get("/api/destinations").respond(200, json=make_paginated_response(
        [_dest(i, t) for i, t in enumerate(types)], data_key="destinations",
    ))
    assert [d.type for d in client.destinations.list().data] == types


def test_destination_get_of_a_bridge(mock_api, client):
    mock_api.get("/api/destinations/dst_1").respond(200, json={"destination": _dest(1, "bridge")})
    assert client.destinations.get("dst_1").type == "bridge"


async def test_async_transforms_list_with_every_type(mock_api, async_client):
    types = [*TRANSFORM_TYPES, FUTURE]
    mock_api.get("/api/transforms").respond(200, json=make_paginated_response(
        [_transform(i, t) for i, t in enumerate(types)], data_key="transforms",
    ))
    page = await async_client.transforms.list()
    assert [t.transform_type for t in page.data] == types


def test_transform_with_an_unknown_content_format_parses():
    t = Transform.model_validate(_transform(1, "jsonata", fmt="yaml"))
    assert (t.input_format, t.output_format) == ("yaml", "yaml")


def test_known_values_match_the_api():
    known = {name: set(get_args(get_args(alias)[0])) for name, alias in (
        ("DestinationType", DestinationType),
        ("TransformType", TransformType),
        ("ContentFormat", ContentFormat),
    )}
    assert known == {
        "DestinationType": set(DESTINATION_TYPES),
        "TransformType": set(TRANSFORM_TYPES),
        # "form" was never accepted by the API.
        "ContentFormat": {"json", "xml", "text"},
    }
