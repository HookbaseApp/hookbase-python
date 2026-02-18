from __future__ import annotations

from typing import Any

from ..models.messages import SendEventResponse
from ._base import AsyncResource, SyncResource


class Messages(SyncResource):
    """Send webhook events via the send-event endpoint."""

    def send(
        self,
        application_id: str,
        *,
        event_type: str,
        payload: dict[str, Any],
        event_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        endpoint_ids: list[str] | None = None,
        idempotency_key: str | None = None,
    ) -> SendEventResponse:
        body: dict[str, Any] = {
            "applicationId": application_id,
            "eventType": event_type,
            "payload": payload,
        }
        if event_id is not None:
            body["eventId"] = event_id
        if metadata is not None:
            body["metadata"] = metadata
        if endpoint_ids is not None:
            body["endpointIds"] = endpoint_ids
        resp = self._request(
            "POST", "/api/send-event", json=body, idempotency_key=idempotency_key
        )
        data = resp.get("data", resp) if isinstance(resp, dict) else resp
        return self._parse(SendEventResponse, data)


class AsyncMessages(AsyncResource):
    """Send webhook events via the send-event endpoint (async)."""

    async def send(
        self,
        application_id: str,
        *,
        event_type: str,
        payload: dict[str, Any],
        event_id: str | None = None,
        metadata: dict[str, Any] | None = None,
        endpoint_ids: list[str] | None = None,
        idempotency_key: str | None = None,
    ) -> SendEventResponse:
        body: dict[str, Any] = {
            "applicationId": application_id,
            "eventType": event_type,
            "payload": payload,
        }
        if event_id is not None:
            body["eventId"] = event_id
        if metadata is not None:
            body["metadata"] = metadata
        if endpoint_ids is not None:
            body["endpointIds"] = endpoint_ids
        resp = await self._request(
            "POST", "/api/send-event", json=body, idempotency_key=idempotency_key
        )
        data = resp.get("data", resp) if isinstance(resp, dict) else resp
        return self._parse(SendEventResponse, data)
