import asyncio
import argparse
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from app.core.config import settings
from app.core.security import hash_password

async def create_admin(email: str, password: str):
    engine = create_async_engine(settings.DATABASE_URL)
    async with engine.begin() as conn:
        hashed = hash_password(password)
        
        # Checking if admin exists
        query = text("SELECT id FROM vms.users WHERE email = :email")
        result = await conn.execute(query, {"email": email})
        if result.fetchone():
            print(f"User {email} already exists!")
            return

        # Insert user
        insert_query = text("""
            INSERT INTO vms.users (email, password_hash, role, status)
            VALUES (:email, :password_hash, 'admin', 'ACTIVE')
        """)
        await conn.execute(insert_query, {
            "email": email,
            "password_hash": hashed
        })
        print(f"Admin user {email} created successfully!")
        
    await engine.dispose()

def main():
    parser = argparse.ArgumentParser(description="VMS CLI")
    subparsers = parser.add_subparsers(dest="command")
    
    admin_parser = subparsers.add_parser("create-admin", help="Create an admin user")
    admin_parser.add_argument("email", help="Admin email")
    admin_parser.add_argument("password", help="Admin password")
    
    args = parser.parse_args()
    
    if args.command == "create-admin":
        asyncio.run(create_admin(args.email, args.password))
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
