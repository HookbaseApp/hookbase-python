from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import Field, field_validator, model_validator

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
    description: str | None = None
    type: DestinationType = "http"
    url: str = ""
    method: HttpMethod = "POST"
    headers: dict[str, str] | None = None
    auth_type: str | None = "none"
    auth_config: dict[str, Any] | None = None
    timeout: int = 30
    retry_count: int = 3
    retry_interval: int = 60
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
    description: str | None = None
    type: DestinationType | None = None
    url: str | None = None
    method: HttpMethod | None = None
    headers: dict[str, str] | None = None
    auth_type: AuthType | None = None
    auth_config: dict[str, Any] | None = None
    timeout: int | None = None
    retry_count: int | None = None
    retry_interval: int | None = None
    throttle: Throttle | None = None
    config: dict[str, Any] | None = None
    field_mapping: list[FieldMapping] | None = None
    use_static_ip: bool | None = None
    batch_size: int | None = None
    batch_window_seconds: int | None = None


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
    throttle: Throttle | None = None
    is_active: bool | None = None
    config: dict[str, Any] | None = None
    field_mapping: list[FieldMapping] | None = None
    use_static_ip: bool | None = None
    batch_size: int | None = None
    batch_window_seconds: int | None = None


class TestResult(HookbaseModel):
    success: bool
    # The API answers with `status`/`latencyMs` (api/src/routes/destinations.ts), not the
    # `statusCode`/`duration` that HookbaseModel's to_camel alias_generator would otherwise
    # expect for these field names — override the alias explicitly rather than rely on it.
    status_code: int | None = Field(default=None, alias="status")
    duration: float | None = Field(default=None, alias="latencyMs")
    response_body: str | None = None
    error: str | None = None
