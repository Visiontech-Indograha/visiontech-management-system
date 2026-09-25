"""
V-29 · RESTORE_EMPLOYEE (`domain.js`): HR memulihkan karyawan yang dihapus sebagai NONAKTIF;
akses lama tetap dicabut. POST /employees/{id}/restore
"""
from __future__ import annotations

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _delete(world: World, who: str) -> str:
    employee_id = world.employees[who]
    sync_query("UPDATE vms.employee SET deleted_at = now(), is_active = false WHERE id = %s", (employee_id,))
    sync_query("UPDATE vms.app_user SET is_active = false WHERE employee_id = %s", (employee_id,))
    return employee_id


def _restore(client, world: World, employee_id: str, who: str = "hr"):
    return client.post(f"/employees/{employee_id}/restore", headers=world.headers(client, who), json={})


def test_hr_restores_a_deleted_employee_as_inactive(client, world):
    employee_id = _delete(world, "member")

    restored = _restore(client, world, employee_id)

    assert restored.status_code == 200, restored.text
    assert restored.json() == {"id": employee_id, "is_active": False,
                               "message": "Data dipulihkan sebagai nonaktif. Akses lama tetap dicabut."}
    assert sync_query("SELECT deleted_at IS NULL, is_active FROM vms.employee WHERE id = %s",
                      (employee_id,)) == [(True, False)]
    assert sync_query("SELECT is_active FROM vms.app_user WHERE employee_id = %s", (employee_id,)) == [(False,)]


def test_restore_rules(client, world, other_world):
    not_deleted = _restore(client, world, world.employees["leader"])
    assert not_deleted.status_code == 409
    assert not_deleted.json()["error"]["message"] == \
        "Karyawan tidak dihapus. Untuk bergabung kembali dibutuhkan masa kerja dan akses baru."

    employee_id = _delete(world, "member")
    assert _restore(client, world, employee_id, who="pm").status_code == 403
    assert _restore(client, other_world, employee_id).status_code == 404
    assert sync_query("SELECT deleted_at IS NOT NULL FROM vms.employee WHERE id = %s", (employee_id,)) == [(True,)]


# ── Hapus karyawan (keputusan pemilik 2026-09-25; pasangan RESTORE_EMPLOYEE) ─────────────────
def _archive(client, world: World, employee_id: str, who: str = "hr"):
    return client.post(f"/employees/{employee_id}/archive", headers=world.headers(client, who), json={})


def test_hr_archives_an_offboarded_employee_and_can_restore_it(client, world):
    employee_id = world.employees["member"]
    active = _archive(client, world, employee_id)
    assert active.status_code == 409
    assert active.json()["error"]["message"] == "Nonaktifkan (offboard) karyawan terlebih dahulu."

    offboarded = client.post(f"/employees/{employee_id}/offboard", headers=world.headers(client, "hr"),
                             json={"reason": "Kontrak selesai"})
    assert offboarded.status_code == 200, offboarded.text
    assert _archive(client, world, employee_id, who="pm").status_code == 403

    archived = _archive(client, world, employee_id)
    assert archived.status_code == 200, archived.text
    assert archived.json() == {"id": employee_id, "message": "Karyawan dihapus. Data historis tetap tersimpan."}
    assert sync_query("SELECT deleted_at IS NOT NULL, is_active FROM vms.employee WHERE id = %s",
                      (employee_id,)) == [(True, False)]
    listed = client.get("/employees", headers=world.headers(client, "hr"), params={"size": 100})
    assert listed.status_code == 200 and employee_id not in [e["id"] for e in listed.json()["items"]]
    again = _archive(client, world, employee_id)
    assert again.status_code == 409 and again.json()["error"]["message"] == "Karyawan sudah dihapus."

    assert _restore(client, world, employee_id).status_code == 200
    assert sync_query("SELECT deleted_at IS NULL FROM vms.employee WHERE id = %s", (employee_id,)) == [(True,)]
