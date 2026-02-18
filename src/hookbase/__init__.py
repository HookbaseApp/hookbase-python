"""Hookbase Python SDK - Official client for the Hookbase webhook platform."""

from ._version import __version__
from .client import AsyncHookbase, Hookbase
from .errors import (
    APIError,
    AuthenticationError,
    ConflictError,
    ForbiddenError,
    HookbaseError,
    NetworkError,
    NotFoundError,
    RateLimitError,
    TimeoutError,
    ValidationError,
    WebhookVerificationError,
)
from .webhook import Webhook

__all__ = [
    "__version__",
    # Clients
    "Hookbase",
    "AsyncHookbase",
    # Webhook verification
    "Webhook",
    # Errors
    "HookbaseError",
    "APIError",
    "AuthenticationError",
    "ForbiddenError",
    "NotFoundError",
    "ValidationError",
    "ConflictError",
    "RateLimitError",
    "TimeoutError",
    "NetworkError",
    "WebhookVerificationError",
]
