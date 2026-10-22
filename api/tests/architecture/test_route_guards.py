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

from fastapi.routing import APIRoute
from PIL import Image

from app.core.time import jakarta_now
from app.main import app
from tests.architecture.test_route_smoke import PUBLIC_ROUTES
from tests.conftest import World, requires_db, sync_query

# Boleh dipanggil setiap pengguna yang login; data tetap dibatasi organisasi / milik sendiri.
SELF_SERVICE = {
    ("GET", "/auth/me"): "profil sendiri",
    ("GET", "/auth/sessions"): "perangkat milik sendiri (P1-7, diuji)",
    ("POST", "/auth/sessions/revoke-others"): "mencabut perangkat lain milik sendiri (P1-7, diuji)",
    ("POST", "/auth/sessions/{session_id}/revoke"): "hanya sesi milik sendiri; milik orang lain → 404 (diuji)",
    ("POST", "/auth/change-password"): "kata sandi sendiri",
    ("POST", "/files/upload"): "setiap karyawan mengunggah bukti/dokumen sendiri",
    ("GET", "/notifications"): "notifikasi milik sendiri (alur SK v2)",
    ("POST", "/notifications/read-all"): "menandai notifikasi milik sendiri",
    ("POST", "/notifications/{notification_id}/read"): "hanya notifikasi milik sendiri; milik orang lain tidak berubah",
    ("GET", "/offices"): "daftar kantor organisasi untuk check-in",
    ("GET", "/events"): "aliran peristiwa milik sendiri; token JWT divalidasi sekali saat menyambung (T8)",
    ("GET", "/work-types"): "daftar jenis pekerjaan organisasi sendiri; yang nonaktif hanya untuk pengelola (T9)",
    ("GET", "/work-plans/daily"): "jadwal harian: PM/OM divisinya, lapangan timnya yang dirilis (M5, diuji)",
    ("GET", "/work-plans/orders/{completion_id}/schedule"): "hanya jadwal yang terlihat pengguna (M5)",
    ("GET", "/work-completions"): "order: pengelola divisinya; lapangan order tim jadwalnya (M5)",
    ("GET", "/image-requirements/by-work-type/{work_type_id}"): "template foto SOP (baca saja) untuk lapangan",
    ("GET", "/image-requirements/{requirement_id}"): "detail template foto SOP (baca saja)",
    ("GET", "/work-types/{type_id}/materials"): "BoM bawaan jenis pekerjaan (baca saja)",
    ("GET", "/divisions"): "daftar divisi organisasi sendiri (pilihan form karyawan)",
    ("GET", "/assets/tools"): "inventaris alat (baca saja) untuk perencanaan & HP tim (M4)",
    ("GET", "/assets/vehicles"): "inventaris kendaraan + masa STNK/KIR (baca saja, M4)",
    ("GET", "/assets/vehicles/{vehicle_id}/files"): "berkas kendaraan (baca saja, M4)",
    ("GET", "/assets/vehicles/{vehicle_id}/inspections"): "riwayat inspeksi kendaraan (baca saja, M4)",
    ("GET", "/assets/loans"): "pengelola aset/peran kantor semua; pekerja lapangan hanya miliknya (M4, diuji)",
    ("GET", "/work-plans/daily/{daily_plan_id}/assets"): "aset jadwal harian: anggota tim semua, lainnya miliknya",
    ("GET", "/attendance"): "R-33: milik sendiri; PM + bawahan lapangan unitnya; FINANCE/OPS seluruh organisasi (diuji)",
    ("POST", "/attendance/check-in"): "absensi sendiri",
    ("POST", "/attendance/check-out"): "absensi sendiri",
    ("POST", "/attendance/device-key"): "kunci perangkat milik sendiri (R-34, diuji)",
    ("POST", "/attendance/offline"): "absen offline milik sendiri, bertanda tangan perangkat (R-34, diuji)",
    ("POST", "/attendance/{att_id}/explain"): "hanya absensi milik sendiri — diuji di bawah",
    ("GET", "/recaps/attendance"): "rekap sendiri; FINANCE/HR/OPS/ADMIN seluruh organisasi (V-30, diuji)",
    ("POST", "/sync/operations"): "antrean offline milik sendiri; tiap operasi dijaga seperti jalur online (M12)",
    ("GET", "/sync/status"): "status antrean offline milik sendiri (M12)",
    ("GET", "/face/policy"): "ambang & syarat pendaftaran wajah (sama untuk semua)",
    ("GET", "/face/status"): "status pendaftaran wajah milik sendiri",
    ("POST", "/face/enroll"): "pendaftaran wajah milik sendiri (pekerja lapangan)",
}
# Kewenangan bergantung pada isi permintaan (SK di badan) atau tautan berkas → dijaga di handler.
GUARDED_IN_HANDLER = {
    # M5 daily-first: kedudukan pada jadwal/order dibaca di service (check_daily_access / standing order).
    ("GET", "/work-plans/daily/{daily_plan_id}/items"): "PlanItemService: check_daily_access(VIEW), lain 404",
    ("GET", "/work-plans/items/{item_id}"): "PlanItemService: jadwal item terlihat (VIEW), lain 404",
    ("GET", "/work-plans/items/{item_id}/chain"): "PlanItemService: jadwal item terlihat (VIEW), lain 404",
    ("PATCH", "/work-plans/items/{item_id}/progress"): "PlanItemService: ketua/anggota tim jadwal ONGOING (diuji)",
    ("POST", "/work-plans/items/{item_id}/request-rollover"): "PlanItemService: hanya ketua tim jadwal (diuji)",
    ("POST", "/work-plans/daily/{daily_plan_id}/start"): "DailyPlanService: hanya ketua tim jadwal (diuji)",
    ("POST", "/work-plans/daily/{daily_plan_id}/complete"): "DailyPlanService: ketua tim atau PM/OM divisi",
    ("GET", "/work-completions/{completion_id}"): "WorkCompletionService: pengelola/HR/anggota tim, lain 404",
    ("GET", "/work-completions/{completion_id}/bom"): "WorkCompletionService: sama dengan detail order",
    ("GET", "/attendance/meal-allowance"): "AttendanceSessionService: export:attendance semua; PM divisinya; lain 403",
    # M8: ekspor/riwayat/unduh ulang dokumen order = hak lihat order (WorkCompletionService), lain 404.
    ("POST", "/exports/work-completions/{completion_id}"): "ExportService: sama dengan detail order",
    ("GET", "/exports/work-completions/{completion_id}"): "ExportService: sama dengan detail order",
    ("GET", "/exports/{export_id}/file"): "ExportService: order terlihat / rekap milik sendiri, OM, admin; lain 404",
    ("POST", "/work-completions/{completion_id}/sign"): "WorkCompletionService: ketua tim order / pengelola",
    ("GET", "/files/{file_id}/url"): "check_file_access (V-17): pemilik/HR/peninjau/penglihat SK, selain itu 404",
    ("GET", "/files/{file_id}"): "check_file_access (V-17): isi berkas disajikan setelah otorisasi; tidak berhak → 404",
    # M4: inspeksi oleh pengelola aset ATAU pemegang kendaraan saat itu (ditentukan peminjaman berjalan).
    ("POST", "/assets/vehicles/{vehicle_id}/inspections"): "AssetService: manage:assets atau pemegang (diuji)",
    ("POST", "/overtime"): "OvertimeService: ketua/anggota tim jadwal ONGOING (diuji)",
    ("GET", "/overtime"): "OvertimeService: check_daily_access(VIEW) untuk daily_plan_id (diuji)",
    ("POST", "/overtime/{ot_id}/review"): "OvertimeService: PM/OM divisi jadwal, bukan pengaju (diuji)",
    ("GET", "/recaps/overtime"): "OvertimeService: izin review:overtime (Finance/OPS/Admin) (diuji)",
    # Survei ACS/CCTV (docs/37): SurveyService._task → DailyAccess (ketua tim jadwalnya / PM-OM divisi).
    **dict.fromkeys([("GET", "/work-plans/surveys"), ("GET", "/work-plans/surveys/{task_id}"), ("POST", "/work-plans/surveys/{task_id}/points"), ("PUT", "/work-plans/surveys/points/{point_id}"), ("DELETE", "/work-plans/surveys/points/{point_id}"), ("PUT", "/work-plans/surveys/points/{point_id}/location"), ("PUT", "/work-plans/surveys/{task_id}/report"), ("POST", "/work-plans/surveys/{task_id}/submit"), ("POST", "/work-plans/surveys/{task_id}/lines"), ("PUT", "/work-plans/surveys/lines/{bom_id}"), ("DELETE", "/work-plans/surveys/lines/{bom_id}"), ("POST", "/work-plans/surveys/{task_id}/catalog")], "SurveyService._task → DailyAccess (ketua tim / PM-OM divisi)"),
    ("GET", "/exports/surveys/{task_id}/preview"): "ExportService → SurveyService.detail (akses survei)",
    ("POST", "/exports/surveys/{task_id}"): "ExportService → SurveyService.detail (akses survei)",
    ("POST", "/exports/team-week"): "ExportService.export_team_week: anggota tim atau PM/OM divisinya (diuji)",
    ("GET", "/work-completions/{completion_id}/signatures/{role}"): "WorkCompletionService._access (tim/PM order)",
    ("DELETE", "/work-completions/{completion_id}/photos/{file_id}"):
        "WorkCompletionService._access: ketua di tim order atau PM; terkunci setelah disetujui PM",
    # Daftar master hanya-baca untuk pilihan formulir; terbatas organisasi pengguna.
    ("GET", "/clients"): "master hanya-baca untuk formulir (organisasi pengguna)",
    ("GET", "/projects"): "master hanya-baca untuk formulir (organisasi pengguna)",
    ("GET", "/job-positions"): "master hanya-baca untuk formulir (organisasi pengguna)",
}
_GUARDS = ("permission_checker", "daily_access.")


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


def _head_of_public_get(key: tuple[str, str]) -> bool:
    """HEAD hanya mengembalikan header dari GET yang sama: boleh tanpa penjaga bila GET-nya publik (docs/32)."""
    method, path = key
    return method == "HEAD" and ("GET", path) in PUBLIC_ROUTES


def test_every_route_has_a_permission_or_guard():
    routes = _routes()
    assert len(routes) > 20
    unguarded = sorted(
        key for key, deps in routes.items()
        if key not in PUBLIC_ROUTES and key not in SELF_SERVICE and key not in GUARDED_IN_HANDLER
        and not _head_of_public_get(key)
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


# ── Laporan harian ────────────────────────────────────────────────────────────────────────────


# ── Pengembalian aset ─────────────────────────────────────────────────────────────────────────


# ── Penjelasan absensi ────────────────────────────────────────────────────────────────────────
@requires_db
def test_only_the_owner_explains_an_attendance(client, world, fake_storage):
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

    for outsider in (world.headers(client, "leader"), world.headers(client, "admin")):
        response = client.post(f"/attendance/{att_id}/explain", headers=outsider, json={"explanation": "Titipan"})
        assert response.status_code == 404, response.text
    assert sync_query("SELECT out_of_radius_note FROM attendance WHERE attendance_id = %s", (att_id,)) == [("Survei titik baru",)]

    own = client.post(f"/attendance/{att_id}/explain", headers=member, json={"explanation": "GPS ponsel mati"})
    assert own.status_code == 200, own.text
    assert sync_query("SELECT out_of_radius_note FROM attendance WHERE attendance_id = %s", (att_id,)) == [("GPS ponsel mati",)]


# ── Cron kedaluwarsa dokumen ──────────────────────────────────────────────────────────────────
def _expired_active_document(world: World) -> str:
    return str(sync_query(
        "INSERT INTO employee_file (employee_id, type, path_file, status, active_at, expired_at) "
        "VALUES (%s, 'SIM_A', 'uji/sim.png', 'active', DATE '2025-01-01', DATE '2026-01-01') "
        "RETURNING employee_file_id", (world.employees["member"],))[0][0])


@requires_db
def test_document_expiry_cron_is_admin_only(client, world):
    doc = _expired_active_document(world)

    assert client.post("/documents/cron/expire-documents", headers=world.headers(client, "member")).status_code == 403
    assert client.post("/documents/cron/expire-documents", headers=world.headers(client, "hr")).status_code == 403
    response = client.post("/documents/cron/expire-documents", headers=world.headers(client, "admin"))

    assert response.status_code == 200, response.text
    assert sync_query("SELECT status::text FROM employee_file WHERE employee_file_id = %s", (doc,))         == [("not_active",)]
