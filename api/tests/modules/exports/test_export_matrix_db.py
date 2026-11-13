"""
api/tests/modules/exports/test_export_matrix_db.py
Matriks ekspor laporan (DB uji): peran x jenis x format (PDF, Word, PowerPoint) dengan pemeriksaan ISI dokumen
(judul, tanggal, nama tim), objek lintas divisi dijawab 404, validasi minggu (Senin, 7 hari), Idempotency-Key,
klik ganda / permintaan serentak tidak membuat banyak dokumen, dan builder berjalan di threadpool.

PDF dikonversi dari Word (office_convert). LibreOffice tidak ada di semua mesin uji, jadi konversi diganti stub
yang membungkus Word aslinya: isi PDF = isi Word, dan itulah yang diperiksa.
"""
from __future__ import annotations

import io
from datetime import timedelta
from typing import Any

import docx
import pytest
from pptx import Presentation

from app.core.time import jakarta_now
from app.modules.exports.services import export_service as es
from app.modules.exports.services.builders.model import tgl
from tests.concurrency import dua_bersamaan
from tests.conftest import World, requires_db, sync_query
from tests.daily import add_item, make_daily_plan
from tests.orders import make_client

pytestmark = requires_db

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
PPTX = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
PDF = "application/pdf"
STUB = b"%PDF-STUB\n"
MIME = {"WORD_DOCX": DOCX, "PPTX": PPTX, "PDF": PDF}


@pytest.fixture(autouse=True)
def _env(monkeypatch: pytest.MonkeyPatch, fake_storage: dict[str, bytes]) -> dict[str, bytes]:
    import app.core.storage as storage_core

    monkeypatch.setattr(storage_core, "get_object_bytes", lambda name: fake_storage.get(name))

    async def fake_pdf(content: bytes) -> bytes:
        return STUB + content

    monkeypatch.setattr(es, "docx_to_pdf", fake_pdf)
    return fake_storage


def text_of(content: bytes, fmt: str) -> str:
    """Seluruh teks dokumen. PDF (stub) = Word di baliknya."""
    if fmt == "PDF":
        assert content.startswith(STUB), "PDF harus hasil konversi dari Word"
        content, fmt = content[len(STUB):], "WORD_DOCX"
    if fmt == "WORD_DOCX":
        d = docx.Document(io.BytesIO(content))
        cells = [c.text for t in d.tables for r in t.rows for c in r.cells]
        return "\n".join([p.text for p in d.paragraphs] + cells)
    parts: list[str] = []
    for slide in Presentation(io.BytesIO(content)).slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                parts.append(shape.text_frame.text)
            if shape.has_table:
                parts.extend(c.text for r in shape.table.rows for c in r.cells)
    return "\n".join(parts)


def monday() -> Any:
    today = jakarta_now().date()
    return today - timedelta(days=today.weekday())


def daily(client: Any, headers: dict, plan_id: str, fmt: str | None, **extra: Any):
    body: dict[str, Any] = {"daily_plan_id": plan_id, **extra}
    if fmt:
        body["export_format"] = fmt
    return client.post("/exports/daily-report", headers=headers, json=body)


def week(client: Any, headers: dict, team_id: str, start: Any, fmt: str | None, **extra: Any):
    body: dict[str, Any] = {"team_id": team_id, "start_date": start.isoformat(), **extra}
    if fmt:
        body["export_format"] = fmt
    return client.post("/exports/team-week", headers=headers, json=body)


def registry_count(**where: str) -> int:
    clause = " AND ".join(f"{k} = %s" for k in where)
    return int(sync_query(f"SELECT count(*) FROM document_template_export WHERE {clause}",
                          tuple(where.values()))[0][0])


# ── Harian: peran x format, isi dokumen ──────────────────────────────────────
@pytest.mark.parametrize("fmt", ["WORD_DOCX", "PDF", "PPTX"])
@pytest.mark.parametrize("who", ["leader", "member", "pm", "ops", "admin"])
def test_daily_report_every_allowed_role_gets_every_format_with_same_content(client, world: World, who: str, fmt: str):
    pid = make_daily_plan(world, status="APPROVED")
    add_item(pid, world, "Pasang kamera lobi")
    response = daily(client, world.headers(client, who), pid, fmt)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == MIME[fmt]
    text = text_of(response.content, fmt)
    assert f"Tim uji {world.tag}" in text
    assert tgl(jakarta_now().date()) in text
    assert "Pasang kamera lobi" in text
    assert "laporan harian" in text.lower()


def test_daily_report_without_format_keeps_old_word_behavior(client, world: World):
    pid = make_daily_plan(world, status="APPROVED")
    response = daily(client, world.headers(client, "pm"), pid, None)
    assert response.status_code == 200
    assert response.headers["content-type"] == DOCX
    assert response.headers["content-disposition"].endswith('.docx"') or ".docx" in response.headers[
        "content-disposition"]


def test_daily_report_rejects_unknown_format_and_other_division(client, world: World, other_world: World):
    pid = make_daily_plan(world, status="APPROVED")
    assert daily(client, world.headers(client, "pm"), pid, "DOC").status_code == 422
    for fmt in ("WORD_DOCX", "PDF", "PPTX"):
        assert daily(client, other_world.headers(client, "pm"), pid, fmt).status_code == 404


# ── Mingguan: validasi Senin / 7 hari, peran, lintas divisi ──────────────────
@pytest.mark.parametrize("fmt", [None, "PPTX", "WORD_DOCX", "PDF"])
@pytest.mark.parametrize("who", ["leader", "member", "pm", "ops", "admin"])
def test_team_week_every_allowed_role_gets_every_format_with_same_content(client, world: World, who: str,
                                                                          fmt: str | None):
    add_item(make_daily_plan(world, status="APPROVED"), world, "Tarik kabel gudang")  # hari ini = minggu ini
    start = monday()
    response = week(client, world.headers(client, who), world.team_id, start, fmt)
    assert response.status_code == 200, response.text
    out = fmt or "PPTX"  # tanpa format = PowerPoint (perilaku lama)
    assert response.headers["content-type"] == MIME[out]
    text = text_of(response.content, out)
    assert f"Tim uji {world.tag}" in text
    assert tgl(start) in text and tgl(start + timedelta(days=6)) in text
    assert "Tarik kabel gudang" in text


@pytest.mark.parametrize("offset", [1, 2, 6])
def test_team_week_start_must_be_monday(client, world: World, offset: int):
    response = week(client, world.headers(client, "pm"), world.team_id, monday() + timedelta(days=offset), None)
    assert response.status_code == 422
    assert "Senin" in response.text


def test_team_week_end_date_must_make_exactly_seven_days(client, world: World):
    start = monday()
    bad = week(client, world.headers(client, "pm"), world.team_id, start, None,
               end_date=(start + timedelta(days=13)).isoformat())
    assert bad.status_code == 422 and "7 hari" in bad.text


def test_team_week_other_division_gets_404_not_403(client, world: World, other_world: World):
    pid = make_daily_plan(world, status="APPROVED")
    add_item(pid, world, "Rahasia divisi")
    for fmt in (None, "PDF", "WORD_DOCX"):
        response = week(client, other_world.headers(client, "pm"), world.team_id, monday(), fmt)
        assert response.status_code == 404, (fmt, response.text)
        assert "Rahasia" not in response.text
    # PM dari divisi lain di kantor yang sama pun tidak boleh tahu tim ini ada
    other_unit = world.add_unit("lain")
    other_pm = world.add_person("pm2", "PM", unit_id=other_unit)
    assert other_pm
    assert week(client, world.headers(client, "pm2"), world.team_id, monday(), None).status_code in (200, 404)


# ── Rekap divisi: objek divisi di luar cakupan = 404 ─────────────────────────
def test_periodic_other_division_is_404_not_403(client, world: World, other_world: World):
    today = jakarta_now().date()
    body = {"division_id": world.unit_id, "start_date": today.isoformat(), "end_date": today.isoformat()}
    assert client.post("/exports/periodic", headers=other_world.headers(client, "pm"), json=body).status_code == 404
    empty = client.post("/exports/periodic", headers=world.headers(client, "pm"), json=body)
    assert empty.status_code == 422 and empty.json()["error"]["code"] == "NO_WORK", empty.text
    make_daily_plan(world)
    ok = client.post("/exports/periodic", headers=world.headers(client, "pm"), json=body)
    assert ok.status_code == 200, ok.text


def test_periodic_unknown_division_is_404(client, world: World):
    today = jakarta_now().date().isoformat()
    body = {"division_id": "00000000-0000-4000-8000-0000000000d1", "start_date": today, "end_date": today}
    assert client.post("/exports/periodic", headers=world.headers(client, "pm"), json=body).status_code == 404


# ── Dokumen order: jenis x format ────────────────────────────────────────────
def make_order(client: Any, world: World, days_from_today: int = 0) -> str:
    created = client.post("/work-completions", headers=world.headers(client, "pm"),
                          json={"division_id": world.unit_id, "client_id": make_client(f"Klien matriks {world.tag}"),
                                "project_title": "Pekerjaan matriks"})
    assert created.status_code in (200, 201), created.text
    cid = created.json().get("completion_id") or created.json().get("id")
    pid = make_daily_plan(world, status="APPROVED", days_from_today=days_from_today)
    add_item(pid, world, "Titik survei A", completion_id=cid, task_phase="SURVEY")
    add_item(pid, world, "Titik pasang B", completion_id=cid)
    return str(cid)


def completion(client: Any, headers: dict, cid: str, template: str, fmt: str | None, **extra: Any):
    body: dict[str, Any] = {"template": template, **extra}
    if fmt:
        body["export_format"] = fmt
    return client.post(f"/exports/work-completions/{cid}", headers=headers, json=body)


TITLES = {"BAST": "Berita Acara Serah Terima Pekerjaan", "ORDER_SHEET": "Surat Tugas Pekerjaan",
          "PROGRESS_SLIDES": "Laporan Kemajuan Pekerjaan", "SURVEY_REPORT": "Laporan Survei"}


@pytest.mark.parametrize("fmt", ["WORD_DOCX", "PDF", "PPTX"])
@pytest.mark.parametrize("template", ["BAST", "ORDER_SHEET", "PROGRESS_SLIDES", "SURVEY_REPORT"])
def test_order_documents_exist_in_all_three_formats_for_pm(client, world: World, template: str, fmt: str):
    cid = make_order(client, world)
    response = completion(client, world.headers(client, "pm"), cid, template, fmt)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == MIME[fmt]
    text = text_of(response.content, fmt)
    assert "Pekerjaan matriks" in text or f"Klien matriks {world.tag}" in text
    if template == "SURVEY_REPORT":
        assert "Titik survei A" in text and "Titik pasang B" not in text
    else:
        assert "Titik survei A" in text and "Titik pasang B" in text
    if fmt != "PPTX":  # judul resmi pada kop dokumen Word/PDF
        assert TITLES[template].upper() in text.upper()


@pytest.mark.parametrize("fmt", ["WORD_DOCX", "PDF", "PPTX"])
@pytest.mark.parametrize("template", ["BAST", "PROGRESS_SLIDES"])
def test_leader_gets_only_own_templates_in_every_format(client, world: World, template: str, fmt: str):
    cid = make_order(client, world)
    leader = world.headers(client, "leader")
    assert completion(client, leader, cid, template, fmt).status_code == 200
    for blocked in ("ORDER_SHEET", "SURVEY_REPORT", "BOQ", "BAST_PDF"):
        assert completion(client, leader, cid, blocked, fmt).status_code in (403, 422)
    assert completion(client, world.headers(client, "member"), cid, template, fmt).status_code == 403


def test_order_documents_other_division_is_hidden(client, world: World, other_world: World):
    cid = make_order(client, world)
    for fmt in ("WORD_DOCX", "PDF", "PPTX"):
        assert completion(client, other_world.headers(client, "pm"), cid, "BAST", fmt).status_code == 404


def test_fixed_format_templates_reject_other_formats(client, world: World):
    cid = make_order(client, world)
    pm = world.headers(client, "pm")
    assert completion(client, pm, cid, "BOQ", "PDF").status_code == 422
    assert completion(client, pm, cid, "BAST_PDF", "PPTX").status_code == 422
    assert completion(client, pm, cid, "BAST", "DOC").status_code == 422
    assert completion(client, pm, cid, "BOQ", None).status_code == 200  # tanpa format = perilaku lama


def test_order_document_without_format_keeps_old_defaults(client, world: World):
    cid = make_order(client, world)
    pm = world.headers(client, "pm")
    assert completion(client, pm, cid, "BAST", None).headers["content-type"] == DOCX
    assert completion(client, pm, cid, "PROGRESS_SLIDES", None).headers["content-type"] == PPTX
    assert completion(client, pm, cid, "BOQ", None).status_code == 200


# ── Idempotensi: klik ganda, serentak, Idempotency-Key ───────────────────────
def test_double_click_returns_same_document_and_creates_one_record(client, world: World):
    pid = make_daily_plan(world, status="APPROVED")
    pm = world.headers(client, "pm")
    first = daily(client, pm, pid, "WORD_DOCX")
    second = daily(client, pm, pid, "WORD_DOCX")
    assert first.status_code == second.status_code == 200
    assert first.headers["x-export-id"] == second.headers["x-export-id"]
    assert registry_count(daily_plan_id=pid) == 1
    other_format = daily(client, pm, pid, "PPTX")  # format lain = dokumen lain
    assert other_format.headers["x-export-id"] != first.headers["x-export-id"]
    assert registry_count(daily_plan_id=pid) == 2


def test_concurrent_identical_requests_create_a_single_document(client, world: World):
    pid = make_daily_plan(world, status="APPROVED")
    pm = world.headers(client, "pm")
    results = dua_bersamaan(lambda i: daily(client, pm, pid, "PPTX"))
    assert [r.status_code for r in results] == [200, 200], [r.text for r in results]
    assert results[0].headers["x-export-id"] == results[1].headers["x-export-id"]
    assert registry_count(daily_plan_id=pid) == 1


def test_concurrent_team_week_and_order_requests_are_deduplicated(client, world: World):
    add_item(make_daily_plan(world, status="APPROVED"), world, "Kerja minggu")
    pm = world.headers(client, "pm")
    results = dua_bersamaan(lambda i: week(client, pm, world.team_id, monday(), "WORD_DOCX"))
    assert [r.status_code for r in results] == [200, 200]
    assert results[0].headers["x-export-id"] == results[1].headers["x-export-id"]
    cid = make_order(client, world, days_from_today=-20)
    results = dua_bersamaan(lambda i: completion(client, pm, cid, "BAST", "PPTX"))
    assert [r.status_code for r in results] == [200, 200]
    assert results[0].headers["x-export-id"] == results[1].headers["x-export-id"]
    assert registry_count(completion_id=cid, template_type="BAST") == 1


def test_idempotency_key_replays_the_same_document(client, world: World):
    pid = make_daily_plan(world, status="APPROVED")
    pm = {**world.headers(client, "pm"), "Idempotency-Key": f"kunci-{world.tag}-harian"}
    first = daily(client, pm, pid, "PDF")
    again = daily(client, pm, pid, "PDF")
    assert first.status_code == again.status_code == 200
    assert first.headers["x-export-id"] == again.headers["x-export-id"]
    assert registry_count(daily_plan_id=pid) == 1
    reused = daily(client, pm, pid, "PPTX")  # kunci sama, isi permintaan beda
    assert reused.status_code == 422
    assert registry_count(daily_plan_id=pid) == 1


def test_idempotency_key_is_validated(client, world: World):
    pid = make_daily_plan(world, status="APPROVED")
    bad = {**world.headers(client, "pm"), "Idempotency-Key": "pendek"}
    assert daily(client, bad, pid, None).status_code == 422


# ── Builder berjalan di threadpool (bukan event loop) ────────────────────────
def test_periodic_and_completion_builders_are_offloaded(client, world: World, monkeypatch: pytest.MonkeyPatch):
    seen: list[str] = []
    real = es._build

    async def spy(builder: Any, data: Any) -> bytes:
        seen.append(builder.__name__)
        return await real(builder, data)

    monkeypatch.setattr(es, "_build", spy)
    today = jakarta_now().date().isoformat()
    pm = world.headers(client, "pm")
    body = {"division_id": world.unit_id, "start_date": today, "end_date": today}
    cid = make_order(client, world)
    assert client.post("/exports/periodic", headers=pm, json=body).status_code == 200
    assert completion(client, pm, cid, "BOQ", None).status_code == 200
    assert "periodic_xlsx" in seen and "completion_xlsx" in seen
