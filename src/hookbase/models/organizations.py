from __future__ import annotations

from pydantic import model_validator

from ._base import HookbaseModel


class Organization(HookbaseModel):
    id: str
    name: str
    slug: str
    plan: str = "free"
    billing_email: str | None = None
    data_region: str | None = None
    data_region_label: str | None = None
    role: str | None = None
    """Your role in the organization (``organizations.list()``)."""
    user_role: str | None = None
    """Your role in the organization (``organizations.get()``)."""
    member_count: int | None = None
    source_count: int | None = None
    created_at: str = ""
    updated_at: str = ""


class OrganizationMember(HookbaseModel):
    """A member as ``GET /api/organizations/{org_id}/members`` returns it.

    The API's ``id`` is the member's user id (pass it to ``update_member``/``remove_member``);
    ``membership_id`` is the id of the membership row.
    """

    id: str
    user_id: str = ""
    organization_id: str | None = None
    membership_id: str | None = None
    role: str = "member"
    email: str = ""
    display_name: str | None = None
    name: str | None = None
    avatar_url: str | None = None
    created_at: str = ""

    @model_validator(mode="after")
    def _derive(self) -> OrganizationMember:
        if not self.user_id:
            self.user_id = self.id
        if self.name is None:
            self.name = self.display_name
        return self


class Invite(HookbaseModel):
    id: str
    email: str
    organization_id: str | None = None
    role: str = "member"
    status: str = "pending"
    invited_by_name: str | None = None
    email_sent: bool | None = None
    """Only on ``invite()``: whether the invitation email went out."""
    created_at: str = ""
    expires_at: str | None = None
