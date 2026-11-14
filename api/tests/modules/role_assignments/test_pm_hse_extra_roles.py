"""
Perluasan fase 2 ADR 0002: PROJECT_MANAGER dan HSE sebagai peran tambahan per kantor.
Aturan penugasan (pemberi SA dan OM saja), cakupan kantor di endpoint PM/HSE, kombinasi {EMPLOYEE+PM, EMPLOYEE+HSE,
HR+HSE, OM+PM}, pencabutan seketika, dan paritas flag mati.
"""
from __future__ import annotations

import pytest

from app.core.config import settings
from tests.conftest import World, requires_db, sync_query
from tests.modules.role_assignments.test_role_assignments import FIN, HR, OM, _assign

pytestmark = requires_db

PM, HSE = "PROJECT_MANAGER", "HSE"


@pytest.fixture
def flag_on(monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", True)


@pytest.fixture
def flag_off(monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", False)


# ── Layanan penugasan ─────────────────────────────────────────────────────────
def test_add_per_office_ok_and_requires_office(client, world: World, other_world: World):
    world.add_person("x", None)
    for role in (PM, HSE):
        r = _assign(client, world, "x", role, None)
        assert r.status_code == 422, r.text  # tanpa kantor ditolak (ck_ura_office)
    assert _assign(client, world, "x", PM, world.org_id).status_code == 201
    assert _assign(client, world, "x", PM, world.org_id).status_code == 422  # duplikat
    assert _assign(client, world, "x", PM, other_world.org_id).status_code == 201  # kantor lain boleh
    row = sync_query("SELECT count(*) FROM user_role_assignment WHERE user_id = %s AND role = 'PROJECT_MANAGER' "
                     "AND delete_at IS NULL", (world.users["x"],))
    assert row[0][0] == 2


def test_self_super_admin_and_primary_same_role_rejected(client, world: World):
    world.add_person("sa2", "ADMIN")
    assert _assign(client, world, "sa2", PM, world.org_id).status_code == 422  # SA tak digabung
    assert _assign(client, world, "pm", PM, world.org_id).status_code == 422   # sudah PM utama
    assert _assign(client, world, "admin", HSE, world.org_id).status_code == 422  # diri sendiri


def test_pm_plus_hse_allowed_hr_finance_still_forbidden_and_limit(client, world: World, monkeypatch):
    world.add_person("x", None)
    assert _assign(client, world, "x", PM, world.org_id).status_code == 201
    assert _assign(client, world, "x", HSE, world.org_id).status_code == 201  # PM + HSE satu orang boleh
    r = _assign(client, world, "x", HR, world.org_id)  # batas MAX_EXTRA_ROLES = 2
    assert r.status_code == 422 and "peran tambahan" in r.json()["error"]["message"]
    world.add_person("y", None)
    assert _assign(client, world, "y", HR, world.org_id).status_code == 201
    assert _assign(client, world, "y", FIN, world.org_id).status_code == 422  # HR + Finance tetap dilarang
    assert _assign(client, world, "y", HSE, world.org_id).status_code == 201  # HR + HSE boleh


def test_givers_sa_and_om_only(client, world: World):
    world.add_person("x", None)
    assert _assign(client, world, "x", PM, world.org_id, by="ops").status_code == 201   # OM memberi PM
    assert _assign(client, world, "x", HSE, world.org_id, by="ops").status_code == 201  # OM memberi HSE
    for role, office in ((HR, world.org_id), (FIN, world.org_id), (OM, None)):
        assert _assign(client, world, "x", role, office, by="ops").status_code in (403, 422)
    r = _assign(client, world, "x", HR, world.org_id, by="ops")
    assert r.status_code == 403  # OM tak boleh memberi HR
    for who in ("hr", "pm", "member", "leader"):  # HR dan peran lain tidak boleh memberi PM/HSE
        assert _assign(client, world, "x", PM, world.org_id, by=who).status_code == 403
        r = client.get(f"/users/{world.users['x']}/role-assignments", headers=world.headers(client, who))
        assert r.status_code == 403
    # OM mencabut PM/HSE boleh, mencabut HR (diberi SA) tidak
    hr_row = _assign(client, world, "x", HR, world.org_id)
    assert hr_row.status_code == 422  # sudah 2 peran tambahan; cabut satu dahulu
    listed = client.get(f"/users/{world.users['x']}/role-assignments", headers=world.headers(client, "ops")).json()
    assert len(listed) == 2
    d = client.delete(f"/users/{world.users['x']}/role-assignments/{listed[0]['assignment_id']}",
                      headers=world.headers(client, "ops"))
    assert d.status_code == 204
    hr_row = _assign(client, world, "x", HR, world.org_id)
    assert hr_row.status_code == 201
    d = client.delete(f"/users/{world.users['x']}/role-assignments/{hr_row.json()['assignment_id']}",
                      headers=world.headers(client, "ops"))
    assert d.status_code == 403


def test_audit_before_after(client, world: World):
    world.add_person("x", None)
    assert _assign(client, world, "x", HSE, world.org_id).status_code == 201
    row = sync_query("SELECT action FROM app_activity_logs WHERE entity_table = 'users' AND entity_id = %s "
                     "AND action = 'ROLE_ASSIGNMENT_ADD'", (world.users["x"],))
    assert len(row) == 1


def test_extra_pm_hse_cannot_reach_admin_endpoints(client, world: World, flag_on):
    world.add_person("x", None)
    world.add_person("t", None)
    assert _assign(client, world, "x", PM, world.org_id).status_code == 201
    assert _assign(client, world, "x", HSE, world.org_id).status_code == 201
    h = world.headers(client, "x")
    assert client.get(f"/users/{world.users['t']}/role-assignments", headers=h).status_code == 403
    r = client.post(f"/users/{world.users['t']}/role-assignments", headers=h,
                    json={"role": HSE, "office_id": world.org_id})
    assert r.status_code == 403
    assert client.post("/users", headers=h, json={}).status_code in (403, 404, 405)


# ── Matriks peran x endpoint ──────────────────────────────────────────────────
@pytest.fixture
def vehicles(world: World, other_world: World):
    ids = {}
    for key, w in (("a", world), ("b", other_world)):
        vid = str(sync_query(
            "INSERT INTO vehicle (office_id, division_id, vehicle_type, name, number_plate, status) "
            "VALUES (%s, %s, 'Car', 'Mobil uji', %s, 'ready') RETURNING vehicle_id",
            (w.org_id, w.unit_id, f"B {w.tag[:4]} {key.upper()}"))[0][0])
        insp = str(sync_query(
            "INSERT INTO vehicle_safety_inspections (vehicle_id, inspector_id, period_type, inspection_date, "
            "odometer_km, checklist_json, photos_json, status) "
            "VALUES (%s, %s, 'DAILY', CURRENT_DATE, 100, '{}'::jsonb, '[]'::jsonb, 'SUBMITTED') "
            "RETURNING inspection_id", (vid, w.employees["leader"]))[0][0])
        ids[key] = (vid, insp)
    yield ids
    for vid, _insp in ids.values():
        sync_query("DELETE FROM vehicle_safety_inspections WHERE vehicle_id = %s RETURNING 1", (vid,))
        sync_query("DELETE FROM vehicle WHERE vehicle_id = %s RETURNING 1", (vid,))


def _insp_ids(client, w: World, who: str) -> set[str]:
    r = client.get("/hse/inspections", headers=w.headers(client, who))
    assert r.status_code == 200, r.text
    return {i["inspection_id"] for i in r.json()}


def test_hse_extra_scoped_to_assigned_office(client, world: World, other_world: World, vehicles, flag_on):
    (_va, ia), (_vb, ib) = vehicles["a"], vehicles["b"]
    world.add_person("x", None)
    world.add_person("hrx", "HR")
    h = world.headers(client, "x")
    assert client.get("/hse/inspections", headers=h).status_code == 403  # belum ditugaskan
    assert _assign(client, world, "x", HSE, world.org_id).status_code == 201
    assert _assign(client, world, "hrx", HSE, world.org_id).status_code == 201
    for who in ("x", "hrx"):  # EMPLOYEE+HSE@A dan HR+HSE@A
        ids = _insp_ids(client, world, who)
        assert ia in ids and ib not in ids, (who, len(ids))
        assert client.get(f"/hse/inspections/{ia}", headers=world.headers(client, who)).status_code == 200
        assert client.get(f"/hse/inspections/{ib}", headers=world.headers(client, who)).status_code == 404
        v = client.patch(f"/hse/inspections/{ib}/verify", headers=world.headers(client, who),
                         json={"status": "VERIFIED", "notes": "x"})
        assert v.status_code == 404
    ok = client.patch(f"/hse/inspections/{ia}/verify", headers=h, json={"status": "VERIFIED", "notes": "ok"})
    assert ok.status_code == 200, ok.text
    # tolak: kantor lain 404 (tanpa menulis alasan), kantor sendiri menyimpan alasan di reject_reason
    other = client.patch(f"/hse/inspections/{ib}/verify", headers=h, json={"status": "REJECTED", "reject_reason": "x"})
    assert other.status_code == 404
    rej = client.patch(f"/hse/inspections/{ia}/verify", headers=h,
                       json={"status": "REJECTED", "reject_reason": "Foto buram"})
    assert rej.status_code == 200 and rej.json()["reject_reason"] == "Foto buram"
    untouched = client.get(f"/hse/inspections/{ib}", headers=world.headers(client, "admin")).json()
    assert untouched["reject_reason"] is None
    # dokumen karyawan: kantor penugasan saja
    assert client.get(f"/employees/{world.employees['member']}/documents", headers=h).status_code == 200
    assert client.get(f"/employees/{other_world.employees['member']}/documents", headers=h).status_code == 404
    # pencabutan seketika pada token yang sama
    rows = client.get(f"/users/{world.users['x']}/role-assignments", headers=world.headers(client, "admin")).json()
    client.delete(f"/users/{world.users['x']}/role-assignments/{rows[0]['assignment_id']}",
                  headers=world.headers(client, "admin"))
    assert client.get("/hse/inspections", headers=h).status_code == 403


def test_hse_primary_and_super_admin_unrestricted(client, world: World, vehicles, flag_on):
    world.add_person("hse", "HSE")
    for who in ("hse", "admin"):
        ids = _insp_ids(client, world, who)
        assert vehicles["a"][1] in ids and vehicles["b"][1] in ids


def test_hse_inactive_account_ignored(client, world: World, vehicles, flag_on):
    world.add_person("x", None)
    assert _assign(client, world, "x", HSE, world.org_id).status_code == 201
    h = world.headers(client, "x")
    sync_query("UPDATE users SET is_active = FALSE WHERE user_id = %s RETURNING 1", (world.users["x"],))
    assert client.get("/hse/inspections", headers=h).status_code in (401, 403)


@pytest.fixture
def stays(client, world: World, other_world: World):
    place = client.post("/mess/places", headers=world.headers(client, "hr"), json={
        "mess_name": f"Mess pm {world.tag}", "city": "Pekanbaru", "address": "Jl. Uji 1", "capacity": 10})
    assert place.status_code == 201, place.text
    mid = place.json()["mess_id"]
    from datetime import timedelta

    from app.core.time import jakarta_now
    day = lambda n: (jakarta_now().date() + timedelta(days=n)).isoformat()  # noqa: E731
    for w in (world, other_world):
        r = client.post("/mess/requests", headers=w.headers(client, "member"), json={
            "mess_id": mid, "stay_start_date": day(1), "stay_end_date": day(2), "note": "uji"})
        assert r.status_code == 201, r.text
    yield
    sync_query("DELETE FROM company_mess_stay WHERE mess_id = %s RETURNING 1", (mid,))
    sync_query("DELETE FROM company_mess WHERE mess_id = %s RETURNING 1", (mid,))


def _mess_emps(client, w: World, who: str) -> set[str]:
    r = client.get("/mess", headers=w.headers(client, who))
    assert r.status_code == 200, r.text
    return {s["employee_id"] for s in r.json()}


def test_pm_extra_mess_scoped_om_pm_wide_flag_off_old(client, world: World, other_world: World, stays, monkeypatch):
    a, b = world.employees["member"], other_world.employees["member"]
    world.add_person("x", None)
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", True)
    assert _assign(client, world, "x", PM, world.org_id).status_code == 201
    assert _assign(client, world, "ops", PM, world.org_id).status_code == 201  # OM + PM@A
    got = _mess_emps(client, world, "x")  # EMPLOYEE+PM@A: kantor A saja
    assert a in got and b not in got
    om = _mess_emps(client, world, "ops")  # OM (+ PM) melihat semua kantor
    assert a in om and b in om
    pm_primary = _mess_emps(client, world, "pm")  # PM utama: perilaku lama
    assert a in pm_primary
    # PM tambahan tidak punya jalur keputusan data (pm_id divisi): tidak bisa memutuskan
    stay = client.get("/mess", headers=world.headers(client, "hr")).json()[0]["mess_stay_id"]
    d = client.post(f"/mess/{stay}/decision", headers=world.headers(client, "x"), json={"approve": True})
    assert d.status_code == 403
    # pencabutan seketika
    rows = client.get(f"/users/{world.users['x']}/role-assignments", headers=world.headers(client, "admin")).json()
    client.delete(f"/users/{world.users['x']}/role-assignments/{rows[0]['assignment_id']}",
                  headers=world.headers(client, "admin"))
    assert client.get("/mess", headers=world.headers(client, "x")).status_code == 403
    # flag mati: peran tambahan tidak berlaku sama sekali
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", False)
    assert client.get("/mess", headers=world.headers(client, "x")).status_code == 403


def test_om_plus_pm_not_narrowed_to_division(client, world: World, flag_on):
    """OM/HR yang juga PM tambahan tetap melihat tim di luar divisi PM (tanpa penyempitan). Daftar tim global,
    jadi hanya tim dunia ini yang dibandingkan (tes lain berjalan paralel)."""
    assert _assign(client, world, "ops", PM, world.org_id).status_code == 201
    assert _assign(client, world, "hr", PM, world.org_id).status_code == 201
    for who in ("ops", "hr"):
        r = client.get("/teams", headers=world.headers(client, who))
        assert r.status_code == 200 and world.team_id in {t["team_id"] for t in r.json()}, who


def test_hr_plus_pm_leave_review_keeps_hr_path(client, world: World, flag_on):
    """HR yang juga PM tambahan tetap meninjau cuti sebagai HR (bukan 403 'PM hanya divisinya')."""
    assert _assign(client, world, "hr", PM, world.org_id).status_code == 201
    from datetime import timedelta

    from app.core.time import jakarta_now
    day = jakarta_now().date() + timedelta(days=20)
    while day.weekday() == 6:   # cuti 1 hari di hari Minggu ditolak (422 'hari kerja efektif')
        day += timedelta(days=1)
    start = day.isoformat()
    sent = client.post("/leaves", headers=world.headers(client, "leader"), json={
        "leave_type": "OTHER", "start_date": start, "end_date": start, "reason": "Urusan keluarga"})
    assert sent.status_code in (200, 201), sent.text
    lid = sent.json()["leave_id"]
    r = client.post(f"/leaves/{lid}/review", headers=world.headers(client, "hr"),
                    json={"decision": "APPROVED", "note": "ok"})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "APPROVED_BY_HR"
