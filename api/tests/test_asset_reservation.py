"""
V-27 · RESERVE_ASSET, RELEASE_ASSET, CHECK_ASSET (`domain.js`), + START mengaktifkan reservasi.
- POST /assets/{id}/reserve {work_plan_id, driver_employee_id?} — petugas aset / PM unit / OPS.
  Alat pada SK IN_PROGRESS/COMPLETION_REVIEW → IN_USE; selain itu → RESERVED.
- POST /assets/{id}/release {work_plan_id} — hanya reservasi (RESERVED) milik SK itu.
- POST /assets/{id}/check {decision: ACCEPT|APPEAL, reason} — hanya pengemudi yang ditunjuk.
- START: reservasi → IN_USE (alat langsung, kendaraan bila sudah diperiksa pengemudi).
"""
from __future__ import annotations

from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import (
    _row_version,
    create_draft_plan,
    run_plan_to_accepted,
    run_plan_to_in_progress,
)

pytestmark = requires_db


def _asset(client, world: World, code: str, kind: str = "TOOL") -> str:
    body = {"kind": kind, "code": code, "name": f"Aset {code}", "condition": "BAIK"}
    if kind == "VEHICLE":
        body["vehicle_type"] = "CAR"
    created = client.post("/assets", headers=world.headers(client, "asset"), json=body)
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _reserve(client, world: World, asset_id: str, plan_id: str, who: str = "asset", driver: str | None = None):
    return client.post(f"/assets/{asset_id}/reserve", headers=world.headers(client, who), json={
        "work_plan_id": plan_id, "driver_employee_id": world.employees[driver] if driver else None})


def _release(client, world: World, asset_id: str, plan_id: str, who: str = "asset"):
    return client.post(f"/assets/{asset_id}/release", headers=world.headers(client, who),
                       json={"work_plan_id": plan_id})


def _check(client, world: World, asset_id: str, who: str, decision: str, reason: str | None = None):
    return client.post(f"/assets/{asset_id}/check", headers=world.headers(client, who),
                       json={"decision": decision, "reason": reason})


def _status(asset_id: str) -> str:
    return sync_query("SELECT status::text FROM vms.asset WHERE id = %s", (asset_id,))[0][0]


def _open_allocations(asset_id: str) -> int:
    return sync_query("SELECT count(*) FROM vms.asset_allocation WHERE asset_id = %s AND released_at IS NULL",
                      (asset_id,))[0][0]


def _start(client, world: World, plan_id: str) -> None:
    started = client.post(f"/work-plans/{plan_id}/start", headers=world.headers(client, "leader"),
                          json={"row_version": _row_version(plan_id), "reason": ""})
    assert started.status_code == 200, started.text


def _give_sim_a(world: World, who: str) -> None:
    sync_query(
        "WITH _ctx AS (SELECT set_config('app.organization_id', %s, true)) "
        "INSERT INTO vms.employee_document (employee_id, doc_type, number_masked, expiry_date, status, lifecycle, "
        "uploaded_by) SELECT e.id, 'SIM A', '****4321', DATE '2030-12-31', 'VERIFIED', 'CURRENT', u.id "
        "FROM vms.employee e JOIN vms.app_user u ON u.employee_id = e.id, _ctx WHERE e.id = %s",
        (world.org_id, world.employees[who]))


def test_tool_is_reserved_until_the_plan_starts(client, world):
    plan_id, _ = run_plan_to_accepted(client, world)
    tool = _asset(client, world, "TL-RSV")

    reserved = _reserve(client, world, tool, plan_id)
    assert reserved.status_code == 200, reserved.text
    assert _status(tool) == "RESERVED" and _open_allocations(tool) == 1

    _start(client, world, plan_id)
    assert _status(tool) == "IN_USE"


def test_tool_on_a_running_plan_is_in_use_at_once_and_cannot_be_released(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)
    tool = _asset(client, world, "TL-RUN")

    not_manager = _reserve(client, world, tool, plan_id, who="member")     # SK terlihat, bukan pengelola
    assert not_manager.status_code == 403 and _open_allocations(tool) == 0
    assert _reserve(client, world, tool, plan_id).status_code == 200
    assert _status(tool) == "IN_USE"
    used = _release(client, world, tool, plan_id)
    assert used.status_code == 409
    assert used.json()["error"]["message"] == "Hanya reservasi yang belum dipakai dapat dilepas."
    check = _check(client, world, tool, "leader", "ACCEPT")
    assert check.status_code == 409
    assert check.json()["error"]["message"] == "Hanya kendaraan yang memerlukan pemeriksaan pengemudi."


def test_reserve_permissions_and_double_booking(client, world, other_world):
    plan_id, _ = create_draft_plan(client, world, start_offset_days=7)
    tool = _asset(client, world, "TL-IZN")

    assert _reserve(client, world, tool, plan_id, who="member").status_code == 404   # draf tak terlihat anggota
    assert _reserve(client, other_world, tool, plan_id, who="pm").status_code == 404
    assert _open_allocations(tool) == 0

    by_pm = _reserve(client, world, tool, plan_id, who="pm")
    assert by_pm.status_code == 200, by_pm.text
    double = _reserve(client, world, tool, plan_id)
    assert double.status_code == 409
    assert double.json()["error"]["message"] == "Aset ini sedang dialokasikan dan belum dikembalikan."
    assert _open_allocations(tool) == 1


def test_release_only_frees_the_reservation_of_that_plan(client, world):
    plan_a, _ = create_draft_plan(client, world, start_offset_days=7)
    plan_b, _ = create_draft_plan(client, world, start_offset_days=20)
    tool = _asset(client, world, "TL-LPS")
    assert _reserve(client, world, tool, plan_a).status_code == 200

    wrong_plan = _release(client, world, tool, plan_b)
    assert wrong_plan.status_code == 409
    assert _release(client, world, tool, plan_a, who="member").status_code == 404   # draf tak terlihat anggota

    released = _release(client, world, tool, plan_a, who="pm")
    assert released.status_code == 200, released.text
    assert released.json()["status"] == "AVAILABLE"
    assert _status(tool) == "AVAILABLE" and _open_allocations(tool) == 0
    assert sync_query("SELECT released_at IS NOT NULL FROM vms.asset_allocation WHERE asset_id = %s",
                      (tool,)) == [(True,)]


def test_driver_checks_vehicles_before_they_are_used(client, world):
    plan_id, _ = run_plan_to_accepted(client, world)
    _give_sim_a(world, "member")
    checked, unchecked = _asset(client, world, "KD-01", "VEHICLE"), _asset(client, world, "KD-02", "VEHICLE")
    assert _reserve(client, world, checked, plan_id, driver="member").status_code == 200
    assert _reserve(client, world, unchecked, plan_id, driver="member").status_code == 200

    not_driver = _check(client, world, checked, "leader", "ACCEPT")
    assert not_driver.status_code == 403
    assert not_driver.json()["error"]["message"] == "Hanya pengemudi yang ditunjuk yang dapat melakukan pemeriksaan."
    accepted = _check(client, world, checked, "member", "ACCEPT")
    assert accepted.status_code == 200, accepted.text
    assert _status(checked) == "RESERVED"                         # SK belum berjalan
    assert sync_query("SELECT driver_checked_at IS NOT NULL FROM vms.asset_allocation WHERE asset_id = %s",
                      (checked,)) == [(True,)]
    again = _check(client, world, checked, "member", "ACCEPT")
    assert again.status_code == 409 and again.json()["error"]["message"] == "Kendaraan ini sudah diperiksa."

    blocked = client.post(f"/work-plans/{plan_id}/start", headers=world.headers(client, "leader"),
                          json={"row_version": _row_version(plan_id), "reason": ""})
    assert blocked.status_code == 409
    assert blocked.json()["error"]["message"] == \
        "Semua kendaraan harus diperiksa dan dinyatakan layak oleh pengemudi sebelum pekerjaan dimulai."
    assert _status(checked) == "RESERVED" and _status(unchecked) == "RESERVED"

    no_reason = _check(client, world, unchecked, "member", "APPEAL", " ")
    assert no_reason.status_code == 422
    assert no_reason.json()["error"]["message"] == "Alasan banding kelayakan wajib diisi."
    appeal = _check(client, world, unchecked, "member", "APPEAL", "Rem depan bunyi")
    assert appeal.status_code == 200, appeal.text
    assert sync_query("SELECT status::text, condition FROM vms.asset WHERE id = %s", (unchecked,)) \
        == [("AVAILABLE", "Banding pengemudi: Rem depan bunyi")]
    assert _open_allocations(unchecked) == 0

    _start(client, world, plan_id)
    assert _status(checked) == "IN_USE"
