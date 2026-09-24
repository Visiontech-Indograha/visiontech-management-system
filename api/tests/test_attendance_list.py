"""
GET /attendance (dok 05 §3.5). Siapa melihat apa mengikuti prototipe (operations.js attendance()):
FINANCE, HR, OPS — dan ADMIN — melihat seluruh absensi organisasinya; selain itu hanya milik sendiri.
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
    body = {"site_id": world.site_id, "location": location}
    if location is OUTSIDE:
        buf = io.BytesIO()
        Image.new("RGB", (32, 32), (sum(map(ord, who)) % 255, 40, 200)).save(buf, "PNG")
        body["selfie_file_id"] = client.post("/files/upload", headers=world.headers(client, who), files={
            "file": ("s.png", buf.getvalue(), "image/png")}).json()["file_id"]
    response = client.post("/attendance/check-in", headers=world.headers(client, who), json=body)
    assert response.status_code == 200, response.text
    return response.json()["id"]


def _list(client, world: World, who: str, **params) -> dict:
    response = client.get("/attendance", headers=world.headers(client, who), params=params)
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture
def day(client, world, other_world, fake_storage):
    """Tiga absensi di organisasi ini (satu menunggu pemeriksaan) + satu di organisasi lain."""
    return {
        "member": _check_in(client, world, "member", OUTSIDE),
        "leader": _check_in(client, world, "leader"),
        "pm": _check_in(client, world, "pm"),
        "foreign": _check_in(client, other_world, "member"),
    }


@pytest.mark.parametrize("who", ["finance", "hr", "ops", "admin"])
def test_reviewers_see_the_whole_organisation_but_nothing_else(client, world, day, who):
    listed = _list(client, world, who)
    ids = {a["id"] for a in listed["items"]}

    assert {day["member"], day["leader"], day["pm"]} <= ids
    assert day["foreign"] not in ids
    assert listed["total"] == len(ids) == 3


@pytest.mark.parametrize("who", ["member", "leader", "pm", "asset"])
def test_everyone_else_sees_only_their_own(client, world, day, who):
    listed = _list(client, world, who, employee_id=world.employees["leader"])   # upaya melihat milik orang lain

    own = {day[who]} if who in day else set()
    assert {a["id"] for a in listed["items"]} == (own if who == "leader" else set())
    assert all(a["employee_id"] == world.employees[who] for a in listed["items"])


def test_filters_status_employee_and_dates(client, world, day):
    today = jakarta_now().date().isoformat()

    waiting = _list(client, world, "finance", status="NEEDS_REVIEW")
    assert [a["id"] for a in waiting["items"]] == [day["member"]]
    by_employee = _list(client, world, "finance", employee_id=world.employees["pm"])
    assert [a["id"] for a in by_employee["items"]] == [day["pm"]]
    assert _list(client, world, "finance", **{"from": today, "to": today})["total"] == 3
    assert _list(client, world, "finance", **{"from": "2020-01-01", "to": "2020-01-31"})["total"] == 0
    paged = _list(client, world, "finance", page=2, size=2)
    assert (paged["total"], len(paged["items"]), paged["page"], paged["size"]) == (3, 1, 2, 2)
