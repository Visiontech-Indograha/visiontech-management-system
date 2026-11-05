"""Cakupan kantor absensi (keputusan pemilik 2026-11-05): SA/OM semua kantor; HR/Finance kantor sendiri;
cakupan = gabungan jabatan (HR kantor A yang juga penjabat OM divisi = semua kantor)."""
from __future__ import annotations

from collections.abc import Iterator

import pytest

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db

DAY = "2097-07-07"


def _attend(employee_id: str, office_id: str) -> str:
    return str(sync_query(
        "INSERT INTO attendance (employee_id, attendance_date, target_location_type, office_id, scheduled_in, "
        "scheduled_out, clock_in_at, in_lat, in_lng, face_match_score, face_photo_path, distance_to_target_m, "
        "is_within_attendance_radius, distance_from_main_office_m, city_zone_status, meal_allowance_amount) "
        "VALUES (%s, DATE %s, 'OFFICE', %s, '08:00', '17:00', TIMESTAMPTZ '2097-07-07 01:00+00', "
        "-6.2, 106.8, 99, 'x', 0, TRUE, 0, 'DALAM_KOTA', 0) RETURNING attendance_id",
        (employee_id, DAY, office_id),
    )[0][0])


@pytest.fixture
def duo(world: World, other_world: World) -> Iterator[tuple[World, World, str, str]]:
    for w in (world, other_world):
        w.add_person("fin", "FINANCE")
        w.add_person("hr2", "HR")
    a = _attend(world.employees["member"], world.org_id)
    b = _attend(other_world.employees["member"], other_world.org_id)
    yield world, other_world, a, b


def _ids(client, headers, **params) -> tuple[set[str], int]:
    r = client.get("/attendance", headers=headers, params={"date_from": DAY, "date_to": DAY, **params})
    assert r.status_code == 200, r.text
    return {row["id"] for row in r.json()["items"]}, r.json()["total"]


def test_hr_and_finance_only_own_office(client, duo):
    wa, _, a, _b = duo
    for who in ("hr", "fin"):
        ids, total = _ids(client, wa.headers(client, who))
        assert ids == {a} and total == 1, who


def test_om_sees_both_offices(client, duo):
    wa, _, a, b = duo
    ids, total = _ids(client, wa.headers(client, "ops"))
    assert {a, b} <= ids and total >= 2
    ids, _ = _ids(client, wa.headers(client, "admin"))
    assert {a, b} <= ids


def test_hr_with_om_position_sees_both(client, duo):
    wa, _wb, a, b = duo
    # jabatan kedua: HR A menjabat OM sebuah divisi -> gabungan cakupan = semua kantor
    sync_query("INSERT INTO division (om_id, pm_id, name) VALUES (%s, %s, %s)",
               (wa.employees["hr2"], wa.employees["pm"], "Divisi uji OM ganda"))
    ids, total = _ids(client, wa.headers(client, "hr2"))
    assert {a, b} <= ids and total >= 2
    # akun HR lain di kantor yang sama tanpa jabatan OM tetap hanya kantor sendiri
    ids, _ = _ids(client, wa.headers(client, "hr"))
    assert ids == {a}


def test_keyset_scoped_and_cursor_not_transferable(client, duo):
    wa, _wb, a, _b = duo
    ids, _ = _ids(client, wa.headers(client, "hr"), cursor="", size=50)
    assert ids == {a}
    first = client.get("/attendance", headers=wa.headers(client, "ops"),
                       params={"date_from": DAY, "date_to": DAY, "cursor": "", "size": 1})
    assert first.status_code == 200
    cursor = first.headers.get("x-next-cursor", "")
    # kursor OM ditempel ke HR: tetap hanya kantor HR, tidak membuka data baru
    ids, _ = _ids(client, wa.headers(client, "hr"), cursor=cursor, size=50)
    assert ids <= {a}


def test_export_and_recap_scoped(client, duo):
    wa, wb, _a, _b = duo
    emp_a = sync_query("SELECT employee_no FROM employee WHERE employee_id = %s", (wa.employees["member"],))[0][0]
    emp_b = sync_query("SELECT employee_no FROM employee WHERE employee_id = %s", (wb.employees["member"],))[0][0]
    r = client.get("/attendance/export", headers=wa.headers(client, "fin"), params={"start_date": DAY, "end_date": DAY})
    assert r.status_code == 200, r.text
    assert emp_a in r.text and emp_b not in r.text
    r = client.get("/attendance/export", headers=wa.headers(client, "admin"),
                   params={"start_date": DAY, "end_date": DAY})
    assert emp_a in r.text and emp_b in r.text
    r = client.get("/attendance/meal-allowance", headers=wa.headers(client, "fin"),
                   params={"start_date": DAY, "end_date": DAY})
    assert r.status_code == 200, r.text
    assert {x["employee_no"] for x in r.json()} == {emp_a}
