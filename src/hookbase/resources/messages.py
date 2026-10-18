from __future__ import annotations

import uuid
from typing import Any

from ..models.messages import SendEventResponse
from ._base import AsyncResource, SyncResource


def _send_event_body(
    application_id: str,
    event_type: str,
    payload: Any,
    *,
    metadata: dict[str, Any] | None,
    endpoint_ids: list[str] | None,
    endpoint_id: str | None,
    labels: dict[str, str] | None,
    priority: int | None,
    idempotency_key: str,
) -> dict[str, Any]:
    """Build the `POST /api/send-event` body (`sendEventSchema` in the API's send-event.ts).

    The idempotency key goes in the body, which every API version reads, as well as in the
    `Idempotency-Key` header. Several target endpoints go as `endpointIds`; a single one is also
    sent as the singular `endpointId`, which is the only targeting field older API deployments
    read -- without it they fan the event out to every subscribed endpoint.
    """
    body: dict[str, Any] = {
        "applicationId": application_id,
        "eventType": event_type,
        "payload": payload,
        "idempotencyKey": idempotency_key,
    }
    targets = list(dict.fromkeys([*(endpoint_ids or []), *([endpoint_id] if endpoint_id else [])]))
    if targets:
        body["endpointIds"] = targets
        if len(targets) == 1:
            body["endpointId"] = targets[0]
    if metadata is not None:
        body["metadata"] = metadata
    if labels is not None:
        body["labels"] = labels
    if priority is not None:
        body["priority"] = priority
    return body


class Messages(SyncResource):
    """Send webhook events via the send-event endpoint."""

    def send(
        self,
        application_id: str,
        *,
        event_type: str,
        payload: Any,
        event_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        endpoint_ids: list[str] | None = None,
        idempotency_key: str | None = None,
        endpoint_id: str | None = None,
        labels: dict[str, str] | None = None,
        priority: int | None = None,
    ) -> SendEventResponse:
        """Send an event to the application's subscribed endpoints.

        Args:
            endpoint_ids / endpoint_id: Deliver only to these endpoints.
            idempotency_key: Deduplicates the send server-side. When omitted, one is
                generated for this call, so the SDK's automatic retries can never
                deliver the event twice.
            labels: Labels matched against subscription label filters.
            priority: 0 (critical) to 4 (bulk).
            event_id: Deprecated and ignored: the API assigns the event ID (returned
                as `event_id`) and has never read one from the request.
        """
        key = idempotency_key or str(uuid.uuid4())
        body = _send_event_body(
            application_id, event_type, payload,
            metadata=metadata, endpoint_ids=endpoint_ids, endpoint_id=endpoint_id,
            labels=labels, priority=priority, idempotency_key=key,
        )
        resp = self._request("POST", "/api/send-event", json=body, idempotency_key=key)
        data = resp.get("data", resp) if isinstance(resp, dict) else resp
        return self._parse(SendEventResponse, data)


class AsyncMessages(AsyncResource):
    """Send webhook events via the send-event endpoint (async)."""

    async def send(
        self,
        application_id: str,
        *,
        event_type: str,
        payload: Any,
        event_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        endpoint_ids: list[str] | None = None,
        idempotency_key: str | None = None,
        endpoint_id: str | None = None,
        labels: dict[str, str] | None = None,
        priority: int | None = None,
    ) -> SendEventResponse:
        """Send an event to the application's subscribed endpoints. See `Messages.send`."""
        key = idempotency_key or str(uuid.uuid4())
        body = _send_event_body(
            application_id, event_type, payload,
            metadata=metadata, endpoint_ids=endpoint_ids, endpoint_id=endpoint_id,
            labels=labels, priority=priority, idempotency_key=key,
        )
        resp = await self._request("POST", "/api/send-event", json=body, idempotency_key=key)
        data = resp.get("data", resp) if isinstance(resp, dict) else resp
        return self._parse(SendEventResponse, data)
