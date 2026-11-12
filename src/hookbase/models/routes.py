from __future__ import annotations

from typing import Any, Literal

from ._base import HookbaseModel
from .filters import FilterCondition

CircuitStatus = Literal["closed", "open", "half_open"]


class Route(HookbaseModel):
    id: str
    organization_id: str | None = None
    name: str
    source_id: str
    destination_id: str
    filter_id: str | None = None
    filter_conditions: list[FilterCondition] | None = None
    filter_logic: str | None = None
    transform_id: str | None = None
    schema_id: str | None = None
    priority: int = 0
    is_active: bool = True
    circuit_state: CircuitStatus | None = None
    circuit_opened_at: str | None = None
    circuit_cooldown_seconds: int | None = None
    circuit_failure_threshold: int | None = None
    circuit_probe_success_threshold: int | None = None
    notify_on_failure: bool = False
    notify_on_success: bool = False
    notify_on_recovery: bool = False
    notify_emails: str | None = None
    failure_threshold: int | None = None
    failover_destination_ids: list[str] | None = None
    failover_after_attempts: int | None = None
    expected_response: Any = None
    hold_on_circuit_open: bool | None = None
    """Whether deliveries wait as `held` while the circuit is open, and go out when it closes,
    instead of failing. The API defaults it to true; None when the response doesn't say."""
    held_count: int | None = None
    """`get` only: deliveries on this route held now, counted up to 10,000."""
    held_count_capped: bool | None = None
    """`get` only: true when there are more held deliveries than `held_count` says."""
    created_at: str = ""
    updated_at: str = ""


class CreateRouteParams(HookbaseModel):
    name: str
    source_id: str
    destination_id: str
    filter_id: str | None = None
    filter_conditions: list[FilterCondition] | None = None
    filter_logic: str | None = None
    transform_id: str | None = None
    schema_id: str | None = None
    priority: int | None = None
    is_active: bool | None = None
    notify_on_failure: bool | None = None
    notify_on_success: bool | None = None
    notify_on_recovery: bool | None = None
    notify_emails: str | None = None
    failure_threshold: int | None = None
    failover_destination_ids: list[str] | None = None
    failover_after_attempts: int | None = None
    expected_response: Any = None
    hold_on_circuit_open: bool | None = None
    """Hold deliveries while the circuit is open (the API's default, true) or fail them (false).
    Turning it off does not touch deliveries already held: the recovery sweep releases them, and
    they fail on their next attempt if the circuit is still open."""


class UpdateRouteParams(HookbaseModel):
    name: str | None = None
    source_id: str | None = None
    destination_id: str | None = None
    filter_id: str | None = None
    filter_conditions: list[FilterCondition] | None = None
    filter_logic: str | None = None
    transform_id: str | None = None
    schema_id: str | None = None
    priority: int | None = None
    is_active: bool | None = None
    notify_on_failure: bool | None = None
    notify_on_success: bool | None = None
    notify_on_recovery: bool | None = None
    notify_emails: str | None = None
    failure_threshold: int | None = None
    failover_destination_ids: list[str] | None = None
    failover_after_attempts: int | None = None
    expected_response: Any = None
    hold_on_circuit_open: bool | None = None
    """Hold deliveries while the circuit is open (the API's default, true) or fail them (false).
    Turning it off does not touch deliveries already held: the recovery sweep releases them, and
    they fail on their next attempt if the circuit is still open."""


class CircuitStatusInfo(HookbaseModel):
    circuit_state: CircuitStatus
    circuit_opened_at: str | None = None
    cooldown_seconds: int = 0
    probe_attempts: int = 0
    probe_success_threshold: int = 0
    failure_threshold: int = 0
    consecutive_failures: int = 0
    time_until_probe_seconds: int | None = None


class CircuitBreakerConfig(HookbaseModel):
    circuit_cooldown_seconds: int | None = None
    circuit_failure_threshold: int | None = None
    circuit_probe_success_threshold: int | None = None
