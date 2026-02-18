from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import field_validator

from ._base import HookbaseModel

SourceProvider = Literal[
    "generic", "github", "stripe", "shopify", "slack", "twilio",
    "sendgrid", "mailgun", "paddle", "linear", "svix", "custom",
]
DedupStrategy = Literal["none", "header", "payload_hash", "event_id"]
IpFilterMode = Literal["none", "allowlist", "denylist"]


class Source(HookbaseModel):
    id: str
    organization_id: str | None = None
    name: str
    slug: str
    description: str | None = None
    provider: SourceProvider = "generic"
    is_active: bool = True
    signing_secret: str | None = None
    ingest_url: str | None = None
    verify_signature: bool = False
    dedup_strategy: str | None = "none"
    dedup_window: int | None = None
    dedup_header_name: str | None = None
    ip_filter_mode: IpFilterMode = "none"
    ip_allowlist: list[str] | None = None
    ip_denylist: list[str] | None = None
    rate_limit: int | None = None
    rate_limit_window: int | None = None
    event_count: int = 0
    last_event_at: str | None = None
    created_at: str = ""
    updated_at: str = ""

    @field_validator("is_active", "verify_signature", mode="before")
    @classmethod
    def parse_bool_from_int(cls, v: Any) -> Any:
        if isinstance(v, int):
            return bool(v)
        return v

    @field_validator("ip_allowlist", "ip_denylist", mode="before")
    @classmethod
    def parse_json_list(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                return parsed if isinstance(parsed, list) else None
            except (json.JSONDecodeError, ValueError):
                return None
        return v


class SourceWithSecret(Source):
    signing_secret: str = ""


class CreateSourceParams(HookbaseModel):
    name: str
    slug: str | None = None
    description: str | None = None
    provider: SourceProvider | None = None
    verify_signature: bool | None = None
    dedup_strategy: DedupStrategy | None = None
    dedup_window: int | None = None
    dedup_header_name: str | None = None
    ip_filter_mode: IpFilterMode | None = None
    ip_allowlist: list[str] | None = None
    ip_denylist: list[str] | None = None
    rate_limit: int | None = None
    rate_limit_window: int | None = None


class UpdateSourceParams(HookbaseModel):
    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    verify_signature: bool | None = None
    dedup_strategy: DedupStrategy | None = None
    dedup_window: int | None = None
    dedup_header_name: str | None = None
    ip_filter_mode: IpFilterMode | None = None
    ip_allowlist: list[str] | None = None
    ip_denylist: list[str] | None = None
    rate_limit: int | None = None
    rate_limit_window: int | None = None
