"""
Notifikasi pengajuan aset per kantor (ADR 0002): dengan ROLE_ASSIGNMENT_ENABLED hidup hanya HR yang cakupannya
meliputi kantor aset menerima ASSET_REQUESTED / ASSET_RETURN_REQUESTED / ASSET_REQUEST_CANCELLED. Flag mati = semua HR.
"""
from __future__ import annotations

import hashlib

import pytest

from app.core.config import settings
from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db

HR, OM = "ADMIN_HR_GA", "OPERATIONAL_MANAGER"


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", True)


@pytest.fixture
def flag_off(monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", False)


def _tool(client, w: World, code: str) -> str:
    r = client.post("/assets/tools", headers=w.headers(client, "admin"), json={
        "office_id": w.org_id, "division_id": w.unit_id, "ownership_type": "SHARED_TOOL", "category": "BOR",
        "name": f"Bor {w.tag}", "tool_code": f"{code}-{w.tag}"})
    assert r.status_code == 201, r.text
    return r.json()["tool_id"]


def _assign(client, world: World, who: str, role: str, office: str) -> None:
    r = client.post(f"/users/{world.users[who]}/role-assignments", headers=world.headers(client, "admin"),
                    json={"role": role, "office_id": office})
    assert r.status_code == 201, r.text


def _receivers(kind: str, *worlds: World) -> set[str]:
    """Penerima notifikasi `kind` untuk alat dunia-dunia ini (judul memuat tag; kirim-ke-semua-HR dari tes lain
    yang berjalan paralel tidak ikut terhitung)."""
    ids = [u for w in worlds for u in w.users.values()]
    tags = [w.tag for w in worlds]
    rows = sync_query("SELECT user_id::text, title FROM notification WHERE kind = %s AND user_id::text = ANY(%s)",
                      (kind, ids))
    return {r[0] for r in rows if any(t in r[1] for t in tags)}


@pytest.fixture
def stock(client, world: World, other_world: World):
    mine, theirs = _tool(client, world, "nm"), _tool(client, other_world, "nt")
    yield mine, theirs
    ids = [u for w in (world, other_world) for u in w.users.values()]
    sync_query("DELETE FROM notification WHERE user_id::text = ANY(%s)", (ids,))
    sync_query("DELETE FROM asset_loan_request WHERE tool_id IN (%s, %s)", (mine, theirs))
    sync_query("DELETE FROM asset_assignment WHERE tool_id IN (%s, %s)", (mine, theirs))
    sync_query("DELETE FROM tool WHERE tool_id IN (%s, %s)", (mine, theirs))


def _ask(client, w: World, tool: str) -> str:
    r = client.post("/assets/loan-requests", headers=w.headers(client, "member"),
                    json={"asset_type": "TOOL", "tool_id": tool, "purpose": "Pasang kamera di lokasi"})
    assert r.status_code == 201, r.text
    return r.json()["request_id"]


def test_flag_off_all_hr_receive(client, world: World, other_world: World, stock, flag_off):
    mine, _ = stock
    _ask(client, world, mine)
    assert _receivers("ASSET_REQUESTED", world, other_world) == {world.users["hr"], other_world.users["hr"]}


def test_flag_on_hr_of_other_office_does_not_receive(client, world: World, other_world: World, stock, flag_on):
    mine, theirs = stock
    request_id = _ask(client, world, mine)
    assert _receivers("ASSET_REQUESTED", world, other_world) == {world.users["hr"]}
    r = client.post(f"/assets/loan-requests/{request_id}/cancel", headers=world.headers(client, "member"))
    assert r.status_code == 200, r.text
    assert _receivers("ASSET_REQUEST_CANCELLED", world, other_world) == {world.users["hr"]}
    sync_query("DELETE FROM notification WHERE kind = 'ASSET_REQUESTED' AND user_id::text = ANY(%s)",
               ([u for w in (world, other_world) for u in w.users.values()],))
    _ask(client, other_world, theirs)
    assert _receivers("ASSET_REQUESTED", world, other_world) == {other_world.users["hr"]}


def test_flag_on_hr_with_two_offices_receives_both(client, world: World, other_world: World, stock, flag_on):
    mine, theirs = stock
    _assign(client, world, "hr", HR, other_world.org_id)
    _ask(client, world, mine)
    _ask(client, other_world, theirs)
    assert _receivers("ASSET_REQUESTED", world, other_world) == {world.users["hr"], other_world.users["hr"]}


def test_flag_on_om_with_hr_assignment_receives_only_that_office(client, world: World, other_world: World,
                                                                 stock, flag_on):
    mine, theirs = stock
    _assign(client, world, "ops", HR, world.org_id)
    _ask(client, world, mine)
    got = _receivers("ASSET_REQUESTED", world, other_world)
    assert world.users["ops"] in got and world.users["hr"] in got and other_world.users["hr"] not in got
    sync_query("DELETE FROM notification WHERE kind = 'ASSET_REQUESTED' AND user_id::text = ANY(%s)",
               ([u for w in (world, other_world) for u in w.users.values()],))
    _ask(client, other_world, theirs)
    got = _receivers("ASSET_REQUESTED", world, other_world)
    assert got == {other_world.users["hr"]}  # OM+HR kantor A tidak menerima aset kantor B


def test_flag_on_return_requested_only_hr_of_asset_office(client, world: World, other_world: World, stock, flag_on):
    mine, _ = stock
    lent = client.post("/assets/loans", headers=world.headers(client, "admin"), json={
        "asset_type": "TOOL", "tool_id": mine, "employee_id": world.employees["member"]})
    assert lent.status_code == 201, lent.text
    key = "uji/" + hashlib.sha256(world.tag.encode()).hexdigest()[:24] + ".jpg"
    file_id = sync_query(
        "INSERT INTO file_object (office_id, storage_key, file_name, mime_type, byte_size, sha256) "
        "VALUES (%s, %s, 'kondisi.jpg', 'image/jpeg', 10, decode(%s, 'hex')) RETURNING id::text",
        (world.org_id, key, hashlib.sha256(key.encode()).hexdigest()))[0][0]
    try:
        r = client.post(f"/assets/loans/{lent.json()['assignment_id']}/return-request",
                        headers=world.headers(client, "member"), json={"condition": "ready", "photo_file_id": file_id})
        assert r.status_code == 200, r.text
        assert _receivers("ASSET_RETURN_REQUESTED", world, other_world) == {world.users["hr"]}
    finally:
        sync_query("UPDATE asset_assignment SET return_photo_path = NULL WHERE tool_id = %s", (mine,))
        sync_query("DELETE FROM file_object WHERE id = %s", (file_id,))
