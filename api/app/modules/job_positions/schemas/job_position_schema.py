"""Skema jabatan (tabel `job_position`)."""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field


class JobPositionOut(BaseModel):
    position_id: UUID
    division_id: UUID | None = None
    division_name: str | None = None
    code: str
    name: str
    grade_level: int
    daily_allowance: Decimal
    description: str | None = None
    status: bool
    employee_count: int = 0


class JobPositionCreate(BaseModel):
    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=2, max_length=100)
    division_id: UUID | None = None  # kosong = jabatan lintas divisi
    grade_level: int = Field(1, ge=1, le=20)
    daily_allowance: Decimal = Field(Decimal("0"), ge=0, le=Decimal("99999999"))
    description: str | None = Field(None, max_length=2000)


class JobPositionUpdate(BaseModel):
    code: str | None = Field(None, min_length=1, max_length=30)
    name: str | None = Field(None, min_length=2, max_length=100)
    division_id: UUID | None = None
    grade_level: int | None = Field(None, ge=1, le=20)
    daily_allowance: Decimal | None = Field(None, ge=0, le=Decimal("99999999"))
    description: str | None = Field(None, max_length=2000)
    status: bool | None = None
