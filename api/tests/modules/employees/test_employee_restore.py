"""
V-29 · Arsip & pulihkan karyawan (Master Schema V2): hanya karyawan yang sudah selesai proses keluar
yang bisa diarsipkan; pemulihan membatalkan arsip tanpa membuka akses lama. HR/admin saja.
POST /employees/{id}/archive · POST /employees/{id}/restore
"""
from __future__ import annotations

import uuid

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _offboarded(world: World, who: str) -> str:
    # Jalur offboarding V2 (clearance + persetujuan) diuji di tests/modules/offboarding; di sini cukup hasil akhirnya.
    employee_id = world.employees[who]
    sync_query("UPDATE employee SET offboarding_status = 'offboarded' WHERE employee_id = %s RETURNING 1",
               (employee_id,))
    return employee_id


def _archive(client, world: World, employee_id: str, who: str = "hr"):
    return client.post(f"/employees/{employee_id}/archive", headers=world.headers(client, who), json={})


def _restore(client, world: World, employee_id: str, who: str = "hr"):
    return client.post(f"/employees/{employee_id}/restore", headers=world.headers(client, who), json={})


def _state(employee_id: str) -> tuple:
    return sync_query(
        "SELECT e.delete_at IS NOT NULL, u.is_active FROM employee e "
        "LEFT JOIN users u ON u.employee_id = e.employee_id "
        "WHERE e.employee_id = %s", (employee_id,))[0]


def test_hr_archives_an_offboarded_employee_and_can_restore_it(client, world):
    employee_id = world.employees["member"]
    active = _archive(client, world, employee_id)
    assert active.status_code == 409
    assert active.json()["error"]["message"] == "Selesaikan dulu proses keluar karyawan ini."

    _offboarded(world, "member")
    assert _archive(client, world, employee_id, who="pm").status_code == 403

    archived = _archive(client, world, employee_id)
    assert archived.status_code == 200, archived.text
    assert archived.json() == {"id": employee_id, "message": "Karyawan diarsipkan. Data historis tetap tersimpan."}
    assert _state(employee_id) == (True, False)
    listed = client.get("/employees", headers=world.headers(client, "hr"),
                        params={"size": 100, "office_id": world.org_id})
    assert listed.status_code == 200 and employee_id not in [e["employee_id"] for e in listed.json()["items"]]
    again = _archive(client, world, employee_id)
    assert again.status_code == 409 and again.json()["error"]["message"] == "Karyawan sudah diarsipkan."

    restored = _restore(client, world, employee_id)
    assert restored.status_code == 200, restored.text
    assert restored.json()["message"] == "Arsip dibatalkan. Karyawan tetap berstatus selesai bekerja."
    assert _state(employee_id) == (False, False)   # akses lama tetap dicabut


def test_restore_rules(client, world):
    not_archived = _restore(client, world, world.employees["leader"])
    assert not_archived.status_code == 409
    assert not_archived.json()["error"]["message"] == "Karyawan tidak diarsipkan."

    employee_id = _offboarded(world, "member")
    assert _archive(client, world, employee_id).status_code == 200
    assert _restore(client, world, employee_id, who="pm").status_code == 403
    assert _restore(client, world, str(uuid.uuid4())).status_code == 404
    assert _state(employee_id)[0] is True
