from __future__ import annotations

import json
from typing import Any, Literal

from pydantic import field_validator

from ._base import HookbaseModel

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
AuthType = Literal["none", "basic", "bearer", "api_key", "custom_header"]
DestinationType = Literal["http", "s3", "r2", "gcs", "azure_blob"]
FileFormat = Literal["json", "jsonl"]
PartitionBy = Literal["date", "hour", "source"]
FieldMappingType = Literal["string", "number", "boolean", "timestamp", "json"]


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
    rate_limit: int | None = None
    rate_limit_window: int | None = None
    is_active: bool = True
    config: dict[str, Any] | None = None
    field_mapping: list[FieldMapping] | None = None
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
    rate_limit: int | None = None
    rate_limit_window: int | None = None
    config: dict[str, Any] | None = None
    field_mapping: list[FieldMapping] | None = None


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
    config: dict[str, Any] | None = None
    field_mapping: list[FieldMapping] | None = None


class TestResult(HookbaseModel):
    success: bool
    status_code: int | None = None
    duration: float | None = None
    response_body: str | None = None
    error: str | None = None
