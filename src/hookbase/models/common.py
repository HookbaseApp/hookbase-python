from __future__ import annotations

from typing import Any

from ._base import HookbaseModel


class ImportResultItem(HookbaseModel):
    """Deprecated: no import response carries per-item results in this shape.
    See :class:`ImportResult`."""

    name: str
    status: str
    error: str | None = None


class ImportFailure(HookbaseModel):
    """An item that failed to import, and why."""

    name: str = ""
    error: str = ""


class ImportSummary(HookbaseModel):
    """Counts for an import. Which keys are set depends on the resource and on
    whether it was a `validate_only` run."""

    total: int | None = None
    imported: int | None = None
    skipped: int | None = None
    overwritten: int | None = None
    failed: int | None = None
    errors: int | None = None
    to_create: int | None = None
    to_overwrite: int | None = None
    to_skip: int | None = None
    valid: int | None = None
    overwrite: int | None = None


class ImportDetails(HookbaseModel):
    """Names of the items in each outcome (sources and destinations imports)."""

    imported: list[str] = []
    skipped: list[str] = []
    overwritten: list[str] = []
    failed: list[ImportFailure] = []


class ImportValidationResult(HookbaseModel):
    """How one item fared in validation."""

    index: int = 0
    name: str = ""
    slug: str | None = None
    status: str = ""
    """`valid`, `error`, `skip`, `rename` or `overwrite`."""
    errors: list[str] = []
    warnings: list[str] = []
    resolved_slug: str | None = None
    resolved_name: str | None = None


class ImportResult(HookbaseModel):
    """The result of `import_sources`, `import_destinations` or `import_routes`.

    A `validate_only` run sets `valid` (sources, destinations), `validation_results`
    and a `summary` of what would happen. A real import sets `success` and a
    `summary`; sources and destinations list the item names in `details`, while
    routes put them in `imported`, `skipped` and `errors`.
    """

    success: bool = False
    valid: bool | None = None
    validate_only: bool = False
    summary: ImportSummary | None = None
    details: ImportDetails | None = None
    validation_results: list[ImportValidationResult] = []
    imported: list[str] = []
    """Route imports only; sources and destinations use `details.imported`."""
    skipped: list[str] = []
    """Route imports only; sources and destinations use `details.skipped`."""
    errors: list[ImportFailure] = []
    """Route imports only; sources and destinations use `details.failed`."""


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
