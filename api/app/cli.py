"""
Modul CLI (Command Line Interface) untuk operasi administratif VMS.

Modul ini menyediakan perintah untuk membuat admin, mengisi data awal (seed),
membersihkan data yatim (orphan), serta menjalankan backup database otomatis.
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import sys
import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.database.session import make_engine
from app.shared import idempotency_repository


def _operator_url() -> str:
    """CLI adalah alat operator di server: memakai peran pemilik (sama dengan migrasi), bukan peran runtime
    `vms_api` yang tunduk RLS — membuat organisasi & admin pertama terjadi sebelum ada konteks pengguna."""
    return settings.MIGRATION_DATABASE_URL or settings.DATABASE_URL


# Panjang minimal kata sandi untuk admin
ADMIN_PASSWORD_MIN_LENGTH = 12


class CliError(Exception):
    """Galat perintah CLI yang ditampilkan ke operator tanpa jejak tumpukan."""


async def create_admin(email: str, password: str, organization_id: str | None = None) -> str:
    """
    Buat pengguna ber-peran ADMIN. Organisasi: `organization_id` bila diberikan; bila tidak,
    satu-satunya organisasi yang ada (dibuat bila belum ada). Lebih dari satu → wajib dipilih.
    Mengembalikan id pengguna baru.
    """
    if len(password) < ADMIN_PASSWORD_MIN_LENGTH:
        raise CliError(f"Kata sandi admin minimal {ADMIN_PASSWORD_MIN_LENGTH} karakter.")

    engine = make_engine(_operator_url())
    try:
        async with engine.begin() as conn:
            if (await conn.execute(
                text("SELECT 1 FROM users WHERE email = :email AND delete_at IS NULL"), {"email": email}
            )).scalar():
                raise CliError(f"Pengguna {email} sudah ada.")

            if organization_id:
                office_id = (await conn.execute(text(
                    "SELECT office_id FROM office WHERE office_id = CAST(:off AS uuid) AND delete_at IS NULL"
                ), {"off": organization_id})).scalar()
                if not office_id:
                    raise CliError(f"Organisasi {organization_id} tidak ditemukan.")
            else:
                offices = (await conn.execute(
                    text("SELECT office_id FROM office WHERE delete_at IS NULL LIMIT 2")
                )).all()
                if len(offices) > 1:
                    raise CliError("Ada lebih dari satu organisasi; pilih dengan --organization-id.")
                office_id = offices[0][0] if offices else (await conn.execute(text(
                    "INSERT INTO office (name, address, latitude, longitude) "
                    "VALUES ('Kantor Utama', 'Jakarta', -6.2088, 106.8456) RETURNING office_id"
                ))).scalar_one()

            emp_id = (await conn.execute(text(
                "INSERT INTO employee (office_id, full_name, employee_no, join_date) "
                "VALUES (:off, 'Admin Super', :no, NOW()) RETURNING employee_id"
            ), {"off": office_id, "no": f"ADMIN-{uuid.uuid4().hex[:8].upper()}"})).scalar_one()

            user_id = (await conn.execute(
                text("""
                    INSERT INTO users (employee_id, username, email, password_hash, system_role, is_active)
                    VALUES (:emp_id, :email, :email, :password_hash, 'SUPER_ADMIN', true)
                    RETURNING user_id
                """),
                {"emp_id": emp_id, "email": email, "password_hash": hash_password(password)},
            )).scalar_one()
    finally:
        await engine.dispose()
    return str(user_id)


async def seed() -> None:
    """
    Mengisi database dengan data sampel awal (seed) Master Schema V2.
    """
    engine = make_engine(_operator_url())
    async with engine.begin() as conn:
        office_id = (await conn.execute(text("SELECT office_id FROM office LIMIT 1"))).scalar()
        if not office_id:
            office_id = (await conn.execute(text(
                "INSERT INTO office (name, address, latitude, longitude) "
                "VALUES ('Kantor Pusat Visiontech', 'Jl. Sudirman Jakarta', -6.2088, 106.8456) RETURNING office_id"
            ))).scalar()

        print("Database seeded with Master Schema V2 initial data.")
    await engine.dispose()


async def cleanup_orphans() -> None:
    """
    Membersihkan sesi pengguna yang yatim (orphan) atau sudah kedaluwarsa.
    """
    engine = make_engine(_operator_url())
    async with engine.begin() as conn:
        res = await conn.execute(text("""
            DELETE FROM user_sessions
            WHERE (is_revoked = TRUE OR expires_at < now())
            AND update_at < now() - interval '30 days'
        """))
        print(f"Cleaned up {res.rowcount} orphan/expired sessions.")
    await engine.dispose()


async def cleanup_idempotency(hari: int) -> None:
    """Hapus Idempotency-Key yang lebih tua dari `hari` hari (F-03). Dijalankan manual, tanpa cron."""
    engine = make_engine(_operator_url())
    async with engine.begin() as conn:
        jumlah = await idempotency_repository.hapus_lebih_lama(conn, hari)
        print(f"Dihapus {jumlah} Idempotency-Key lebih dari {hari} hari.")
    await engine.dispose()


async def hapus_terjadwal(terapkan: bool, paksa: bool = False) -> int:
    """Hapus terjadwal (anonimisasi karyawan keluar >30 hari + hapus permanen arsip lewat retensi). Mengembalikan
    kode keluar: 0 sukses/sedang berjalan, 1 ada kegagalan atau jenis diblokir pemutus."""
    import json
    import logging

    from app.core import retention_job as retention
    from app.core.alerts import send_business_alert
    from app.core.time import utcnow

    engine = make_engine(_operator_url())
    try:
        summary = await retention.jalankan(engine, terapkan=terapkan, now=utcnow(), paksa=paksa)
    finally:
        await engine.dispose()
    data = summary.as_dict()
    logging.getLogger("app.retention").info(json.dumps(data))
    print(json.dumps(data, indent=2))
    if summary.status == "sedang_berjalan":
        print("Hapus terjadwal sedang berjalan di proses lain; dilewati.")
        return 0
    if terapkan:  # hanya angka, tanpa data pribadi
        ringkas = ", ".join(f"{k}: {v.diproses} dihapus/{v.ditahan} ditahan/{v.gagal} gagal"
                            for k, v in summary.jenis.items() if v.kandidat)
        await send_business_alert("Hapus terjadwal selesai", ringkas or "Tidak ada yang perlu diproses.")
    return 1 if summary.bermasalah else 0


async def hikvision_tarik(
    perangkat: str, dari: str | None, sampai: str | None, dry_run: bool, jeda: float, lanjutkan: bool,
) -> int:
    """Tarik riwayat event perangkat Hikvision ke hikvision_event (idempoten, aman diulang). Kode keluar 0/1."""
    import json
    from datetime import datetime, timedelta

    from app.modules.hikvision.services import konstanta as hk
    from app.modules.hikvision.services.isapi_client import IsapiError
    from app.modules.hikvision.services.tarik_service import TarikError, tarik_riwayat

    def waktu(teks: str) -> datetime:
        try:
            w = datetime.fromisoformat(teks)
        except ValueError:
            raise TarikError(f"Tanggal {teks!r} tidak valid; pakai format 2026-01-31.") from None
        return w if w.tzinfo else w.replace(tzinfo=hk.ZONA_PERANGKAT_BAWAAN)

    akhir = waktu(sampai) if sampai else datetime.now(hk.ZONA_PERANGKAT_BAWAAN)
    mulai = waktu(dari) if dari else akhir - timedelta(days=366)
    if mulai >= akhir:
        print("Tanggal --dari harus sebelum --sampai.")
        return 1
    engine = make_engine(_operator_url())
    try:
        ringkas = await tarik_riwayat(engine, serial=perangkat, mulai=mulai, akhir=akhir, dry_run=dry_run,
                                      jeda=jeda, lanjutkan=lanjutkan)
    except (TarikError, IsapiError) as exc:
        print(f"Gagal: {exc}")
        return 1
    finally:
        await engine.dispose()
    print(json.dumps(ringkas.as_dict(), indent=2))
    return 0


async def buat_partisi(bulan_ke_depan: int) -> int:
    """Buat partisi bulanan app_activity_logs + DEFAULT sebagai peran pemilik (cron host bulanan)."""
    from app.database.migration_v3 import ensure_activity_log_partitions

    engine = make_engine(_operator_url())
    try:
        return await ensure_activity_log_partitions(bulan_ke_depan, eng=engine)
    finally:
        await engine.dispose()


async def backup_database(cycle: str = "WEEKLY", output_dir: str = "backups") -> dict[str, Any]:
    """
    Menjalankan prosedur backup data sistem terkompresi dan mencatatkannya ke registry.
    """
    from app.modules.system_backup.services.backup_service import BackupService

    engine = make_engine(_operator_url())
    async with AsyncSession(engine) as session:
        service = BackupService(session)
        rec = await service.execute_automated_backup(cycle=cycle, output_dir=output_dir)
        await session.commit()
        rec_map = dict(rec._mapping) if hasattr(rec, "_mapping") else dict(rec)
        print(f"Backup berhasil dibuat: {rec_map['file_path_url']} (Checksum: {rec_map['sha256_checksum'][:16]}...)")
        await engine.dispose()
        return rec_map


def main() -> None:
    parser = argparse.ArgumentParser(description="VMS CLI")
    subparsers = parser.add_subparsers(dest="command")

    admin_parser = subparsers.add_parser("create-admin", help="Buat pengguna ADMIN")
    admin_parser.add_argument("email", help="Login admin (email)")
    admin_parser.add_argument("--organization-id", help="Wajib bila ada lebih dari satu organisasi")

    subparsers.add_parser("seed", help="Seed database with initial data")
    subparsers.add_parser("cleanup-orphans", help="Cleanup orphan sessions and tokens")
    idem_parser = subparsers.add_parser("cleanup-idempotency", help="Hapus Idempotency-Key lebih tua dari N hari")
    idem_parser.add_argument("--hari", type=int, default=7, help="Batas umur kunci (hari)")

    part_parser = subparsers.add_parser("buat-partisi", help="Buat partisi app_activity_logs (peran pemilik, untuk cron)")
    part_parser.add_argument("--bulan", type=int, default=6, help="Jumlah bulan ke depan")

    hapus_parser = subparsers.add_parser(
        "hapus-terjadwal", help="Anonimisasi karyawan keluar >30 hari + hapus permanen arsip lewat retensi")
    mode = hapus_parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--cek", action="store_true", help="Hanya lapor jumlah, tidak mengubah apa pun")
    mode.add_argument("--terapkan", action="store_true", help="Jalankan (hanya jenis kebijakan aktif)")
    hapus_parser.add_argument("--paksa", action="store_true", help="Lewati pemutus otomatis (ambang jumlah)")

    hik_parser = subparsers.add_parser(
        "hikvision-tarik", help="Tarik riwayat event perangkat Hikvision (kredensial dari HIKVISION_<SERIAL>_USER/_PASS)")
    hik_parser.add_argument("--perangkat", required=True, help="Nomor seri perangkat yang terdaftar")
    hik_parser.add_argument("--dari", help="Tanggal mulai (YYYY-MM-DD, WIB); bawaan 366 hari sebelum --sampai")
    hik_parser.add_argument("--sampai", help="Tanggal akhir (YYYY-MM-DD, WIB); bawaan sekarang")
    hik_parser.add_argument("--dry-run", action="store_true", help="Hanya hitung dan cari event tertua, tanpa simpan")
    hik_parser.add_argument("--jeda", type=float, default=1.0, help="Jeda antar permintaan ke perangkat (detik)")
    hik_parser.add_argument("--lanjutkan", action="store_true", help="Lanjut dari jendela terakhir yang tersimpan")
    backup_parser = subparsers.add_parser("backup-db", help="Jalankan backup database sistem")
    backup_parser.add_argument(
        "--cycle", default="WEEKLY", choices=["DAILY", "WEEKLY", "MONTHLY"], help="Siklus backup"
    )
    backup_parser.add_argument("--output-dir", default="backups", help="Direktori penyimpanan arsip")

    args = parser.parse_args()

    if args.command == "create-admin":
        # Kata sandi tidak diterima sebagai argumen: argumen tersimpan di riwayat shell & daftar proses.
        password = getpass.getpass("Kata sandi admin: ")
        if password != getpass.getpass("Ulangi kata sandi: "):
            sys.exit("Kata sandi tidak sama.")
        try:
            user_id = asyncio.run(create_admin(args.email, password, args.organization_id))
        except CliError as exc:
            sys.exit(str(exc))
        print(f"Admin {args.email} dibuat (id {user_id}).")
    elif args.command == "seed":
        asyncio.run(seed())
    elif args.command == "cleanup-orphans":
        asyncio.run(cleanup_orphans())
    elif args.command == "cleanup-idempotency":
        asyncio.run(cleanup_idempotency(args.hari))
    elif args.command == "hapus-terjadwal":
        sys.exit(asyncio.run(hapus_terjadwal(terapkan=args.terapkan, paksa=args.paksa)))
    elif args.command == "hikvision-tarik":
        sys.exit(asyncio.run(hikvision_tarik(args.perangkat, args.dari, args.sampai, args.dry_run, args.jeda,
                                             args.lanjutkan)))
    elif args.command == "buat-partisi":
        print(f"Partisi diperiksa/dibuat: {asyncio.run(buat_partisi(args.bulan))} pernyataan.")
    elif args.command == "backup-db":
        asyncio.run(backup_database(cycle=args.cycle, output_dir=args.output_dir))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
