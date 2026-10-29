"""
Milestone 4 · Serah terima & pengembalian aset (asset_assignment), alur docs/35 §6 — juga regresi R9:
siklus pinjam → kembali → pinjam lagi tanpa jalan buntu.
"""
from __future__ import annotations

import pytest

from tests.conftest import World, requires_db, sync_query
from tests.modules.assets.test_asset_master import create_tool, create_vehicle, upload

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _lend(client, world: World, **body):
    return client.post("/assets/loans", headers=world.headers(client, "hr"),
                       json={"employee_id": world.employees["member"], **body})


def _daily_plan(world: World, days_from_today: int = 0) -> str:
    return str(sync_query(
        "INSERT INTO work_plan_daily (work_date, site_name, site_lat, site_lng, division_id, team_id, created_by_id) "
        "VALUES ((now() AT TIME ZONE 'Asia/Jakarta')::date + %s, 'Site uji', -6.2, 106.8, %s, %s, %s)"
        "RETURNING daily_plan_id",
        (days_from_today, world.unit_id, world.team_id, world.employees["pm"]))[0][0])


def _licence(world: World, who: str, sim: str) -> None:
    sync_query("INSERT INTO employee_file (employee_id, type, path_file, active_at, expired_at) "
               "VALUES (%s, %s, 'uji/sim.pdf', now() - interval '1 year', now() + interval '1 year')",
               (world.employees[who], sim))


def test_personal_tool_cycle_without_dead_end(client, world: World):
    tool_id = create_tool(client, world, ownership="PERSONAL_LOAN").json()["tool_id"]
    loan = _lend(client, world, asset_type="TOOL", tool_id=tool_id)
    assert loan.status_code == 201, loan.text
    assert loan.json()["assignment_status"] == "loaned"
    assert _lend(client, world, asset_type="TOOL", tool_id=tool_id).json()["error"]["code"] == "ASSET_NOT_AVAILABLE"

    hr = world.headers(client, "hr")
    returned = client.post(f"/assets/loans/{loan.json()['assignment_id']}/return", headers=hr, json={})
    assert returned.json()["returned_at"] is not None
    again = client.post(f"/assets/loans/{loan.json()['assignment_id']}/return", headers=hr, json={})
    assert again.json()["error"]["code"] == "ALREADY_RETURNED"
    assert _lend(client, world, asset_type="TOOL", tool_id=tool_id).status_code == 201


def test_damaged_return_blocks_next_loan(client, world: World):
    tool_id = create_tool(client, world).json()["tool_id"]
    loan_id = _lend(client, world, asset_type="TOOL", tool_id=tool_id).json()["assignment_id"]
    client.post(f"/assets/loans/{loan_id}/return", headers=world.headers(client, "hr"), json={"condition": "damaged"})
    assert _lend(client, world, asset_type="TOOL", tool_id=tool_id).status_code == 409


def test_shared_tool_for_daily_plan_is_allocated(client, world: World):
    tool_id = create_tool(client, world).json()["tool_id"]
    plan_id = _daily_plan(world)
    loan = _lend(client, world, asset_type="TOOL", tool_id=tool_id, daily_plan_id=plan_id)
    assert loan.json()["assignment_status"] == "allocated"
    # ketua tim melihat aset jadwal yang sudah disetujui (jadwal draf belum terlihat tim)
    sync_query("UPDATE work_plan_daily SET status = 'APPROVED' WHERE daily_plan_id = %s", (plan_id,))
    listed = client.get(f"/work-plans/daily/{plan_id}/assets", headers=world.headers(client, "leader"))
    assert [a["asset_id"] for a in listed.json()] == [tool_id]


def test_plan_rules(client, world: World):
    personal = create_tool(client, world, ownership="PERSONAL_LOAN").json()["tool_id"]
    today_plan = _daily_plan(world)
    assert _lend(client, world, asset_type="TOOL", tool_id=personal, daily_plan_id=today_plan).status_code == 422
    shared = create_tool(client, world).json()["tool_id"]
    assert _lend(client, world, asset_type="TOOL", tool_id=shared, daily_plan_id=_daily_plan(world, -1)).status_code \
        == 422
    outsider = client.post("/assets/loans", headers=world.headers(client, "hr"), json={
        "asset_type": "TOOL", "tool_id": shared, "employee_id": world.employees["hr"],
        "daily_plan_id": today_plan})
    assert outsider.status_code == 422  # bukan anggota tim jadwal


def test_vehicle_needs_valid_stnk_and_licence(client, world: World):
    vehicle_id = create_vehicle(client, world, vehicle_type="Car").json()["vehicle_id"]
    no_stnk = _lend(client, world, asset_type="VEHICLE", vehicle_id=vehicle_id)
    assert no_stnk.json()["error"]["code"] == "VEHICLE_PAPERS_EXPIRED"

    client.post(f"/assets/vehicles/{vehicle_id}/files", headers=world.headers(client, "hr"),
                json={"type": "STNK", "file_id": upload(client, world), "expired_at": "2031-01-01"})
    _licence(world, "member", "SIM_C")  # SIM motor tidak cukup untuk mobil
    assert _lend(client, world, asset_type="VEHICLE", vehicle_id=vehicle_id).json()["error"]["code"] \
        == "DRIVER_LICENCE_REQUIRED"
    _licence(world, "member", "SIM_A")
    assert _lend(client, world, asset_type="VEHICLE", vehicle_id=vehicle_id).status_code == 201


def test_holder_can_inspect_vehicle_others_cannot(client, world: World):
    vehicle_id = create_vehicle(client, world, vehicle_type="Motorcycle").json()["vehicle_id"]
    client.post(f"/assets/vehicles/{vehicle_id}/files", headers=world.headers(client, "hr"),
                json={"type": "STNK", "file_id": upload(client, world), "expired_at": "2031-01-01"})
    _licence(world, "member", "SIM_C")
    assert _lend(client, world, asset_type="VEHICLE", vehicle_id=vehicle_id).status_code == 201

    url = f"/assets/vehicles/{vehicle_id}/inspections"
    body = {"type": "day", "file_id": upload(client, world, who="member", colour=7)}
    assert client.post(url, headers=world.headers(client, "member"), json=body).status_code == 201
    assert client.post(url, headers=world.headers(client, "leader"), json=body).status_code == 403


def test_field_staff_only_see_own_loans(client, world: World):
    tool_id = create_tool(client, world).json()["tool_id"]
    _lend(client, world, asset_type="TOOL", tool_id=tool_id)
    assert client.get("/assets/loans", headers=world.headers(client, "leader")).json() == []
    mine = client.get("/assets/loans", headers=world.headers(client, "member")).json()
    assert [loan["asset_id"] for loan in mine] == [tool_id]


def test_wrong_asset_field_is_rejected(client, world: World):
    tool_id = create_tool(client, world).json()["tool_id"]
    assert _lend(client, world, asset_type="VEHICLE", tool_id=tool_id).status_code == 422
