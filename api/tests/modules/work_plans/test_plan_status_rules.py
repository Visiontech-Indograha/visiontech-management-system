"""
V-11 · Status SK sebagai syarat (`domain.js` requireStatus, RESERVE_ASSET).
- Laporan harian (simpan/ajukan) & insiden hanya untuk SK IN_PROGRESS.
- Alokasi aset hanya bila SK bukan COMPLETED/CANCELLED; pengemudi kendaraan wajib diisi dan harus
  bagian dari tim penugasan; SIM diperiksa trigger `asset_allocation_driver` — pesannya sampai ke
  klien sebagai 422, bukan galat basis data mentah.
"""
from __future__ import annotations

import pytest

from tests.conftest import World, requires_db, sync_query
from tests.modules.work_plans.test_flow_plans import create_draft_plan, run_plan_to_accepted, run_plan_to_in_progress

pytestmark = requires_db

STAGE = (
    "Status rencana kerja belum sesuai untuk tindakan ini. Muat ulang halaman.",
    "Status SK belum sesuai untuk tindakan ini. Muat ulang halaman.",
)


def _error(response) -> dict:
    return response.json()["error"]


# ── Laporan & insiden hanya untuk SK yang sedang berjalan ─────────────────────────────────────
def test_daily_report_needs_a_running_plan(client, world):
    plan_id, day_ids = run_plan_to_accepted(client, world, start_offset_days=1)  # diterima, mulai besok
    leader = world.headers(client, "leader")

    saved = client.put(f"/work-plans/{plan_id}/days/{day_ids[0]}", headers=leader,
                        json={"body": "Kamera 1-4 terpasang dan diuji", "obstacle": "Tidak ada"})
    submitted = client.post(f"/work-plans/{plan_id}/days/{day_ids[0]}/submit", headers=leader)

    for response in (saved, submitted):
        assert response.status_code == 409, response.text
        assert _error(response)["code"] == "INVALID_STATE"
        assert _error(response)["message"] in STAGE
    assert sync_query("SELECT count(*) FROM vms.daily_report WHERE work_plan_day_id = %s", (day_ids[0],)) == [(0,)]


def test_incident_needs_a_running_plan(client, world):
    plan_id, _ = run_plan_to_accepted(client, world, start_offset_days=1)   # alur v2: hari ini = otomatis berjalan

    response = client.post("/hse/incidents", headers=world.headers(client, "member"), json={
        "work_plan_id": plan_id, "category": "K3_RINGAN", "severity": "RENDAH",
        "description": "Tangga licin di area kerja"})

    assert response.status_code == 409, response.text
    assert _error(response)["message"] in STAGE
    assert sync_query("SELECT count(*) FROM vms.incident_report WHERE work_plan_id = %s", (plan_id,)) == [(0,)]


# ── Alokasi aset ──────────────────────────────────────────────────────────────────────────────
def _asset(client, world: World, kind: str = "TOOL") -> str:
    body = {"kind": kind, "code": f"{kind[:2]}-UJI", "name": "Aset uji", "condition": "BAIK"}
    if kind == "VEHICLE":
        body["vehicle_type"] = "CAR"
    created = client.post("/assets", headers=world.headers(client, "asset"), json=body)
    assert created.status_code == 201, created.text
    return created.json()["id"]


def _allocate(client, world: World, asset_id: str, plan_id: str, driver: str | None = None):
    return client.post(f"/assets/{asset_id}/reserve", headers=world.headers(client, "asset"), json={
        "work_plan_id": plan_id,
        "driver_employee_id": world.employees[driver] if driver else None})


def _allocations(asset_id: str) -> int:
    return sync_query("SELECT count(*) FROM vms.asset_allocation WHERE asset_id = %s", (asset_id,))[0][0]


@pytest.mark.parametrize("status", ["COMPLETED", "CANCELLED"])
def test_asset_is_not_allocated_to_a_finished_plan(client, world, status):
    plan_id, _ = run_plan_to_in_progress(client, world)
    # Belum ada endpoint selesai/batal (V-21, V-26) — status disetel langsung untuk menguji aturannya.
    sync_query("UPDATE vms.work_plan SET status = %s WHERE id = %s", (status, plan_id))
    asset_id = _asset(client, world)

    response = _allocate(client, world, asset_id, plan_id)

    assert response.status_code == 409, response.text
    assert _error(response)["code"] == "INVALID_STATE"
    assert _error(response)["message"] in ("Pilih rencana kerja yang masih aktif.", "Pilih SK yang masih aktif.")
    assert _allocations(asset_id) == 0


def test_vehicle_needs_a_driver(client, world):
    plan_id, _ = create_draft_plan(client, world, start_offset_days=7)
    asset_id = _asset(client, world, "VEHICLE")

    response = _allocate(client, world, asset_id, plan_id)

    assert response.status_code == 422, response.text
    assert _error(response)["message"] == "Pilih pengemudi untuk aset kendaraan."
    assert _allocations(asset_id) == 0


def test_vehicle_driver_must_be_on_the_team(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)       # tim: ketua + anggota
    asset_id = _asset(client, world, "VEHICLE")

    response = _allocate(client, world, asset_id, plan_id, driver="hr")

    assert response.status_code == 422, response.text
    assert _error(response)["message"] == "Pengemudi harus bagian dari tim penugasan."
    assert _allocations(asset_id) == 0


def test_driver_licence_rule_reaches_the_client_as_a_clear_422(client, world):
    """Trigger SIM: sebelumnya 400 DB_ERROR berisi teks galat basis data mentah."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    asset_id = _asset(client, world, "VEHICLE")

    response = _allocate(client, world, asset_id, plan_id, driver="member")   # anggota tanpa SIM A

    assert response.status_code == 422, response.text
    assert _error(response)["message"] == "Pengemudi tidak memiliki SIM A aktif dalam profilnya."
    assert _allocations(asset_id) == 0


def test_team_driver_with_a_valid_licence_is_allocated(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)
    sync_query(
        "WITH _ctx AS (SELECT set_config('app.organization_id', %s, true)) "
        "INSERT INTO vms.employee_document (employee_id, doc_type, number_masked, expiry_date, status, lifecycle, "
        "uploaded_by) SELECT e.id, 'SIM A', '****4321', DATE '2030-12-31', 'VERIFIED', 'CURRENT', u.id "
        "FROM vms.employee e JOIN vms.app_user u ON u.employee_id = e.id, _ctx WHERE e.id = %s",
        (world.org_id, world.employees["member"]))
    asset_id = _asset(client, world, "VEHICLE")

    response = _allocate(client, world, asset_id, plan_id, driver="member")

    assert response.status_code == 200, response.text
    assert sync_query("SELECT driver_employee_id::text FROM vms.asset_allocation WHERE asset_id = %s",
                      (asset_id,)) == [(world.employees["member"],)]
