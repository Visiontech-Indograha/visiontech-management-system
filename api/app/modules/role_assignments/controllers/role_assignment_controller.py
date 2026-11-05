"""Controller penugasan peran tambahan."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import Depends

from app.core.security import CurrentUser
from app.modules.role_assignments.dependencies import get_role_assignment_service
from app.modules.role_assignments.schemas.role_assignment_schema import RoleAssignmentCreate, RoleAssignmentOut
from app.modules.role_assignments.services.role_assignment_service import RoleAssignmentService


def _out(r: Any) -> RoleAssignmentOut:
    return RoleAssignmentOut(
        assignment_id=r.assignment_id, user_id=r.user_id, role=r.role, office_id=r.office_id,
        office_name=r.office_name, source=r.source, created_at=r.created_at,
    )


class RoleAssignmentController:
    def __init__(self, service: RoleAssignmentService = Depends(get_role_assignment_service)) -> None:
        self.service = service

    async def handle_list(self, user_id: UUID) -> list[RoleAssignmentOut]:
        return [_out(r) for r in await self.service.list_for_user(user_id)]

    async def handle_add(self, actor: CurrentUser, user_id: UUID, data: RoleAssignmentCreate) -> RoleAssignmentOut:
        return _out(await self.service.add(actor, user_id, data.role, data.office_id))

    async def handle_revoke(self, actor: CurrentUser, user_id: UUID, assignment_id: UUID) -> None:
        await self.service.revoke(actor, user_id, assignment_id)
