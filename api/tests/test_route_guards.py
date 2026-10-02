"""
V-09 · Setiap rute punya izin atau penjaga.
1. Inventaris: rute non-publik tanpa `require_permission` dan tanpa penjaga SK (`plan_access` dkk.)
   gagal — kecuali terdaftar eksplisit sebagai layanan-mandiri atau dijaga di dalam handler,
   masing-masing dengan alasan. Menambah baris = keputusan keamanan.
2. Perilaku: insiden (ketua/anggota, `domain.js` REPORT_INCIDENT), laporan harian (ketua),
   pengembalian aset (ketua, bukan petugas aset, `domain.js` RETURN_ASSET), penyelesaian insiden
   (PM unit/OPS/ASSET — regresi **R2**: PM unit lain tidak melihat insiden unit lain),
   penjelasan absensi (hanya milik sendiri), cek bentrok (pengelola SK), cron kedaluwarsa (ADMIN,
   hanya organisasinya).
"""
from __future__ import annotations

import io
import re
from datetime import timedelta

import pytest
from fastapi.routing import APIRoute
from PIL import Image

from app.core.time import jakarta_now
from app.main import app
from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import run_plan_to_in_progress
from tests.test_route_smoke import PUBLIC_ROUTES

# Boleh dipanggil setiap pengguna yang login; data tetap dibatasi organisasi / milik sendiri.
SELF_SERVICE = {
    ("GET", "/auth/me"): "profil sendiri",
    ("GET", "/auth/sessions"): "perangkat milik sendiri (P1-7, diuji)",
    ("POST", "/auth/sessions/revoke-others"): "mencabut perangkat lain milik sendiri (P1-7, diuji)",
    ("POST", "/auth/sessions/{session_id}/revoke"): "hanya sesi milik sendiri; milik orang lain → 404 (diuji)",
    ("POST", "/auth/change-password"): "kata sandi sendiri",
    ("POST", "/files/upload"): "setiap karyawan mengunggah bukti/dokumen sendiri",
    ("GET", "/work-plans"): "hanya SK yang terlihat (V-07)",
    ("GET", "/sites"): "daftar lokasi organisasi untuk check-in",
    ("GET", "/units"): "daftar unit organisasi sendiri (pilihan mutasi/promosi, R-19)",
    ("GET", "/assets/{asset_id}/returns"): "riwayat pengembalian aset organisasi sendiri; asing → 404 (diuji)",
    ("GET", "/assets/returns/{return_id}/pdf"): "BAST pengembalian organisasi sendiri; asing → 404 (diuji)",
    ("GET", "/assets"): "daftar aset organisasi (CHECK_ASSET oleh tim)",
    ("GET", "/attendance"): "R-33: milik sendiri; PM + bawahan lapangan unitnya; FINANCE/OPS seluruh organisasi (diuji)",
    ("POST", "/attendance/check-in"): "absensi sendiri",
    ("POST", "/attendance/check-out"): "absensi sendiri",
    ("POST", "/attendance/{att_id}/explain"): "hanya absensi milik sendiri — diuji di bawah",
    ("GET", "/recaps/attendance"): "rekap sendiri; FINANCE/HR/OPS/ADMIN seluruh organisasi (V-30, diuji)",
    ("POST", "/sync/operations"): "antrean luring milik sendiri; tiap operasi dijaga seperti jalur daring (M12)",
    ("GET", "/sync/status"): "status antrean luring milik sendiri (M12)",
}
# Kewenangan bergantung pada isi permintaan (SK di badan) atau tautan berkas → dijaga di handler.
GUARDED_IN_HANDLER = {
    ("POST", "/hse/incidents"): "check_plan_access(LEADER_OR_MEMBER) untuk work_plan_id di badan",
    ("GET", "/files/{file_id}/url"): "check_file_access (V-17): pemilik/HR/peninjau/penglihat SK, selain itu 404",
    # V-22: kewenangan bergantung jenis usulan; ketua baru adendum personel belum tentu anggota SK.
    ("POST", "/work-plans/{plan_id}/changes"): "PlanChangeService: EXTEND=ketua, PERSONNEL=PM unit/OPS",
    ("POST", "/changes/{change_id}/approve"): "PlanChangeService: PM unit/OPS",
    ("POST", "/changes/{change_id}/accept"): "PlanChangeService: ketua (EXTEND) / ketua baru (PERSONNEL)",
    ("POST", "/changes/{change_id}/reject"): "PlanChangeService: ketua/PM (EXTEND) / ketua baru (PERSONNEL)",
    ("POST", "/changes/{change_id}/withdraw"): "PlanChangeService: PM unit/OPS, hanya PERSONNEL",
    # V-27: SK ada di badan permintaan; pengemudi ditentukan alokasi aset.
    ("POST", "/assets/{asset_id}/reserve"): "AssetReservationService: manage:assets atau PM unit/OPS SK (diuji)",
    ("POST", "/assets/{asset_id}/release"): "AssetReservationService: manage:assets atau PM unit/OPS SK (diuji)",
    ("POST", "/assets/{asset_id}/check"): "AssetReservationService: hanya pengemudi yang ditunjuk (diuji)",
    # V-28: SK ada di badan/kueri atau ditentukan baris lembur.
    ("POST", "/overtime"): "OvertimeService: SK terlihat + ketua/anggota (diuji)",
    ("GET", "/overtime"): "OvertimeService: check_plan_access(VIEW) untuk work_plan_id (diuji)",
    ("GET", "/hse/incidents"): "check_plan_access(VIEW) untuk plan_id (diuji di test_flow_plans)",
    ("POST", "/overtime/{ot_id}/review"): "OvertimeService: PM unit/OPS SK, bukan pengaju (diuji)",
    ("GET", "/recaps/overtime"): "OvertimeService: izin review:overtime (Finance/OPS/Admin) (diuji)",
    # Fase 6: dokumen ditentukan id di jalur → SK-nya dicek check_plan_access di service.
    ("GET", "/documents/{document_id}/signatures"): "SignatureService: SK dokumen terlihat (VIEW), selain itu 404",
    ("GET", "/documents/{document_id}/pdf"): "SignatureService: SK dokumen terlihat (VIEW), selain itu 404",
    ("POST", "/signatures/{signature_id}/revoke"): "SignatureService: PM unit/OPS SK (PM_UNIT)",
}
_GUARDS = ("permission_checker", "plan_access.", "plan_day_access.", "allocation_plan_access.",
           "incident_plan_access.")


def _dependency_names(dependant) -> list[str]:
    names = []
    for sub in dependant.dependencies:
        names.append(getattr(sub.call, "__qualname__", repr(sub.call)))
        names += _dependency_names(sub)
    return names


def _routes() -> dict[tuple[str, str], list[str]]:
    """(METODE, jalur tanpa awalan API) → nama dependency. Router yang di-include disimpan malas
    sejak FastAPI 0.14x (`_IncludedRouter.original_router`)."""
    found = {}

    def walk(routes, nested: bool) -> None:
        for route in routes:
            if nested and isinstance(route, APIRoute):  # /health & /ready di akar: publik
                for method in route.methods:
                    # "{token:path}" → "{token}", sama seperti inventaris rute publik (test_route_smoke)
                    path = re.sub(r"\{(\w+):\w+\}", lambda m: "{" + m.group(1) + "}", route.path)
                    found[(method, path)] = _dependency_names(route.dependant)
            # router bertingkat sejak R-28 M2: app → api_router (api/v1/router.py) → router modul
            walk(getattr(getattr(route, "original_router", None), "routes", []), True)

    walk(app.routes, False)
    return found


def test_every_route_has_a_permission_or_guard():
    routes = _routes()
    assert len(routes) > 20
    unguarded = sorted(
        key for key, deps in routes.items()
        if key not in PUBLIC_ROUTES and key not in SELF_SERVICE and key not in GUARDED_IN_HANDLER
        and not any(guard in name for name in deps for guard in _GUARDS)
    )
    assert unguarded == [], f"Rute tanpa izin/penjaga: {unguarded}"


def test_allowlists_have_no_stale_entries():
    routes = _routes()
    assert set(SELF_SERVICE) <= set(routes)
    assert set(GUARDED_IN_HANDLER) <= set(routes)


def _other_unit_pm(world: World) -> None:
    unit = world.add_unit("WALL_DISPLAY")
    world.add_person("pm_other", "PM", unit, per_unit=True)


def _incident(client, world: World, plan_id: str, who: str):
    return client.post("/hse/incidents", headers=world.headers(client, who), json={
        "work_plan_id": plan_id, "occurred_on": jakarta_now().date().isoformat(), "category": "K3_RINGAN",
        "severity": "RENDAH", "description": "Tangga licin di area kerja"})


# ── Insiden ───────────────────────────────────────────────────────────────────────────────────
@requires_db
@pytest.mark.parametrize(("who", "expected"), [
    ("leader", 201), ("member", 201),
    ("pm", 403), ("ops", 403), ("asset", 403),      # terlihat, tetapi bukan tim
    ("pm_other", 404), ("hr", 404),                   # tidak terlihat
])
def test_only_the_team_reports_incidents(client, world, who, expected):
    _other_unit_pm(world)
    plan_id, _ = run_plan_to_in_progress(client, world)

    response = _incident(client, world, plan_id, who)

    assert response.status_code == expected, response.text
    assert sync_query("SELECT count(*) FROM vms.incident_report WHERE work_plan_id = %s", (plan_id,)) \
        == [(1 if expected == 201 else 0,)]


@requires_db
@pytest.mark.parametrize(("who", "expected"), [
    ("pm", 200), ("ops", 200), ("asset", 200),
    ("leader", 403), ("member", 403),
    ("pm_other", 404),                                # R2: PM unit lain tidak melihat insiden unit ini
    ("hr", 404),
])
def test_incident_is_resolved_by_unit_managers_or_asset_officers(client, world, who, expected):
    _other_unit_pm(world)
    plan_id, _ = run_plan_to_in_progress(client, world)
    incident = _incident(client, world, plan_id, "member")
    assert incident.status_code == 201, incident.text
    inc_id = incident.json()["id"]

    response = client.post(f"/hse/incidents/{inc_id}/resolve", headers=world.headers(client, who),
                           json={"resolution_note": "Dipasang karpet anti selip"})

    assert response.status_code == expected, response.text
    assert sync_query("SELECT status::text FROM vms.incident_report WHERE id = %s", (inc_id,)) \
        == [("RESOLVED" if expected == 200 else "OPEN",)]


# ── Laporan harian ────────────────────────────────────────────────────────────────────────────
@requires_db
@pytest.mark.parametrize(("who", "expected"), [
    ("leader", 200), ("member", 403), ("pm", 403), ("pm_other", 404), ("hr", 404),
])
def test_only_the_leader_writes_and_submits_daily_reports(client, world, who, expected):
    _other_unit_pm(world)
    plan_id, day_ids = run_plan_to_in_progress(client, world)
    headers = world.headers(client, who)

    saved = client.put(f"/work-plans/{plan_id}/days/{day_ids[0]}", headers=headers,
                        json={"body": "Kamera 1-4 terpasang dan diuji", "obstacle": "Tidak ada"})
    submitted = client.post(f"/work-plans/{plan_id}/days/{day_ids[0]}/submit", headers=headers)

    assert saved.status_code == expected, saved.text
    assert submitted.status_code == expected, submitted.text
    assert sync_query("SELECT count(*) FROM vms.daily_report WHERE work_plan_day_id = %s", (day_ids[0],)) \
        == [(1 if expected == 200 else 0,)]


# ── Pengembalian aset ─────────────────────────────────────────────────────────────────────────
@requires_db
@pytest.mark.parametrize(("who", "expected"), [
    ("leader", 200),
    ("asset", 403),                                    # domain.js RETURN_ASSET: bukan petugas aset
    ("member", 403), ("pm", 403),
    ("pm_other", 404), ("hr", 404),
])
def test_only_the_leader_requests_an_asset_return(client, world, who, expected):
    _other_unit_pm(world)
    plan_id, _ = run_plan_to_in_progress(client, world)
    officer = world.headers(client, "asset")
    asset = client.post("/assets", headers=officer,
                        json={"kind": "TOOL", "code": "TL-UJI", "name": "Tangga lipat", "condition": "BAIK"})
    assert asset.status_code == 201, asset.text
    allocated = client.post(f"/assets/{asset.json()['id']}/reserve", headers=officer,
                            json={"work_plan_id": plan_id})
    assert allocated.status_code == 200, allocated.text
    alloc_id = allocated.json()["id"]

    response = client.post(f"/assets/allocations/{alloc_id}/return", headers=world.headers(client, who),
                           json={"condition_on_return": "BAIK", "note": "Lengkap"})

    assert response.status_code == expected, response.text
    assert sync_query("SELECT count(*) FROM vms.asset_return WHERE asset_allocation_id = %s", (alloc_id,)) \
        == [(1 if expected == 200 else 0,)]


# ── Penjelasan absensi ────────────────────────────────────────────────────────────────────────
@requires_db
def test_only_the_owner_explains_an_attendance(client, world, other_world, fake_storage):
    member = world.headers(client, "member")
    # Di luar radius + swafoto → NEEDS_REVIEW; hanya absensi yang menunggu pemeriksaan dapat dijelaskan (V-12).
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (5, 6, 7)).save(buf, "PNG")
    selfie = client.post("/files/upload", headers=member, files={"file": ("s.png", buf.getvalue(), "image/png")})
    check_in = client.post("/attendance/check-in", headers=member, json={
        "site_id": world.site_id, "location": {"lat": -6.3, "lng": 106.8},
        "selfie_file_id": selfie.json()["file_id"], "explanation": "Survei titik baru"})
    assert check_in.status_code == 200, check_in.text
    att_id = check_in.json()["id"]

    for outsider in (world.headers(client, "leader"), world.headers(client, "admin"),
                     other_world.headers(client, "member")):
        response = client.post(f"/attendance/{att_id}/explain", headers=outsider, json={"explanation": "Titipan"})
        assert response.status_code == 404, response.text
    assert sync_query("SELECT explanation FROM vms.attendance WHERE id = %s", (att_id,)) == [("Survei titik baru",)]

    own = client.post(f"/attendance/{att_id}/explain", headers=member, json={"explanation": "GPS ponsel mati"})
    assert own.status_code == 200, own.text
    assert sync_query("SELECT explanation FROM vms.attendance WHERE id = %s", (att_id,)) == [("GPS ponsel mati",)]


# ── Cek bentrok jadwal ────────────────────────────────────────────────────────────────────────
@requires_db
def test_schedule_conflicts_are_for_plan_managers_in_the_same_organisation(client, world, other_world):
    today = jakarta_now().date()
    query = f"start_date={today.isoformat()}&end_date={(today + timedelta(days=3)).isoformat()}"
    own_emp, foreign_emp = world.employees["member"], other_world.employees["member"]

    assert client.get(f"/employees/{own_emp}/conflicts?{query}", headers=world.headers(client, "pm")).status_code == 200
    assert client.get(f"/employees/{own_emp}/conflicts?{query}",
                      headers=world.headers(client, "member")).status_code == 403
    foreign = client.get(f"/employees/{foreign_emp}/conflicts?{query}", headers=world.headers(client, "pm"))
    assert foreign.status_code == 404, foreign.text


# ── Cron kedaluwarsa dokumen ──────────────────────────────────────────────────────────────────
def _expired_current_document(world: World) -> str:
    return str(sync_query(
        "WITH _ctx AS (SELECT set_config('app.organization_id', %s, true)) "
        "INSERT INTO vms.employee_document (employee_id, doc_type, number_masked, expiry_date, status, lifecycle, "
        "uploaded_by) SELECT e.id, 'SIM A', '****1234', DATE '2026-01-01', 'VERIFIED', 'CURRENT', u.id "
        "FROM vms.employee e JOIN vms.app_user u ON u.employee_id = e.id, _ctx WHERE e.id = %s RETURNING id",
        (world.org_id, world.employees["member"]))[0][0])


@requires_db
def test_document_expiry_cron_is_admin_only_and_stays_in_its_organisation(client, world, other_world):
    own_doc, foreign_doc = _expired_current_document(world), _expired_current_document(other_world)

    assert client.post("/documents/cron/expire-documents", headers=world.headers(client, "member")).status_code == 403
    assert client.post("/documents/cron/expire-documents", headers=world.headers(client, "hr")).status_code == 403
    response = client.post("/documents/cron/expire-documents", headers=world.headers(client, "admin"))

    assert response.status_code == 200, response.text
    lifecycle = "SELECT lifecycle::text FROM vms.employee_document WHERE id = %s"
    assert sync_query(lifecycle, (own_doc,)) == [("EXPIRED",)]
    assert sync_query(lifecycle, (foreign_doc,)) == [("CURRENT",)]

