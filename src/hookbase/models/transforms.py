from __future__ import annotations

from typing import Any, Literal

from ._base import HookbaseModel

TransformType = Literal["jsonata", "javascript", "mapping", "liquid", "xslt"]
ContentFormat = Literal["json", "xml", "form", "text"]


class Transform(HookbaseModel):
    id: str
    organization_id: str | None = None
    name: str
    slug: str
    description: str | None = None
    transform_type: TransformType = "jsonata"
    code: str = ""
    input_format: ContentFormat = "json"
    output_format: ContentFormat = "json"
    version: int = 1
    created_at: str = ""
    updated_at: str = ""


class CreateTransformParams(HookbaseModel):
    name: str
    slug: str | None = None
    description: str | None = None
    transform_type: TransformType
    code: str
    input_format: ContentFormat | None = None
    output_format: ContentFormat | None = None


class UpdateTransformParams(HookbaseModel):
    name: str | None = None
    description: str | None = None
    transform_type: TransformType | None = None
    code: str | None = None
    input_format: ContentFormat | None = None
    output_format: ContentFormat | None = None


class TransformTestResult(HookbaseModel):
    success: bool
    output: Any = None
    error: str | None = None
    execution_time_ms: float | None = None
