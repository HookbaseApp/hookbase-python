from __future__ import annotations

from ._base import HookbaseModel


class Subscription(HookbaseModel):
    id: str
    endpoint_id: str
    event_type_id: str
    event_type_name: str = ""
    is_enabled: bool = True
    created_at: str = ""
    updated_at: str = ""


class CreateSubscriptionParams(HookbaseModel):
    endpoint_id: str
    event_type_id: str


class UpdateSubscriptionParams(HookbaseModel):
    is_enabled: bool | None = None
