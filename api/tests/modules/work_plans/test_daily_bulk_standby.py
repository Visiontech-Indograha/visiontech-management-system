"""
Alokasi massal & siaga (matriks mingguan): POST /work-plans/daily/bulk membuat jadwal per sel (tim × tanggal) dan
melaporkan sel yang bentrok tanpa membatalkan sel lain; siaga hari kosong hanya mengisi sel kosong; aktivasi
mengubah jadwal siaga jadi pekerjaan (kind WORK) dan menolak jadwal kerja biasa.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.daily import make_daily_plan

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _day(offset: int) -> str:
    return str(jakarta_now().date() + timedelta(days=offset))


def _cells(body: dict) -> dict[tuple[str, str], dict]:
    return {(c["team_id"], c["work_date"]): c for c in body["cells"]}


def test_bulk_creates_drafts_and_reports_taken_cell_without_rollback(client, world: World):
    pm = world.headers(client, "pm")
    taken = _day(5)
    make_daily_plan(world, status="DRAFT", days_from_today=5)  # tim sudah punya jadwal di tanggal 'taken'

    response = client.post("/work-plans/daily/bulk", headers=pm, json={
        "division_id": world.unit_id, "team_ids": [world.team_id], "work_dates": [taken, _day(6), _day(7)],
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["created"] == 2 and body["skipped"] == 1
    cell = _cells(body)[(world.team_id, taken)]
    assert cell["status"] == "SKIPPED" and cell["reason"] == "TEAM_DAY_TAKEN"
    created = [c for c in body["cells"] if c["status"] == "CREATED"]
    assert all(c["daily_plan_id"] for c in created)
    status = sync_query("SELECT status, kind FROM work_plan_daily WHERE daily_plan_id = %s",
                        (created[0]["daily_plan_id"],))[0]
    assert status == ("DRAFT", "WORK")


def test_bulk_reports_team_outside_division_and_past_dates(client, world: World):
    pm = world.headers(client, "pm")
    other_division = world.add_unit("Lain")

    response = client.post("/work-plans/daily/bulk", headers=pm, json={
        "division_id": other_division, "team_ids": [world.team_id], "work_dates": [_day(3)],
    })
    assert response.status_code == 200, response.text
    assert _cells(response.json())[(world.team_id, _day(3))]["reason"] == "TEAM_BUKAN_DIVISI"

    past = client.post("/work-plans/daily/bulk", headers=pm, json={
        "division_id": world.unit_id, "team_ids": [world.team_id], "work_dates": [_day(-2)],
    })
    assert past.status_code == 200, past.text
    assert past.json()["cells"][0]["reason"] == "TANGGAL_LAMPAU"


def test_bulk_refuses_approved_target_for_work_plans(client, world: World):
    pm = world.headers(client, "pm")
    response = client.post("/work-plans/daily/bulk", headers=pm, json={
        "division_id": world.unit_id, "team_ids": [world.team_id], "work_dates": [_day(4)], "target": "APPROVED",
    })
    assert response.status_code == 422, response.text


def test_bulk_standby_fills_only_empty_days_as_approved(client, world: World):
    pm = world.headers(client, "pm")
    busy = _day(8)
    make_daily_plan(world, status="DRAFT", days_from_today=8)

    response = client.post("/work-plans/daily/bulk-standby", headers=pm, json={
        "division_id": world.unit_id, "team_ids": [world.team_id], "work_dates": [busy, _day(9)],
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert _cells(body)[(world.team_id, busy)]["reason"] == "TEAM_DAY_TAKEN"
    created = next(c for c in body["cells"] if c["status"] == "CREATED")
    row = sync_query("SELECT status, kind FROM work_plan_daily WHERE daily_plan_id = %s",
                     (created["daily_plan_id"],))[0]
    assert row == ("APPROVED", "STANDBY")


def test_activate_turns_standby_into_work_with_item(client, world: World):
    pm = world.headers(client, "pm")
    standby = client.post("/work-plans/daily/bulk-standby", headers=pm, json={
        "division_id": world.unit_id, "team_ids": [world.team_id], "work_dates": [_day(10)],
    }).json()["cells"][0]["daily_plan_id"]
    work_type = str(sync_query("INSERT INTO work_type (division_id, name) VALUES (%s, %s) RETURNING work_type_id",
                               (world.unit_id, f"Jenis aktivasi {world.tag}"))[0][0])

    activated = client.post(f"/work-plans/daily/{standby}/activate", headers=pm, json={
        "items": [{"work_type_id": work_type, "title": "Titik aktivasi uji", "target_qty": 1}],
    })
    assert activated.status_code == 200, activated.text
    assert activated.json()["kind"] == "WORK"
    assert activated.json()["status"] == "APPROVED"
    assert activated.json()["item_count"] == 1

    again = client.post(f"/work-plans/daily/{standby}/activate", headers=pm, json={
        "items": [{"work_type_id": work_type, "title": "Titik kedua uji", "target_qty": 1}],
    })
    assert again.status_code == 409 and "BUKAN_SIAGA" in again.text


def test_activate_refuses_plain_work_plan(client, world: World):
    plan = make_daily_plan(world, status="DRAFT", days_from_today=11)
    work_type = str(sync_query("INSERT INTO work_type (division_id, name) VALUES (%s, %s) RETURNING work_type_id",
                               (world.unit_id, f"Jenis kerja {world.tag}"))[0][0])
    response = client.post(f"/work-plans/daily/{plan}/activate", headers=world.headers(client, "pm"), json={
        "items": [{"work_type_id": work_type, "title": "Titik kerja uji", "target_qty": 1}],
    })
    assert response.status_code == 409, response.text
    assert "BUKAN_SIAGA" in response.text
