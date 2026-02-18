from __future__ import annotations

import base64
import json
import math
import time

import pytest

from hookbase import Webhook, WebhookVerificationError

SECRET_RAW = base64.b64encode(b"test-secret-key-for-webhook-sign").decode()
SECRET_PREFIXED = f"whsec_{SECRET_RAW}"


@pytest.fixture
def wh():
    return Webhook(SECRET_PREFIXED)


def test_verify_valid_signature(wh):
    payload = json.dumps({"event": "test", "data": {"id": 1}})
    headers = wh.generate_test_headers(payload)

    result = wh.verify(payload, headers)
    assert result["event"] == "test"
    assert result["data"]["id"] == 1


def test_verify_without_prefix():
    wh = Webhook(SECRET_RAW)
    payload = json.dumps({"ok": True})
    headers = wh.generate_test_headers(payload)
    result = wh.verify(payload, headers)
    assert result["ok"] is True


def test_verify_bytes_payload(wh):
    payload = json.dumps({"key": "value"})
    headers = wh.generate_test_headers(payload)
    result = wh.verify(payload.encode("utf-8"), headers)
    assert result["key"] == "value"


def test_verify_missing_id_header(wh):
    with pytest.raises(WebhookVerificationError, match="Missing webhook-id"):
        wh.verify("{}", {"webhook-timestamp": "123", "webhook-signature": "v1,abc"})


def test_verify_missing_timestamp_header(wh):
    with pytest.raises(WebhookVerificationError, match="Missing webhook-timestamp"):
        wh.verify("{}", {"webhook-id": "msg_1", "webhook-signature": "v1,abc"})


def test_verify_missing_signature_header(wh):
    with pytest.raises(WebhookVerificationError, match="Missing webhook-signature"):
        wh.verify("{}", {"webhook-id": "msg_1", "webhook-timestamp": "123"})


def test_verify_invalid_timestamp(wh):
    with pytest.raises(WebhookVerificationError, match="Invalid timestamp"):
        wh.verify("{}", {
            "webhook-id": "msg_1",
            "webhook-timestamp": "not-a-number",
            "webhook-signature": "v1,abc",
        })


def test_verify_expired_timestamp(wh):
    old_ts = math.floor(time.time()) - 600  # 10 minutes ago
    payload = json.dumps({"old": True})
    headers = wh.generate_test_headers(payload, timestamp=old_ts)

    with pytest.raises(WebhookVerificationError, match="outside tolerance"):
        wh.verify(payload, headers)


def test_verify_bad_signature(wh):
    payload = json.dumps({"data": 1})
    ts = str(math.floor(time.time()))
    with pytest.raises(WebhookVerificationError, match="verification failed"):
        wh.verify(payload, {
            "webhook-id": "msg_test",
            "webhook-timestamp": ts,
            "webhook-signature": "v1,aW52YWxpZHNpZ25hdHVyZQ==",
        })


def test_verify_no_valid_signatures(wh):
    ts = str(math.floor(time.time()))
    with pytest.raises(WebhookVerificationError, match="No valid signatures"):
        wh.verify("{}", {
            "webhook-id": "msg_test",
            "webhook-timestamp": ts,
            "webhook-signature": "invalid-format",
        })


def test_verify_invalid_json(wh):
    payload = "not valid json"
    headers = wh.generate_test_headers(payload)
    with pytest.raises(WebhookVerificationError, match="Invalid JSON"):
        wh.verify(payload, headers)


def test_verify_case_insensitive_headers(wh):
    payload = json.dumps({"ci": True})
    headers = wh.generate_test_headers(payload)
    # Convert to mixed case
    upper_headers = {
        "Webhook-Id": headers["webhook-id"],
        "Webhook-Timestamp": headers["webhook-timestamp"],
        "Webhook-Signature": headers["webhook-signature"],
    }
    result = wh.verify(payload, upper_headers)
    assert result["ci"] is True


def test_generate_test_headers(wh):
    payload = json.dumps({"test": 1})
    headers = wh.generate_test_headers(payload)
    assert "webhook-id" in headers
    assert "webhook-timestamp" in headers
    assert "webhook-signature" in headers
    assert headers["webhook-signature"].startswith("v1,")


def test_generate_with_custom_id_and_timestamp(wh):
    payload = json.dumps({"test": 1})
    headers = wh.generate_test_headers(
        payload, webhook_id="msg_custom", timestamp=1000000
    )
    assert headers["webhook-id"] == "msg_custom"
    assert headers["webhook-timestamp"] == "1000000"


def test_empty_secret_raises():
    with pytest.raises(ValueError, match="required"):
        Webhook("")


def test_custom_tolerance(wh):
    payload = json.dumps({"data": 1})
    old_ts = math.floor(time.time()) - 60  # 1 minute ago
    headers = wh.generate_test_headers(payload, timestamp=old_ts)
    # Should pass with 120s tolerance
    result = wh.verify(payload, headers, tolerance=120)
    assert result["data"] == 1
    # Should fail with 30s tolerance
    with pytest.raises(WebhookVerificationError, match="outside tolerance"):
        wh.verify(payload, headers, tolerance=30)
