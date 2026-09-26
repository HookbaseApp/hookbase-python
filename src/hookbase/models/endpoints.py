from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import field_validator

from . import _wire
from ._base import HookbaseModel

CircuitState = Literal["closed", "open", "half_open"]
BackoffType = Literal["exponential", "linear", "fixed"]

# The API takes either an explicit status code or a class pattern like "2xx"
# (`z.union([z.number().int().min(100).max(599), z.string().regex(/^\d{1}xx$/i)])`).
SuccessStatusCode = Union[int, str]


class CustomHeader(HookbaseModel):
    """One endpoint header, in the `{"name": .., "value": ..}` form the API takes."""

    name: str
    value: str


class WebhookEndpoint(HookbaseModel):
    id: str
    application_id: str
    url: str
    description: str | None = None
    secret: str = ""
    is_disabled: bool = False
    circuit_state: CircuitState = "closed"
    circuit_opened_at: str | None = None
    headers: dict[str, str] | None = None
    use_static_ip: bool = True
    total_messages: int = 0
    total_successes: int = 0
    total_failures: int = 0
    created_at: str = ""
    updated_at: str = ""

    # Deprecated: the API has no such column and never returns these, so they
    # are always the defaults below. Kept so existing attribute access keeps
    # working.
    filter_types: list[str] | None = None
    rate_limit: int | None = None
    rate_limit_period: int | None = None
    metadata: dict[str, Any] | None = None

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
