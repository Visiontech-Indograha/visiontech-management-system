"""
Alur mess: master mess dipilih (bukan diketik), karyawan mengajukan hunian, PM/OM/HR memutuskan, kapasitas dijaga.
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta

import pytest

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _day(offset: int) -> str:
    return (jakarta_now().date() + timedelta(days=offset)).isoformat()


@pytest.fixture
def place(client, world: World) -> Iterator[dict]:
    created = client.post("/mess/places", headers=world.headers(client, "hr"), json={
        "mess_name": f"Mess uji {world.tag}", "city": "Pekanbaru", "address": "Jl. Uji No. 5", "capacity": 1,
    })
    assert created.status_code == 201, created.text
    data = created.json()
    yield data
    sync_query("DELETE FROM company_mess_stay WHERE mess_id = %s RETURNING 1", (data["mess_id"],))
    sync_query("DELETE FROM company_mess WHERE mess_id = %s RETURNING 1", (data["mess_id"],))


def _request(client, world, who, place, start=1, end=3, note="Penugasan proyek"):
    return client.post("/mess/requests", headers=world.headers(client, who), json={
        "mess_id": place["mess_id"], "stay_start_date": _day(start), "stay_end_date": _day(end), "note": note,
    })


def test_everyone_can_list_places_but_only_hr_manages(client, world: World, place):
    listed = client.get("/mess/places", headers=world.headers(client, "member"))
    assert listed.status_code == 200
    assert place["mess_id"] in [p["mess_id"] for p in listed.json()]
    denied = client.post("/mess/places", headers=world.headers(client, "member"), json={
        "mess_name": "Mess liar", "city": "Medan", "address": "Jl. Liar 1"})
    assert denied.status_code == 403


def test_request_then_pm_approves_and_employee_is_notified(client, world: World, place):
    sent = _request(client, world, "member", place)
    assert sent.status_code == 201, sent.text
    stay = sent.json()
    assert stay["status"] == "REQUESTED" and stay["mess_name"] == place["mess_name"]
    assert len(sync_query(
        "SELECT 1 FROM notification WHERE kind = 'MESS_REQUESTED' AND user_id = %s", (world.users["pm"],))) == 1

    assert client.post(f"/mess/{stay['mess_stay_id']}/decision", headers=world.headers(client, "member"),
                       json={"approve": True}).status_code == 403
    decided = client.post(f"/mess/{stay['mess_stay_id']}/decision", headers=world.headers(client, "pm"),
                          json={"approve": True, "note": "Silakan"})
    assert decided.status_code == 200, decided.text
    assert decided.json()["status"] == "APPROVED"
    assert client.get("/mess/me", headers=world.headers(client, "member")).json()[0]["status"] == "APPROVED"
    assert len(sync_query(
        "SELECT 1 FROM notification WHERE kind = 'MESS_DECIDED' AND user_id = %s", (world.users["member"],))) == 1
    again = client.post(f"/mess/{stay['mess_stay_id']}/decision", headers=world.headers(client, "pm"),
                        json={"approve": True})
    assert again.status_code == 409


def test_reject_requires_a_reason(client, world: World, place):
    stay = _request(client, world, "member", place).json()
    url = f"/mess/{stay['mess_stay_id']}/decision"
    assert client.post(url, headers=world.headers(client, "pm"), json={"approve": False}).status_code == 422
    rejected = client.post(url, headers=world.headers(client, "pm"), json={"approve": False, "note": "Penuh"})
    assert rejected.status_code == 200 and rejected.json()["status"] == "REJECTED"


def test_request_validation_and_overlap(client, world: World, place):
    assert _request(client, world, "member", place, start=-2, end=1).status_code == 422
    assert _request(client, world, "member", place, start=5, end=2).status_code == 422
    assert _request(client, world, "member", place).status_code == 201
    assert _request(client, world, "member", place, start=2, end=4).status_code == 409


def test_capacity_blocks_second_approval(client, world: World, place):
    first = _request(client, world, "member", place).json()
    second = _request(client, world, "leader", place).json()
    pm = world.headers(client, "pm")
    first_url = f"/mess/{first['mess_stay_id']}/decision"
    assert client.post(first_url, headers=pm, json={"approve": True}).status_code == 200
    full = client.post(f"/mess/{second['mess_stay_id']}/decision", headers=pm, json={"approve": True})
    assert full.status_code == 409 and full.json()["error"]["code"] == "MESS_FULL"


def test_cancel_only_by_owner_and_end_only_when_running(client, world: World, place):
    stay = _request(client, world, "member", place).json()
    cancel_url = f"/mess/{stay['mess_stay_id']}/cancel"
    assert client.post(cancel_url, headers=world.headers(client, "leader")).status_code == 403
    cancelled = client.post(f"/mess/{stay['mess_stay_id']}/cancel", headers=world.headers(client, "member"))
    assert cancelled.status_code == 200 and cancelled.json()["status"] == "CANCELLED"

    running = _request(client, world, "member", place, start=0, end=5).json()
    pm = world.headers(client, "pm")
    member = world.headers(client, "member")
    end_url = f"/mess/{running['mess_stay_id']}/end"
    assert client.post(end_url, headers=member).status_code == 409
    decision_url = f"/mess/{running['mess_stay_id']}/decision"
    assert client.post(decision_url, headers=pm, json={"approve": True}).status_code == 200
    ended = client.post(end_url, headers=member)
    assert ended.status_code == 200 and ended.json()["stay_end_date"] == _day(0)


def test_hr_records_stay_directly_and_place_in_use_cannot_be_deleted(client, world: World, place):
    hr = world.headers(client, "hr")
    stay = client.post("/mess", headers=hr, json={
        "employee_id": world.employees["member"], "mess_id": place["mess_id"],
        "stay_start_date": _day(0), "stay_end_date": _day(4)})
    assert stay.status_code == 201, stay.text
    assert stay.json()["status"] == "APPROVED"
    in_use = client.delete(f"/mess/places/{place['mess_id']}", headers=hr)
    assert in_use.status_code == 409 and in_use.json()["error"]["code"] == "MESS_IN_USE"


def test_create_stay_idempotency_key(client, world: World, place):
    hr = {**world.headers(client, "hr"), "Idempotency-Key": f"mess-{world.tag}"}
    body = {"employee_id": world.employees["member"], "mess_id": place["mess_id"],
            "stay_start_date": _day(0), "stay_end_date": _day(4)}
    first = client.post("/mess", headers=hr, json=body)
    second = client.post("/mess", headers=hr, json=body)
    assert first.status_code == 201, first.text
    assert second.status_code == 201 and second.json() == first.json()
    count = sync_query("SELECT count(*) FROM company_mess_stay WHERE mess_id = %s", (place["mess_id"],))[0][0]
    assert count == 1


def test_cancel_status_rules_future_approved_running_and_hr_removal(client, world: World, place):
    """B-38: hunian disetujui yang belum mulai bisa dikeluarkan (HR) atau dibatalkan (pemohon, HP);
    yang sudah berjalan hanya lewat 'Selesai inap'; kapasitas kembali setelah batal."""
    pm = world.headers(client, "pm")
    hr = world.headers(client, "hr")
    member = world.headers(client, "member")

    def approve(stay: dict) -> None:
        res = client.post(f"/mess/{stay['mess_stay_id']}/decision", headers=pm, json={"approve": True})
        assert res.status_code == 200, res.text

    future = _request(client, world, "member", place, start=3, end=6).json()
    approve(future)
    by_hr = client.post(f"/mess/{future['mess_stay_id']}/cancel", headers=hr)
    assert by_hr.status_code == 200 and by_hr.json()["status"] == "CANCELLED"
    notified = sync_query(
        "SELECT 1 FROM notification WHERE kind = 'MESS_CANCELLED' AND user_id = %s", (world.users["member"],))
    assert len(notified) == 1

    again = _request(client, world, "member", place, start=3, end=6).json()  # kapasitas sudah kembali
    approve(again)
    by_owner = client.post(f"/mess/{again['mess_stay_id']}/cancel", headers=member)
    assert by_owner.status_code == 200 and by_owner.json()["status"] == "CANCELLED"

    running = _request(client, world, "member", place, start=0, end=3).json()
    approve(running)
    refused = client.post(f"/mess/{running['mess_stay_id']}/cancel", headers=hr)
    assert refused.status_code == 409 and refused.json()["error"]["code"] == "MESS_NOT_CANCELLABLE"
    assert "Selesai inap" in refused.json()["error"]["message"]
