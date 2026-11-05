"""Offboarding bersamaan: UPDATE status bersyarat (compare-and-set), bukan menimpa diam-diam."""
from __future__ import annotations

import pytest

from tests.concurrency import tahan_lalu_ubah
from tests.conftest import World, requires_db, sync_query

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _employee_status(emp: str) -> str:
    return sync_query("SELECT offboarding_status::text FROM employee WHERE employee_id = %s", (emp,))[0][0]


def test_buat_offboarding_untuk_karyawan_yang_tertahan_dapat_409(client, world: World):
    emp = world.employees["member"]
    hasil = tahan_lalu_ubah(
        "UPDATE employee SET offboarding_status = 'in_process' WHERE employee_id = %s", (emp,),
        lambda: client.post("/offboarding", headers=world.headers(client, "hr"),
                            json={"employee_id": emp, "reason_type": "RESIGN", "effective_date": "2026-02-01"}),
    )
    assert hasil.status_code == 409, hasil.text
    assert hasil.json()["error"]["code"] == "ALREADY_OFFBOARDING", hasil.text
    assert sync_query("SELECT count(*) FROM employee_offboarding WHERE employee_id = %s", (emp,))[0][0] == 0


def test_selesaikan_offboarding_yang_dibatalkan_bersamaan_tidak_diselesaikan(client, world: World):
    emp = world.employees["member"]
    created = client.post("/offboarding", headers=world.headers(client, "hr"),
                          json={"employee_id": emp, "reason_type": "RESIGN", "effective_date": "2026-02-01"})
    assert created.status_code == 201, created.text
    oid = created.json()["offboarding_id"]
    sync_query("UPDATE employee_offboarding SET status = 'APPROVED' WHERE offboarding_id = %s RETURNING 1", (oid,))
    hasil = tahan_lalu_ubah(
        "UPDATE employee_offboarding SET delete_at = now() WHERE offboarding_id = %s", (oid,),
        lambda: client.post("/offboarding/complete-due", headers=world.headers(client, "admin")),
    )
    assert hasil.status_code == 200, hasil.text
    assert _employee_status(emp) == "in_process"
    assert sync_query("SELECT status FROM employee_offboarding WHERE offboarding_id = %s", (oid,))[0][0] == "APPROVED"
