"""V-04 · Enum Python identik dengan enum PostgreSQL (ai-testing h: daftar ganda wajib uji kesetaraan)."""
from __future__ import annotations

import pytest

from app.core.enums import DB_ENUMS
from tests.conftest import requires_db, sync_query

pytestmark = requires_db


@pytest.mark.parametrize("db_type", sorted(DB_ENUMS))
def test_python_enum_matches_database(db_type: str):
    (labels,) = sync_query(f"SELECT enum_range(NULL::vms.{db_type})::text[]")[0]

    assert [member.value for member in DB_ENUMS[db_type]] == list(labels)
