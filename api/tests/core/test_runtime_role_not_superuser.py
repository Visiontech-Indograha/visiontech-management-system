"""CI/pytest wajib berjalan sebagai peran runtime non-superuser (`vms_api`), bukan pemilik/superuser (PR 0 RLS)."""
from __future__ import annotations

import os

import pytest

from tests.conftest import _sync_conn, requires_db


@requires_db
def test_vms_api_role_exists_and_is_not_superuser_and_no_bypassrls() -> None:
    """Memastikan peran vms_api sudah dibuat dan bukan superuser serta tidak BYPASSRLS (B-06)."""
    with _sync_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT rolname, rolsuper, rolbypassrls, rolcreatedb, rolcreaterole "
            "FROM pg_roles WHERE rolname = 'vms_api'"
        )
        row = cur.fetchone()
    assert row is not None, "Role vms_api belum dibuat di database"
    assert row[0] == "vms_api"
    assert row[1] is False, "vms_api tidak boleh superuser"
    assert row[2] is False, "vms_api tidak boleh BYPASSRLS"
    assert row[3] is False, "vms_api tidak boleh CREATEDB"
    assert row[4] is False, "vms_api tidak boleh CREATEROLE"


@requires_db
def test_vms_api_role_has_schema_and_table_privileges() -> None:
    """Memastikan peran vms_api memiliki hak minimal skema & tabel (USAGE, SELECT, INSERT, UPDATE, DELETE)."""
    with _sync_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT has_schema_privilege('vms_api', 'public', 'USAGE')")
        has_usage = cur.fetchone()[0]
        assert has_usage is True, "vms_api harus memiliki hak USAGE pada schema public"

        for priv in ("SELECT", "INSERT", "UPDATE", "DELETE"):
            cur.execute(f"SELECT has_table_privilege('vms_api', 'public.employee', '{priv}')")
            has_priv = cur.fetchone()[0]
            assert has_priv is True, f"vms_api harus memiliki hak {priv} pada public.employee"


@requires_db
@pytest.mark.skipif(not os.getenv("VMS_REQUIRE_DB"), reason="hanya di CI (VMS_REQUIRE_DB) peran runtime non-superuser")
def test_runtime_connection_is_not_superuser_and_has_no_bypassrls() -> None:
    import psycopg2

    from app.core.config import settings

    with psycopg2.connect(settings.DATABASE_URL.replace("+asyncpg", "")) as conn, conn.cursor() as cur:
        cur.execute("SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
        row = cur.fetchone()
    assert row == ("vms_api", False, False)


@requires_db
@pytest.mark.skipif(not os.getenv("VMS_REQUIRE_DB"), reason="hanya di CI (VMS_REQUIRE_DB) peran runtime non-superuser")
def test_startup_partition_ddl_is_skipped_silently_for_non_owner(caplog: pytest.LogCaptureFixture) -> None:
    import asyncio

    from app.database.migration_v3 import ensure_activity_log_partitions

    assert asyncio.run(ensure_activity_log_partitions()) == 0
    assert "tidak dibuat" not in caplog.text
