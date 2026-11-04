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
    elif args.command == "backup-db":
        asyncio.run(backup_database(cycle=args.cycle, output_dir=args.output_dir))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
