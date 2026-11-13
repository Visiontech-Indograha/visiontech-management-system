"""
api/tests/modules/exports/test_export_monthly_db.py
Laporan bulanan divisi: bulan kalender (tahun + bulan), tiga format dengan isi setara, izin sama dengan rekap divisi
(PM/OM divisi atau SUPER_ADMIN), divisi lain 404, validasi tahun/bulan, dan klik ganda tidak membuat dokumen ganda.
"""
from __future__ import annotations

import pytest

from app.core.time import jakarta_now
from app.modules.exports.services.builders.model import month_label
from tests.conftest import World, requires_db, sync_query
from tests.daily import make_daily_plan
from tests.modules.exports.test_export_matrix_db import MIME, _env, text_of  # noqa: F401

pytestmark = requires_db


def plan_on(world: World, day: str) -> None:
    """Satu jadwal harian tim pada tanggal tertentu (agar bulannya tidak kosong)."""
    sync_query(
        "INSERT INTO work_plan_daily (division_id, team_id, work_date, site_name, status, created_by_id) "
        "VALUES (%s, %s, %s, 'Site uji', 'APPROVED', %s)",
        (world.unit_id, world.team_id, day, world.employees["pm"]))


def monthly(client, headers: dict, division_id: str, year: int, month: int, fmt: str | None = None):
    body = {"division_id": division_id, "year": year, "month": month}
    if fmt:
        body["export_format"] = fmt
    return client.post("/exports/monthly", headers=headers, json=body)


@pytest.mark.parametrize("fmt", [None, "WORD_DOCX", "PDF", "PPTX"])
@pytest.mark.parametrize("who", ["pm", "ops", "admin"])
def test_monthly_report_for_managers_in_every_format_with_same_content(client, world: World, who: str,
                                                                       fmt: str | None):
    today = jakarta_now().date()
    make_daily_plan(world)
    response = monthly(client, world.headers(client, who), world.unit_id, today.year, today.month, fmt)
    assert response.status_code == 200, response.text
    out = fmt or "WORD_DOCX"
    assert response.headers["content-type"] == MIME[out]
    text = text_of(response.content, out)
    assert "laporan bulanan" in text.lower()
    assert month_label(today.replace(day=1)) in text
    assert "Divisi uji" in text


def test_monthly_covers_the_whole_calendar_month(client, world: World):
    for day in ("2026-02-10", "2028-02-10", "2026-12-10"):
        plan_on(world, day)
    response = monthly(client, world.headers(client, "pm"), world.unit_id, 2026, 2, "WORD_DOCX")
    assert response.status_code == 200
    text = text_of(response.content, "WORD_DOCX")
    assert "1 Februari 2026" in text and "28 Februari 2026" in text
    leap = monthly(client, world.headers(client, "pm"), world.unit_id, 2028, 2, "WORD_DOCX")
    assert "29 Februari 2028" in text_of(leap.content, "WORD_DOCX")
    december = monthly(client, world.headers(client, "pm"), world.unit_id, 2026, 12, "PPTX")
    assert "31 Desember 2026" in text_of(december.content, "PPTX")
    row = sync_query("SELECT period_start_date, period_end_date FROM document_template_export "
                     "WHERE template_type = 'MONTHLY_REPORT' AND generated_by_id = %s ORDER BY create_at DESC LIMIT 1",
                     (world.employees["pm"],))[0]
    assert (str(row[0]), str(row[1])) == ("2026-12-01", "2026-12-31")


def test_monthly_permissions_and_cross_division(client, world: World, other_world: World):
    today = jakarta_now().date()
    for who in ("leader", "member"):
        assert monthly(client, world.headers(client, who), world.unit_id, today.year, today.month).status_code == 403
    for fmt in (None, "PDF", "PPTX"):
        response = monthly(client, other_world.headers(client, "pm"), world.unit_id, today.year, today.month, fmt)
        assert response.status_code == 404, (fmt, response.text)
    missing = monthly(client, world.headers(client, "pm"), "00000000-0000-4000-8000-0000000000d2", today.year,
                      today.month)
    assert missing.status_code == 404


@pytest.mark.parametrize(("year", "month"), [(2026, 0), (2026, 13), (1999, 5), (2101, 5)])
def test_monthly_validates_year_and_month(client, world: World, year: int, month: int):
    response = monthly(client, world.headers(client, "pm"), world.unit_id, year, month)
    assert response.status_code == 422


def test_monthly_rejects_unknown_format_and_double_click_is_deduplicated(client, world: World):
    pm = world.headers(client, "pm")
    plan_on(world, "2026-10-05")
    assert monthly(client, pm, world.unit_id, 2026, 10, "DOC").status_code == 422
    first = monthly(client, pm, world.unit_id, 2026, 10, "PPTX")
    second = monthly(client, pm, world.unit_id, 2026, 10, "PPTX")
    assert first.headers["x-export-id"] == second.headers["x-export-id"]
    count = sync_query("SELECT count(*) FROM document_template_export WHERE template_type = 'MONTHLY_REPORT' "
                       "AND generated_by_id = %s", (world.employees["pm"],))[0][0]
    assert count == 1


@pytest.mark.parametrize("fmt", [None, "WORD_DOCX", "PDF", "PPTX"])
def test_monthly_without_work_is_422_no_work_not_empty_document(client, world: World, fmt: str | None):
    response = monthly(client, world.headers(client, "pm"), world.unit_id, 2026, 2, fmt)
    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "NO_WORK"
    assert "bulan tersebut" in response.json()["error"]["message"]
    count = sync_query("SELECT count(*) FROM document_template_export WHERE template_type = 'MONTHLY_REPORT' "
                       "AND generated_by_id = %s", (world.employees["pm"],))[0][0]
    assert count == 0
