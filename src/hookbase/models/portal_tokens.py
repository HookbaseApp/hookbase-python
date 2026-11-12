from __future__ import annotations

from pydantic import Field

from ._base import SECRET_MODEL_CONFIG, HookbaseModel


class PortalToken(HookbaseModel):
    model_config = SECRET_MODEL_CONFIG

    id: str
    application_id: str = ""
    token: str | None = Field(default=None, repr=False)
    """The token in full. Only `create` returns it."""
    token_prefix: str | None = None
    name: str | None = None
    scopes: list[str] = []
    expires_at: str = ""
    created_at: str = ""
    is_expired: bool | None = None
    is_revoked: bool | None = None
    last_used_at: str | None = None
    use_count: int | None = None
    revoked_at: str | None = None
    api_key_id: str | None = None
    """The API key that created the token, when one did."""
    revoked_by_api_key_id: str | None = None


class CreatePortalTokenParams(HookbaseModel):
    name: str | None = None
    scopes: list[str] | None = None
    expires_in_days: int | None = None
    allowed_ips: list[str] | None = None
