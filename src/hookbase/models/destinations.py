from __future__ import annotations

import json
from typing import Any, Literal, Union

from pydantic import Field, field_validator, model_validator

from . import _wire
from ._base import SECRET_MODEL_CONFIG, HookbaseModel

HttpMethod = Literal["GET", "POST", "PUT", "PATCH", "DELETE"]
AuthType = Literal["none", "basic", "bearer", "api_key", "custom_header"]
# Every destination type the API accepts today (DESTINATION_TYPES in
# api/src/routes/destinations.ts). The field accepts any string, like MessageStatus: when this was a
# closed Literal, one sqs or bridge destination in an org made destinations.list() and get() raise
# a ValidationError for the whole call.
DestinationType = Union[
    Literal[
        "http", "sqs", "eventbridge", "servicebus", "pubsub", "oci_queue",
        "s3", "r2", "gcs", "azure_blob", "bridge",
    ],
    str,
]
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
    model_config = SECRET_MODEL_CONFIG

    bucket: str
    region: str
    access_key_id: str
    secret_access_key: str = Field(repr=False)
    prefix: str | None = None
    file_format: FileFormat | None = None
    partition_by: PartitionBy | None = None


class R2Config(HookbaseModel):
    bucket: str
    prefix: str | None = None
    file_format: FileFormat | None = None
    partition_by: PartitionBy | None = None


class GCSConfig(HookbaseModel):
    model_config = SECRET_MODEL_CONFIG

    bucket: str
    project_id: str
    service_account_key: str = Field(repr=False)
    prefix: str | None = None
    file_format: FileFormat | None = None
    partition_by: PartitionBy | None = None


class AzureBlobConfig(HookbaseModel):
    model_config = SECRET_MODEL_CONFIG

    account_name: str
    account_key: str = Field(repr=False)
    container_name: str
    prefix: str | None = None
    file_format: FileFormat | None = None
    partition_by: PartitionBy | None = None


# How a bridge destination picks the outbound event type: one fixed type, or read from a payload
# field. Any string, so a source the API adds later still parses.
BridgeEventTypeSource = Union[Literal["fixed", "field"], str]


class BridgeConfig(HookbaseModel):
    """A bridge destination's `config` (`bridgeConfigSchema` in api/src/types/warehouse.ts).

    A bridge publishes each delivery it receives as an outbound event, so it has no URL, headers,
    auth or static IP, and creating one also takes the `events:send` permission. Pass it as
    `config` with `type="bridge"`::

        client.destinations.create(CreateDestinationParams(
            name="Orders to customers", type="bridge",
            config=BridgeConfig(event_type_source="fixed", event_type="order.created"),
        ))
    """

    event_type_source: BridgeEventTypeSource
    event_type: str | None = None
    """The outbound event type to publish. Required, and only allowed, for `"fixed"`; it must
    exist and be enabled."""
    event_type_field: str | None = None
    """Dot path of the payload field holding the event type (`data.type`), at most five segments.
    Required, and only allowed, for `"field"`."""
    event_type_prefix: str | None = None
    """`"field"` only: prepended to the value read from `event_type_field`."""
    application_id: str | None = None
    """Publish to this application's endpoints only; all applications when unset."""
    allow_unverified_sources: bool | None = None
    """Publish events whose sender the source did not verify (by signature or IP allowlist).
    The API publishes verified events only unless this is true."""


class Throttle(HookbaseModel):
    mode: ThrottleMode = "off"
    rate_limit: int | None = None
    rate_unit: RateUnit | None = None
    max_concurrency: int | None = None
    queue_limit: int | None = None


class Destination(HookbaseModel):
    # The API returns headers and auth_config in full to a key with the write scope.
    model_config = SECRET_MODEL_CONFIG

    id: str
    organization_id: str | None = None
    name: str
    slug: str
    type: DestinationType = "http"
    url: str = ""
    method: HttpMethod = "POST"
    headers: dict[str, str] | None = Field(default=None, repr=False)
    auth_type: str | None = "none"
    auth_config: dict[str, Any] | None = Field(default=None, repr=False)
    timeout_ms: int = 30000
    throttle: Throttle | None = None
    is_active: bool = True
    use_static_ip: bool = True
    config: dict[str, Any] | None = None
    field_mapping: list[FieldMapping] | None = None
    batch_size: int | None = None
    batch_window_seconds: int | None = None
    has_signing_secret: bool = False
    """Whether deliveries to this destination are signed (HTTP destinations only). The secret
    itself is returned once, by `create`; after that use `destinations.reveal_secret`."""
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

    @property
    def bridge_config(self) -> BridgeConfig | None:
        """`config` as a :class:`BridgeConfig` for a bridge destination; None for other types."""
        if self.type != "bridge" or not self.config:
            return None
        return BridgeConfig.model_validate(self.config)


class DestinationWithSecret(Destination):
    """What `destinations.create` returns: the destination plus its signing secret, this once."""

    model_config = SECRET_MODEL_CONFIG

    signing_secret: str | None = Field(default=None, repr=False)
    """The full signing secret of a new HTTP destination; save it now. Every delivery carries a
    Standard Webhooks `webhook-signature` made with it, which `Webhook(signing_secret).verify()`
    checks. None for queue, storage and bridge destinations, which are not signed."""


class DestinationSecret(HookbaseModel):
    """The result of `destinations.reveal_secret` and `destinations.rotate_secret`."""

    model_config = SECRET_MODEL_CONFIG

    signing_secret: str = Field(default="", repr=False)
    """The current signing secret, in full."""
    previous_secret_expires_at: str | None = None
    """Until when deliveries are also signed with the previous secret, after a rotation with a
    grace period; None when no previous secret is in use."""


class CreateDestinationParams(HookbaseModel):
    model_config = SECRET_MODEL_CONFIG

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
    headers: dict[str, str] | None = Field(default=None, repr=False)
    """Sent as a mapping — the shape the destinations API takes, unlike
    endpoint headers."""
    auth_type: AuthType | None = None
    auth_config: dict[str, Any] | None = Field(default=None, repr=False)
    timeout_ms: int | None = None
    """Request timeout in milliseconds, 1000-60000. The API defaults to 30000."""
    throttle: Throttle | None = None
    config: dict[str, Any] | BridgeConfig | None = Field(default=None, repr=False)
    """Settings for a non-HTTP type: a mapping for queue and storage types, or a
    :class:`BridgeConfig` (or its camelCase mapping) for `type="bridge"`. Left out of repr()
    because a queue or storage config holds its credentials."""
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
    model_config = SECRET_MODEL_CONFIG

    name: str | None = None
    url: str | None = None
    method: HttpMethod | None = None
    headers: dict[str, str] | None = Field(default=None, repr=False)
    auth_type: AuthType | None = None
    auth_config: dict[str, Any] | None = Field(default=None, repr=False)
    timeout_ms: int | None = None
    """Request timeout in milliseconds, 1000-60000."""
    throttle: Throttle | None = None
    is_active: bool | None = None
    config: dict[str, Any] | BridgeConfig | None = Field(default=None, repr=False)
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
    # A params model serializes a BridgeConfig itself; a caller's dict can still hold the model.
    config = body.get("config")
    if hasattr(config, "model_dump"):
        body["config"] = _wire.dump(config)


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
    """The result of `destinations.test`.

    For a bridge destination the test is a dry run: nothing is published. `success` is whether
    the event type resolved from the sample payload exists, and the `dry_run` fields below are
    set; `status`, `latency_ms` and `response_body` are not.
    """

    success: bool
    status: int | None = None
    """The HTTP status the destination answered with."""
    latency_ms: int | None = None
    response_body: str | None = None
    error: str | None = None

    dry_run: bool | None = None
    """True for a bridge destination's test; None for every other type."""
    event_type: str | None = None
    """Bridge only: the event type resolved from the sample payload."""
    event_type_exists: bool | None = None
    """Bridge only: whether that event type exists and is enabled."""
    matching_endpoints: int | None = None
    """Bridge only: how many endpoints are subscribed to it and would receive the event."""

    status_code: int | None = None
    """Deprecated: the API calls this `status`; read `status` instead. Kept in
    step with it so existing attribute access keeps working."""
    duration: float | None = None
    """Deprecated: the API calls this `latencyMs`; read `latency_ms` instead.
    Kept in step with it so existing attribute access keeps working."""

    @model_validator(mode="before")
    @classmethod
    def _mirror_deprecated(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        out = dict(data)
        if out.get("status") is not None:
            out["statusCode"] = out["status"]
        latency = out.get("latencyMs", out.get("latency_ms"))
        if latency is not None:
            out["duration"] = latency
        return out
