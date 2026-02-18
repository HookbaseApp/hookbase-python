from __future__ import annotations

import pytest
import respx

from hookbase import Hookbase
from hookbase.models import DlqMessage, DlqRetryResult, DlqStats

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


DLQ_MSG = {
    "id": "dlq_1",
    "messageId": "msg_1",
    "endpointId": "ep_1",
    "applicationId": "app_1",
    "eventType": "order.created",
    "status": "exhausted",
    "dlqReason": "max_retries_exceeded",
    "attempts": 5,
    "maxAttempts": 5,
    "createdAt": "2024-01-01T00:00:00Z",
    "updatedAt": "2024-01-01T00:00:00Z",
}


def test_list_dlq(mock_api, client):
    mock_api.get(
        "/api/outbound-messages/dlq/messages",
    ).respond(200, json=make_cursor_response([DLQ_MSG]))
    page = client.outbound.dlq.list()
    assert len(page) == 1
    msg = page.data[0]
    assert isinstance(msg, DlqMessage)
    assert msg.dlq_reason == "max_retries_exceeded"


def test_dlq_stats(mock_api, client):
    mock_api.get("/api/outbound-messages/dlq/stats").respond(200, json={
        "data": {
            "total": 10,
            "byReason": {"max_retries_exceeded": 8, "endpoint_disabled": 2},
            "topFailingEndpoints": [
                {"endpointId": "ep_1", "endpointUrl": "https://a.com", "count": 5},
            ],
        }
    })
    stats = client.outbound.dlq.stats()
    assert isinstance(stats, DlqStats)
    assert stats.total == 10
    assert stats.by_reason["max_retries_exceeded"] == 8


def test_dlq_retry(mock_api, client):
    mock_api.post("/api/outbound-messages/dlq/dlq_1/retry").respond(200, json={
        "data": {
            "originalMessageId": "msg_1",
            "newMessageId": "msg_2",
            "status": "queued",
        }
    })
    result = client.outbound.dlq.retry("dlq_1")
    assert isinstance(result, DlqRetryResult)
    assert result.new_message_id == "msg_2"


def test_dlq_delete(mock_api, client):
    mock_api.delete("/api/outbound-messages/dlq/dlq_1").respond(204)
    client.outbound.dlq.delete("dlq_1")


def test_dlq_bulk_delete(mock_api, client):
    mock_api.delete("/api/outbound-messages/dlq/bulk").respond(200, json={"total": 2, "deleted": 2})
    result = client.outbound.dlq.bulk_delete(["dlq_1", "dlq_2"])
    assert result.deleted == 2
