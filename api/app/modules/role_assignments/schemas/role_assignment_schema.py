"""Skema penugasan peran tambahan (ADR 0002)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel

AssignableRole = Literal["ADMIN_HR_GA", "FINANCE", "OPERATIONAL_MANAGER"]


class RoleAssignmentCreate(BaseModel):
    """Tambah peran. HR/Finance wajib `office_id`; OM tanpa `office_id` (semua kantor)."""

    role: AssignableRole
    office_id: UUID | None = None


class RoleAssignmentOut(BaseModel):
    assignment_id: UUID
    user_id: UUID
    role: str
    office_id: UUID | None = None
    office_name: str | None = None
    source: str
    created_at: datetime
