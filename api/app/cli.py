import argparse
import asyncio
import getpass
import sys

from sqlalchemy import text

from app.core.permissions import RoleCode
from app.core.security import hash_password
from app.db.session import make_engine

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

    engine = make_engine()
    try:
        async with engine.begin() as conn:
            if organization_id:
                if not (await conn.execute(
                    text("SELECT 1 FROM vms.organization WHERE id = :id"), {"id": organization_id}
                )).scalar():
                    raise CliError(f"Organisasi {organization_id} tidak ditemukan.")
                org_id = organization_id
            else:
                orgs = (await conn.execute(text("SELECT id FROM vms.organization"))).scalars().all()
                if len(orgs) > 1:
                    raise CliError("Ada lebih dari satu organisasi; pilih dengan --organization-id.")
                org_id = orgs[0] if orgs else (await conn.execute(text(
                    "INSERT INTO vms.organization (name) VALUES ('Default Organization') RETURNING id"
                ))).scalar_one()

            if (await conn.execute(
                text("SELECT 1 FROM vms.app_user WHERE login = :login"), {"login": email}
            )).scalar():
                raise CliError(f"Pengguna {email} sudah ada.")

            user_id = (await conn.execute(
                text("""
                    INSERT INTO vms.app_user (organization_id, login, password_hash, is_active)
                    VALUES (:org_id, :login, :password_hash, true)
                    RETURNING id
                """),
                {"org_id": org_id, "login": email, "password_hash": hash_password(password)},
            )).scalar_one()
            await conn.execute(
                text("INSERT INTO vms.user_role (user_id, role) VALUES (:user_id, :role)"),
                {"user_id": user_id, "role": RoleCode.ADMIN.value},
            )
    finally:
        await engine.dispose()
    return str(user_id)


async def seed():
    engine = make_engine()
    async with engine.begin() as conn:
        # Check org
        org_id = (await conn.execute(text("SELECT id FROM vms.organization LIMIT 1"))).scalar()
        if not org_id:
            org_id = (await conn.execute(text("INSERT INTO vms.organization (name) VALUES ('VisionTech') RETURNING id"))).scalar()
            
        # Business Unit
        unit_id = (await conn.execute(text("SELECT id FROM vms.business_unit WHERE code = 'IT'"))).scalar()
        if not unit_id:
            unit_id = (await conn.execute(text("INSERT INTO vms.business_unit (organization_id, code, name) VALUES (:org, 'IT', 'Information Technology') RETURNING id"), {"org": org_id})).scalar()
            
        # Employee
        emp_id = (await conn.execute(text("SELECT id FROM vms.employee WHERE employee_no = 'EMP001'"))).scalar()
        if not emp_id:
            emp_id = (await conn.execute(text("""
                INSERT INTO vms.employee (organization_id, employee_no, full_name, position, unit_id, join_date)
                VALUES (:org, 'EMP001', 'John Doe', 'Engineer', :unit, '2026-01-01') RETURNING id
            """), {"org": org_id, "unit": unit_id})).scalar()
            
        print("Database seeded with sample data.")
    await engine.dispose()

async def cleanup_orphans():
    engine = make_engine()
    async with engine.begin() as conn:
        # Hapus session kedaluwarsa atau ter-revoke yang lebih dari 30 hari
        res = await conn.execute(text("""
            DELETE FROM vms.user_session 
            WHERE (state = 'REVOKED' OR state = 'ROTATED' OR expires_at < now())
            AND last_used_at < now() - interval '30 days'
        """))
        print(f"Cleaned up {res.rowcount} orphan/expired sessions.")
    await engine.dispose()

def main():
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
