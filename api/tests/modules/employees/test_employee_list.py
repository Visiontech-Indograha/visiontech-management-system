"""
GET/POST /employees — daftar (cari `q`, saring kantor & status, halaman) dan galat NIK ganda.
V2: satu perusahaan — uji membatasi diri ke kantor dunia uji (`office_id`).
"""
from __future__ import annotations

from tests.conftest import requires_db, sync_query

pytestmark = requires_db


def _list(client, world, **params) -> dict:
    response = client.get("/employees", headers=world.headers(client, "hr"),
                          params={"office_id": world.org_id, **params})
    assert response.status_code == 200, response.text
    return response.json()


def test_search_filter_and_paging(client, world):
    everyone = _list(client, world, size=100)
    ids = {i["employee_id"] for i in everyone["items"]}
    assert set(world.employees.values()) <= ids and everyone["total"] == len(ids)
    assert [i["full_name"] for i in everyone["items"]] == sorted(i["full_name"] for i in everyone["items"])

    found = _list(client, world, q="karyawan uji pm")
    assert [i["employee_id"] for i in found["items"]] == [world.employees["pm"]]

    page = _list(client, world, size=3, page=2)
    assert page["total"] == everyone["total"] and page["page"] == 2 and len(page["items"]) <= 3


def test_duplicate_employee_number_is_a_friendly_error(client, world):
    taken = sync_query("SELECT employee_no FROM employee WHERE employee_id = %s", (world.employees["pm"],))[0][0]
    body = {"employee_no": taken, "full_name": "Kembar", "office_id": world.org_id, "join_date": "2026-01-05"}
    response = client.post("/employees", headers=world.headers(client, "hr"), json=body)
    assert response.status_code in (400, 409), response.text
    assert "duplicate" not in response.text and "constraint" not in response.text
