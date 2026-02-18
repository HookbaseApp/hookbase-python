from __future__ import annotations

from typing import Any, TypeVar

from pydantic import TypeAdapter

from .._client import AsyncTransport, SyncTransport

T = TypeVar("T")


def _to_body(params: Any) -> Any:
    """Convert a Pydantic model or dict to a JSON-serializable dict."""
    if hasattr(params, "model_dump"):
        return params.model_dump(by_alias=True, exclude_none=True)
    return params


class SyncResource:
    """Base class for synchronous API resources."""

    def __init__(self, transport: SyncTransport) -> None:
        self._transport = transport

    def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        return self._transport.request(
            method, path, json=json, params=params, idempotency_key=idempotency_key
        )

    def _parse(self, model: type[T], data: Any) -> T:
        adapter = TypeAdapter(model)
        return adapter.validate_python(data)

    def _parse_list(self, model: type[T], data: Any) -> list[T]:
        adapter = TypeAdapter(list[model])  # type: ignore[valid-type]
        return adapter.validate_python(data)

    @staticmethod
    def _clean_params(params: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in params.items() if v is not None}


class AsyncResource:
    """Base class for asynchronous API resources."""

    def __init__(self, transport: AsyncTransport) -> None:
        self._transport = transport

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: Any = None,
        params: dict[str, Any] | None = None,
        idempotency_key: str | None = None,
    ) -> Any:
        return await self._transport.request(
            method, path, json=json, params=params, idempotency_key=idempotency_key
        )

    def _parse(self, model: type[T], data: Any) -> T:
        adapter = TypeAdapter(model)
        return adapter.validate_python(data)

    def _parse_list(self, model: type[T], data: Any) -> list[T]:
        adapter = TypeAdapter(list[model])  # type: ignore[valid-type]
        return adapter.validate_python(data)

    @staticmethod
    def _clean_params(params: dict[str, Any]) -> dict[str, Any]:
        return {k: v for k, v in params.items() if v is not None}
