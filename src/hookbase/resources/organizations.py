from __future__ import annotations

from typing import Any

from ..models.organizations import Invite, Organization, OrganizationMember
from ._base import AsyncResource, SyncResource


class Organizations(SyncResource):
    def list(self) -> list[Organization]:
        resp = self._request("GET", "/api/organizations")
        items = resp.get("data", resp) if isinstance(resp, dict) else resp
        return self._parse_list(Organization, items if isinstance(items, list) else [])

    def get(self, id: str) -> Organization:
        resp = self._request("GET", f"/api/organizations/{id}")
        data = resp.get("data", resp.get("organization", resp))
        return self._parse(Organization, data)

    def create(self, name: str, slug: str) -> Organization:
        resp = self._request("POST", "/api/organizations", json={"name": name, "slug": slug})
        data = resp.get("data", resp.get("organization", resp))
        return self._parse(Organization, data)

    def update(self, id: str, params: dict[str, Any]) -> Organization:
        resp = self._request("PATCH", f"/api/organizations/{id}", json=params)
        data = resp.get("data", resp.get("organization", resp))
        return self._parse(Organization, data)

    def list_members(self, org_id: str) -> list[OrganizationMember]:
        resp = self._request("GET", f"/api/organizations/{org_id}/members")
        items = resp.get("members", resp.get("data", []))
        return self._parse_list(OrganizationMember, items if isinstance(items, list) else [])

    def update_member(self, org_id: str, user_id: str, role: str) -> None:
        self._request(
            "PATCH", f"/api/organizations/{org_id}/members/{user_id}",
            json={"role": role},
        )

    def remove_member(self, org_id: str, user_id: str) -> None:
        self._request("DELETE", f"/api/organizations/{org_id}/members/{user_id}")

    def invite(self, org_id: str, email: str, role: str = "member") -> Invite:
        resp = self._request(
            "POST", f"/api/organizations/{org_id}/invites",
            json={"email": email, "role": role},
        )
        data = resp.get("data", resp.get("invite", resp))
        return self._parse(Invite, data)

    def list_invites(self, org_id: str) -> list[Invite]:
        resp = self._request("GET", f"/api/organizations/{org_id}/invites")
        items = resp.get("invites", resp.get("data", []))
        return self._parse_list(Invite, items if isinstance(items, list) else [])

    def cancel_invite(self, org_id: str, invite_id: str) -> None:
        self._request("DELETE", f"/api/organizations/{org_id}/invites/{invite_id}")


class AsyncOrganizations(AsyncResource):
    async def list(self) -> list[Organization]:
        resp = await self._request("GET", "/api/organizations")
        items = resp.get("data", resp) if isinstance(resp, dict) else resp
        return self._parse_list(Organization, items if isinstance(items, list) else [])

    async def get(self, id: str) -> Organization:
        resp = await self._request("GET", f"/api/organizations/{id}")
        data = resp.get("data", resp.get("organization", resp))
        return self._parse(Organization, data)

    async def create(self, name: str, slug: str) -> Organization:
        resp = await self._request("POST", "/api/organizations", json={"name": name, "slug": slug})
        data = resp.get("data", resp.get("organization", resp))
        return self._parse(Organization, data)

    async def update(self, id: str, params: dict[str, Any]) -> Organization:
        resp = await self._request("PATCH", f"/api/organizations/{id}", json=params)
        data = resp.get("data", resp.get("organization", resp))
        return self._parse(Organization, data)

    async def list_members(self, org_id: str) -> list[OrganizationMember]:
        resp = await self._request("GET", f"/api/organizations/{org_id}/members")
        items = resp.get("members", resp.get("data", []))
        return self._parse_list(OrganizationMember, items if isinstance(items, list) else [])

    async def update_member(self, org_id: str, user_id: str, role: str) -> None:
        await self._request(
            "PATCH", f"/api/organizations/{org_id}/members/{user_id}",
            json={"role": role},
        )

    async def remove_member(self, org_id: str, user_id: str) -> None:
        await self._request("DELETE", f"/api/organizations/{org_id}/members/{user_id}")

    async def invite(self, org_id: str, email: str, role: str = "member") -> Invite:
        resp = await self._request(
            "POST", f"/api/organizations/{org_id}/invites",
            json={"email": email, "role": role},
        )
        data = resp.get("data", resp.get("invite", resp))
        return self._parse(Invite, data)

    async def list_invites(self, org_id: str) -> list[Invite]:
        resp = await self._request("GET", f"/api/organizations/{org_id}/invites")
        items = resp.get("invites", resp.get("data", []))
        return self._parse_list(Invite, items if isinstance(items, list) else [])

    async def cancel_invite(self, org_id: str, invite_id: str) -> None:
        await self._request("DELETE", f"/api/organizations/{org_id}/invites/{invite_id}")
