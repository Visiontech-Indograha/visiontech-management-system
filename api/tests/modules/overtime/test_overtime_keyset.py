"""GET /overtime mode keyset: tanpa duplikat/lompat (created_at kembar), kursor rusak 422, mode lama utuh."""
from __future__ import annotations

from tests.conftest import World, requires_db, sync_query
from tests.daily import run_daily_to_ongoing

pytestmark = requires_db


def _seed(world: World, plan_id: str, n: int) -> set[str]:
    """n lembur dengan create_at SAMA (uji tie-break) untuk satu karyawan."""
    ids: set[str] = set()
    for _ in range(n):
        row = sync_query(
            "INSERT INTO overtime (daily_plan_id, employee_id, work_date, hours, reason, create_at) "
            "VALUES (%s, %s, CURRENT_DATE, 1, 'uji keyset', '2026-01-01T00:00:00+00') RETURNING overtime_id",
            (plan_id, world.employees["member"]),
        )
        ids.add(str(row[0][0]))
    return ids


def _walk(client, headers, params: dict, size: int) -> list[str]:
    seen: list[str] = []
    cursor = ""
    for _ in range(20):
        r = client.get("/overtime", headers=headers, params={**params, "cursor": cursor, "size": size})
        assert r.status_code == 200, r.text
        assert "x-total-count" not in r.headers
        seen += [row["id"] for row in r.json()]
        cursor = r.headers.get("x-next-cursor", "")
        if not cursor:
            return seen
    raise AssertionError("tidak berhenti")


def test_pages_cover_all_rows_without_duplicates(client, world: World):
    plan_id = run_daily_to_ongoing(world)
    ids = _seed(world, plan_id, 5)
    seen = _walk(client, world.headers(client, "pm"), {"daily_plan_id": plan_id}, 2)
    assert len(seen) == len(set(seen)) == 5 and set(seen) == ids


def test_old_mode_unchanged(client, world: World):
    plan_id = run_daily_to_ongoing(world)
    _seed(world, plan_id, 3)
    r = client.get("/overtime", headers=world.headers(client, "pm"), params={"daily_plan_id": plan_id})
    assert r.status_code == 200 and len(r.json()) == 3
    assert "x-next-cursor" not in r.headers and r.headers["x-total-count"] == "3"


def test_bad_cursor_is_422(client, world: World):
    r = client.get("/overtime", headers=world.headers(client, "pm"), params={"cursor": "rusak!!"})
    assert r.status_code == 422


def test_other_division_stays_closed(client, world: World, other_world: World):
    plan_id = run_daily_to_ongoing(world)
    _seed(world, plan_id, 2)
    r = client.get("/overtime", headers=other_world.headers(client, "pm"),
                   params={"daily_plan_id": plan_id, "cursor": ""})
    assert r.status_code == 404
