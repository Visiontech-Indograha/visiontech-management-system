import asyncio
import argparse
from app.db.session import make_engine
from sqlalchemy import text
from app.core.config import settings
from app.core.security import hash_password

async def create_admin(email: str, password: str):
    engine = make_engine()
    async with engine.begin() as conn:
        hashed = hash_password(password)
        
        # 1. Ensure at least one organization exists (Default Org)
        org_query = text("SELECT id FROM vms.organization LIMIT 1")
        result = await conn.execute(org_query)
        org_row = result.fetchone()
        
        if not org_row:
            print("No organization found. Creating 'Default Organization'...")
            insert_org = text("""
                INSERT INTO vms.organization (name) VALUES ('Default Organization') RETURNING id
            """)
            result = await conn.execute(insert_org)
            org_id = result.scalar()
        else:
            org_id = org_row[0]
            
        # 2. Checking if user exists
        query = text("SELECT id FROM vms.app_user WHERE login = :login")
        result = await conn.execute(query, {"login": email})
        user_row = result.fetchone()
        if user_row:
            print(f"User {email} already exists!")
            return

        # 3. Insert user
        insert_query = text("""
            INSERT INTO vms.app_user (organization_id, login, password_hash, is_active)
            VALUES (:org_id, :login, :password_hash, true)
            RETURNING id
        """)
        result = await conn.execute(insert_query, {
            "org_id": org_id,
            "login": email,
            "password_hash": hashed
        })
        user_id = result.scalar()
        
        # 4. Insert role
        insert_role_query = text("""
            INSERT INTO vms.user_role (user_id, role)
            VALUES (:user_id, 'admin')
        """)
        await conn.execute(insert_role_query, {"user_id": user_id})
        
    print(f"Admin user {email} created successfully in organization {org_id}!")
        
    await engine.dispose()

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
    
    admin_parser = subparsers.add_parser("create-admin", help="Create an admin user")
    admin_parser.add_argument("email", help="Admin email")
    admin_parser.add_argument("password", help="Admin password")
    
    subparsers.add_parser("seed", help="Seed database with initial data")
    subparsers.add_parser("cleanup-orphans", help="Cleanup orphan sessions and tokens")
    
    args = parser.parse_args()
    
    if args.command == "create-admin":
        asyncio.run(create_admin(args.email, args.password))
    elif args.command == "seed":
        asyncio.run(seed())
    elif args.command == "cleanup-orphans":
        asyncio.run(cleanup_orphans())
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
