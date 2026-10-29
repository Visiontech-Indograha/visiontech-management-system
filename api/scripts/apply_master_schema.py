"""
Skrip eksekutor Master DDL & Seed Data PostgreSQL V2 ke Database Uji (test_migration).
Membaca koneksi dari api/.env.test.
"""
import asyncio
import os
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine

ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENV_TEST_FILE = ROOT_DIR / "api" / ".env.test"
DDL_FILE = ROOT_DIR / "db" / "06_master_schema_v2.sql"
SEED_FILE = ROOT_DIR / "db" / "07_master_seed_v2.sql"

def get_test_db_url() -> str:
    if os.environ.get("TEST_DATABASE_URL"):
        return os.environ["TEST_DATABASE_URL"]
    if ENV_TEST_FILE.exists():
        for line in ENV_TEST_FILE.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("TEST_DATABASE_URL="):
                return line.split("=", 1)[1].strip()
    raise SystemExit("TEST_DATABASE_URL belum diisi (env atau .env.test).")

async def main():
    url = get_test_db_url()
    print(f"Connecting to database via URL: {url.split('@')[-1]}...")
    engine = create_async_engine(url, isolation_level="AUTOCOMMIT")

    ddl_sql = DDL_FILE.read_text(encoding="utf-8")
    seed_sql = SEED_FILE.read_text(encoding="utf-8")

    async with engine.connect() as conn:
        print("1. Applying DDL (06_master_schema_v2.sql)...")
        await conn.execute(text(ddl_sql))
        print("   -> DDL applied successfully.")

        print("2. Applying Seed Data (07_master_seed_v2.sql)...")
        await conn.execute(text(seed_sql))
        print("   -> Seed data inserted successfully.")

        print("3. Verifying created tables and row counts...")
        res = await conn.execute(text(
            "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY table_name;"
        ))
        tables = [r[0] for r in res.fetchall()]
        print(f"   Total tables found ({len(tables)}): {', '.join(tables)}")

        # Hitung beberapa baris kunci
        for sample_tbl in ["office", "employee", "users", "division", "team", "work_plan_item", "attendance"]:
            if sample_tbl in tables:
                cnt = (await conn.execute(text(f"SELECT count(*) FROM {sample_tbl};"))).scalar()
                print(f"   Row count in '{sample_tbl}': {cnt}")

    await engine.dispose()
    print("ALL DONE: Master Schema and Seed Data are active and verified!")

if __name__ == "__main__":
    asyncio.run(main())
