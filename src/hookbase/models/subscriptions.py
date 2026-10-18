from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import model_validator

from ._base import HookbaseModel

LabelFilterMode = Literal["all", "any"]
LabelFilterValue = Union[str, list[str]]


class Subscription(HookbaseModel):
    """A subscription as `/api/webhook-subscriptions` returns it.

    `list` adds the endpoint URL, event type and application names; `get` nests
    them as objects, which are folded onto the same flat fields here.
    """

    id: str
    endpoint_id: str
    event_type_id: str
    event_type_name: str = ""
    event_type_display_name: str | None = None
    endpoint_url: str | None = None
    application_id: str | None = None
    application_name: str | None = None
    filter_expression: str | None = None
    label_filters: dict[str, Any] | None = None
    label_filter_mode: str | None = None
    transform_id: str | None = None
    priority_override: int | None = None
    is_enabled: bool = True
    created_at: str = ""
    created_by: str | None = None
    api_key_id: str | None = None

    updated_at: str = ""
    """Deprecated: not returned by the API; always empty."""

    @model_validator(mode="before")
    @classmethod
    def _flatten_get(cls, data: Any) -> Any:
        """Fold `get`'s nested `endpoint`/`eventType`/`application` onto the flat fields."""
        if not isinstance(data, dict):
            return data
        out = dict(data)
        for nested, pairs in (
            ("endpoint", {"url": "endpointUrl"}),
            ("eventType", {"name": "eventTypeName", "displayName": "eventTypeDisplayName"}),
            ("application", {"id": "applicationId", "name": "applicationName"}),
        ):
            obj = out.get(nested)
            if isinstance(obj, dict):
                for src, dst in pairs.items():
                    if out.get(dst) is None and obj.get(src) is not None:
                        out[dst] = obj[src]
        return out


class CreateSubscriptionParams(HookbaseModel):
    endpoint_id: str
    event_type_id: str
    filter_expression: str | None = None
    label_filters: dict[str, LabelFilterValue] | None = None
    label_filter_mode: LabelFilterMode | None = None
    transform_id: str | None = None
    is_enabled: bool | None = None
    priority_override: int | None = None


class UpdateSubscriptionParams(HookbaseModel):
    is_enabled: bool | None = None
    filter_expression: str | None = None
    label_filters: dict[str, LabelFilterValue] | None = None
    label_filter_mode: LabelFilterMode | None = None
    transform_id: str | None = None
    priority_override: int | None = None
