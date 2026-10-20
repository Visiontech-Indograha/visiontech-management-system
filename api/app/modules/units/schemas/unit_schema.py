"""Skema divisi operasional (tabel `division`): dipimpin satu OM (om_id) dan satu PM (pm_id) — docs/35 §2."""
from uuid import UUID

from pydantic import BaseModel, Field


class UnitOut(BaseModel):
    """Divisi aktif beserta OM & PM-nya."""

    id: UUID
    code: str
    name: str
    status: bool = True
    om_id: UUID | None = None
    pm_id: UUID | None = None
    om_name: str | None = None
    pm_name: str | None = None
    team_count: int = 0


class UnitCreate(BaseModel):
    """Divisi baru."""

    name: str = Field(min_length=2, max_length=100)
    om_id: UUID   # employee ber-peran OPERATIONAL_MANAGER
    pm_id: UUID   # employee ber-peran PROJECT_MANAGER


class UnitUpdate(BaseModel):
    """Perubahan sebagian divisi; field kosong tidak diubah."""

    name: str | None = Field(default=None, min_length=2, max_length=100)
    om_id: UUID | None = None
    pm_id: UUID | None = None
    status: bool | None = None
