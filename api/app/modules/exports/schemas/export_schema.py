"""
app/modules/exports/schemas/export_schema.py
Ekspor dokumen resmi (Milestone 8, docs/35 §8) dan registri `document_template_export`.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# Dokumen per order → format tetap (docs/35 §8: DOCX BAST & Survey Report, PDF resmi ber-QR, XLSX BoQ, PPTX progres).
CompletionTemplate = Literal["BAST", "SURVEY_REPORT", "BAST_PDF", "BOQ", "PROGRESS_SLIDES"]
PeriodicFormat = Literal["EXCEL_XLSX", "PPTX"]


class SurveyLogoOut(BaseModel):
    """Logo kop laporan survei: ukuran baku (cm & px 300 dpi) dan apakah sudah diganti."""

    role: Literal["company", "client"]
    label: str
    width_cm: float
    height_cm: float
    recommended_px: tuple[int, int]
    custom: bool


class CompletionExportRequest(BaseModel):
    template: CompletionTemplate


class TeamWeekExportRequest(BaseModel):
    team_id: UUID
    start_date: date  # hari pertama minggu (Senin); laporan mencakup 7 hari


class PeriodicExportRequest(BaseModel):
    division_id: UUID
    start_date: date
    end_date: date
    export_format: PeriodicFormat = "EXCEL_XLSX"


class ExportOut(BaseModel):
    export_id: UUID
    source_type: str
    completion_id: UUID | None = None
    period_start_date: date | None = None
    period_end_date: date | None = None
    template_type: str
    export_format: str
    generated_by_id: UUID
    generated_by_name: str | None = None
    create_at: datetime
    file_name: str = Field(..., description="Nama berkas saat diunduh")
