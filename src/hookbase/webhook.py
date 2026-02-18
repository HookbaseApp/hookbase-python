from __future__ import annotations

import base64
import hashlib
import hmac
import json
import math
import secrets
import time
from typing import Any

from .errors import WebhookVerificationError

DEFAULT_TOLERANCE = 300  # 5 minutes


class Webhook:
    """Verify and parse incoming webhook payloads.

    Args:
        secret: The webhook signing secret (with or without ``whsec_`` prefix).
    """

    def __init__(self, secret: str) -> None:
        if not secret:
            raise ValueError("Webhook secret is required")
        self._secret = secret

    def verify(
        self,
        payload: str | bytes,
        headers: dict[str, str],
        *,
        tolerance: int = DEFAULT_TOLERANCE,
    ) -> dict[str, Any]:
        """Verify a webhook payload and return the parsed JSON.

        Args:
            payload: Raw request body as a string or bytes.
            headers: Request headers containing ``webhook-id``,
                ``webhook-timestamp``, and ``webhook-signature``.
            tolerance: Maximum age of the webhook in seconds (default 300).

        Returns:
            Parsed payload as a dict.

        Raises:
            WebhookVerificationError: If verification fails.
        """
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")

        normalized = {k.lower(): v for k, v in headers.items()}

        webhook_id = normalized.get("webhook-id")
        webhook_timestamp = normalized.get("webhook-timestamp")
        webhook_signature = normalized.get("webhook-signature")

        if not webhook_id:
            raise WebhookVerificationError("Missing webhook-id header")
        if not webhook_timestamp:
            raise WebhookVerificationError("Missing webhook-timestamp header")
        if not webhook_signature:
            raise WebhookVerificationError("Missing webhook-signature header")

        # Verify timestamp
        self._verify_timestamp(webhook_timestamp, tolerance)

        # Verify signature
        self._verify_signature(payload, webhook_id, webhook_timestamp, webhook_signature)

        # Parse and return
        try:
            return json.loads(payload)  # type: ignore[no-any-return]
        except json.JSONDecodeError as exc:
            raise WebhookVerificationError("Invalid JSON payload") from exc

    def generate_test_headers(
        self,
        payload: str,
        *,
        webhook_id: str | None = None,
        timestamp: int | None = None,
    ) -> dict[str, str]:
        """Generate valid webhook headers for testing.

        Args:
            payload: The payload string to sign.
            webhook_id: Optional webhook ID (generated if not provided).
            timestamp: Optional Unix timestamp (current time if not provided).

        Returns:
            Dict with ``webhook-id``, ``webhook-timestamp``, ``webhook-signature``.
        """
        wh_id = webhook_id or f"msg_{secrets.token_urlsafe(18)}"
        ts = str(timestamp or math.floor(time.time()))
        signed_content = f"{wh_id}.{ts}.{payload}"
        signature = self._sign(signed_content)

        return {
            "webhook-id": wh_id,
            "webhook-timestamp": ts,
            "webhook-signature": f"v1,{signature}",
        }

    def _verify_timestamp(self, timestamp: str, tolerance: int) -> None:
        try:
            webhook_time = int(timestamp)
        except ValueError:
            raise WebhookVerificationError("Invalid timestamp format")

        now = math.floor(time.time())
        diff = abs(now - webhook_time)

        if diff > tolerance:
            raise WebhookVerificationError(
                f"Webhook timestamp is outside tolerance ({diff}s > {tolerance}s)"
            )

    def _verify_signature(
        self,
        payload: str,
        webhook_id: str,
        webhook_timestamp: str,
        webhook_signature: str,
    ) -> None:
        signed_content = f"{webhook_id}.{webhook_timestamp}.{payload}"
        expected = self._sign(signed_content)

        signatures = _parse_signatures(webhook_signature)
        if not signatures:
            raise WebhookVerificationError("No valid signatures found")

        for version, sig in signatures:
            if version == "v1":
                try:
                    expected_bytes = base64.b64decode(expected)
                    actual_bytes = base64.b64decode(sig)
                    if hmac.compare_digest(expected_bytes, actual_bytes):
                        return
                except Exception:
                    continue

        raise WebhookVerificationError("Webhook signature verification failed")

    def _sign(self, signed_content: str) -> str:
        key = self._decode_secret()
        mac = hmac.new(key, signed_content.encode("utf-8"), hashlib.sha256)
        return base64.b64encode(mac.digest()).decode("utf-8")

    def _decode_secret(self) -> bytes:
        secret = self._secret
        if secret.startswith("whsec_"):
            secret = secret[6:]
        return base64.b64decode(secret)


def _parse_signatures(header: str) -> list[tuple[str, str]]:
    """Parse ``v1,<sig> v2,<sig>`` format into list of (version, signature)."""
    result: list[tuple[str, str]] = []
    for part in header.split(" "):
        pieces = part.split(",", 1)
        if len(pieces) == 2:
            result.append((pieces[0], pieces[1]))
    return result
