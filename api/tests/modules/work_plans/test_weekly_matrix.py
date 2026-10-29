"""
Matriks alokasi mingguan (PR-1): GET /work-plans/weekly memuat tim × 7 hari (Senin–Minggu) untuk divisi yang dikelola
PM/OM (`division_id` opsional = semua divisi PM). Sel memuat status, jenis (WORK/STANDBY), ringkasan item, dan sisa
target order. Peran lapangan (ketua/anggota) tidak boleh melihat matriks ini.
"""
from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

import pytest

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.daily import add_item, make_daily_plan
from tests.orders import make_client

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _today() -> str:
    return str(jakarta_now().date())


def _monday() -> str:
    today = jakarta_now().date()
    return str(today - timedelta(days=today.weekday()))


def _matrix(client, world: World, *, who: str = "pm", **params):
    return client.get("/work-plans/weekly", headers=world.headers(client, who), params=params)


def _cell(body: dict, team_id: str, work_date: str) -> dict:
    row = next(r for r in body["rows"] if r["team_id"] == team_id)
    return next(c for c in row["cells"] if c["work_date"] == work_date)


def _second_team(world: World, division_id: str | None = None) -> str:
    team = str(sync_query(
        "INSERT INTO team (office_id, division_id, leader_employee_id, name) VALUES (%s, %s, %s, %s) RETURNING team_id",
        (world.org_id, division_id or world.unit_id, world.employees["leader"], f"Tim C {world.tag} {uuid4().hex[:4]}"),
    )[0][0])
    return team


def test_matrix_has_seven_days_and_a_cell_per_day_for_every_team(client, world: World):
    plan = make_daily_plan(world, status="DRAFT", days_from_today=0)

    response = _matrix(client, world, week_start=_monday())

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["week_start"] == _monday()
    assert len(body["days"]) == 7 and body["days"][0] == _monday()
    row = next(r for r in body["rows"] if r["team_id"] == world.team_id)
    assert len(row["cells"]) == 7
    today = _cell(body, world.team_id, _today())
    assert today["daily_plan_id"] == plan
    assert today["status"] == "DRAFT" and today["kind"] == "WORK"
    empty = next(c for c in row["cells"] if c["work_date"] != _today())
    assert empty["daily_plan_id"] is None and empty["status"] is None and empty["kind"] is None
    assert empty["item_count"] == 0 and empty["items"] == [] and empty["orders"] == []


def test_matrix_rejects_week_start_that_is_not_monday(client, world: World):
    wednesday = date.fromisoformat(_monday()) + timedelta(days=2)
    response = _matrix(client, world, week_start=str(wednesday))
    assert response.status_code == 422, response.text


def test_matrix_is_hidden_from_field_roles(client, world: World):
    response = _matrix(client, world, who="leader", week_start=_monday())
    assert response.status_code == 403, response.text


def test_matrix_shows_standby_kind_and_item_summary(client, world: World):
    pm = world.headers(client, "pm")
    work = make_daily_plan(world, status="APPROVED", days_from_today=0)
    add_item(work, world, "Titik matriks")
    standby_team = _second_team(world)
    standby = client.post("/work-plans/daily/bulk-standby", headers=pm, json={
        "division_id": world.unit_id, "team_ids": [standby_team], "work_dates": [_today()],
    })
    assert standby.status_code == 200, standby.text

    body = _matrix(client, world, week_start=_monday()).json()

    siaga = _cell(body, standby_team, _today())
    assert siaga["kind"] == "STANDBY" and siaga["status"] == "APPROVED"
    assert siaga["item_count"] == 0
    cell = _cell(body, world.team_id, _today())
    assert cell["kind"] == "WORK" and cell["item_count"] == 1
    assert [i["title"] for i in cell["items"]] == ["Titik matriks"]


def test_matrix_reports_order_remaining_target_per_cell(client, world: World):
    pm = world.headers(client, "pm")
    created = client.post("/work-completions", headers=pm, json={
        "division_id": world.unit_id, "client_id": make_client(),
        "project_title": "Pekerjaan matriks", "total_target_unit": 10,
    })
    assert created.status_code in (200, 201), created.text
    cid = created.json()["completion_id"]
    plan = make_daily_plan(world, status="APPROVED", days_from_today=0)
    add_item(plan, world, "Titik order", completion_id=cid, target_qty=4)

    body = _matrix(client, world, week_start=_monday()).json()

    cell = _cell(body, world.team_id, _today())
    assert len(cell["orders"]) == 1
    order = cell["orders"][0]
    assert order["completion_id"] == cid
    assert order["remaining_qty"] == 10
    assert order["unscheduled_qty"] == 6


def test_matrix_lists_all_pm_divisions_and_filters_by_division(client, world: World):
    other_division = world.add_unit("Kedua")
    other_team = _second_team(world, other_division)

    all_divisions = _matrix(client, world, week_start=_monday()).json()
    assert {d["division_id"] for d in all_divisions["divisions"]} == {world.unit_id, other_division}
    team_ids = {r["team_id"] for r in all_divisions["rows"]}
    assert {world.team_id, other_team} <= team_ids

    only_other = _matrix(client, world, week_start=_monday(), division_id=other_division).json()
    assert {r["team_id"] for r in only_other["rows"]} == {other_team}
    assert {d["division_id"] for d in only_other["divisions"]} == {world.unit_id, other_division}


def test_matrix_refuses_division_outside_pm_scope(client, world: World):
    response = _matrix(client, world, week_start=_monday(), division_id=str(uuid4()))
    assert response.status_code == 404, response.text
