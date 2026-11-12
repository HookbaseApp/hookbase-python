from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import model_validator

from ._base import HookbaseModel

# The engines the API runs (api/src/transforms/catalog.ts; `transforms.engines()` lists them
# live). "mapping" was never one: the API rejects it with a 400. "jq" needs transform isolation on
# the server; without it the API answers TRANSFORM_ENGINE_UNAVAILABLE.
#
# Both aliases accept any string, like MessageStatus, so a transform written in a language added
# after this release still parses instead of failing the whole list() or get() call.
TransformType = Union[
    Literal[
        "jsonata",
        "javascript",
        "typescript",
        "liquid",
        "xslt",
        "jmespath",
        "jsonlogic",
        "jq",
    ],
    str,
]
# The formats the API accepts (VALID_CONTENT_FORMATS in api/src/transforms/validation.ts). "form"
# was never one of them: a transform created with it got a 400.
ContentFormat = Union[Literal["json", "xml", "text"], str]


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
    """The result of `transforms.test`. A transform that fails to run comes back
    with `success` false and `error` set, not as an exception."""

    success: bool
    result: Any = None
    """The transform's output: parsed JSON for JSON output, otherwise a string."""
    content_type: str | None = None
    error: str | None = None

    output: Any = None
    """Deprecated: the API calls this `result`; read `result` instead. Kept in
    step with it so existing attribute access keeps working."""
    execution_time_ms: float | None = None
    """Deprecated: the API does not report execution time; always None."""

    @model_validator(mode="before")
    @classmethod
    def _mirror_result(cls, data: Any) -> Any:
        if isinstance(data, dict) and "result" in data:
            return {**data, "output": data["result"]}
        return data
