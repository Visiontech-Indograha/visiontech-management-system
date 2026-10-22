"""V-04 · Enum Python identik dengan enum PostgreSQL Master Schema V2 (daftar ganda wajib uji kesetaraan)."""
from __future__ import annotations

from app.core.permissions import SystemRole
from tests.conftest import requires_db, sync_query

pytestmark = requires_db


def test_system_role_matches_database():
    (labels,) = sync_query("SELECT enum_range(NULL::system_role_enum)::text[]")[0]

    assert [member.value for member in SystemRole] == list(labels)
