from __future__ import annotations

from typing import Any

from ._base import HookbaseModel


class SchemaRoute(HookbaseModel):
    id: str
    name: str


class Schema(HookbaseModel):
    id: str
    organization_id: str | None = None
    name: str
    slug: str
    description: str | None = None
    json_schema: Any = None
    version: int = 1
    routes: list[SchemaRoute] | None = None
    created_at: str = ""
    updated_at: str = ""


class CreateSchemaParams(HookbaseModel):
    name: str
    slug: str | None = None
    description: str | None = None
    json_schema: dict[str, Any]


class UpdateSchemaParams(HookbaseModel):
    name: str | None = None
    description: str | None = None
    json_schema: dict[str, Any] | None = None


class SchemaValidationError(HookbaseModel):
    path: str = ""
    """Where in the payload the problem is: a dotted path such as ``customer.email``, or
    ``root`` for the payload itself."""
    message: str


class SchemaValidationResult(HookbaseModel):
    """``schemas.validate()``: whether the payload matches the schema, and why not."""

    valid: bool
    errors: list[SchemaValidationError] = []
