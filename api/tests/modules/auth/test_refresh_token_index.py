"""
PERF · Indeks `ix_user_sessions_refresh_token_hash` (migrasi v2_0024, db/06).
Setiap refresh mencari `user_sessions.refresh_token_hash`; tanpa indeks itu pemindaian penuh.
- Indeks ada, berkolom `refresh_token_hash`, dan tidak parsial (kueri rotate tidak memfilter delete_at).
- Perencana kueri memakai indeks itu bila sekuensial dimatikan (kemampuan, bukan rencana tabel kecil).
"""
from __future__ import annotations

from tests.conftest import _sync_conn, requires_db

pytestmark = requires_db

INDEX_NAME = "ix_user_sessions_refresh_token_hash"


def test_refresh_token_hash_index_exists_and_is_not_partial() -> None:
    conn = _sync_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT indexdef FROM pg_indexes WHERE tablename = 'user_sessions' AND indexname = %s",
                (INDEX_NAME,),
            )
            row = cur.fetchone()
    finally:
        conn.close()

    assert row is not None, f"indeks {INDEX_NAME} tidak ada"
    indexdef = row[0]
    assert "(refresh_token_hash)" in indexdef
    assert " WHERE " not in indexdef


def test_planner_can_use_refresh_token_hash_index() -> None:
    conn = _sync_conn()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("SET LOCAL enable_seqscan = off")
            cur.execute(
                "EXPLAIN SELECT s.session_id FROM user_sessions s WHERE s.refresh_token_hash = %s",
                ("0" * 64,),
            )
            plan = "\n".join(line[0] for line in cur.fetchall())
    finally:
        conn.rollback()
        conn.close()

    assert INDEX_NAME in plan, plan
