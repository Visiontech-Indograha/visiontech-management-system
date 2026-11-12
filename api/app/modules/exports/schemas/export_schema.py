"""
app/modules/exports/schemas/export_schema.py
Ekspor dokumen resmi (Milestone 8, docs/35 §8) dan registri `document_template_export`.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

# Dokumen per order → format tetap (docs/35 §8: DOCX BAST & Survey Report, PDF resmi ber-QR, XLSX BoQ, PPTX progres).
CompletionTemplate = Literal["BAST", "SURVEY_REPORT", "BAST_PDF", "BOQ", "PROGRESS_SLIDES", "ORDER_SHEET"]
PeriodicFormat = Literal["EXCEL_XLSX", "PPTX"]
# Format dokumen laporan (survei, harian, mingguan, order): PDF (dikonversi dari Word, isi sama), Word, PowerPoint.
# Tanpa nilai = format bawaan lama tiap jenis (kompatibel dengan klien lama).
ReportFormat = Literal["PDF", "WORD_DOCX", "PPTX"]


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
    export_format: ReportFormat | None = Field(None, description="PDF, WORD_DOCX, atau PPTX; kosong = bawaan jenisnya")


class DailyReportExportRequest(BaseModel):
    daily_plan_id: UUID  # jadwal harian yang laporannya dicetak (satu hari, satu tim)
    export_format: ReportFormat | None = Field(None, description="PDF, WORD_DOCX, atau PPTX; kosong = Word")


class TeamWeekExportRequest(BaseModel):
    team_id: UUID
    start_date: date  # hari pertama minggu (Senin); laporan mencakup 7 hari
    end_date: date | None = Field(None, description="Opsional; bila diisi harus Minggu (tepat 7 hari dari Senin)")
    export_format: ReportFormat | None = Field(None, description="PDF, WORD_DOCX, atau PPTX; kosong = PowerPoint")

    @model_validator(mode="after")
    def _week(self) -> TeamWeekExportRequest:
        if self.start_date.weekday() != 0:
            raise ValueError("Tanggal mulai minggu harus hari Senin.")
        if self.end_date is not None and (self.end_date - self.start_date).days != 6:
            raise ValueError("Laporan mingguan harus tepat 7 hari (Senin sampai Minggu).")
        return self


class PeriodicExportRequest(BaseModel):
    division_id: UUID
    start_date: date
    end_date: date
    export_format: PeriodicFormat = "EXCEL_XLSX"

    @model_validator(mode="after")
    def _dates(self) -> PeriodicExportRequest:
        if self.end_date < self.start_date:
            raise ValueError("Tanggal selesai tidak boleh sebelum tanggal mulai.")
        return self


class MonthlyExportRequest(BaseModel):
    """Laporan bulanan satu divisi: seluruh bulan kalender (tanggal 1 sampai akhir bulan)."""

    division_id: UUID
    year: int = Field(..., ge=2020, le=2100, description="Tahun, mis. 2026")
    month: int = Field(..., ge=1, le=12, description="Bulan 1 sampai 12")
    export_format: ReportFormat | None = Field(None, description="PDF, WORD_DOCX, atau PPTX; kosong = Word")


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
