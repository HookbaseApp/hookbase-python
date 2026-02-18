from __future__ import annotations

from typing import Any, Literal

from pydantic import field_validator

from ._base import HookbaseModel

CircuitState = Literal["closed", "open", "half_open"]


class WebhookEndpoint(HookbaseModel):
    id: str
    application_id: str
    url: str
    description: str | None = None
    secret: str = ""
    is_disabled: bool = False
    circuit_state: CircuitState = "closed"
    circuit_opened_at: str | None = None
    filter_types: list[str] | None = None
    rate_limit: int | None = None
    rate_limit_period: int | None = None
    headers: dict[str, str] | None = None

    @field_validator("headers", mode="before")
    @classmethod
    def _coerce_headers(cls, v: Any) -> Any:
        if isinstance(v, list):
            return {}
        return v
    metadata: dict[str, Any] | None = None
    total_messages: int = 0
    total_successes: int = 0
    total_failures: int = 0
    created_at: str = ""
    updated_at: str = ""


class EndpointWithSecret(WebhookEndpoint):
    secret: str = ""


class CreateEndpointParams(HookbaseModel):
    url: str
    description: str | None = None
    filter_types: list[str] | None = None
    rate_limit: int | None = None
    rate_limit_period: int | None = None
    headers: dict[str, str] | None = None
    metadata: dict[str, Any] | None = None


class UpdateEndpointParams(HookbaseModel):
    url: str | None = None
    description: str | None = None
    is_disabled: bool | None = None
    filter_types: list[str] | None = None
    rate_limit: int | None = None
    rate_limit_period: int | None = None
    headers: dict[str, str] | None = None
    metadata: dict[str, Any] | None = None


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
