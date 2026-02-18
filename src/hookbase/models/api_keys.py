from __future__ import annotations

import json
from typing import Any

from pydantic import field_validator

from ._base import HookbaseModel


class ApiKey(HookbaseModel):
    id: str
    name: str
    key_prefix: str = ""
    scopes: list[str] = []
    is_disabled: bool = False

    @field_validator("scopes", mode="before")
    @classmethod
    def _parse_scopes(cls, v: Any) -> Any:
        if isinstance(v, str):
            return json.loads(v)
        return v
    last_used_at: str | None = None
    expires_at: str | None = None
    created_at: str = ""


class ApiKeyWithSecret(ApiKey):
    key: str = ""


class CreateApiKeyParams(HookbaseModel):
    name: str
    scopes: list[str] | None = None
    expires_in: int | None = None
