from __future__ import annotations

import pytest
import respx

from hookbase import Hookbase
from hookbase.models import OutboundMessage, SendEventResponse, StatsSummary

from ..conftest import make_cursor_response


@pytest.fixture
def mock_api():
    with respx.mock(base_url="https://api.hookbase.app") as mock:
        yield mock


@pytest.fixture
def client(mock_api):
    c = Hookbase(api_key="whr_test")
    yield c
    c.close()


def test_send_event(mock_api, client):
    mock_api.post("/api/send-event").respond(200, json={
        "data": {
            "eventId": "evt_123",
            "messagesQueued": 2,
            "endpoints": [
                {"id": "ep_1", "url": "https://a.com"},
                {"id": "ep_2", "url": "https://b.com"},
            ],
        }
    })
    result = client.outbound.messages.send(
        "app_1",
        event_type="order.created",
        payload={"orderId": "123"},
    )
    assert isinstance(result, SendEventResponse)
    assert result.event_id == "evt_123"
    assert result.messages_queued == 2
    assert len(result.endpoints) == 2


def test_list_message_log(mock_api, client):
    mock_api.get("/api/outbound-messages").respond(200, json=make_cursor_response([
        {
            "id": "om_1",
            "messageId": "msg_1",
            "endpointId": "ep_1",
            "endpointUrl": "https://a.com",
            "eventType": "order.created",
            "status": "success",
            "attempts": 1,
            "maxAttempts": 5,
            "createdAt": "2024-01-01T00:00:00Z",
            "updatedAt": "2024-01-01T00:00:00Z",
        }
    ]))
    page = client.outbound.message_log.list(application_id="app_1")
    assert len(page) == 1
    msg = page.data[0]
    assert isinstance(msg, OutboundMessage)
    assert msg.status == "success"


def test_get_stats(mock_api, client):
    mock_api.get("/api/outbound-messages/stats/summary").respond(200, json={
        "data": {
            "pending": 5,
            "processing": 2,
            "success": 100,
            "failed": 3,
            "exhausted": 1,
            "dlq": 1,
            "total": 112,
        }
    })
    stats = client.outbound.message_log.stats()
    assert isinstance(stats, StatsSummary)
    assert stats.total == 112
    assert stats.success == 100
