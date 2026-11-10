"""
Matriks cakupan kantor per IZIN untuk orang OM+HR (ADR 0002 bagian 5; docs/audit-izin-hr-finance-per-kantor.md).

Aturan: izin yang HANYA dibawa HR (MANAGE_OFFBOARDING, MANAGE_MESS) dibatasi ke kantor tugas HR walau orangnya
juga OM; izin yang juga dibawa OM (VIEW_OFFBOARDING, VIEW_MESS, peran OM pada cuti) mengikuti OM = semua kantor.
Target selalu karyawan kantor B; pelaku berkantor A.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.config import settings
from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db

HR = "ADMIN_HR_GA"

# kind -> (akun uji, penugasan HR: None | "A" | "B")
ACTORS = {
    "om_hr": ("ops", "A"),    # OM utama + HR kantor A
    "hr_two": ("hr", "B"),    # HR kantor A + HR kantor B
    "hr_one": ("hr", None),   # HR tunggal kantor A
    "om_one": ("ops", None),  # OM tunggal
}
#             om_hr  hr_two hr_one om_one
VIEW_B = {"om_hr": 200, "hr_two": 200, "hr_one": 404, "om_one": 200}
MANAGE_B = {"om_hr": 404, "hr_two": 200, "hr_one": 404, "om_one": 403}


def _weekday(offset: int) -> str:
    """Hari kerja (Sen-Jum) pada/setelah offset: cuti di akhir pekan ditolak 422 (flake bergantung tanggal)."""
    d = jakarta_now().date() + timedelta(days=offset)
    while d.weekday() >= 5:
        d += timedelta(days=1)
    return d.isoformat()


def _day(offset: int) -> str:
    return (jakarta_now().date() + timedelta(days=offset)).isoformat()


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", True)


@pytest.fixture
def flag_off(monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", False)


def _actor(client, world: World, other: World, kind: str) -> str:
    who, where = ACTORS[kind]
    if where is not None:
        office = world.org_id if where == "A" else other.org_id
        r = client.post(f"/users/{world.users[who]}/role-assignments", headers=world.headers(client, "admin"),
                        json={"role": HR, "office_id": office})
        assert r.status_code == 201, r.text
    return who


@pytest.fixture
def stay_b(client, world: World, other_world: World):
    """Hunian karyawan kantor B, dibuat SA."""
    admin = world.headers(client, "admin")
    place = client.post("/mess/places", headers=admin, json={
        "mess_name": f"Mess matriks {world.tag}", "city": "Pekanbaru", "address": "Jl. Uji No. 7", "capacity": 5})
    assert place.status_code == 201, place.text
    mess_id = place.json()["mess_id"]
    r = client.post("/mess", headers=admin, json={
        "employee_id": other_world.employees["member"], "mess_id": mess_id,
        "stay_start_date": _day(5), "stay_end_date": _day(9)})
    assert r.status_code == 201, r.text
    yield r.json()["mess_stay_id"]
    sync_query("DELETE FROM company_mess_stay WHERE mess_id = %s RETURNING 1", (mess_id,))
    sync_query("DELETE FROM company_mess WHERE mess_id = %s RETURNING 1", (mess_id,))


@pytest.mark.parametrize("kind", list(ACTORS))
def test_mess_matrix(client, world: World, other_world: World, flag_on, stay_b, kind):
    who = _actor(client, world, other_world, kind)
    h = world.headers(client, who)
    assert client.get(f"/mess/{stay_b}", headers=h).status_code == VIEW_B[kind]
    listed = client.get("/mess", headers=h)
    assert listed.status_code == 200
    assert (stay_b in [s["mess_stay_id"] for s in listed.json()]) == (VIEW_B[kind] == 200)
    # kelola (MANAGE_MESS, tidak dibawa OM): OM+HR dibatasi; HR dua kantor boleh
    upd = client.put(f"/mess/{stay_b}", headers=h, json={"stay_start_date": _day(6), "stay_end_date": _day(9)})
    assert upd.status_code == MANAGE_B[kind], upd.text


@pytest.mark.parametrize("kind", ["om_hr", "hr_one", "om_one"])
def test_mess_flag_off_parity(client, world: World, other_world: World, flag_off, stay_b, kind):
    who = ACTORS[kind][0]
    h = world.headers(client, who)
    assert client.get(f"/mess/{stay_b}", headers=h).status_code == 200


@pytest.fixture
def offboarding_b(client, world: World, other_world: World):
    r = client.post("/offboarding", headers=world.headers(client, "admin"), json={
        "employee_id": other_world.employees["hr"], "reason_type": "RESIGN", "effective_date": _day(20)})
    assert r.status_code == 201, r.text
    return r.json()["offboarding_id"]


@pytest.mark.parametrize("kind", list(ACTORS))
def test_offboarding_matrix(client, world: World, other_world: World, flag_on, offboarding_b, kind):
    who = _actor(client, world, other_world, kind)
    h = world.headers(client, who)
    # lihat (VIEW_OFFBOARDING, juga dibawa OM)
    assert client.get(f"/offboarding/{offboarding_b}", headers=h).status_code == VIEW_B[kind]
    listed = client.get("/offboarding", headers=h)
    assert listed.status_code == 200
    ids = [o["offboarding_id"] for o in listed.json()]
    assert (offboarding_b in ids) == (VIEW_B[kind] == 200)
    # buat/batalkan (MANAGE_OFFBOARDING, tidak dibawa OM)
    created = client.post("/offboarding", headers=h, json={
        "employee_id": other_world.employees["member"], "reason_type": "RESIGN", "effective_date": _day(20)})
    expect = {"om_hr": 404, "hr_two": 201, "hr_one": 404, "om_one": 403}[kind]
    assert created.status_code == expect, created.text
    cancel = client.post(f"/offboarding/{offboarding_b}/cancel", headers=h, json={"reason": "Uji matriks cakupan"})
    assert (cancel.status_code == 404) == (MANAGE_B[kind] == 404), cancel.text
    if kind == "om_one":
        assert cancel.status_code == 403


@pytest.mark.parametrize("kind", ["om_hr", "hr_one", "om_one"])
def test_offboarding_flag_off_parity(client, world: World, other_world: World, flag_off, offboarding_b, kind):
    h = world.headers(client, ACTORS[kind][0])
    assert client.get(f"/offboarding/{offboarding_b}", headers=h).status_code == 200


@pytest.fixture
def leave_b(client, other_world: World):
    r = client.post("/leaves", headers=other_world.headers(client, "member"), json={
        "leave_type": "SICK", "start_date": _weekday(40), "end_date": _weekday(40), "reason": "Uji matriks cakupan"})
    assert r.status_code == 201, r.text
    return r.json()["leave_id"]


@pytest.mark.parametrize("kind", list(ACTORS))
def test_leave_matrix(client, world: World, other_world: World, flag_on, leave_b, kind):
    """Cuti diperiksa lewat PERAN (bukan izin): peran OM berwenang meninjau semua kantor, jadi OM+HR tidak
    dibatasi; HR yang bukan OM dibatasi ke kantor tugas."""
    who = _actor(client, world, other_world, kind)
    h = world.headers(client, who)
    reach = {"om_hr": True, "hr_two": True, "hr_one": False, "om_one": True}[kind]
    got = client.get(f"/leaves/{leave_b}", headers=h)
    assert (got.status_code == 200) == reach, got.text
    rev = client.post(f"/leaves/{leave_b}/review", headers=h, json={"decision": "REJECTED", "note": "Uji"})
    assert (rev.status_code == 404) == (not reach), rev.text


def test_leave_flag_off_parity(client, world: World, other_world: World, flag_off, leave_b):
    h = world.headers(client, "hr")
    assert client.get(f"/leaves/{leave_b}", headers=h).status_code == 200


@pytest.mark.parametrize("kind", list(ACTORS))
def test_manage_users_and_documents_matrix(client, world: World, other_world: World, flag_on, kind):
    """MANAGE_USERS / MANAGE_EMPLOYEE_DOCUMENTS tidak dibawa OM: OM+HR dibatasi ke kantor tugas HR;
    OM tunggal tidak memegang izin itu (403)."""
    who = _actor(client, world, other_world, kind)
    h = world.headers(client, who)
    emp = other_world.employees["member"]
    expect = {"om_hr": 404, "hr_two": 200, "hr_one": 404, "om_one": 403}[kind]
    assert client.get(f"/face/enrollments/{emp}/status", headers=h).status_code == expect
    if kind != "om_one":
        assert client.get(f"/employees/{emp}/documents", headers=h).status_code == expect
