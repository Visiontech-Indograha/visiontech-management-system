"""Pindahkan data produksi V1 (skema `vms`) ke basis data baru Master Schema V2 (docs/40).

Sumber TIDAK diubah (hanya dibaca). Tujuan = DB V2 baru yang sudah berisi skema `db/06` + DDL `migration_v3`
dan masih kosong dari data karyawan. Satu transaksi: gagal di tengah → tujuan tetap kosong.
ID karyawan, akun, berkas, dan dokumen dipertahankan sehingga storage key MinIO & tautan lama tetap berlaku.

    SUMBER_DSN=postgresql://user:sandi@host:port/visiontech_db \\
    TUJUAN_DSN=postgresql://user:sandi@host:port/vms_v2 \\
    python scripts/migrasi_v1_ke_v2.py [--uji-kering]

Pemetaan:
  site → office · divisi = ketetapan pemilik (CCTV, ACS, Wall Display di Pekanbaru; OM Ade Candra;
  PM CCTV & ACS RAMADANI, PM Wall Display HANDOKO). Karyawan unit "CCTV & ACS" → CCTV, "Wall Display" → Wall Display,
  unit kantor lain (Management, HSE, …) tanpa divisi lapangan
  employee (+ face_enrollment aktif terbaru) → employee · app_user + user_role → users
  employee.position → job_position · employee_document → employee_file · asset → vehicle / tool
  file_object → file_object · attendance → attendance
  Tidak dipindah: sesi login, notifikasi, log percobaan masuk (pengguna cukup login ulang).
"""
from __future__ import annotations

import asyncio
import json
import os
import re
import sys
from collections import Counter
from typing import Any

import asyncpg

ROLE = {  # V1 role_code → V2 system_role (FINANCE/ASSET dihapus di V2 — keputusan pemilik 2026-10-20)
    "ADMIN": "SUPER_ADMIN", "OPS": "OPERATIONAL_MANAGER", "PM": "PROJECT_MANAGER", "LEADER": "TEAM_LEADER",
    "HR": "ADMIN_HR_GA", "FINANCE": "ADMIN_HR_GA", "ASSET": "ADMIN_HR_GA", "MEMBER": "EMPLOYEE",
}
ROLE_RANK = ["SUPER_ADMIN", "OPERATIONAL_MANAGER", "PROJECT_MANAGER", "ADMIN_HR_GA", "TEAM_LEADER", "EMPLOYEE"]
# Ketetapan pemilik (2026-10-22): V2 hanya 3 divisi lapangan, semuanya di kantor Pekanbaru; OM satu orang.
# Orang dicari dari nama lengkap V1 (tanpa beda huruf besar/kecil) dan WAJIB tepat satu — kalau tidak, migrasi berhenti.
OFFICE_OF_DIVISIONS = "pekanbaru"
OM_NAME = "Ade Candra"
DIVISIONS = [  # (nama divisi V2, nama PM, unit V1 yang karyawannya masuk ke divisi ini)
    ("CCTV", "RAMADANI", "CCTV & ACS"),
    ("ACS", "RAMADANI", None),
    ("Wall Display", "HANDOKO", "Wall Display"),
]
ASSET_STATUS = {"AVAILABLE": "ready", "RESERVED": "allocated", "IN_USE": "allocated", "RETURN_PENDING": "loaned",
                "MAINTENANCE": "damaged", "RETIRED": "pension"}


def _slug(text: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "-", text.upper()).strip("-")[:40] or "JABATAN"


def _vehicle_type(raw: str | None) -> str:
    t = (raw or "").lower()
    if "motor" in t:
        return "Motorcycle"
    if "truck" in t or "truk" in t:
        return "Truck"
    return "Car"


async def migrate(src: asyncpg.Connection, dst: asyncpg.Connection) -> Counter[str]:
    n: Counter[str] = Counter()
    if await dst.fetchval("SELECT count(*) FROM employee"):
        raise SystemExit("Tujuan sudah berisi karyawan — migrasi hanya untuk DB V2 baru yang kosong.")
    org = await src.fetchrow("SELECT * FROM vms.organization LIMIT 1")
    if org is None:
        raise SystemExit("Sumber tidak punya organisasi.")

    # ── Kantor (site) ──────────────────────────────────────────────────────────────────────
    sites = await src.fetch("SELECT id, name, address, radius_m, unit_id, ST_Y(location::geometry) lat, "
                            "ST_X(location::geometry) lng FROM vms.site WHERE deleted_at IS NULL ORDER BY name")
    city = (org["city_name"] or "").lower()
    main_site = next((s for s in sites if city and city in s["name"].lower()), sites[0] if sites else None)
    office_of_site: dict[Any, Any] = {}
    for s in sites:
        office_of_site[s["id"]] = await dst.fetchval(
            "INSERT INTO office (office_id, name, is_main_office, address, latitude, longitude, attendance_radius_m, "
            "clock_in_time, clock_out_time) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING office_id",
            s["id"], s["name"], s is main_site, s["address"] or s["name"], s["lat"] or 0, s["lng"] or 0,
            s["radius_m"] or org["geofence_radius_m"] or 100, org["shift_start"], org["shift_end"])
        n["office"] += 1
    if not office_of_site:
        raise SystemExit("Sumber tidak punya site — tidak ada kantor untuk karyawan.")
    main_office = office_of_site[main_site["id"]] if main_site else next(iter(office_of_site.values()))
    office_of_unit = {s["unit_id"]: office_of_site[s["id"]] for s in sites if s["unit_id"]}

    # ── Peran per karyawan ─────────────────────────────────────────────────────────────────
    roles = await src.fetch("SELECT u.employee_id, r.role::text role, r.unit_id FROM vms.user_role r "
                            "JOIN vms.app_user u ON u.id = r.user_id")
    best_role: dict[Any, str] = {}
    for r in roles:
        v2 = ROLE.get(r["role"], "EMPLOYEE")
        cur = best_role.get(r["employee_id"])
        if cur is None or ROLE_RANK.index(v2) < ROLE_RANK.index(cur):
            best_role[r["employee_id"]] = v2

    # ── Karyawan (tanpa divisi dulu: divisi butuh OM/PM yang juga karyawan) ────────────────
    employees = await src.fetch("SELECT * FROM vms.employee WHERE deleted_at IS NULL ORDER BY created_at")
    files = {f["id"]: f for f in await src.fetch("SELECT * FROM vms.file_object")}
    faces = {f["employee_id"]: f for f in await src.fetch(
        "SELECT DISTINCT ON (employee_id) employee_id, embedding::text emb, model_name, model_version, captured_at "
        "FROM vms.face_enrollment WHERE is_active ORDER BY employee_id, captured_at DESC")}
    for e in employees:
        face = faces.get(e["id"])
        embedding = None
        if face:
            embedding = json.dumps({"vector": json.loads(face["emb"]), "model": face["model_name"],
                                    "version": face["model_version"],
                                    "enrolled_at": face["captured_at"].isoformat()})
        photo = files.get(e["photo_file_id"])
        await dst.execute(
            "INSERT INTO employee (employee_id, office_id, full_name, employee_no, join_date, phone_number, "
            "photo_path, profile_photo_path, face_embedding, offboarding_status, create_at, update_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $7, $8::jsonb, $9::offboarding_status_enum, $10, $11)",
            e["id"], office_of_unit.get(e["unit_id"], main_office), e["full_name"], e["employee_no"],
            e["join_date"] or e["created_at"], e["phone"], photo["storage_key"] if photo else None, embedding,
            "offboarded" if e["offboarded_at"] or not e["is_active"] else "active", e["created_at"],
            e["updated_at"])
        n["employee"] += 1
        n["face_embedding"] += bool(embedding)

    # ── Divisi: ketetapan pemilik (3 divisi lapangan, kantor Pekanbaru, OM satu orang) ────────
    def person(name: str) -> Any:
        found = [e["id"] for e in employees if (e["full_name"] or "").strip().lower() == name.strip().lower()]
        if len(found) != 1:
            raise SystemExit(f"'{name}' harus tepat 1 karyawan di sumber, ditemukan {len(found)} — periksa nama.")
        return found[0]

    pekanbaru = next((office_of_site[s["id"]] for s in sites if OFFICE_OF_DIVISIONS in s["name"].lower()), None)
    if pekanbaru is None:
        raise SystemExit(f"Kantor '{OFFICE_OF_DIVISIONS}' tidak ditemukan di sumber.")
    om = person(OM_NAME)
    units = {u["name"]: u["id"] for u in await src.fetch("SELECT id, name FROM vms.business_unit "
                                                          "WHERE deleted_at IS NULL")}
    division_of_unit: dict[Any, Any] = {}
    for name, pm_name, unit_name in DIVISIONS:
        div_id = await dst.fetchval(
            "INSERT INTO division (om_id, pm_id, name) VALUES ($1, $2, $3) RETURNING division_id",
            om, person(pm_name), name)
        n["division"] += 1
        if unit_name:
            if unit_name not in units:
                raise SystemExit(f"Unit V1 '{unit_name}' tidak ditemukan di sumber.")
            division_of_unit[units[unit_name]] = div_id
    # Karyawan divisi lapangan bekerja di kantor Pekanbaru.
    for e in employees:
        if e["unit_id"] in division_of_unit:
            await dst.execute("UPDATE employee SET office_id = $2 WHERE employee_id = $1", e["id"], pekanbaru)

    # ── Jabatan & divisi karyawan ──────────────────────────────────────────────────────────
    position_ids: dict[tuple[Any, str], Any] = {}
    for e in employees:
        div = division_of_unit.get(e["unit_id"])
        pos = None
        if e["position"]:
            key = (div, e["position"].strip())
            if key not in position_ids:
                position_ids[key] = await dst.fetchval(
                    "INSERT INTO job_position (division_id, code, name) VALUES ($1, $2, $3) RETURNING position_id",
                    div, f"{_slug(key[1])}-{len(position_ids) + 1:02d}", key[1])
                n["job_position"] += 1
            pos = position_ids[key]
        await dst.execute("UPDATE employee SET division_id = $2, position_id = $3 WHERE employee_id = $1",
                          e["id"], div, pos)

    # ── Akun ───────────────────────────────────────────────────────────────────────────────
    emp_ids = {e["id"] for e in employees}
    for u in await src.fetch("SELECT * FROM vms.app_user WHERE employee_id IS NOT NULL"):
        if u["employee_id"] not in emp_ids:
            continue
        login = str(u["login"])
        await dst.execute(
            "INSERT INTO users (user_id, employee_id, username, email, password_hash, system_role, is_active, "
            "create_at, update_at) VALUES ($1, $2, $3, $4, $5, $6::system_role_enum, $7, $8, $9)",
            u["id"], u["employee_id"], login.split("@")[0], login, u["password_hash"],
            best_role.get(u["employee_id"], "EMPLOYEE"), u["is_active"], u["created_at"], u["updated_at"])
        n["users"] += 1

    # ── Berkas (metadata; isi tetap di MinIO dengan storage key yang sama) ─────────────────
    for f in files.values():
        await dst.execute(
            "INSERT INTO file_object (id, office_id, storage_key, file_name, mime_type, byte_size, sha256, "
            "uploaded_by, created_at) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)",
            f["id"], main_office, f["storage_key"], f["file_name"], f["mime_type"], f["byte_size"], f["sha256"],
            f["uploaded_by"] if f["uploaded_by"] in emp_ids else None, f["created_at"])
        n["file_object"] += 1

    # ── Dokumen karyawan ───────────────────────────────────────────────────────────────────
    for d in await src.fetch("SELECT * FROM vms.employee_document"):
        if d["employee_id"] not in emp_ids:
            continue
        f = files.get(d["file_id"])
        active = d["lifecycle"] == "CURRENT" and d["status"] != "REJECTED"
        await dst.execute(
            "INSERT INTO employee_file (employee_file_id, employee_id, type, path_file, status, active_at, "
            "expired_at, create_at) VALUES ($1, $2, $3, $4, $5::doc_status_enum, $6, $7, $6)",
            d["id"], d["employee_id"], d["doc_type"], f["storage_key"] if f else "",
            "active" if active else "not_active", d["created_at"], d["expiry_date"])
        n["employee_file"] += 1

    # ── Aset ───────────────────────────────────────────────────────────────────────────────
    asset_div = next((division_of_unit[u] for u, d in division_of_unit.items()), None)
    for a in await src.fetch("SELECT * FROM vms.asset WHERE deleted_at IS NULL"):
        status = ASSET_STATUS.get(str(a["status"]), "ready")
        if a["kind"] == "VEHICLE":
            await dst.execute(
                "INSERT INTO vehicle (vehicle_id, office_id, division_id, vehicle_type, name, number_plate, status) "
                "VALUES ($1, $2, $3, $4::vehicle_type_enum, $5, $6, $7::asset_status_enum)",
                a["id"], main_office, asset_div, _vehicle_type(a["vehicle_type"]), a["name"], a["code"] or a["name"],
                status)
            n["vehicle"] += 1
        else:
            await dst.execute(
                "INSERT INTO tool (tool_id, office_id, ownership_type, category, name, tool_code, status) "
                "VALUES ($1, $2, 'SHARED_TOOL', 'LAINNYA', $3, $4, $5::asset_status_enum)",
                a["id"], main_office, a["name"], a["code"] or a["name"], status)
            n["tool"] += 1

    # ── Absensi ────────────────────────────────────────────────────────────────────────────
    att = await src.fetch(
        "SELECT a.*, ST_Y(a.location::geometry) lat, ST_X(a.location::geometry) lng FROM vms.attendance a")
    for a in att:
        if a["employee_id"] not in emp_ids:
            continue
        selfie = files.get(a["selfie_file_id"])
        approval = {"AUTO_VALID": "AUTO_VALID", "NEEDS_REVIEW": "PENDING_OM", "APPROVED": "APPROVED_BY_OM",
                    "REJECTED": "REJECTED_BY_OM"}.get(str(a["status"]), "PENDING_OM")
        await dst.execute(
            "INSERT INTO attendance (attendance_id, employee_id, attendance_date, target_location_type, office_id, "
            "scheduled_in, scheduled_out, clock_in_at, clock_out_at, in_lat, in_lng, face_match_score, "
            "face_photo_path, distance_to_target_m, is_within_attendance_radius, out_of_radius_note, "
            "om_approval_status, distance_from_main_office_m, city_zone_status, meal_allowance_amount, create_at) "
            "VALUES ($1, $2, $3, 'OFFICE', $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, $16, 0, "
            "'DALAM_KOTA', 0, $17)",
            a["id"], a["employee_id"], a["work_date"], office_of_site.get(a["site_id"], main_office),
            org["shift_start"], org["shift_end"], a["check_in_at"], a["check_out_at"], a["lat"] or 0, a["lng"] or 0,
            a["face_similarity"] or 0, selfie["storage_key"] if selfie else "", int(a["distance_m"] or 0),
            str(a["status"]) in ("AUTO_VALID", "APPROVED"), a["explanation"], approval, a["created_at"])
        n["attendance"] += 1
    return n


async def main(dry_run: bool) -> None:
    src_dsn, dst_dsn = os.environ.get("SUMBER_DSN"), os.environ.get("TUJUAN_DSN")
    if not src_dsn or not dst_dsn:
        raise SystemExit("Isi SUMBER_DSN dan TUJUAN_DSN (postgresql://…).")
    src = await asyncpg.connect(src_dsn)
    dst = await asyncpg.connect(dst_dsn)
    try:
        await src.execute("SET default_transaction_read_only = on")  # sumber hanya dibaca
        # RLS V1 menyaring baris per organisasi; migrasi butuh SEMUA baris → gagal jelas bila peran tak boleh melewatinya.
        await src.execute("SET row_security = off")
        tx = dst.transaction()
        await tx.start()
        try:
            counts = await migrate(src, dst)
        except BaseException:
            await tx.rollback()
            raise
        for k, v in sorted(counts.items()):
            print(f"  {k:<16} {v}")
        if dry_run:
            await tx.rollback()
            print("uji kering: dibatalkan, tujuan tidak berubah")
        else:
            await tx.commit()
            print("selesai: data tersimpan di tujuan")
    finally:
        await src.close()
        await dst.close()


if __name__ == "__main__":
    asyncio.run(main("--uji-kering" in sys.argv))
