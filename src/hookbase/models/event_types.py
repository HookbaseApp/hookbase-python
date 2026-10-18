from __future__ import annotations

import json
from typing import Any

from pydantic import Field, model_validator

from . import _wire
from ._base import HookbaseModel


class EventType(HookbaseModel):
    id: str
    organization_id: str
    name: str
    display_name: str | None = None
    description: str | None = None
    category: str | None = None
    schema_: Any = Field(default=None, alias="schema")
    """The JSON Schema, decoded. The API stores it as JSON, so this is usually a dict."""
    schema_version: int | None = None
    example_payload: Any = None
    documentation_url: str | None = None
    default_priority: int | None = None
    is_enabled: bool = True
    is_deprecated: bool = False
    deprecated_at: str | None = None
    deprecated_message: str | None = None
    is_public: bool = False
    published_at: str | None = None
    subscription_count: int | None = None
    """Set on `list` responses only."""
    created_at: str = ""
    updated_at: str = ""

    is_archived: bool = False
    """Deprecated: not returned by the API; always false. See `is_deprecated`."""

    @model_validator(mode="before")
    @classmethod
    def _decode_json_strings(cls, data: Any) -> Any:
        """Decode `schema`/`examplePayload` if the API returned them as JSON text."""
        if not isinstance(data, dict):
            return data
        out = dict(data)
        for key in ("schema", "examplePayload"):
            value = out.get(key)
            if isinstance(value, str):
                try:
                    out[key] = json.loads(value)
                except ValueError:
                    pass
        return out


class CreateEventTypeParams(HookbaseModel):
    name: str
    display_name: str | None = None
    description: str | None = None
    category: str | None = None
    schema_: dict[str, Any] | str | None = Field(default=None, alias="schema")
    """A JSON Schema, as a dict or as JSON text."""
    example_payload: Any = None
    """An example payload, as a value or as JSON text."""
    documentation_url: str | None = None
    is_enabled: bool | None = None
    default_priority: int | None = None


class UpdateEventTypeParams(HookbaseModel):
    display_name: str | None = None
    description: str | None = None
    category: str | None = None
    schema_: dict[str, Any] | str | None = Field(default=None, alias="schema")
    """A JSON Schema, as a dict or as JSON text."""
    example_payload: Any = None
    """An example payload, as a value or as JSON text."""
    documentation_url: str | None = None
    is_enabled: bool | None = None
    is_deprecated: bool | None = None
    deprecated_message: str | None = None
    is_public: bool | None = None
    default_priority: int | None = None


def event_type_body(
    params: CreateEventTypeParams | UpdateEventTypeParams | dict[str, Any],
) -> dict[str, Any]:
    """Build the body for `POST /api/event-types` or `PATCH /api/event-types/:id`.

    The API validates `schema` and `examplePayload` as JSON *strings*
    (`z.string()` in event-types.ts) and its schemas are `.strict()`, so a dict
    there is a 400. Serialize anything that is not already a string.
    """
    body = _wire.dump(params)
    _wire.canonicalize(body, "examplePayload")
    if "schema_" in body:
        body.setdefault("schema", body.pop("schema_"))
    for key in ("schema", "examplePayload"):
        value = body.get(key)
        if value is not None and not isinstance(value, str):
            body[key] = json.dumps(value)
    return body
