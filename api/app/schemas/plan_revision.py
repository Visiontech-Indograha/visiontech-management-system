"""Skema revisi rencana kerja oleh PM (Rencana Kerja v3, T6)."""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel

from app.schemas.plan_draft import PlanDraftRequest


class PlanRevisionIn(PlanDraftRequest):
    """Isi rencana kerja yang baru ditambah alasan revisi; `change_id` = permintaan ketua yang diselesaikan."""
    reason: str  # Alasan revisi (wajib)
    change_id: UUID | None = None  # Permintaan ketua (PENDING_PM) yang selesai lewat revisi ini


class PlanRevisionOut(BaseModel):
    """Satu baris riwayat revisi: siapa, kapan, mengapa, dan apa yang berubah."""
    id: UUID  # ID baris riwayat
    revision: int  # Nomor revisi (= versi dokumen)
    revised_by_name: str | None = None  # Nama PM yang merevisi
    reason: str  # Alasan revisi
    diff: list[dict[str, Any]]  # Daftar perubahan {field, label, before, after, added, removed, changed}
    created_at: datetime  # Waktu revisi
