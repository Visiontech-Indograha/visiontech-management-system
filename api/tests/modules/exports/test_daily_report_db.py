"""
api/tests/modules/exports/test_daily_report_db.py
Uji integrasi (DB uji) laporan harian cetak: SQL daily_header/daily_items berjalan, akses mengikuti jadwal
(ketua/PM melihat jadwal yang dirilis; lain 404), dan berkas .docx yang diunduh memuat data jadwal.
"""
from __future__ import annotations

import io

import docx

from tests.conftest import World, requires_db
from tests.daily import make_daily_plan

pytestmark = requires_db

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _text(content: bytes) -> str:
    d = docx.Document(io.BytesIO(content))
    cells = [c.text for t in d.tables for r in t.rows for c in r.cells]
    return "\n".join([p.text for p in d.paragraphs] + cells)


def _export(client, who_headers: dict, plan_id: str):
    return client.post("/exports/daily-report", headers=who_headers, json={"daily_plan_id": plan_id})


def test_released_plan_prints_for_leader_and_pm(client, world: World, fake_storage):
    pid = make_daily_plan(world, status="APPROVED")
    leader = _export(client, world.headers(client, "leader"), pid)
    assert leader.status_code == 200, leader.text
    assert leader.headers["content-type"] == DOCX
    assert "Laporan-harian-tim" in leader.headers["content-disposition"]
    assert f"Tim uji {world.tag}" in _text(leader.content)
    assert "Belum ada item pekerjaan pada jadwal ini." in _text(leader.content)

    pm = _export(client, world.headers(client, "pm"), pid)
    assert pm.status_code == 200, pm.text


def test_unreleased_plan_is_hidden_from_team_and_outsiders(client, world: World, other_world: World, fake_storage):
    pid = make_daily_plan(world, status="DRAFT")
    assert _export(client, world.headers(client, "leader"), pid).status_code == 404
    assert _export(client, world.headers(client, "member"), pid).status_code == 404
    assert _export(client, other_world.headers(client, "pm"), pid).status_code == 404


def test_missing_plan_is_not_found(client, world: World, fake_storage):
    response = _export(client, world.headers(client, "pm"), "00000000-0000-4000-8000-0000000000d9")
    assert response.status_code == 404
