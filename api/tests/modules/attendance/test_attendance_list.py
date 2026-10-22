"""
GET /attendance (dok 05 §3.5). Siapa melihat apa — R-33 (keputusan pemilik 2026-10-02, menggantikan R-10):
FINANCE & OPS melihat seluruh absensi organisasinya; PM miliknya + bawahan lapangan di unitnya;
HR, ASSET, ADMIN, dan lainnya hanya milik sendiri.
Filter: employee_id, from, to, status. Organisasi lain tidak pernah terlihat.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from app.core.time import jakarta_now
from tests.conftest import World, requires_db

pytestmark = requires_db

INSIDE = {"lat": -6.2, "lng": 106.8}
OUTSIDE = {"lat": -6.3, "lng": 106.8}


def _check_in(client, world: World, who: str, location=INSIDE) -> str:
    # V2: peran kantor absen lewat web, anggota & ketua tim lewat HP (docs/35 §1).
    channel = "MOBILE" if who in ("member", "leader") else "WEB"
    body = {"site_id": world.site_id, "location": location, "channel": channel}
    # V2: swafoto selalu wajib (docs/35 §5).
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (sum(map(ord, who)) % 255, 40, 200)).save(buf, "PNG")
    body["selfie_file_id"] = client.post("/files/upload", headers=world.headers(client, who), files={
        "file": ("s.png", buf.getvalue(), "image/png")}).json()["file_id"]
    if location is OUTSIDE:
        body["explanation"] = "Survei titik di luar lokasi"  # R-33: wajib di luar zona
    response = client.post("/attendance/check-in", headers=world.headers(client, who), json=body)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _list(client, world: World, who: str, **params) -> dict:
    response = client.get("/attendance", headers=world.headers(client, who), params=params)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def day(client, world, fake_storage):
    """Tiga absensi (satu menunggu pemeriksaan). V2: satu perusahaan — tidak ada organisasi lain (docs/10)."""
    return {
        "member": _check_in(client, world, "member", OUTSIDE),
        "leader": _check_in(client, world, "leader"),
        "pm": _check_in(client, world, "pm"),
    }


@pytest.mark.parametrize("who", ["pm", "ops", "admin"])
def test_reviewers_see_the_whole_company(client, world, day, who):
    ids = {a["id"] for a in _list(client, world, who, size=100)["items"]}
    assert {day["member"], day["leader"], day["pm"]} <= ids


def test_pm_sees_attendance_of_the_team(client, world, day):
    # R-33: PM meninjau bawahan lapangan di unitnya, jadi daftar PM memuat miliknya + bawahannya.
    ids = {a["id"] for a in _list(client, world, "pm")["items"]}
    assert {day["member"], day["leader"], day["pm"]} <= ids
    by_leader = _list(client, world, "pm", employee_id=world.employees["leader"])
    assert [a["id"] for a in by_leader["items"]] == [day["leader"]]


@pytest.mark.parametrize("who", ["pm", "ops", "admin"])
def test_scope_separates_personal_from_team_or_general(client, world, day, who):
    """Absensi pribadi dipisah dari absensi anggota/umum untuk pemegang wewenang lihat (PM, Finance, OPS)."""
    own = day.get(who)
    mine = {a["id"] for a in _list(client, world, who, scope="mine")["items"]}
    team = {a["id"] for a in _list(client, world, who, scope="team")["items"]}
    everything = {a["id"] for a in _list(client, world, who, size=100)["items"]}

    assert mine == ({own} if own else set())                       # hanya milik sendiri
    assert not (mine & team)                                       # tidak tercampur
    assert own is None or own in everything


def test_scope_mine_for_account_without_employee_is_empty_and_rejects_bad_value(client, world, day):
    assert _list(client, world, "admin", scope="mine")["items"] == []
    bad = client.get("/attendance", headers=world.headers(client, "pm"), params={"scope": "semua"})
    assert bad.status_code == 422


@pytest.mark.parametrize("who", ["member", "leader", "hr"])
def test_everyone_else_sees_only_their_own(client, world, day, who):
    listed = _list(client, world, who, employee_id=world.employees["leader"])   # upaya melihat milik orang lain

    own = {day[who]} if who in day else set()
    assert {a["id"] for a in listed["items"]} == (own if who == "leader" else set())
    assert all(a["employee_id"] == world.employees[who] for a in listed["items"])


def test_filters_status_employee_and_dates(client, world, day):
    today = jakarta_now().date().isoformat()

    member = world.employees["member"]
    waiting = _list(client, world, "ops", status="NEEDS_REVIEW", employee_id=member)
    assert [a["id"] for a in waiting["items"]] == [day["member"]]
    by_employee = _list(client, world, "ops", employee_id=world.employees["pm"])
    assert [a["id"] for a in by_employee["items"]] == [day["pm"]]
    assert _list(client, world, "ops", employee_id=member, **{"from": today, "to": today})["total"] == 1
    old = {"from": "2020-01-01", "to": "2020-01-31"}
    assert _list(client, world, "ops", employee_id=member, **old)["total"] == 0
    paged = _list(client, world, "ops", page=2, size=2)
    assert paged["page"] == 2 and paged["size"] == 2 and len(paged["items"]) <= 2
