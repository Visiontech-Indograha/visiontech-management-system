"""CI/pytest wajib berjalan sebagai peran runtime non-superuser (`vms_api`), bukan pemilik/superuser (PR 0 RLS)."""
from __future__ import annotations

import os

import pytest

from tests.conftest import requires_db


@requires_db
@pytest.mark.skipif(not os.getenv("VMS_REQUIRE_DB"), reason="hanya di CI (VMS_REQUIRE_DB) peran runtime non-superuser")
def test_runtime_connection_is_not_superuser_and_has_no_bypassrls() -> None:
    import psycopg2

    from app.core.config import settings

    with psycopg2.connect(settings.DATABASE_URL.replace("+asyncpg", "")) as conn, conn.cursor() as cur:
        cur.execute("SELECT current_user, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = current_user")
        row = cur.fetchone()
    assert row == ("vms_api", False, False)
