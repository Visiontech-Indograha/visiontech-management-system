"""
app/modules/work_plans/schemas/daily_report_schema.py
Skema laporan harian aktif tim lapangan (work_plan_daily_report).
Satu per rencana harian (work_plan_daily), diisi oleh ketua tim saat selesai bekerja atau saat check-out.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class DailyReportCreate(BaseModel):
    summary: str = Field(..., min_length=3, description="Ringkasan hasil kerja harian")
    obstacles: str | None = Field(None, description="Kendala atau hambatan di lapangan jika ada")
    photos_json: list[dict[str, Any] | str] = Field(default_factory=list, description="Foto dokumentasi hasil kerja")


class DailyReportOut(BaseModel):
    report_id: UUID
    daily_plan_id: UUID
    leader_employee_id: UUID
    leader_name: str | None = None
    summary: str
    obstacles: str | None = None
    photos_json: list[dict[str, Any] | str] = Field(default_factory=list)
    submitted_at: datetime
    create_at: datetime


class WeeklyMeetingSubmit(BaseModel):
    meeting_date: datetime | str
    presentation_notes: str = Field(min_length=3, description="Catatan presentasi mingguan oleh ketua tim")
    pm_feedback: str | None = Field(None, description="Tanggapan / evaluasi dari PM")
    attendee_employee_ids: list[UUID] = Field(default_factory=list, description="Daftar ID karyawan hadir meeting")


class WeeklyPresentationOut(BaseModel):
    team_id: UUID
    team_name: str
    week_start: str
    week_end: str
    total_plans: int
    completed_plans: int
    daily_reports: list[DailyReportOut] = Field(default_factory=list)
    presentation_notes: str | None = None
    pm_feedback: str | None = None

