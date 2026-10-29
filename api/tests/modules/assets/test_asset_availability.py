"""
Bentrok aset per tanggal (butir 7): alat yang dipakai tim lain pada tanggal jadwal yang sama ditolak; pada tanggal
lain boleh. GET /assets/availability melaporkan tim pemakai per tanggal. Peminjaman dilepas otomatis saat jadwal
selesai.
"""
from __future__ import annotations

import pytest

from tests.conftest import World, requires_db, sync_query
from tests.daily import make_daily_plan
from tests.modules.assets.test_asset_master import create_tool

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _plan(world: World, team_id: str, days: int) -> str:
    return str(sync_query(
        "INSERT INTO work_plan_daily (work_date, site_name, site_lat, site_lng, division_id, team_id, created_by_id) "
        "VALUES ((now() AT TIME ZONE 'Asia/Jakarta')::date + %s, 'Site uji', -6.2, 106.8, %s, %s, %s) "
        "RETURNING daily_plan_id",
        (days, world.unit_id, team_id, world.employees["pm"]))[0][0])


def _second_team(world: World) -> str:
    team = str(sync_query(
        "INSERT INTO team (office_id, division_id, leader_employee_id, name) "
        "VALUES (%s, %s, %s, %s) RETURNING team_id",
        (world.org_id, world.unit_id, world.employees["leader"], f"Tim B {world.tag}"))[0][0])
    sync_query("INSERT INTO member (team_id, employee_id) VALUES (%s, %s)", (team, world.employees["member"]))
    return team


def _lend_plan(client, world: World, tool_id: str, plan_id: str):
    return client.post("/assets/loans", headers=world.headers(client, "hr"), json={
        "asset_type": "TOOL", "tool_id": tool_id, "employee_id": world.employees["member"],
        "daily_plan_id": plan_id})


def _day(days: int) -> str:
    return str(sync_query("SELECT ((now() AT TIME ZONE 'Asia/Jakarta')::date + %s)::text", (days,))[0][0])


def test_other_day_is_free_for_the_same_asset(client, world: World):
    tool_id = create_tool(client, world).json()["tool_id"]
    first = _lend_plan(client, world, tool_id, _plan(world, world.team_id, 1))
    assert first.status_code == 201, first.text

    second = _lend_plan(client, world, tool_id, _plan(world, world.team_id, 2))

    assert second.status_code == 201, second.text


def test_same_day_for_another_team_is_refused_with_team_name(client, world: World):
    tool_id = create_tool(client, world).json()["tool_id"]
    assert _lend_plan(client, world, tool_id, _plan(world, world.team_id, 1)).status_code == 201
    other_team = _second_team(world)

    clash = _lend_plan(client, world, tool_id, _plan(world, other_team, 1))

    assert clash.status_code == 409, clash.text
    assert clash.json()["error"]["code"] == "ASSET_NOT_AVAILABLE"
    assert f"Tim uji {world.tag}" in clash.json()["error"]["message"]


def test_availability_reports_team_using_asset_on_date(client, world: World):
    tool_id = create_tool(client, world).json()["tool_id"]
    assert _lend_plan(client, world, tool_id, _plan(world, world.team_id, 1)).status_code == 201
    other_team = _second_team(world)
    hr = world.headers(client, "hr")

    busy = client.get("/assets/availability", headers=hr,
                      params={"date": _day(1), "team_id": other_team})
    free = client.get("/assets/availability", headers=hr,
                      params={"date": _day(2), "team_id": other_team})

    row = next(r for r in busy.json() if r["asset_id"] == tool_id)
    assert row["available"] is False
    assert row["used_by_team_id"] == world.team_id
    assert row["used_by_team_name"] == f"Tim uji {world.tag}"
    assert row["used_by_requested_team"] is False
    row_free = next(r for r in free.json() if r["asset_id"] == tool_id)
    assert row_free["available"] is True
    assert row_free["used_by_team_id"] is None


def test_completing_plan_releases_its_loans(client, world: World):
    tool_id = create_tool(client, world).json()["tool_id"]
    plan = make_daily_plan(world, status="ONGOING", days_from_today=0)
    loan = _lend_plan(client, world, tool_id, plan)
    assert loan.status_code == 201, loan.text
    leader = world.headers(client, "leader")
    assert client.post(f"/work-plans/daily/{plan}/report", headers=leader,
                       json={"summary": "Selesai", "photos_json": []}).status_code == 201

    done = client.post(f"/work-plans/daily/{plan}/complete", headers=leader)

    assert done.status_code == 200, done.text
    returned = sync_query("SELECT returned_at IS NOT NULL FROM asset_assignment WHERE assignment_id = %s",
                          (loan.json()["assignment_id"],))[0][0]
    assert returned is True
    status = sync_query("SELECT status::text FROM tool WHERE tool_id = %s", (tool_id,))[0][0]
    assert status == "ready"
