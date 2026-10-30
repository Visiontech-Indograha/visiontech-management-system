"""
Peringatan per sel pada alokasi massal (matriks mingguan): ketua yang sedang cuti dan aset (alat/kendaraan) yang
sedang dipinjam pada tanggal sel. Peringatan tidak menggagalkan sel: sel tetap dibuat (CREATED) dan membawa daftar
`warnings`.
"""
from __future__ import annotations

from uuid import uuid4

import pytest

from tests.conftest import World, requires_db, sync_query
from tests.modules.assets.test_asset_master import create_tool

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _day(days: int) -> str:
    return str(sync_query("SELECT ((now() AT TIME ZONE 'Asia/Jakarta')::date + %s)::text", (days,))[0][0])


def _cells(body: dict) -> dict[tuple[str, str], dict]:
    return {(c["team_id"], c["work_date"]): c for c in body["cells"]}


def _second_team(world: World) -> str:
    team = str(sync_query(
        "INSERT INTO team (office_id, division_id, leader_employee_id, name) VALUES (%s, %s, %s, %s) RETURNING team_id",
        (world.org_id, world.unit_id, world.employees["member"], f"Tim D {world.tag} {uuid4().hex[:4]}"),
    )[0][0])
    return team


def _plan_on(world: World, team_id: str, days: int) -> str:
    return str(sync_query(
        "INSERT INTO work_plan_daily (work_date, site_name, site_lat, site_lng, division_id, team_id, created_by_id) "
        "VALUES ((now() AT TIME ZONE 'Asia/Jakarta')::date + %s, 'Site uji', -6.2, 106.8, %s, %s, %s) "
        "RETURNING daily_plan_id",
        (days, world.unit_id, team_id, world.employees["pm"]))[0][0])


def test_bulk_warns_when_team_leader_is_on_leave(client, world: World):
    pm = world.headers(client, "pm")
    sync_query(
        "INSERT INTO leave_request (employee_id, leave_type, start_date, end_date, total_days, reason, status) "
        "VALUES (%s, 'ANNUAL', %s::date, %s::date, 1, 'Cuti uji', 'APPROVED_BY_HR')",
        (world.employees["leader"], _day(3), _day(3)),
    )

    body = client.post("/work-plans/daily/bulk", headers=pm, json={
        "division_id": world.unit_id, "team_ids": [world.team_id], "work_dates": [_day(3), _day(4)],
    }).json()

    on_leave = _cells(body)[(world.team_id, _day(3))]
    assert on_leave["status"] == "CREATED"
    assert [w["code"] for w in on_leave["warnings"]] == ["LEADER_CUTI"]
    assert _cells(body)[(world.team_id, _day(4))]["warnings"] == []


def test_bulk_warns_when_asset_is_loaned_on_the_cell_date(client, world: World):
    hr = world.headers(client, "hr")
    pm = world.headers(client, "pm")
    tool_id = create_tool(client, world).json()["tool_id"]
    lend = client.post("/assets/loans", headers=hr, json={
        "asset_type": "TOOL", "tool_id": tool_id, "employee_id": world.employees["member"],
        "daily_plan_id": _plan_on(world, world.team_id, 5)})
    assert lend.status_code == 201, lend.text
    other_team = _second_team(world)

    body = client.post("/work-plans/daily/bulk", headers=pm, json={
        "division_id": world.unit_id, "team_ids": [other_team], "work_dates": [_day(5), _day(6)],
        "assets": [{"asset_type": "TOOL", "asset_id": tool_id}],
    }).json()

    clash = _cells(body)[(other_team, _day(5))]
    assert clash["status"] == "CREATED"
    assert [w["code"] for w in clash["warnings"]] == ["ASET_BENTROK"]
    assert _cells(body)[(other_team, _day(6))]["warnings"] == []


def test_bulk_without_assets_or_leave_has_no_warnings(client, world: World):
    body = client.post("/work-plans/daily/bulk", headers=world.headers(client, "pm"), json={
        "division_id": world.unit_id, "team_ids": [world.team_id], "work_dates": [_day(8)],
    }).json()
    assert _cells(body)[(world.team_id, _day(8))]["warnings"] == []
