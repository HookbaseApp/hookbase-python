from __future__ import annotations

from ._base import HookbaseModel


class Organization(HookbaseModel):
    id: str
    name: str
    slug: str
    plan: str = "free"
    created_at: str = ""
    updated_at: str = ""


class OrganizationMember(HookbaseModel):
    id: str
    user_id: str
    organization_id: str
    role: str = "member"
    email: str = ""
    name: str | None = None
    created_at: str = ""


class Invite(HookbaseModel):
    id: str
    organization_id: str
    email: str
    role: str = "member"
    status: str = "pending"
    created_at: str = ""
    expires_at: str | None = None
