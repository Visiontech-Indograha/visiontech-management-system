"""
app/modules/exports/services/builders/model.py
Model data dokumen yang sudah dirakit service (tanpa DB): builder hanya menata, tidak mengambil data.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

PHASE_LABEL = {
    "SURVEY": "Survei",
    "PREPARATION": "Persiapan",
    "INSTALLATION": "Instalasi",
    "REPLACEMENT": "Replacement",
    "MAINTENANCE": "Maintenance",
}
STATUS_LABEL = {
    "TODO": "Belum mulai",
    "IN_PROGRESS": "Berjalan",
    "DONE": "Selesai",
    "PENDING_ROLLOVER": "Minta pindah hari",
    "SHIFTED_DAY": "Pindah hari",
}
PLAN_STATUS_LABEL = {
    "DRAFT": "Draf",
    "SUBMITTED": "Diajukan",
    "APPROVED": "Disetujui",
    "ONGOING": "Berjalan",
    "COMPLETED": "Selesai",
    "REJECTED": "Ditolak",
}
MONTHS = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli", "Agustus", "September", "Oktober",
          "November", "Desember"]
COMPANY = "PT VISIONTECH INDOGRAHA"


def tgl(value: Any) -> str:
    """date / '2026-10-03' → '3 Oktober 2026'; kosong → '-'."""
    if value is None or value == "":
        return "-"
    text = value.isoformat() if isinstance(value, date | datetime) else str(value)
    try:
        y, m, d = (int(x) for x in text[:10].split("-"))
        return f"{d} {MONTHS[m - 1]} {y}"
    except (ValueError, IndexError):
        return text


def qty(value: Any) -> str:
    """12.0 → '12', 1.5 → '1,5'."""
    number = float(value or 0)
    return f"{number:.0f}" if number.is_integer() else f"{number:.2f}".rstrip("0").replace(".", ",")


@dataclass
class ReportPhoto:
    label: str
    image: bytes  # JPEG yang sudah diperkecil


@dataclass
class ReportPoint:
    """Satu item = satu titik pekerjaan."""

    item_id: str
    title: str
    phase: str
    status: str
    work_date: date
    team_name: str
    location: str
    lat: float | None
    lng: float | None
    target: float
    completed: float
    progress: float
    notes: str | None
    delay_reason: str | None
    assignees: str
    work_type: str
    photos: list[ReportPhoto] = field(default_factory=list)
    bom: list[dict[str, Any]] = field(default_factory=list)

    @property
    def phase_label(self) -> str:
        return PHASE_LABEL.get(self.phase, self.phase)

    @property
    def status_label(self) -> str:
        return STATUS_LABEL.get(self.status, self.status)


@dataclass
class CompletionReport:
    order: dict[str, Any]
    points: list[ReportPoint]
    roster: list[Any]
    bom: list[dict[str, Any]]
    generated_by: str
    generated_at: datetime
    verify_url: str | None = None
    photos: list[ReportPhoto] = field(default_factory=list)  # foto realisasi tingkat order (ketua tim)
    leader_signature: bytes | None = None
    pm_signature: bytes | None = None
    map_image: bytes | None = None  # PNG peta + penanda titik (None: tanpa koneksi / tanpa koordinat)
    has_coordinates: bool = False  # ada titik berkoordinat (beda 'tanpa koneksi' dan 'tanpa titik')

    @property
    def survey_points(self) -> list[ReportPoint]:
        return [p for p in self.points if p.phase == "SURVEY"]

    @property
    def all_photos(self) -> list[tuple[str, bytes]]:
        """Foto per titik lalu foto realisasi order, berketerangan."""
        return [(f"{p.title} — {ph.label}", ph.image) for p in self.points for ph in p.photos] + [
            (ph.label, ph.image) for ph in self.photos]

    @property
    def number(self) -> str:
        return str(self.order.get("order_number") or str(self.order["completion_id"])[:8].upper())


@dataclass
class DailyReport:
    """Laporan harian satu jadwal: tim, ketua, item (progres, catatan, alasan tunda) dan laporan ketua."""

    team_name: str
    division_name: str
    work_date: date
    site_name: str | None
    status: str
    leader_name: str
    points: list[ReportPoint]
    roster: list[Any]
    summary: str | None
    obstacles: str | None
    generated_by: str
    generated_at: datetime
    report_submitted_at: datetime | None = None


@dataclass
class PeriodicReport:
    division_name: str
    start: date
    end: date
    days: list[Any]
    boq: list[Any]
    meal: list[Any]
    generated_by: str
    generated_at: datetime


@dataclass
class TeamWeekReport:
    """Laporan mingguan satu tim: semua pekerjaan (foto, keterangan, status) dalam rentang tanggal."""

    team_name: str
    division_name: str
    start: date
    end: date
    points: list[ReportPoint]
    roster: list[Any]
    generated_by: str
    generated_at: datetime


def plan_status_label(value: str | None) -> str:
    """Status jadwal harian dalam Bahasa Indonesia (dokumen cetak tidak memuat kode enum)."""
    return PLAN_STATUS_LABEL.get(value or "", value or "-")


def coord_text(lat: Any, lng: Any) -> str:
    """Koordinat untuk dokumen cetak: '-6.194400, 106.822900'; tanpa koordinat → '-'."""
    if lat is None or lng is None:
        return "-"
    return f"{float(lat):.6f}, {float(lng):.6f}"

