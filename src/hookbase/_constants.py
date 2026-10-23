from __future__ import annotations

DEFAULT_BASE_URL = "https://api.hookbase.app"
DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 3
#: Seconds to wait before retrying a 429 that has no usable ``Retry-After`` header.
DEFAULT_RETRY_AFTER = 60.0


class NotGiven:
    """Sentinel for "argument not passed", distinct from an explicit ``None``.

    ``timeout=None`` means no timeout (as in httpx); leaving ``timeout`` out means the default.
    """

    _instance: NotGiven | None = None

    def __new__(cls) -> NotGiven:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __bool__(self) -> bool:
        return False

    def __repr__(self) -> str:
        return "NOT_GIVEN"


NOT_GIVEN = NotGiven()
