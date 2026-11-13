"""
ADR 0003 · Penerima eksternal aset: master penerima, serah terima ke eksternal (employee_id NULL), pengembalian,
BAST, dan semua jalur baca yang sebelumnya mengandaikan employee_id terisi (daftar, detail, ketersediaan, 'aset saya').
Matriks peran: HR/GA (pengelola aset) bisa; peran lain 403; di luar kantor 404 (cakupan kantor aktif).
"""
from __future__ import annotations

import json
from datetime import timedelta

import pytest

from app.core.config import settings
from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.modules.assets.test_asset_master import create_tool, upload

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]

OTHERS = ("member", "leader", "pm")


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", True)


@pytest.fixture(autouse=True)
def _cleanup(world: World, other_world: World):
    yield
    for w in (world, other_world):
        sync_query("DELETE FROM asset_assignment WHERE external_borrower_id IN "
                   "(SELECT borrower_id FROM asset_external_borrowers WHERE office_id = %s)", (w.org_id,))
        sync_query("DELETE FROM asset_external_borrowers WHERE office_id = %s", (w.org_id,))


def _borrower(client, w: World, nama: str = "PT Sewa Jaya", **extra):
    return client.post("/assets/external-borrowers", headers=w.headers(client, "hr"),
                       json={"office_id": w.org_id, "nama": nama, "instansi": "Pertamina", "kontak": "0812", **extra})


def _blist(client, w: World, query: str = ""):
    return client.get(f"/assets/external-borrowers?office_id={w.org_id}{query}", headers=w.headers(client, "hr"))


def _lend_ext(client, w: World, tool_id: str, borrower_id: str, **extra):
    return client.post("/assets/loans", headers=w.headers(client, "hr"),
                       json={"asset_type": "TOOL", "tool_id": tool_id, "external_borrower_id": borrower_id, **extra})


def _setup(client, world: World, nama: str = "PT Sewa Jaya"):
    tool_id = create_tool(client, world).json()["tool_id"]
    borrower_id = _borrower(client, world, nama).json()["borrower_id"]
    return tool_id, borrower_id


def test_borrower_crud_list_and_prefix_search(client, world: World):
    hr = world.headers(client, "hr")
    created = _borrower(client, world, "  PT   Maju Jaya ")
    assert created.status_code == 201, created.text
    assert created.json()["nama"] == "PT Maju Jaya" and created.json()["has_open_loan"] is False
    bid = created.json()["borrower_id"]
    _borrower(client, world, "CV Beta")

    listed = _blist(client, world)
    assert listed.status_code == 200 and listed.headers["X-Total-Count"] == "2"
    assert _blist(client, world, "&q=pt%20maju").json()[0]["borrower_id"] == bid
    assert _blist(client, world, "&q=jaya").json() == []  # awalan, bukan 'mengandung'
    paged = _blist(client, world, "&page=1&size=1")
    assert len(paged.json()) == 1 and paged.headers["X-Total-Count"] == "2"

    upd = client.put(f"/assets/external-borrowers/{bid}", headers=hr, json={"instansi": "PLN"})
    assert upd.status_code == 200 and upd.json()["instansi"] == "PLN" and upd.json()["nama"] == "PT Maju Jaya"
    assert client.put(f"/assets/external-borrowers/{bid}", headers=hr, json={"nama": " "}).status_code in (400, 422)
    assert client.put("/assets/external-borrowers/00000000-0000-0000-0000-000000000001", headers=hr,
                      json={"nama": "X"}).status_code == 404
    assert client.post("/assets/external-borrowers", headers=hr,
                       json={"office_id": world.org_id, "nama": "x" * 151}).status_code == 422


@pytest.mark.parametrize("who", OTHERS)
def test_borrower_endpoints_forbidden_for_other_roles(client, world: World, who: str):
    bid = _borrower(client, world).json()["borrower_id"]
    h = world.headers(client, who)
    assert client.get("/assets/external-borrowers", headers=h).status_code == 403
    assert client.post("/assets/external-borrowers", headers=h,
                       json={"office_id": world.org_id, "nama": "Z"}).status_code == 403
    assert client.put(f"/assets/external-borrowers/{bid}", headers=h, json={"nama": "Z"}).status_code == 403


def test_borrower_office_scope_404(client, world: World, other_world: World, flag_on):
    theirs = _borrower(client, other_world).json()["borrower_id"]
    hr = world.headers(client, "hr")
    ids = {r["borrower_id"] for r in client.get("/assets/external-borrowers", headers=hr).json()}
    assert theirs not in ids
    assert client.put(f"/assets/external-borrowers/{theirs}", headers=hr, json={"nama": "Z"}).status_code == 404
    assert client.post("/assets/external-borrowers", headers=hr,
                       json={"office_id": other_world.org_id, "nama": "Z"}).status_code == 404


def test_borrower_changes_are_audited_without_contact(client, world: World):
    bid = _borrower(client, world, kontak="08123456789").json()["borrower_id"]
    client.put(f"/assets/external-borrowers/{bid}", headers=world.headers(client, "hr"), json={"nama": "PT Baru"})
    rows = sync_query("SELECT action, changed_diff FROM app_activity_logs WHERE entity_id = %s ORDER BY created_at",
                      (bid,))
    assert [r[0] for r in rows] == ["ASSET_BORROWER_CREATE", "ASSET_BORROWER_UPDATE"]
    assert "08123456789" not in json.dumps([r[1] for r in rows], default=str)


def test_lend_to_external_and_all_read_paths_survive_null_employee(client, world: World):
    tool_id, bid = _setup(client, world)
    due = (jakarta_now().date() + timedelta(days=7)).isoformat()
    bast = upload(client, world)
    loan = _lend_ext(client, world, tool_id, bid, due_date=due, bast_file_id=bast)
    assert loan.status_code == 201, loan.text
    body = loan.json()
    assert body["employee_id"] is None and body["external_borrower_id"] == bid
    assert body["employee_name"] == "PT Sewa Jaya" and body["borrower_name"] == "PT Sewa Jaya"
    assert body["borrower_instansi"] == "Pertamina" and body["due_date"] == due and body["bast_file_id"] == bast
    assert body["assignment_status"] == "loaned"
    aid = body["assignment_id"]

    hr = world.headers(client, "hr")
    # daftar peminjaman (pengelola) memuat baris eksternal; filter per penerima; filter karyawan tidak memuatnya
    assert aid in {r["assignment_id"] for r in client.get("/assets/loans", headers=hr).json()}
    assert [r["assignment_id"] for r in client.get(f"/assets/loans?borrower_id={bid}", headers=hr).json()] == [aid]
    emp = world.employees["member"]
    assert aid not in {r["assignment_id"] for r in client.get(f"/assets/loans?employee_id={emp}", headers=hr).json()}
    # daftar alat menampilkan pemegang eksternal; ketersediaan tidak error
    tool = next(t for t in client.get("/assets/tools", headers=hr).json() if t["tool_id"] == tool_id)
    assert tool["holder_name"] == "PT Sewa Jaya" and tool["holder_employee_id"] is None
    assert tool["holder_external_borrower_id"] == bid
    assert client.get(f"/assets/availability?date={due}", headers=hr).status_code == 200
    assert client.get("/assets/vehicles", headers=hr).status_code == 200
    # penerima punya pinjaman aktif
    assert _blist(client, world).json()[0]["has_open_loan"] is True
    # peran lain: 'aset saya' dan daftar alat tidak memuat serah eksternal dan tidak error
    for who in OTHERS:
        h = world.headers(client, who)
        mine = client.get("/assets/loans", headers=h)
        assert mine.status_code == 200 and aid not in {r["assignment_id"] for r in mine.json()}
        assert client.get("/assets/tools", headers=h).status_code == 200
        assert client.get("/assets/vehicles", headers=h).status_code == 200
    # satu aset satu pinjaman aktif berlaku juga untuk eksternal
    again = _lend_ext(client, world, tool_id, bid)
    assert again.status_code == 409 and again.json()["error"]["code"] == "ASSET_NOT_AVAILABLE"
    # tidak menahan offboarding / tidak muncul di 'pinjaman saya' karyawan
    assert sync_query("SELECT count(*) FROM asset_assignment WHERE employee_id = %s AND returned_at IS NULL",
                      (emp,))[0][0] == 0


def test_return_from_external_and_audit(client, world: World):
    tool_id, bid = _setup(client, world)
    aid = _lend_ext(client, world, tool_id, bid).json()["assignment_id"]
    hr = world.headers(client, "hr")
    done = client.post(f"/assets/loans/{aid}/return", headers=hr, json={"condition": "ready"})
    assert done.status_code == 200, done.text
    assert done.json()["returned_at"] is not None and done.json()["employee_id"] is None
    assert client.post(f"/assets/loans/{aid}/return", headers=hr, json={}).json()["error"]["code"] == "ALREADY_RETURNED"
    assert _blist(client, world).json()[0]["has_open_loan"] is False
    assert _lend_ext(client, world, tool_id, bid).status_code == 201  # siklus pinjam lagi
    acts = {r[0] for r in sync_query("SELECT action FROM app_activity_logs WHERE entity_id = %s", (aid,))}
    assert {"ASSET_LOAN_EXTERNAL", "ASSET_RETURN_EXTERNAL"} <= acts
    closed = client.get("/assets/loans?open=false", headers=hr).json()
    assert aid in {r["assignment_id"] for r in closed}


def test_exactly_one_recipient_and_input_rules(client, world: World):
    tool_id, bid = _setup(client, world)
    hr = world.headers(client, "hr")
    emp = world.employees["member"]
    base = {"asset_type": "TOOL", "tool_id": tool_id}
    assert client.post("/assets/loans", headers=hr, json=base).status_code == 422
    assert client.post("/assets/loans", headers=hr,
                       json={**base, "employee_id": emp, "external_borrower_id": bid}).status_code == 422
    yesterday = (jakarta_now().date() - timedelta(days=1)).isoformat()
    assert _lend_ext(client, world, tool_id, bid, due_date=yesterday).status_code == 422
    assert _lend_ext(client, world, tool_id, "00000000-0000-0000-0000-000000000001").status_code == 404
    # karyawan tetap jalan seperti biasa (APK lama: tanpa field baru)
    ok = client.post("/assets/loans", headers=hr, json={**base, "employee_id": emp})
    assert ok.status_code == 201 and ok.json()["employee_id"] == emp and ok.json()["external_borrower_id"] is None


@pytest.mark.parametrize("who", OTHERS)
def test_lend_to_external_forbidden_for_other_roles(client, world: World, who: str):
    tool_id, bid = _setup(client, world)
    r = client.post("/assets/loans", headers=world.headers(client, who),
                    json={"asset_type": "TOOL", "tool_id": tool_id, "external_borrower_id": bid})
    assert r.status_code == 403


def test_borrower_must_share_office_with_asset(client, world: World, other_world: World):
    tool_id = create_tool(client, world).json()["tool_id"]
    foreign = _borrower(client, other_world).json()["borrower_id"]
    r = _lend_ext(client, world, tool_id, foreign)  # flag mati: HR melihat semua kantor, tapi kantor harus sama
    assert r.status_code == 422, r.text


def test_foreign_office_borrower_is_404_with_office_scope(client, world: World, other_world: World, flag_on):
    tool_id = create_tool(client, world).json()["tool_id"]
    foreign = _borrower(client, other_world).json()["borrower_id"]
    assert _lend_ext(client, world, tool_id, foreign).status_code == 404


def test_bast_office_and_access(client, world: World, other_world: World):
    tool_id, bid = _setup(client, world)
    foreign_bast = upload(client, other_world, colour=7)
    assert _lend_ext(client, world, tool_id, bid, bast_file_id=foreign_bast).status_code == 422
    bast = upload(client, world, colour=9)
    assert _lend_ext(client, world, tool_id, bid, bast_file_id=bast).status_code == 201
    assert client.get(f"/files/{bast}/url", headers=world.headers(client, "hr")).status_code == 200
    assert client.get(f"/files/{bast}/url", headers=world.headers(client, "member")).status_code != 200
