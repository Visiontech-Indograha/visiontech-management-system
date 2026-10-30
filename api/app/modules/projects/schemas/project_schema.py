"""Skema proyek/SPK (tabel `project`)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

ProjectStatus = Literal["DRAFT", "ONGOING", "COMPLETED", "CANCELLED"]


class ProjectOut(BaseModel):
    project_id: UUID
    client_id: UUID
    client_name: str
    office_id: UUID
    office_name: str
    division_id: UUID
    division_name: str
    pm_id: UUID
    pm_name: str
    spk_number: str
    project_title: str
    total_target_qty: Decimal
    unit_measure: str
    start_date: date
    end_date: date
    status: ProjectStatus
    daily_plan_count: int = 0
    order_count: int = 0


class ProjectCreate(BaseModel):
    client_id: UUID
    office_id: UUID
    division_id: UUID
    pm_id: UUID | None = None  # kosong = PM divisi
    spk_number: str = Field(min_length=2, max_length=100)
    project_title: str = Field(min_length=3, max_length=255)
    total_target_qty: Decimal = Field(Decimal("1"), gt=0, max_digits=12, decimal_places=2,
                                      le=Decimal("9999999999.99"))
    unit_measure: str = Field("Unit", min_length=1, max_length=50)
    start_date: date
    end_date: date
    status: ProjectStatus = "ONGOING"

    @model_validator(mode="after")
    def _dates(self) -> ProjectCreate:
        if self.end_date < self.start_date:
            raise ValueError("Tanggal selesai tidak boleh sebelum tanggal mulai.")
        return self


class ProjectUpdate(BaseModel):
    client_id: UUID | None = None
    office_id: UUID | None = None
    pm_id: UUID | None = None
    spk_number: str | None = Field(None, min_length=2, max_length=100)
    project_title: str | None = Field(None, min_length=3, max_length=255)
    total_target_qty: Decimal | None = Field(None, gt=0, max_digits=12, decimal_places=2,
                                             le=Decimal("9999999999.99"))
    unit_measure: str | None = Field(None, min_length=1, max_length=50)
    start_date: date | None = None
    end_date: date | None = None
    status: ProjectStatus | None = None
