"""
A2 · Cakupan data aset & jadwal. Pinjaman terlihat sesuai peran: pengelola aset (MANAGE_ASSETS) semua; PM/OM
(VIEW_TEAMS) hanya pinjaman divisinya atau jadwal yang ia kelola; lainnya hanya miliknya. Id acak → 404.
"""
from __future__ import annotations

import uuid

import pytest

from tests.conftest import World, requires_db, sync_query
from tests.modules.assets.test_asset_master import create_tool

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _lend(client, world: World, **body):
    return client.post("/assets/loans", headers=world.headers(client, "hr"),
                       json={"employee_id": world.employees["member"], **body})


def _daily_plan(world: World) -> str:
    return str(sync_query(
        "INSERT INTO work_plan_daily (work_date, site_name, site_lat, site_lng, division_id, team_id, created_by_id) "
        "VALUES ((now() AT TIME ZONE 'Asia/Jakarta')::date, 'Site uji', -6.2, 106.8, %s, %s, %s)"
        "RETURNING daily_plan_id",
        (world.unit_id, world.team_id, world.employees["pm"]))[0][0])


def _second_division_pm(world: World) -> None:
    unit2 = world.add_unit("Dua")
    pm2 = world.add_person("pm2", "PM", unit_id=unit2)
    sync_query("UPDATE division SET pm_id = %s WHERE division_id = %s", (pm2, unit2))


def _loan_ids(client, world: World, who: str, path: str = "/assets/loans") -> set[str]:
    response = client.get(path, headers=world.headers(client, who))
    assert response.status_code == 200, response.text
    return {row["assignment_id"] for row in response.json()}


def test_loans_visible_to_division_pm_only(client, world: World):
    _second_division_pm(world)
    tool_id = create_tool(client, world).json()["tool_id"]
    loan_id = _lend(client, world, asset_type="TOOL", tool_id=tool_id).json()["assignment_id"]

    assert loan_id in _loan_ids(client, world, "hr")
    assert loan_id in _loan_ids(client, world, "pm")
    assert loan_id not in _loan_ids(client, world, "pm2")
    assert loan_id not in _loan_ids(client, world, "leader")


def test_plan_loans_visible_to_managing_pm_not_other_pm(client, world: World):
    _second_division_pm(world)
    tool_id = create_tool(client, world).json()["tool_id"]
    plan_id = _daily_plan(world)
    loan_id = _lend(client, world, asset_type="TOOL", tool_id=tool_id, daily_plan_id=plan_id).json()["assignment_id"]

    path = f"/work-plans/daily/{plan_id}/assets"
    assert loan_id in _loan_ids(client, world, "pm", path)
    denied = client.get(path, headers=world.headers(client, "pm2"))
    assert denied.status_code == 404, denied.text


def test_random_plan_and_order_ids_are_not_found(client, world: World):
    random_id = str(uuid.uuid4())
    for who in ("member", "leader", "pm", "admin"):
        plan = client.get(f"/work-plans/daily/{random_id}/assets", headers=world.headers(client, who))
        assert plan.status_code == 404, (who, plan.text)
        order = client.get(f"/work-plans/orders/{random_id}/schedule", headers=world.headers(client, who))
        assert order.status_code == 404, (who, order.text)
