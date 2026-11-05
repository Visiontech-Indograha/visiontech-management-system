"""GET /audit-events mode keyset: urutan created_at DESC, log_id ASC; tie-break; kursor rusak 422; mode lama utuh."""
from __future__ import annotations

import uuid

from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _seed(n: int, table: str) -> set[str]:
    ids: set[str] = set()
    for _ in range(n):
        row = sync_query(
            "INSERT INTO app_activity_logs (created_at, actor_role, platform, action, entity_table, entity_id, "
            "changed_diff) VALUES (NOW() - interval '1 minute' * 0, 'ADMIN', 'web_react', 'UPDATE', %s, %s, '{}') "
            "RETURNING log_id",
            (table, str(uuid.uuid4())),
        )
        ids.add(str(row[0][0]))
    return ids


def _fix_same_time(table: str) -> None:
    sync_query(
        "UPDATE app_activity_logs SET created_at = date_trunc('minute', NOW()) WHERE entity_table = %s", (table,)
    )


def test_keyset_pages_with_equal_created_at(client, world: World):
    table = f"zz_ks_{uuid.uuid4().hex[:8]}"
    ids = _seed(5, table)
    _fix_same_time(table)
    headers, seen, cursor = world.headers(client, "admin"), [], ""
    try:
        for _ in range(10):
            r = client.get("/audit-events", headers=headers,
                           params={"entity_type": table, "cursor": cursor, "size": 2})
            assert r.status_code == 200, r.text
            seen += [e["id"] for e in r.json()["items"]]
            cursor = r.headers.get("x-next-cursor", "")
            if not cursor:
                break
        assert seen == sorted(seen) and len(seen) == len(set(seen)) and set(seen) == ids  # log_id ASC pada waktu sama
    finally:
        sync_query("DELETE FROM app_activity_logs WHERE entity_table = %s", (table,))


def test_old_mode_and_bad_cursor(client, world: World):
    headers = world.headers(client, "admin")
    old = client.get("/audit-events", headers=headers, params={"page": 1, "size": 5})
    assert old.status_code == 200 and "x-next-cursor" not in old.headers and "total" in old.json()
    assert client.get("/audit-events", headers=headers, params={"cursor": "rusak!!"}).status_code == 422
