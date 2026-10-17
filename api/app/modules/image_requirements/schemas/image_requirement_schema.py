"""
app/modules/image_requirements/schemas/image_requirement_schema.py
Skema data Pydantic untuk Persyaratan Foto Dokumentasi Lapangan (image_requirement).
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ImageRequirementCreate(BaseModel):
    work_type_id: UUID
    name: str = Field(..., min_length=2, max_length=150)
    path_image: str = Field(..., description="URL contoh foto/panduan")
    is_mandatory: bool = True
    sort_order: int = 1


class ImageRequirementUpdate(BaseModel):
    name: str | None = Field(None, min_length=2, max_length=150)
    path_image: str | None = None
    is_mandatory: bool | None = None
    sort_order: int | None = None


class ImageRequirementOut(BaseModel):
    image_requirement_id: UUID
    work_type_id: UUID
    work_type_name: str | None = None
    name: str
    path_image: str
    is_mandatory: bool
    sort_order: int
    create_at: datetime
