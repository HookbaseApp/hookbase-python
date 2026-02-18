from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import field_validator

from ._base import HookbaseModel

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
AuthType = Literal["none", "basic", "bearer", "api_key", "custom_header"]


class Destination(HookbaseModel):
    id: str
    organization_id: str | None = None
    name: str
    slug: str
    description: str | None = None
    url: str
    method: HttpMethod = "POST"
    headers: dict[str, str] | None = None
    auth_type: str | None = "none"
    auth_config: dict[str, Any] | None = None
    timeout: int = 30
    retry_count: int = 3
    retry_interval: int = 60
    rate_limit: int | None = None
    rate_limit_window: int | None = None
    is_active: bool = True
    delivery_count: int = 0
    last_delivery_at: str | None = None
    created_at: str = ""
    updated_at: str = ""

    @field_validator("headers", mode="before")
    @classmethod
    def parse_headers(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return None
        return v

    @field_validator("auth_config", mode="before")
    @classmethod
    def parse_auth_config(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return None
        return v

    @field_validator("is_active", mode="before")
    @classmethod
    def parse_is_active(cls, v: Any) -> Any:
        if isinstance(v, int):
            return bool(v)
        return v


class CreateDestinationParams(HookbaseModel):
    name: str
    slug: str | None = None
    description: str | None = None
    url: str
    method: HttpMethod | None = None
    headers: dict[str, str] | None = None
    auth_type: AuthType | None = None
    auth_config: dict[str, Any] | None = None
    timeout: int | None = None
    retry_count: int | None = None
    retry_interval: int | None = None
    rate_limit: int | None = None
    rate_limit_window: int | None = None


class UpdateDestinationParams(HookbaseModel):
    name: str | None = None
    description: str | None = None
    url: str | None = None
    method: HttpMethod | None = None
    headers: dict[str, str] | None = None
    auth_type: AuthType | None = None
    auth_config: dict[str, Any] | None = None
    timeout: int | None = None
    retry_count: int | None = None
    retry_interval: int | None = None
    rate_limit: int | None = None
    rate_limit_window: int | None = None
    is_active: bool | None = None


class TestResult(HookbaseModel):
    success: bool
    status_code: int | None = None
    duration: float | None = None
    response_body: str | None = None
    error: str | None = None
