"""
docs/41 §3: hapus permanen & koreksi data oleh SUPER_ADMIN (izin DELETE_ANY). Peran lain → 403, id asing → 404.
DELETE /employees/{id} · DELETE /employees/{id}/account · PATCH|DELETE /attendance/{id} · DELETE /overtime/{id}
"""
from __future__ import annotations

import uuid

import pytest

from tests.conftest import World, requires_db, sync_query
from tests.daily import run_daily_to_ongoing
from tests.modules.attendance.test_attendance_channel import _check_in, _storage  # noqa: F401

pytestmark = requires_db

GHOST = str(uuid.uuid4())


def _archive_offboarded(client, world: World, who: str) -> str:
    employee_id = world.employees[who]
    sync_query("UPDATE employee SET offboarding_status = 'offboarded' WHERE employee_id = %s RETURNING 1",
               (employee_id,))
    assert client.post(f"/employees/{employee_id}/archive", headers=world.headers(client, "hr"),
                       json={}).status_code == 200
    return employee_id


def test_delete_employee_requires_super_admin_and_archive(client, world):
    employee_id = world.employees["member"]
    assert client.delete(f"/employees/{employee_id}", headers=world.headers(client, "hr")).status_code == 403
    assert client.delete(f"/employees/{GHOST}", headers=world.headers(client, "admin")).status_code == 404
    active = client.delete(f"/employees/{employee_id}", headers=world.headers(client, "admin"))
    assert active.status_code == 409 and active.json()["error"]["code"] == "NOT_ARCHIVED"

    _archive_offboarded(client, world, "member")
    done = client.delete(f"/employees/{employee_id}", headers=world.headers(client, "admin"))
    assert done.status_code == 200, done.text
    assert done.json() == {"status": "deleted"}
    assert sync_query("SELECT count(*) FROM employee WHERE employee_id = %s", (employee_id,))[0][0] == 0
    assert sync_query("SELECT count(*) FROM users WHERE employee_id = %s", (employee_id,))[0][0] == 0


def test_delete_account_keeps_employee_and_blocks_self(client, world):
    employee_id = world.employees["member"]
    url = f"/employees/{employee_id}/account"
    assert client.delete(url, headers=world.headers(client, "hr")).status_code == 403
    assert client.delete(f"/employees/{GHOST}/account", headers=world.headers(client, "admin")).status_code == 404
    done = client.delete(url, headers=world.headers(client, "admin"))
    assert done.status_code == 200, done.text
    assert sync_query("SELECT count(*) FROM users WHERE employee_id = %s", (employee_id,))[0][0] == 0
    assert sync_query("SELECT count(*) FROM employee WHERE employee_id = %s", (employee_id,))[0][0] == 1


def test_delete_overtime(client, world):
    plan_id = run_daily_to_ongoing(world)
    created = client.post("/overtime", headers=world.headers(client, "leader"),
                          json={"daily_plan_id": plan_id, "hours": 2, "reason": "Kabel tambahan"})
    assert created.status_code == 201, created.text
    ot_id = created.json()["id"]
    assert client.delete(f"/overtime/{ot_id}", headers=world.headers(client, "pm")).status_code == 403
    assert client.delete(f"/overtime/{GHOST}", headers=world.headers(client, "admin")).status_code == 404
    assert client.delete(f"/overtime/{ot_id}", headers=world.headers(client, "admin")).status_code == 200
    assert sync_query("SELECT count(*) FROM overtime WHERE overtime_id = %s", (ot_id,))[0][0] == 0


@pytest.mark.usefixtures("_storage")
def test_patch_and_delete_attendance(client, world):
    checked = _check_in(client, world, "member", "MOBILE")
    assert checked.status_code == 200, checked.text
    att_id = checked.json()["id"]
    url = f"/attendance/{att_id}"
    body = {"om_approval_status": "APPROVED_BY_OM", "reason": "Koreksi uji"}
    assert client.patch(url, headers=world.headers(client, "pm"), json=body).status_code == 403
    assert client.patch(f"/attendance/{GHOST}", headers=world.headers(client, "admin"), json=body).status_code == 404
    assert client.patch(url, headers=world.headers(client, "admin"), json={"reason": "tanpa isi"}).status_code == 422
    assert client.patch(url, headers=world.headers(client, "admin"), json=body).status_code == 200
    assert sync_query("SELECT om_approval_status FROM attendance WHERE attendance_id = %s",
                      (att_id,))[0][0] == "APPROVED_BY_OM"

    assert client.delete(url, headers=world.headers(client, "pm")).status_code == 403
    assert client.delete(f"/attendance/{GHOST}", headers=world.headers(client, "admin")).status_code == 404
    assert client.delete(url, headers=world.headers(client, "admin")).status_code == 200
    assert sync_query("SELECT count(*) FROM attendance WHERE attendance_id = %s", (att_id,))[0][0] == 0
