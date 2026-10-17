"""
Modul CLI (Command Line Interface) untuk operasi administratif VMS.

Modul ini menyediakan perintah untuk membuat admin, mengisi data awal (seed),
serta membersihkan data yatim (orphan) pada database.
"""
import argparse
import asyncio
import getpass
import sys

from sqlalchemy import text

from app.core.config import settings
from app.core.security import hash_password
from app.db.session import make_engine


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

            office_id = (await conn.execute(text("SELECT office_id FROM office WHERE delete_at IS NULL LIMIT 1"))).scalar()
            if not office_id:
                office_id = (await conn.execute(text(
                    "INSERT INTO office (name, address, latitude, longitude) VALUES ('Kantor Utama', 'Jakarta', -6.2088, 106.8456) RETURNING office_id"
                ))).scalar_one()

            emp_id = (await conn.execute(text(
                "INSERT INTO employee (office_id, full_name, employee_no, join_date) VALUES (:off, 'Admin Super', 'EMP-ADMIN', NOW()) RETURNING employee_id"
            ), {"off": office_id})).scalar_one()

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
                "INSERT INTO office (name, address, latitude, longitude) VALUES ('Kantor Pusat Visiontech', 'Jl. Sudirman Jakarta', -6.2088, 106.8456) RETURNING office_id"
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

def main() -> None:
    parser = argparse.ArgumentParser(description="VMS CLI")
    subparsers = parser.add_subparsers(dest="command")

    admin_parser = subparsers.add_parser("create-admin", help="Buat pengguna ADMIN")
    admin_parser.add_argument("email", help="Login admin (email)")
    admin_parser.add_argument("--organization-id", help="Wajib bila ada lebih dari satu organisasi")

    subparsers.add_parser("seed", help="Seed database with initial data")
    subparsers.add_parser("cleanup-orphans", help="Cleanup orphan sessions and tokens")

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
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
