"""
GET/POST /employees — daftar (cari `q`, filter `is_active`, halaman) dan galat NIK ganda.
Dijaga saat SQL router karyawan dipindah ke crud (P9-7/R-25b).
"""
from __future__ import annotations

from tests.conftest import requires_db, sync_query

pytestmark = requires_db


def _list(client, world, **params) -> dict:
    response = client.get("/employees", headers=world.headers(client, "hr"), params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_search_filter_and_paging(client, world, other_world):
    everyone = _list(client, world)
    assert everyone["total"] == len(world.employees) and len(everyone["items"]) == len(world.employees)
    assert [i["full_name"] for i in everyone["items"]] == sorted(i["full_name"] for i in everyone["items"])

    found = _list(client, world, q="uji pm")
    assert [i["id"] for i in found["items"]] == [world.employees["pm"]]
    assert _list(client, world, q="UJI-0")["total"] == len(world.employees)   # NIK juga dicari, tanpa beda huruf

    sync_query("UPDATE vms.employee SET is_active = false WHERE id = %s", (world.employees["member"],))
    inactive = _list(client, world, is_active="false")
    assert [i["id"] for i in inactive["items"]] == [world.employees["member"]]
    assert _list(client, world, is_active="true")["total"] == len(world.employees) - 1

    page = _list(client, world, size=3, page=2)
    assert page["total"] == len(world.employees) and len(page["items"]) == 3 and page["page"] == 2


def test_duplicate_employee_number_is_a_friendly_error(client, world):
    body = {"employee_no": "UJI-00", "full_name": "Kembar", "position": "Teknisi", "join_date": "2026-01-05"}
    response = client.post("/employees", headers=world.headers(client, "hr"), json=body)
    assert response.status_code == 400
    error = response.json()["error"]
    assert error["code"] == "DB_ERROR" and "duplicate" not in response.text and "constraint" not in response.text
