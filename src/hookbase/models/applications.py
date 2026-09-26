from __future__ import annotations

from typing import Any

from pydantic import model_validator

from . import _wire
from ._base import HookbaseModel


class Application(HookbaseModel):
    id: str
    name: str
    organization_id: str
    external_id: str = ""
    metadata: dict[str, Any] | None = None
    created_at: str = ""
    updated_at: str = ""

    uid: str = ""
    """Deprecated: the API calls this `externalId`; read `external_id` instead.
    Kept in step with it so existing attribute access keeps working."""

    @model_validator(mode="before")
    @classmethod
    def _mirror_external_id(cls, data: Any) -> Any:
        """Keep `uid` and `external_id` showing the same value.

        Application responses carry the field as `externalId`; `uid` is only
        the SDK's older name for it, so populate both from whichever spelling
        the response used. `externalId` is null for applications created
        without one, so fall back to the empty string both fields default to.
        """
        if not isinstance(data, dict):
            return data
        value = data.get("externalId")
        if value is None:
            value = data.get("external_id")
        if value is None:
            value = data.get("uid")
        return {**data, "externalId": value or "", "uid": value or ""}


class CreateApplicationParams(HookbaseModel):
    name: str
    external_id: str | None = None
    metadata: dict[str, Any] | None = None

    uid: str | None = None
    """Deprecated: renamed to `external_id`, which is the only name the API
    accepts. The value is sent under that name, and `external_id` wins if both
    are set."""


class UpdateApplicationParams(HookbaseModel):
    name: str | None = None
    metadata: dict[str, Any] | None = None


def application_body(params: CreateApplicationParams | dict[str, Any]) -> dict[str, Any]:
    """Build the request body for an application create or upsert.

    The API has always called the caller's own identifier `externalId`; the SDK
    sent `uid`, which `z.object()` stripped, so every application the Python
    SDK created came back with no external ID at all. Map the old name onto the
    new one the way the Node SDK already does.
    """
    body = _wire.dump(params)
    _wire.rename(body, "uid", "externalId")
    return body
