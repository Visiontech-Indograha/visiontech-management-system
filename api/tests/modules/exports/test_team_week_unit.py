"""
api/tests/modules/exports/test_team_week_unit.py
Uji unit tanpa DB: laporan mingguan tim (.pptx bertema), aturan akses ekspor mingguan, dan header nama berkas
non-ASCII.
"""
from __future__ import annotations

import io
from datetime import UTC, date, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from PIL import Image
from pptx import Presentation

from app.core.errors import AppError
from app.modules.exports.services import export_service as es
from app.modules.exports.services.builders.model import ReportPhoto, ReportPoint, TeamWeekReport
from app.modules.exports.services.builders.office_builders import team_week_pptx
from app.shared.content_disposition import content_disposition


def _jpeg() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (80, 60), (40, 60, 90)).save(buf, "JPEG")
    return buf.getvalue()


def _point(day: int, title: str, phase: str, status: str, photos: int) -> ReportPoint:
    return ReportPoint(
        item_id=title, title=title, phase=phase, status=status, work_date=date(2026, 10, day), team_name="Tim CCTV",
        location="Kantor Rumbai", lat=None, lng=None, target=2, completed=1, progress=50.0, notes="Diuji normal.",
        delay_reason=None, assignees="", work_type="",
        photos=[ReportPhoto(f"Foto {i + 1}", _jpeg()) for i in range(photos)], bom=[],
    )


def _report() -> TeamWeekReport:
    return TeamWeekReport(
        team_name="Tim CCTV", division_name="Divisi CCTV", start=date(2026, 10, 26), end=date(2026, 11, 1),
        points=[_point(26, "Survei titik", "SURVEY", "DONE", 2), _point(27, "Pasang kamera", "INSTALLATION",
                                                                        "IN_PROGRESS", 3)],
        roster=[SimpleNamespace(full_name="Zulkifli", is_leader=True), SimpleNamespace(full_name="Ageng",
                                                                                       is_leader=False)],
        generated_by="ketua", generated_at=datetime(2026, 11, 1, tzinfo=UTC),
    )


def _slide_text(slide) -> str:  # type: ignore[no-untyped-def]
    parts = []
    for shape in slide.shapes:
        if shape.has_text_frame:
            parts.append(shape.text_frame.text)
        if shape.has_table:
            parts.extend(c.text for r in shape.table.rows for c in r.cells)
    return "\n".join(parts)


def test_team_week_deck_has_cover_summary_table_work_and_closing():
    prs = Presentation(io.BytesIO(team_week_pptx(_report())))
    texts = [_slide_text(s) for s in prs.slides]
    # sampul + ringkasan + tabel + 2 pekerjaan + penutup
    assert len(texts) == 6
    assert "Laporan Mingguan" in texts[0] and "Tim CCTV" in texts[0]
    assert "Pekerjaan selesai" in texts[1] and "Zulkifli" in texts[1]
    assert "Survei titik" in texts[2] and "Pasang kamera" in texts[2] and "Berjalan" in texts[2]
    assert "Keterangan: Diuji normal." in texts[4] and "Foto 3" in texts[4]
    assert "Terima kasih" in texts[-1]


def test_team_week_photos_are_placed_on_work_slides():
    prs = Presentation(io.BytesIO(team_week_pptx(_report())))
    pictures = [sum(1 for sh in s.shapes if sh.shape_type == 13) for s in prs.slides]
    # slide pekerjaan: logo kecil + foto pekerjaan
    assert pictures[3] == 1 + 2 and pictures[4] == 1 + 3


def _service(*, member: bool, items: list | None = None) -> es.ExportService:  # type: ignore[type-arg]
    svc = es.ExportService.__new__(es.ExportService)
    repo = MagicMock()
    repo.db = MagicMock()
    repo.team_info = AsyncMock(return_value=SimpleNamespace(name="Tim CCTV", division_id=uuid4(),
                                                            division_name="Divisi CCTV"))
    repo.is_team_member = AsyncMock(return_value=member)
    repo.team_week_items = AsyncMock(return_value=items or [])
    svc.repo = repo
    return svc


@pytest.mark.anyio
async def test_team_week_rejects_outsider_who_is_not_division_manager(monkeypatch):
    svc = _service(member=False)
    check = AsyncMock(side_effect=AppError("FORBIDDEN", "bukan PM divisi ini", status=403))
    monkeypatch.setattr(es, "check_division_manager", check)
    user = SimpleNamespace(employee_id=str(uuid4()), role="PROJECT_MANAGER", email="pm@x")
    with pytest.raises(AppError):
        await svc.export_team_week(user, uuid4(), date(2026, 10, 26))  # type: ignore[arg-type]
    check.assert_awaited_once()


@pytest.mark.anyio
async def test_team_week_member_without_work_gets_clear_message(monkeypatch):
    svc = _service(member=True)
    check = AsyncMock()
    monkeypatch.setattr(es, "check_division_manager", check)
    user = SimpleNamespace(employee_id=str(uuid4()), role="TEAM_LEADER", email="ketua@x")
    with pytest.raises(AppError) as err:
        await svc.export_team_week(user, uuid4(), date(2026, 10, 26))  # type: ignore[arg-type]
    assert err.value.code == "NO_WORK"
    check.assert_not_awaited()  # anggota tim tidak perlu cek PM divisi


@pytest.mark.parametrize(
    ("name", "ascii_part", "utf8_part"),
    [
        ("Replacement CCTV — Gudang Duri.jpg", 'filename="Replacement CCTV  Gudang Duri.jpg"',
         "filename*=UTF-8''Replacement%20CCTV%20%E2%80%94%20Gudang%20Duri.jpg"),
        ('laporan "a".pptx', 'filename="laporan a.pptx"', "filename*=UTF-8''laporan%20%22a%22.pptx"),
    ],
)
def test_content_disposition_is_latin1_safe(name: str, ascii_part: str, utf8_part: str):
    header = content_disposition("inline", name)
    header.encode("latin-1")  # tidak boleh error (dulu → 500)
    assert header.startswith("inline; ") and ascii_part in header and utf8_part in header
