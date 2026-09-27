from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import field_validator, model_validator

from . import _wire
from ._base import HookbaseModel

CircuitState = Literal["closed", "open", "half_open"]
BackoffType = Literal["exponential", "linear", "fixed"]

# The five endpoint settings `PATCH /api/webhook-endpoints/:id` accepts an
# explicit null for (`.optional().nullable()` in `updateEndpointSchema`). Naming
# one in `UpdateEndpointParams.clear` resets it to the platform default. The
# camelCase spelling is the wire name; `clear` also takes the snake_case one.
ClearableEndpointField = Literal[
    "description",
    "successStatusCodes",
    "backoffType",
    "retryDelays",
    "ipAllowlistNotes",
    "success_status_codes",
    "backoff_type",
    "retry_delays",
    "ip_allowlist_notes",
]

CLEARABLE_ENDPOINT_FIELDS: tuple[str, ...] = (
    "description",
    "successStatusCodes",
    "backoffType",
    "retryDelays",
    "ipAllowlistNotes",
)

# The API takes either an explicit status code or a class pattern like "2xx"
# (`z.union([z.number().int().min(100).max(599), z.string().regex(/^\d{1}xx$/i)])`).
SuccessStatusCode = Union[int, str]


class CustomHeader(HookbaseModel):
    """One endpoint header, in the `{"name": .., "value": ..}` form the API takes."""

    name: str
    value: str


class WebhookEndpoint(HookbaseModel):
    """An endpoint as `GET`/`PATCH /api/webhook-endpoints` returns it.

    The field list mirrors the API's `formatEndpoint`. It used to carry fifteen
    of the API's thirty-six response keys, so most of an endpoint's
    configuration was unreadable from Python: the timeout, the circuit-breaker
    thresholds, the verification state, and all six of the delivery-policy
    settings below simply had nowhere to be decoded into and were dropped by
    `extra="ignore"` without a word.
    """

    id: str
    application_id: str
    url: str
    description: str | None = None
    secret: str = ""
    """The full signing secret. Populated by `create` alone; save it then,
    because no later response repeats it."""
    secret_prefix: str = ""
    """The first twelve characters of the signing secret, then `"..."`."""
    has_secret: bool = False
    secret_version: int = 0
    headers: dict[str, str] | None = None
    header_list: list[CustomHeader] = []
    """Headers in the `[{"name": .., "value": ..}]` form the API sends and
    takes. `headers` is the same data as a mapping, which cannot represent a
    repeated name; pass this back into an update."""
    timeout_seconds: int = 0
    is_disabled: bool = False
    disabled_at: str | None = None
    disabled_reason: str | None = None

    # The endpoint's delivery policy. All six are accepted on create and
    # update and acted on by the delivery path, and none of them were in any
    # response until the API started returning them -- so they were
    # write-only settings, and this model had no field for any of them.
    rate_limit_per_second: int = 0
    """Deliveries per second; 0 means unlimited."""
    success_status_codes: list[SuccessStatusCode] | None = None
    """Response statuses counted as a success. `None` means the platform
    default, 200 through 299."""
    backoff_type: BackoffType | None = None
    """The curve used between retries. `None` means the default, exponential."""
    retry_delays: list[int] | None = None
    """Explicit retry delays in seconds. `None` means the default schedule."""
    ip_allowlist_notes: str | None = None
    """Informational only."""
    use_static_ip: bool = False
    """Whether deliveries go through the dedicated static-IP proxy. The API
    defaults this to false, and so does this model -- it defaulted to true
    here, which reported the opposite of the truth for every endpoint created
    without the setting."""

    circuit_state: CircuitState = "closed"
    circuit_opened_at: str | None = None
    circuit_failure_count: int = 0
    circuit_failure_threshold: int = 0
    circuit_success_threshold: int = 0
    circuit_cooldown_seconds: int = 0
    total_messages: int = 0
    total_successes: int = 0
    total_failures: int = 0
    avg_response_time_ms: float | None = None
    last_success_at: str | None = None
    last_failure_at: str | None = None
    last_response_status: int | None = None
    is_verified: bool = False
    verified_at: str | None = None
    subscription_count: int = 0
    """Set on `list` responses only; `get` and `create` leave it at zero."""
    created_by: str | None = None
    api_key_id: str | None = None
    created_at: str = ""
    updated_at: str = ""

    # Deprecated: the API has no such column and never returns these, so they
    # are always the defaults below. Kept so existing attribute access keeps
    # working.
    filter_types: list[str] | None = None
    rate_limit: int | None = None
    rate_limit_period: int | None = None
    metadata: dict[str, Any] | None = None

    @model_validator(mode="before")
    @classmethod
    def _keep_header_pairs(cls, data: Any) -> Any:
        """Put the wire array of headers on `header_list` before `headers` eats it.

        `_coerce_headers` below folds the array into a mapping, which is lossy:
        two headers of the same name collapse into one. A caller round-tripping
        headers into an update needs the array the API sent.
        """
        if not isinstance(data, dict) or "headerList" in data:
            return data
        if isinstance(data.get("headers"), list):
            data = {**data, "headerList": data["headers"]}
        return data

    @field_validator("headers", mode="before")
    @classmethod
    def _coerce_headers(cls, v: Any) -> Any:
        """Fold the API's `[{"name": .., "value": ..}]` headers into a mapping.

        Endpoint responses carry headers as an array of objects (`[]` when the
        endpoint has none), while this field has always been typed as a
        mapping. Build the mapping from the array rather than discarding it.
        """
        if isinstance(v, list):
            headers: dict[str, str] = {}
            for item in v:
                if isinstance(item, dict) and "name" in item:
                    headers[str(item["name"])] = str(item.get("value", ""))
            return headers
        return v


class EndpointWithSecret(WebhookEndpoint):
    secret: str = ""


class CreateEndpointParams(HookbaseModel):
    url: str
    description: str | None = None
    headers: dict[str, str] | list[CustomHeader] | None = None
    timeout_seconds: int | None = None
    rate_limit_per_second: int | None = None
    success_status_codes: list[SuccessStatusCode] | None = None
    backoff_type: BackoffType | None = None
    retry_delays: list[int] | None = None
    ip_allowlist_notes: str | None = None
    use_static_ip: bool | None = None
    circuit_failure_threshold: int | None = None
    circuit_success_threshold: int | None = None
    circuit_cooldown_seconds: int | None = None

    # Deprecated fields, kept so existing callers keep type-checking and
    # running. See `endpoint_body` for what each one does on the wire.
    filter_types: list[str] | None = None
    """Deprecated: never accepted by the API and no longer sent. Subscribe an
    endpoint to event types through `client.outbound.subscriptions` instead."""
    rate_limit: int | None = None
    """Deprecated: renamed to `rate_limit_per_second`. The value is sent under
    that name, and `rate_limit_per_second` wins if both are set."""
    rate_limit_period: int | None = None
    """Deprecated: never accepted by the API and no longer sent. Rate limits
    are per second; use `rate_limit_per_second`."""
    metadata: dict[str, Any] | None = None
    """Deprecated: never accepted on endpoints and no longer sent. Applications
    carry metadata; endpoints do not."""


class UpdateEndpointParams(HookbaseModel):
    url: str | None = None
    description: str | None = None
    is_disabled: bool | None = None
    disabled_reason: str | None = None
    headers: dict[str, str] | list[CustomHeader] | None = None
    timeout_seconds: int | None = None
    rate_limit_per_second: int | None = None
    success_status_codes: list[SuccessStatusCode] | None = None
    backoff_type: BackoffType | None = None
    retry_delays: list[int] | None = None
    ip_allowlist_notes: str | None = None
    use_static_ip: bool | None = None
    circuit_failure_threshold: int | None = None
    circuit_success_threshold: int | None = None
    circuit_cooldown_seconds: int | None = None

    clear: list[ClearableEndpointField] | None = None
    """Settings to reset to their defaults.

    Every field above is `X | None = None` and `None` means "leave this alone",
    so `None` cannot also mean "set this back to nothing" -- and five settings
    the API explicitly lets you clear had no way to be cleared from Python at
    all. Naming one here sends an explicit JSON null for it::

        client.outbound.endpoints.update(
            "ep_1", UpdateEndpointParams(clear=["retryDelays"]),
        )

    Only the five fields in `CLEARABLE_ENDPOINT_FIELDS` are accepted, and a
    field that is also set on this model raises rather than the SDK choosing
    one of the two silently."""

    # Deprecated fields; see `CreateEndpointParams` for each one's replacement.
    filter_types: list[str] | None = None
    """Deprecated: never accepted by the API and no longer sent."""
    rate_limit: int | None = None
    """Deprecated: renamed to `rate_limit_per_second`. The value is sent under
    that name, and `rate_limit_per_second` wins if both are set."""
    rate_limit_period: int | None = None
    """Deprecated: never accepted by the API and no longer sent."""
    metadata: dict[str, Any] | None = None
    """Deprecated: never accepted on endpoints and no longer sent."""


def endpoint_body(
    params: CreateEndpointParams | UpdateEndpointParams | dict[str, Any],
) -> dict[str, Any]:
    """Build the request body for an endpoint create or update.

    `POST /api/webhook-endpoints` and `PATCH /api/webhook-endpoints/:id` accept
    the same field names apart from `applicationId` (create only) and
    `isDisabled`/`disabledReason` (update only), so one builder serves both.
    """
    body = _wire.dump(params)
    _wire.drop(body, "filterTypes", "rateLimitPeriod", "metadata")
    _wire.rename(body, "rateLimit", "rateLimitPerSecond")
    _wire.headers_to_pairs(body)
    # Last, so "that field is also set" sees the body the API will get rather
    # than the one before `rateLimit` was renamed onto `rateLimitPerSecond`.
    _wire.apply_clear(body, CLEARABLE_ENDPOINT_FIELDS, "endpoint")
    return body


class EndpointStats(HookbaseModel):
    total_messages: int = 0
    total_successes: int = 0
    total_failures: int = 0
    success_rate: float = 0.0
    average_latency: float = 0.0
    recent_failures: int = 0


class RotateSecretResult(HookbaseModel):
    secret: str
    previous_secret_valid_until: str | None = None
