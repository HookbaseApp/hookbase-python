from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import math
import re
import secrets
import time
from typing import TYPE_CHECKING, Any

from .errors import WebhookVerificationError

if TYPE_CHECKING:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import (
        Ed25519PrivateKey,
        Ed25519PublicKey,
    )

DEFAULT_TOLERANCE = 300  # 5 minutes

_LEGACY_HEX_SECRET = re.compile(r"[0-9a-fA-F]{64}")

ED25519_PUBLIC_KEY_PREFIX = "whpk_"
"""Prefix of a Standard Webhooks Ed25519 public key: ``whpk_<base64 of 32 bytes>``."""
ED25519_SECRET_KEY_PREFIX = "whsk_"
"""Prefix of a Standard Webhooks Ed25519 secret key: ``whsk_<base64 of seed || public key>``."""

_ED25519_MISSING = (
    "Ed25519 (v1a) webhook verification needs the 'cryptography' package. "
    "Install it with: pip install 'hookbase[ed25519]'"
)


class Webhook:
    """Verify and parse incoming webhook payloads.

    Both Standard Webhooks signature schemes are supported, chosen by the key
    you pass:

    * ``whsec_...`` (or a bare base64 secret): HMAC-SHA256, ``v1,<sig>`` entries.
    * ``whpk_...``: the endpoint's Ed25519 public key (``publicKey`` on the
      endpoint, or on the rotate-secret response), ``v1a,<sig>`` entries.
      Needs the optional ``cryptography`` dependency:
      ``pip install 'hookbase[ed25519]'``.
    * ``whsk_...``: an Ed25519 secret key. Hookbase never hands these out; it
      is accepted so tests can produce ``v1a`` headers with
      :meth:`generate_test_headers`.

    A header may carry several space-separated entries (e.g. during a key
    rotation grace period, or a mix of ``v1`` and ``v1a``). Verification
    passes if any entry of this key's scheme matches; entries of the other
    scheme are ignored.

    Args:
        secret: The signing secret, or for Ed25519 endpoints the public key.
    """

    def __init__(self, secret: str) -> None:
        if not secret:
            raise ValueError("Webhook secret is required")
        self._secret = secret
        self._ed25519_public: Ed25519PublicKey | None = None
        self._ed25519_private: Ed25519PrivateKey | None = None
        if secret.startswith(ED25519_PUBLIC_KEY_PREFIX):
            raw = _b64decode_key(secret[len(ED25519_PUBLIC_KEY_PREFIX):], "public")
            if len(raw) != 32:
                raise ValueError(f"Ed25519 public key must be 32 bytes, got {len(raw)}")
            self._ed25519_public = _ed25519().Ed25519PublicKey.from_public_bytes(raw)
        elif secret.startswith(ED25519_SECRET_KEY_PREFIX):
            raw = _b64decode_key(secret[len(ED25519_SECRET_KEY_PREFIX):], "secret")
            if len(raw) != 64:
                raise ValueError(
                    f"Ed25519 secret key must be 64 bytes (seed || public key), got {len(raw)}"
                )
            ed = _ed25519()
            self._ed25519_private = ed.Ed25519PrivateKey.from_private_bytes(raw[:32])
            self._ed25519_public = ed.Ed25519PublicKey.from_public_bytes(raw[32:])

    @property
    def signature_scheme(self) -> str:
        """``"ed25519"`` for a ``whpk_``/``whsk_`` key, otherwise ``"hmac-sha256"``.

        Matches the endpoint's ``signature_scheme``.
        """
        return "ed25519" if self._ed25519_public is not None else "hmac-sha256"

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
            try:
                payload = payload.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise WebhookVerificationError("Payload is not valid UTF-8") from exc

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
            timestamp: Optional Unix timestamp (current time when None; 0 is used as given).

        Returns:
            Dict with ``webhook-id``, ``webhook-timestamp``, ``webhook-signature``.
            The signature is ``v1,<sig>`` for an HMAC secret and ``v1a,<sig>``
            for an Ed25519 secret key (``whsk_``).

        Raises:
            ValueError: If this instance holds an Ed25519 public key, which
                cannot sign.
        """
        if self._ed25519_public is not None and self._ed25519_private is None:
            raise ValueError(
                "Cannot generate test headers with an Ed25519 public key (whpk_); "
                "use the matching secret key (whsk_)"
            )
        wh_id = webhook_id or f"msg_{secrets.token_urlsafe(18)}"
        ts = str(math.floor(time.time()) if timestamp is None else timestamp)
        signed_content = f"{wh_id}.{ts}.{payload}"
        if self._ed25519_private is not None:
            raw_sig = self._ed25519_private.sign(signed_content.encode("utf-8"))
            entry = f"v1a,{base64.b64encode(raw_sig).decode('ascii')}"
        else:
            entry = f"v1,{self._sign(signed_content)}"

        return {
            "webhook-id": wh_id,
            "webhook-timestamp": ts,
            "webhook-signature": entry,
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

        signatures = _parse_signatures(webhook_signature)
        if not signatures:
            raise WebhookVerificationError("No valid signatures found")

        if self._ed25519_public is not None:
            self._verify_ed25519(signed_content.encode("utf-8"), signatures)
            return

        expected = self._sign(signed_content)

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

    def _verify_ed25519(self, data: bytes, signatures: list[tuple[str, str]]) -> None:
        """Accept if any ``v1a`` entry is a valid Ed25519 signature over ``data``."""
        from cryptography.exceptions import InvalidSignature

        assert self._ed25519_public is not None
        for version, sig in signatures:
            if version != "v1a":
                continue
            try:
                raw = base64.b64decode(sig, validate=True)
            except (ValueError, binascii.Error):
                continue
            if len(raw) != 64:
                continue
            try:
                self._ed25519_public.verify(raw, data)
                return
            except InvalidSignature:
                continue

        raise WebhookVerificationError("Webhook signature verification failed")

    def _sign(self, signed_content: str) -> str:
        key = self._decode_secret()
        mac = hmac.new(key, signed_content.encode("utf-8"), hashlib.sha256)
        return base64.b64encode(mac.digest()).decode("utf-8")

    def _decode_secret(self) -> bytes:
        """Decode the secret to key bytes the way the API's `decodeSecret` does.

        Strip `whsec_` and the `op_` infix operational-webhook secrets carry
        (`whsec_op_<base64>`). A 64-character hex remainder is a legacy secret
        and is hex-decoded; it is also valid base64, so it must be checked first.
        Anything else is base64.
        """
        secret = self._secret
        if secret.startswith("whsec_"):
            secret = secret[6:]
            if secret.startswith("op_"):
                secret = secret[3:]
        if _LEGACY_HEX_SECRET.fullmatch(secret):
            return bytes.fromhex(secret)
        return base64.b64decode(secret)


def _ed25519() -> Any:
    """Import the Ed25519 module from the optional ``cryptography`` dependency."""
    try:
        from cryptography.hazmat.primitives.asymmetric import ed25519
    except ImportError as exc:  # pragma: no cover - exercised only without the extra
        raise ImportError(_ED25519_MISSING) from exc
    return ed25519


def _b64decode_key(value: str, kind: str) -> bytes:
    try:
        return base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError(f"Ed25519 {kind} key is not valid base64") from exc


def _parse_signatures(header: str) -> list[tuple[str, str]]:
    """Parse ``v1,<sig> v1a,<sig>`` format into list of (version, signature)."""
    result: list[tuple[str, str]] = []
    for part in header.split(" "):
        pieces = part.split(",", 1)
        if len(pieces) == 2:
            result.append((pieces[0], pieces[1]))
    return result
