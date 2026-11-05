"""
Aset (/assets/*) per kantor (ADR 0002; docs/audit-izin-hr-finance-per-kantor.md): pengelola aset yang izinnya hanya
datang dari HR dibatasi ke kantor tugasnya. Cakupan divisi/pemegang yang ada tidak dilemahkan. Flag mati = lama.
"""
from __future__ import annotations

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
        "name": "Bor uji", "tool_code": f"{code}-{w.tag}"})
    assert r.status_code == 201, r.text
    return r.json()["tool_id"]


def _vehicle(w: World) -> str:
    return str(sync_query(
        "INSERT INTO vehicle (office_id, division_id, vehicle_type, name, number_plate, status) "
        "VALUES (%s, %s, 'Car', 'Mobil uji', %s, 'ready') RETURNING vehicle_id",
        (w.org_id, w.unit_id, f"B {w.tag[:4]} KT"))[0][0])


def _assign(client, world: World, who: str, role: str, office: str) -> None:
    r = client.post(f"/users/{world.users[who]}/role-assignments", headers=world.headers(client, "admin"),
                    json={"role": role, "office_id": office})
    assert r.status_code == 201, r.text


def _ids(client, w: World, who: str, path: str, key: str) -> set[str]:
    r = client.get(path, headers=w.headers(client, who))
    assert r.status_code == 200, r.text
    return {x[key] for x in r.json()}


@pytest.fixture
def stock(client, world: World, other_world: World):
    mine, theirs = _tool(client, world, "tm"), _tool(client, other_world, "tt")
    veh_mine, veh_theirs = _vehicle(world), _vehicle(other_world)
    yield mine, theirs, veh_mine, veh_theirs
    sync_query("DELETE FROM asset_loan_request WHERE tool_id IN (%s, %s)", (mine, theirs))
    sync_query("DELETE FROM asset_assignment WHERE tool_id IN (%s, %s)", (mine, theirs))
    sync_query("DELETE FROM tool WHERE tool_id IN (%s, %s)", (mine, theirs))
    sync_query("DELETE FROM vehicle WHERE vehicle_id IN (%s, %s)", (veh_mine, veh_theirs))


def test_flag_off_hr_sees_and_changes_all_offices(client, world: World, other_world: World, stock, flag_off):
    mine, theirs, veh_mine, veh_theirs = stock
    assert {mine, theirs} <= _ids(client, world, "hr", "/assets/tools", "tool_id")
    assert {veh_mine, veh_theirs} <= _ids(client, world, "hr", "/assets/vehicles", "vehicle_id")
    hr = world.headers(client, "hr")
    assert client.get(f"/assets/vehicles/{veh_theirs}/files", headers=hr).status_code == 200
    assert client.post(f"/assets/tools/{theirs}/status", headers=hr, json={"status": "damaged"}).status_code == 200


def test_flag_on_hr_single_office(client, world: World, other_world: World, stock, flag_on):
    mine, theirs, veh_mine, veh_theirs = stock
    hr = world.headers(client, "hr")
    tools = _ids(client, world, "hr", "/assets/tools", "tool_id")
    assert mine in tools and theirs not in tools
    vehicles = _ids(client, world, "hr", "/assets/vehicles", "vehicle_id")
    assert veh_mine in vehicles and veh_theirs not in vehicles
    avail = _ids(client, world, "hr", "/assets/availability?date=2030-01-01", "asset_id")
    assert mine in avail and theirs not in avail
    assert client.get(f"/assets/vehicles/{veh_mine}/files", headers=hr).status_code == 200
    for url in (f"/assets/vehicles/{veh_theirs}/files", f"/assets/vehicles/{veh_theirs}/inspections"):
        assert client.get(url, headers=hr).status_code == 404
    assert client.post(f"/assets/tools/{theirs}/status", headers=hr, json={"status": "damaged"}).status_code == 404
    assert client.post(f"/assets/vehicles/{veh_theirs}/status", headers=hr,
                       json={"status": "damaged"}).status_code == 404
    assert client.put(f"/assets/tools/{theirs}", headers=hr, json={"name": "Ubah"}).status_code == 404
    assert client.put(f"/assets/vehicles/{veh_theirs}", headers=hr, json={"name": "Ubah"}).status_code == 404
    assert client.delete(f"/assets/tools/{theirs}", headers=hr).status_code == 404
    assert client.delete(f"/assets/vehicles/{veh_theirs}", headers=hr).status_code == 404
    stnk = {"type": "STNK", "file_id": "00000000-0000-0000-0000-000000000000", "expired_at": "2030-01-01"}
    assert client.post(f"/assets/vehicles/{veh_theirs}/files", headers=hr, json=stnk).status_code == 404
    assert client.post(f"/assets/tools/{mine}/status", headers=hr, json={"status": "damaged"}).status_code == 200


def test_flag_on_hr_cannot_create_or_move_asset_to_foreign_office(client, world: World, other_world: World,
                                                                  stock, flag_on):
    mine, *_ = stock
    hr = world.headers(client, "hr")
    r = client.post("/assets/tools", headers=hr, json={
        "office_id": other_world.org_id, "ownership_type": "SHARED_TOOL", "category": "BOR", "name": "Xx",
        "tool_code": f"tx-{world.tag}"})
    assert r.status_code == 404, r.text
    assert client.put(f"/assets/tools/{mine}", headers=hr, json={"office_id": other_world.org_id}).status_code == 404


def test_flag_on_hr_two_offices(client, world: World, other_world: World, stock, flag_on):
    mine, theirs, _, veh_theirs = stock
    _assign(client, world, "hr", HR, other_world.org_id)
    assert {mine, theirs} <= _ids(client, world, "hr", "/assets/tools", "tool_id")
    hr = world.headers(client, "hr")
    assert client.get(f"/assets/vehicles/{veh_theirs}/files", headers=hr).status_code == 200
    assert client.post(f"/assets/tools/{theirs}/status", headers=hr, json={"status": "damaged"}).status_code == 200


def test_flag_on_om_plus_hr_reads_all_but_changes_only_hr_office(client, world: World, other_world: World,
                                                                   stock, flag_on):
    mine, theirs, _, veh_theirs = stock
    _assign(client, world, "ops", HR, world.org_id)
    ops = world.headers(client, "ops")
    assert {mine, theirs} <= _ids(client, world, "ops", "/assets/tools", "tool_id")  # OM tetap melihat semua kantor
    assert client.get(f"/assets/vehicles/{veh_theirs}/files", headers=ops).status_code == 200
    assert client.post(f"/assets/tools/{theirs}/status", headers=ops, json={"status": "damaged"}).status_code == 404
    assert client.post(f"/assets/tools/{mine}/status", headers=ops, json={"status": "damaged"}).status_code == 200


def test_flag_on_om_single_role_unrestricted(client, world: World, other_world: World, stock, flag_on):
    mine, theirs, *_ = stock
    assert {mine, theirs} <= _ids(client, world, "ops", "/assets/tools", "tool_id")
    # OM tunggal tidak memegang manage:assets: mutasi tetap 403 seperti sebelumnya
    assert client.post(f"/assets/tools/{mine}/status", headers=world.headers(client, "ops"),
                       json={"status": "damaged"}).status_code == 403


def test_flag_on_super_admin_unrestricted(client, world: World, other_world: World, stock, flag_on):
    mine, theirs, *_ = stock
    assert {mine, theirs} <= _ids(client, world, "admin", "/assets/tools", "tool_id")
    assert client.post(f"/assets/tools/{theirs}/status", headers=world.headers(client, "admin"),
                       json={"status": "damaged"}).status_code == 200


def test_flag_on_pm_and_employee_scope_not_widened(client, world: World, other_world: World, stock, flag_on):
    mine, theirs, *_ = stock
    for who in ("pm", "member"):
        assert theirs not in _ids(client, world, who, "/assets/tools", "tool_id")
    assert mine in _ids(client, world, "pm", "/assets/tools", "tool_id")  # divisi PM: cakupan lama tetap


def test_flag_on_loans_and_requests_scoped(client, world: World, other_world: World, stock, flag_on):
    mine, theirs, *_ = stock
    adm = other_world.headers(client, "admin")
    lent = client.post("/assets/loans", headers=adm, json={
        "asset_type": "TOOL", "tool_id": theirs, "employee_id": other_world.employees["member"]})
    assert lent.status_code == 201, lent.text
    loan_id = lent.json()["assignment_id"]
    asked = client.post("/assets/loan-requests", headers=world.headers(client, "member"),
                        json={"asset_type": "TOOL", "tool_id": mine, "purpose": "Pasang kamera di lokasi"})
    assert asked.status_code == 201, asked.text
    request_id = asked.json()["request_id"]
    hr = world.headers(client, "hr")
    assert loan_id not in _ids(client, world, "hr", "/assets/loans", "assignment_id")
    assert request_id in _ids(client, world, "hr", "/assets/loan-requests", "request_id")
    # pengembalian pinjaman kantor lain oleh HR kantor ini: 404; pemegang tetap melihat pinjamannya
    assert client.post(f"/assets/loans/{loan_id}/return", headers=hr, json={"condition": "ready"}).status_code == 404
    assert loan_id in _ids(client, other_world, "member", "/assets/loans", "assignment_id")
    # HR kantor lain bisa menyetujui pengajuan kantor ini? Tidak: 404
    other_hr = other_world.headers(client, "hr")
    assert client.post(f"/assets/loan-requests/{request_id}/review", headers=other_hr,
                       json={"decision": "REJECTED", "note": "uji"}).status_code == 404
    assert client.post(f"/assets/loan-requests/{request_id}/review", headers=hr,
                       json={"decision": "REJECTED", "note": "uji"}).status_code == 200
    assert client.post(f"/assets/loans/{loan_id}/return", headers=adm, json={"condition": "ready"}).status_code == 200


def test_flag_on_lend_foreign_asset_404(client, world: World, other_world: World, stock, flag_on):
    _, theirs, *_ = stock
    r = client.post("/assets/loans", headers=world.headers(client, "hr"), json={
        "asset_type": "TOOL", "tool_id": theirs, "employee_id": world.employees["member"]})
    assert r.status_code == 404
