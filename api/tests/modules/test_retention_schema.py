"""Skema retensi (v2_0036): kebijakan awal nonaktif, indeks arsip parsial, kolom separated_at."""
from __future__ import annotations

from tests.conftest import _sync_conn, requires_db

pytestmark = requires_db

EXPECTED = {
    "employee_row": 1825, "client": 1825, "employee_file": 1825, "tool": 730, "vehicle": 730,
    "company_mess": 365, "division": 365, "job_position": 365, "employee_personal_files": 30,
}


def _q(sql: str) -> list[tuple]:
    conn = _sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            return list(cur.fetchall())
    finally:
        conn.close()


def test_seed_policies_inactive() -> None:
    rows = _q("SELECT data_type, retention_days, is_active FROM retention_policy")
    got = {r[0]: r[1] for r in rows}
    assert all(got.get(k) == v for k, v in EXPECTED.items())
    assert all(r[2] is False for r in rows if r[0] in EXPECTED)


def test_archive_indexes_partial_and_separated_at() -> None:
    rows = _q("SELECT indexdef FROM pg_indexes WHERE indexname LIKE 'ix\\_%\\_archived\\_delete\\_at'")
    assert len(rows) == 10
    assert all("WHERE (delete_at IS NOT NULL)" in r[0] for r in rows)
    assert _q(
        "SELECT 1 FROM information_schema.columns WHERE table_name='employee' AND column_name='separated_at'"
    )
