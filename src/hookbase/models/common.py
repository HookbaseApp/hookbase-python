from __future__ import annotations

from typing import Any

from ._base import HookbaseModel


class ImportResultItem(HookbaseModel):
    name: str
    status: str
    error: str | None = None


class ImportResult(HookbaseModel):
    success: bool
    imported: int
    skipped: int
    errors: int
    results: list[ImportResultItem] = []


class BulkDeleteResult(HookbaseModel):
    success: bool = True
    deleted: int = 0


class PaginationInfo(HookbaseModel):
    total: int = 0
    page: int = 1
    page_size: int = 20


class CursorPaginationInfo(HookbaseModel):
    has_more: bool = False
    next_cursor: str | None = None


class ApiListResponse(HookbaseModel):
    """Generic wrapper for paginated list API responses."""

    data: list[Any] = []
    pagination: PaginationInfo | None = None
