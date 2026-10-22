"""
app/modules/face/schemas/face_schema.py
Skema wajah V2 sederhana (Milestone 7, keputusan pemilik 2026-10-20): daftar → `employee.face_embedding`;
swafoto absen dicocokkan server → `attendance.face_match_score`.
"""
from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class FacePolicy(BaseModel):
    match_threshold: float          # kemiripan kosinus minimum (0–1) agar dianggap cocok
    enrollment_required: bool       # absen HP ditolak bila wajah belum terdaftar
    min_images: int
    max_images: int


class FaceStatus(BaseModel):
    enrolled: bool
    enrolled_at: datetime | None = None
    model_name: str | None = None
    required: bool


class EnrollResponse(BaseModel):
    enrolled: bool
    images_used: int
    quality: float | None = None


class FaceResetResponse(BaseModel):
    employee_id: UUID
    enrolled: bool
