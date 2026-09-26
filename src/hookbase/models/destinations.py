from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

from . import _wire
from ._base import HookbaseModel

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
AuthType = Literal["none", "basic", "bearer", "api_key", "custom_header"]
DestinationType = Literal["http", "s3", "r2", "gcs", "azure_blob"]
FileFormat = Literal["json", "jsonl"]
PartitionBy = Literal["date", "hour", "source"]
FieldMappingType = Literal["string", "number", "boolean", "timestamp", "json"]
ThrottleMode = Literal["off", "rate", "concurrency"]
RateUnit = Literal["second", "minute", "hour"]


class FieldMapping(HookbaseModel):
    source: str
    target: str
    type: FieldMappingType
    default: str | None = None


class S3Config(HookbaseModel):
    bucket: str
    region: str
    access_key_id: str
    secret_access_key: str
    prefix: str | None = None
    file_format: FileFormat | None = None
    partition_by: PartitionBy | None = None


class R2Config(HookbaseModel):
    bucket: str
    prefix: str | None = None
    file_format: FileFormat | None = None
    partition_by: PartitionBy | None = None


class GCSConfig(HookbaseModel):
    bucket: str
    project_id: str
    service_account_key: str
    prefix: str | None = None
    file_format: FileFormat | None = None
    partition_by: PartitionBy | None = None


class AzureBlobConfig(HookbaseModel):
    account_name: str
    account_key: str
    container_name: str
    prefix: str | None = None
    file_format: FileFormat | None = None
    partition_by: PartitionBy | None = None


class Throttle(HookbaseModel):
    mode: ThrottleMode = "off"
    rate_limit: int | None = None
    rate_unit: RateUnit | None = None
    max_concurrency: int | None = None
    queue_limit: int | None = None


class Destination(HookbaseModel):
    id: str
    organization_id: str | None = None
    name: str
    slug: str
    type: DestinationType = "http"
    url: str = ""
    method: HttpMethod = "POST"
    headers: dict[str, str] | None = None
    auth_type: str | None = "none"
    auth_config: dict[str, Any] | None = None
    timeout_ms: int = 30000
    throttle: Throttle | None = None
    is_active: bool = True
    use_static_ip: bool = True
    config: dict[str, Any] | None = None
    field_mapping: list[FieldMapping] | None = None
    batch_size: int | None = None
    batch_window_seconds: int | None = None
    delivery_count: int = 0
    last_delivery_at: str | None = None
    created_at: str = ""
    updated_at: str = ""

    # Deprecated response fields. The API returns none of these — destinations
    # have no description or per-destination retry columns, and the request
    # timeout comes back as `timeoutMs` — so `description`/`retry_count`/
    # `retry_interval` are always the defaults below. Kept so existing
    # attribute access keeps working.
    description: str | None = None
    """Deprecated: destinations have no description column."""
    timeout: int = 30000
    """Deprecated: read `timeout_ms` instead. Mirrors it (milliseconds) when
    the response carries no `timeout` of its own."""
    retry_count: int = 3
    """Deprecated: retries are configured per route, not per destination."""
    retry_interval: int = 60
    """Deprecated: retries are configured per route, not per destination."""

    @model_validator(mode="before")
    @classmethod
    def _mirror_timeout(cls, data: Any) -> Any:
        """Keep the deprecated `timeout` field showing the real timeout.

        The API answers with `timeoutMs`; `timeout` is only the old name for
        the same number, so populate it from `timeoutMs` when the response has
        no `timeout` of its own.
        """
        if isinstance(data, dict) and "timeoutMs" in data and "timeout" not in data:
            data = dict(data)
            data["timeout"] = data["timeoutMs"]
        return data

    @model_validator(mode="before")
    @classmethod
    def _normalize_throttle(cls, data: Any) -> Any:
        """Normalize the two response shapes the API uses for throttle data.

        POST /api/destinations (create) and GET /api/destinations/export nest
        throttle fields under a `throttle` object, but GET /api/destinations
        (list) and GET /api/destinations/:id return them as flat top-level
        `throttleMode`/`throttleRateLimit`/`throttleRateUnit`/
        `throttleMaxConcurrency`/`throttleQueueLimit` fields (spread directly
        from the DB row). Fold the flat shape into a nested `throttle` dict
        so both response shapes populate the same field.
        """
        if isinstance(data, dict) and "throttle" not in data and "throttleMode" in data:
            data = dict(data)
            data["throttle"] = {
                "mode": data.pop("throttleMode", None) or "off",
                "rateLimit": data.pop("throttleRateLimit", None),
                "rateUnit": data.pop("throttleRateUnit", None),
                "maxConcurrency": data.pop("throttleMaxConcurrency", None),
                "queueLimit": data.pop("throttleQueueLimit", None),
            }
        return data

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

    @field_validator("config", mode="before")
    @classmethod
    def parse_config(cls, v: Any) -> Any:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, ValueError):
                return None
        return v

    @field_validator("field_mapping", mode="before")
    @classmethod
    def parse_field_mapping(cls, v: Any) -> Any:
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
    """URL-safe identifier, `^[a-z0-9-]+$`, max 50 characters.

    Required by the API. Omit it and one is derived from `name` rather than
    letting the request 400 — pass it explicitly whenever the slug matters,
    since it is part of how the destination is addressed and cannot be changed
    afterwards.
    """
    type: DestinationType | None = None
    url: str | None = None
    method: HttpMethod | None = None
    headers: dict[str, str] | None = None
    """Sent as a mapping — the shape the destinations API takes, unlike
    endpoint headers."""
    auth_type: AuthType | None = None
    auth_config: dict[str, Any] | None = None
    timeout_ms: int | None = None
    """Request timeout in milliseconds, 1000-60000. The API defaults to 30000."""
    throttle: Throttle | None = None
    config: dict[str, Any] | None = None
    field_mapping: list[FieldMapping] | None = None
    use_static_ip: bool | None = None
    batch_size: int | None = None
    batch_window_seconds: int | None = None

    # Deprecated fields; see `create_destination_body` for what each one does
    # on the wire.
    description: str | None = None
    """Deprecated: never accepted by the API and no longer sent; destinations
    have no description column."""
    timeout: int | None = None
    """Deprecated: renamed to `timeout_ms`. The value is sent under that name
    unchanged, and `timeout_ms` wins if both are set.

    Milliseconds, 1000-60000, as everywhere else in this SDK. The value was not
    reaching the API before, so a call that passed seconds here landed on the
    30000 default and now 400s instead; multiply by 1000.
    """
    retry_count: int | None = None
    """Deprecated: never accepted by the API and no longer sent; retries are
    configured per route, not per destination."""
    retry_interval: int | None = None
    """Deprecated: never accepted by the API and no longer sent; retries are
    configured per route, not per destination."""


class UpdateDestinationParams(HookbaseModel):
    name: str | None = None
    url: str | None = None
    method: HttpMethod | None = None
    headers: dict[str, str] | None = None
    auth_type: AuthType | None = None
    auth_config: dict[str, Any] | None = None
    timeout_ms: int | None = None
    """Request timeout in milliseconds, 1000-60000."""
    throttle: Throttle | None = None
    is_active: bool | None = None
    config: dict[str, Any] | None = None
    field_mapping: list[FieldMapping] | None = None
    use_static_ip: bool | None = None
    batch_size: int | None = None
    batch_window_seconds: int | None = None

    # Deprecated fields; see `CreateDestinationParams` for each one's status.
    description: str | None = None
    """Deprecated: never accepted by the API and no longer sent."""
    timeout: int | None = None
    """Deprecated: renamed to `timeout_ms`. The value is sent under that name
    unchanged, and `timeout_ms` wins if both are set.

    Milliseconds, 1000-60000, as everywhere else in this SDK. The value was not
    reaching the API before, so a call that passed seconds here landed on the
    30000 default and now 400s instead; multiply by 1000.
    """
    retry_count: int | None = None
    """Deprecated: never accepted by the API and no longer sent."""
    retry_interval: int | None = None
    """Deprecated: never accepted by the API and no longer sent."""


def _strip_deprecated(body: dict[str, Any]) -> None:
    """Apply the rules shared by destination create and update bodies."""
    _wire.drop(body, "description", "retryCount", "retryInterval")
    _wire.rename(body, "timeout", "timeoutMs")


def create_destination_body(
    params: CreateDestinationParams | dict[str, Any],
) -> dict[str, Any]:
    """Build the request body for `POST /api/destinations`.

    `slug` is required by the API (`^[a-z0-9-]+$`, max 50) but has always been
    optional here, so a request that omits it 400s. Derive one from `name`
    instead of letting that happen; an explicit slug is never rewritten.
    """
    body = _wire.dump(params)
    _strip_deprecated(body)
    slug = body.get("slug")
    if slug is None or (isinstance(slug, str) and not slug.strip()):
        name = body.get("name")
        # A missing or non-string `name` is the API's own `name` error to
        # report, not a slug that could not be derived.
        if isinstance(name, str):
            body["slug"] = _wire.derive_destination_slug(name)
    return body


def update_destination_body(
    params: UpdateDestinationParams | dict[str, Any],
) -> dict[str, Any]:
    """Build the request body for `PATCH /api/destinations/:id`.

    Unlike create, the API takes no `slug` here — a destination's slug cannot
    be changed after it is created.
    """
    body = _wire.dump(params)
    _strip_deprecated(body)
    return body


class TestResult(HookbaseModel):
    success: bool
    # The API answers with `status`/`latencyMs` (api/src/routes/destinations.ts), not the
    # `statusCode`/`duration` that HookbaseModel's to_camel alias_generator would otherwise
    # expect for these field names — override the alias explicitly rather than rely on it.
    status_code: int | None = Field(default=None, alias="status")
    duration: float | None = Field(default=None, alias="latencyMs")
    response_body: str | None = None
    error: str | None = None
