"""Seed data uji LOKAL: kosongkan database lalu isi akun, karyawan (ber-SIM), kendaraan, alat, jenis pekerjaan.

HANYA untuk database pengembangan di komputer sendiri. Menolak berjalan bila host database bukan localhost/127.0.0.1.
Semua akun memakai sandi `password123` (daftar lengkap: scripts/akun-uji-lokal.txt).

    cd api
    .venv/Scripts/python.exe ../scripts/seed_uji_lokal.py --ya-hapus-semua      # Windows
    .venv/bin/python ../scripts/seed_uji_lokal.py --ya-hapus-semua              # Linux/macOS
    ... seed_uji_lokal.py --uji-kering        # jalankan semua langkah lalu batalkan (tidak ada yang berubah)

Dipertahankan: organisasi "PT Visiontech Indograha", unit bisnis (SRV, INF, KTR), lokasi kerja, kunci tanda tangan.
Semua data lain (rencana kerja, absensi, laporan, dokumen, akun, aset, audit, organisasi lain) DIHAPUS.
"""
from __future__ import annotations

import asyncio
import contextlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.cli import _operator_url
from app.core.security import hash_password
from app.db.session import make_engine

PASSWORD = "password123"
ORG_NAME = "PT Visiontech Indograha"
KEEP = {"organization", "business_unit", "site", "signing_key", "signature_serial_counter"}

# (no karyawan, nama, jabatan, login, peran, unit peran: kode unit atau None = lintas unit, unit karyawan)
OFFICE = [
    ("VT-0001", "Admin Sistem", "Administrator Sistem", "admin@visiontech.local", "ADMIN", None, "KTR"),
    ("VT-0002", "Rina Kartika", "Project Manager Survei", "pm.survei@visiontech.local", "PM", "SRV", "SRV"),
    ("VT-0003", "Dimas Prasetyo", "Project Manager Infrastruktur", "pm.infra@visiontech.local", "PM", "INF", "INF"),
    ("VT-0004", "Siti Rahmawati", "HR Officer", "hr@visiontech.local", "HR", None, "KTR"),
    ("VT-0005", "Bayu Firmansyah", "Asset Officer", "aset@visiontech.local", "ASSET", None, "KTR"),
    ("VT-0006", "Agus Wibisono", "Finance Officer", "finance@visiontech.local", "FINANCE", None, "KTR"),
    ("VT-0007", "Lestari Handayani", "Operations Manager", "ops@visiontech.local", "OPS", None, "KTR"),
]
MEMBERS = [
    "Agus Setiawan", "Bayu Pratama", "Candra Wijaya", "Dedi Kurniawan", "Eko Saputra", "Fajar Nugroho",
    "Galih Permana", "Hadi Susanto", "Irfan Hakim", "Joko Santoso", "Kurnia Ramadhan", "Lutfi Hidayat",
    "Mahendra Putra", "Nanda Prakoso", "Oki Firmansyah", "Putra Ardiansyah", "Rizky Maulana", "Satria Wibowo",
    "Taufik Hidayatullah", "Umar Said", "Vicky Prasetyo", "Wahyu Hidayat", "Yoga Pratama", "Zainal Arifin",
    "Arif Rahman", "Budi Santoso", "Cahyo Nugroho", "Dimas Anggara", "Erwin Syahputra", "Fikri Haikal",
    "Gilang Ramadhan", "Hendra Gunawan", "Imam Fauzi", "Jefri Nichol", "Krisna Mukti",
]
MEMBERS_IN_SRV = 18   # anggota01–18 → Survei & Pemetaan; anggota19–35 → Infrastruktur Jaringan
POSITIONS = ["Teknisi", "Surveyor", "Helper", "Teknisi Senior", "Drafter"]
MOTOR = ["Honda Vario 125", "Honda Beat", "Yamaha NMAX", "Honda Supra X 125", "Yamaha Mio M3"]
CAR = ["Toyota Avanza", "Daihatsu Gran Max", "Mitsubishi L300", "Toyota Hilux", "Suzuki Carry Pick Up"]
TOOLS = [
    ("ALT-01", "Total Station Topcon"), ("ALT-02", "GPS Geodetik RTK"), ("ALT-03", "Drone DJI Mavic 3"),
    ("ALT-04", "Fusion Splicer Fiber"), ("ALT-05", "OTDR Fiber Optik"), ("ALT-06", "Tangga Lipat 4 m"),
    ("ALT-07", "Bor Listrik Bosch"), ("ALT-08", "Multimeter Digital"), ("ALT-09", "Genset 3 kVA"),
    ("ALT-10", "Laptop Lapangan"),
]
WORK_TYPES = {
    "Survei Lokasi": [("Foto kondisi awal lokasi", "Ambil dari 4 sisi bila memungkinkan", True),
                      ("Foto titik koordinat / patok", "Tampilkan alat GPS atau patok di dalam foto", True),
                      ("Foto akses jalan", None, False)],
    "Instalasi CCTV": [("Foto sebelum pemasangan", "Area yang akan dipasang kamera", True),
                       ("Foto kamera terpasang", "Kamera dan bracket terlihat jelas", True),
                       ("Foto tampilan monitor/NVR", "Semua kanal tampil", True),
                       ("Foto jalur kabel", None, False)],
    "Instalasi Jaringan Fiber": [("Foto titik awal & akhir", None, True),
                                 ("Foto hasil splicing", "Tray tertutup rapi", True),
                                 ("Foto hasil uji OTDR", "Layar alat dengan nilai redaman", True)],
    "Replacement": [("Foto perangkat lama", "Sebelum dibongkar, nomor seri terlihat", True),
                    ("Foto perangkat baru terpasang", "Nomor seri terlihat", True),
                    ("Foto uji fungsi", None, False)],
    "Pemeliharaan Rutin": [("Foto sebelum pemeliharaan", None, True),
                           ("Foto sesudah pemeliharaan", None, True),
                           ("Foto checklist yang ditandatangani", None, False)],
}


class _UjiKering(Exception):
    """Dilempar di akhir transaksi pada mode --uji-kering agar semua perubahan dibatalkan."""


def licences(i: int) -> list[str]:
    """SIM anggota ke-i (0-based), berulang tiap 5: tanpa SIM, A+C, A+C, A saja, C saja."""
    return [[], ["SIM A", "SIM C"], ["SIM A", "SIM C"], ["SIM A"], ["SIM C"]][i % 5]


async def seed(dry_run: bool = False) -> None:
    url = make_url(_operator_url())
    if url.host not in ("localhost", "127.0.0.1", "::1"):
        sys.exit(f"DITOLAK: host database '{url.host}' bukan lokal. Seed ini hanya untuk komputer pengembang.")
    engine = make_engine(_operator_url())
    async with engine.begin() as c:
        org = (await c.execute(text("SELECT id FROM vms.organization WHERE name = :n"), {"n": ORG_NAME})).scalar()
        if org is None:
            sys.exit(f"DITOLAK: organisasi '{ORG_NAME}' tidak ada di database ini.")
        org = str(org)
        await c.execute(text("SELECT set_config('app.organization_id', :o, true), "
                             "set_config('app.actor_label', 'seed data uji lokal', true)"), {"o": org})

        tables = [r[0] for r in await c.execute(text(
            "SELECT c.relname FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'vms' AND c.relkind IN ('r','p') AND NOT c.relispartition"))]
        wipe = sorted(set(tables) - KEEP)
        await c.execute(text("TRUNCATE " + ", ".join(f"vms.{t}" for t in wipe) + " RESTART IDENTITY CASCADE"))
        await c.execute(text("DELETE FROM vms.organization WHERE id <> :o"), {"o": org})

        units = {r.code: str(r.id) for r in await c.execute(
            text("SELECT id, code FROM vms.business_unit WHERE organization_id = :o"), {"o": org})}
        missing = {"SRV", "INF", "KTR"} - set(units)
        if missing:
            sys.exit(f"DITOLAK: unit bisnis {sorted(missing)} tidak ada.")
        pwd = hash_password(PASSWORD)

        async def person(no: str, name: str, position: str, unit: str, mode: str, login: str) -> tuple[str, str]:
            emp = (await c.execute(text(
                "INSERT INTO vms.employee (organization_id, employee_no, full_name, position, unit_id, email, phone, "
                "join_date, attendance_mode) VALUES (:o, :no, :n, :p, :u, :m, :ph, '2025-01-06', :mode) RETURNING id"),
                {"o": org, "no": no, "n": name, "p": position, "u": unit, "m": login,
                 "ph": f"0812{no[-4:].rjust(8, '0')}", "mode": mode})).scalar_one()
            uid = (await c.execute(text(
                "INSERT INTO vms.app_user (organization_id, employee_id, login, password_hash, is_active) "
                "VALUES (:o, :e, :l, :h, true) RETURNING id"), {"o": org, "e": emp, "l": login, "h": pwd})).scalar_one()
            return str(emp), str(uid)

        admin_uid = ""
        for no, name, position, login, role, role_unit, unit in OFFICE:
            _, uid = await person(no, name, position, units[unit], "OFFICE", login)
            await c.execute(text("INSERT INTO vms.user_role (user_id, role, unit_id) "
                                 "VALUES (:u, CAST(:r AS vms.role_code), CAST(:unit AS uuid))"),
                            {"u": uid, "r": role, "unit": units[role_unit] if role_unit else None})
            if role == "ADMIN":
                admin_uid = uid

        for i, name in enumerate(MEMBERS):
            unit = units["SRV"] if i < MEMBERS_IN_SRV else units["INF"]
            emp, uid = await person(f"VT-{101 + i:04d}", name, POSITIONS[i % len(POSITIONS)], unit, "FIELD",
                                    f"anggota{i + 1:02d}@visiontech.local")
            for k, doc in enumerate(licences(i)):
                await c.execute(text(
                    "INSERT INTO vms.employee_document (employee_id, doc_type, number_masked, expiry_date, status, "
                    "lifecycle, uploaded_by, verified_by, verified_at) "
                    "VALUES (:e, :t, :num, '2030-12-31', 'VERIFIED', 'CURRENT', :up, :ver, now())"),
                    {"e": emp, "t": doc, "num": f"****{(1000 + i * 7 + k) % 10000:04d}", "up": uid, "ver": admin_uid})

        for n in range(10):
            for vtype, code, name in (("MOTORCYCLE", f"MTR-{n + 1:02d}", f"{MOTOR[n % 5]} (B {3101 + n} VTI)"),
                                      ("CAR", f"MBL-{n + 1:02d}", f"{CAR[n % 5]} (B {1201 + n} VTI)")):
                await c.execute(text("INSERT INTO vms.asset (organization_id, kind, vehicle_type, code, name) "
                                     "VALUES (:o, 'VEHICLE', :t, :c, :n)"),
                                {"o": org, "t": vtype, "c": code, "n": name})
        for code, name in TOOLS:
            await c.execute(text("INSERT INTO vms.asset (organization_id, kind, code, name) "
                                 "VALUES (:o, 'TOOL', :c, :n)"), {"o": org, "c": code, "n": name})

        for wt_name, slots in WORK_TYPES.items():
            wt = (await c.execute(text("INSERT INTO vms.work_type (organization_id, name) "
                                       "VALUES (:o, :n) RETURNING id"), {"o": org, "n": wt_name})).scalar_one()
            for order, (label, hint, required) in enumerate(slots):
                await c.execute(text(
                    "INSERT INTO vms.work_type_photo "
                    "(organization_id, work_type_id, sort_order, label, hint, required) "
                    "VALUES (:o, :w, :s, :l, :h, :r)"),
                    {"o": org, "w": wt, "s": order, "l": label, "h": hint, "r": required})

        counts = (await c.execute(text(
            "SELECT (SELECT count(*) FROM vms.app_user),"
            " (SELECT count(*) FROM vms.asset WHERE vehicle_type = 'MOTORCYCLE'),"
            " (SELECT count(*) FROM vms.asset WHERE vehicle_type = 'CAR'),"
            " (SELECT count(*) FROM vms.asset WHERE kind = 'TOOL'),"
            " (SELECT count(*) FROM vms.work_type)"))).one()
        if dry_run:
            print(f"UJI KERING berhasil (dibatalkan): {counts[0]} akun, {counts[1]} motor, {counts[2]} mobil, "
                  f"{counts[3]} alat, {counts[4]} jenis pekerjaan.")
            raise _UjiKering
    await engine.dispose()
    print(f"Selesai: {counts[0]} akun, {counts[1]} motor, {counts[2]} mobil, {counts[3]} alat, "
          f"{counts[4]} jenis pekerjaan.")
    print(f"Semua akun bersandi '{PASSWORD}'. Daftar: scripts/akun-uji-lokal.txt")


if __name__ == "__main__":
    if "--uji-kering" in sys.argv:
        with contextlib.suppress(_UjiKering):
            asyncio.run(seed(dry_run=True))
    elif "--ya-hapus-semua" in sys.argv:
        asyncio.run(seed())
    else:
        sys.exit("Seed ini MENGHAPUS semua data uji di database lokal. Jalankan ulang dengan --ya-hapus-semua "
                 "(atau --uji-kering untuk mencoba tanpa mengubah apa pun).")
