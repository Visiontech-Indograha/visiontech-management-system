"""
OFFBOARD (`domain.js`): HR mengakhiri masa kerja — karyawan harus aktif, alasan wajib, tidak sedang
menjadi PM/ketua/anggota SK yang berjalan (selain DRAFT/COMPLETED/CANCELLED); jabatan terbuka ditutup,
akun dicabut. POST /employees/{id}/offboard {reason}
"""
from __future__ import annotations

from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import run_plan_to_in_progress

pytestmark = requires_db


def _offboard(client, world: World, employee_id: str, reason: str = "Kontrak selesai", who: str = "hr"):
    return client.post(f"/employees/{employee_id}/offboard", headers=world.headers(client, who),
                       json={"reason": reason})


def test_employee_on_a_running_plan_cannot_be_offboarded(client, world: World):
    run_plan_to_in_progress(client, world)

    blocked = _offboard(client, world, world.employees["member"])

    assert blocked.status_code == 409, blocked.text
    assert blocked.json()["error"]["message"] == "Selesaikan atau serahterimakan penugasan aktif sebelum offboarding."
    assert sync_query("SELECT is_active FROM vms.employee WHERE id = %s", (world.employees["member"],)) == [(True,)]


def test_hr_offboards_an_employee_and_closes_open_assignments(client, world: World, other_world: World):
    employee_id = world.employees["finance"]
    sync_query("INSERT INTO vms.employee_assignment (employee_id, position, valid_from) VALUES (%s, 'Staf', '2026-01-05')",
               (employee_id,))

    assert _offboard(client, world, employee_id, reason=" ").status_code == 422
    assert _offboard(client, world, employee_id, who="pm").status_code == 403
    assert _offboard(client, other_world, employee_id).status_code == 404

    done = _offboard(client, world, employee_id)
    assert done.status_code == 200, done.text
    assert sync_query("SELECT is_active, offboarded_at IS NOT NULL, offboarding_reason FROM vms.employee WHERE id = %s",
                      (employee_id,)) == [(False, True, "Kontrak selesai")]
    assert sync_query("SELECT is_active FROM vms.app_user WHERE employee_id = %s", (employee_id,)) == [(False,)]
    assert sync_query("SELECT count(*) FROM vms.employee_assignment WHERE employee_id = %s AND valid_to IS NULL",
                      (employee_id,)) == [(0,)]

    again = _offboard(client, world, employee_id)
    assert again.status_code == 409
    assert again.json()["error"]["message"] == "Karyawan sudah nonaktif atau tidak ditemukan."
