"""
GET /mess/me: karyawan hanya melihat hunian mess miliknya sendiri (tanpa izin view:mess).
"""
from __future__ import annotations

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _stay(employee_id: str, name: str) -> None:
    sync_query(
        "INSERT INTO company_mess_stay (mess_name, city, address, latitude, longitude, employee_id, "
        "stay_start_date, stay_end_date) VALUES (%s, 'Pekanbaru', 'Jl. Uji', 0.53, 101.42, %s, "
        "'2026-03-01', '2026-03-31') RETURNING 1",
        (name, employee_id),
    )


def test_employee_sees_only_own_stays(client, world: World):
    _stay(world.employees["member"], "Mess uji A")
    _stay(world.employees["leader"], "Mess uji B")
    response = client.get("/mess/me", headers=world.headers(client, "member"))
    assert response.status_code == 200, response.text
    assert [s["mess_name"] for s in response.json()] == ["Mess uji A"]


def test_employee_without_stays_gets_empty_list(client, world: World):
    assert client.get("/mess/me", headers=world.headers(client, "member")).json() == []


def test_general_mess_list_stays_closed_to_employees(client, world: World):
    assert client.get("/mess", headers=world.headers(client, "member")).status_code == 403
