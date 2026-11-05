"""GET /overtime?mine=true: hanya mempersempit cakupan (offset dan keyset), tanpa parameter = perilaku lama."""
from __future__ import annotations

from tests.conftest import World, requires_db, sync_query
from tests.daily import run_daily_to_ongoing

pytestmark = requires_db


def _seed_for(world: World, plan_id: str, who: str, n: int) -> set[str]:
    ids: set[str] = set()
    for _ in range(n):
        row = sync_query(
            "INSERT INTO overtime (daily_plan_id, employee_id, work_date, hours, reason, create_at) "
            "VALUES (%s, %s, CURRENT_DATE, 1, 'uji mine', now()) RETURNING overtime_id",
            (plan_id, world.employees[who]),
        )
        ids.add(str(row[0][0]))
    return ids


def _ids(r) -> set[str]:
    assert r.status_code == 200, r.text
    return {x["id"] for x in r.json()}


def _walk(client, headers, params: dict, size: int) -> list[str]:
    seen: list[str] = []
    cursor = ""
    for _ in range(20):
        r = client.get("/overtime", headers=headers, params={**params, "cursor": cursor, "size": size})
        assert r.status_code == 200, r.text
        assert "x-total-count" not in r.headers
        seen += [x["id"] for x in r.json()]
        cursor = r.headers.get("x-next-cursor", "")
        if not cursor:
            return seen
    raise AssertionError("tidak berhenti")


def test_mine_matrix_only_narrows(client, world: World):
    plan_id = run_daily_to_ongoing(world)
    m = _seed_for(world, plan_id, "member", 3)
    ld = _seed_for(world, plan_id, "leader", 2)
    for who, own in (("member", m), ("leader", ld)):
        h = world.headers(client, who)
        assert _ids(client.get("/overtime", headers=h, params={"mine": "true"})) == own
        assert _ids(client.get("/overtime", headers=h, params={"mine": "true", "cursor": ""})) == own
        assert _ids(client.get("/overtime", headers=h, params={"mine": "false"})) == _ids(
            client.get("/overtime", headers=h)
        )
    # Paritas tanpa parameter untuk karyawan biasa: hanya miliknya
    assert _ids(client.get("/overtime", headers=world.headers(client, "member"))) == m
    # PM/HR/OM tidak punya lembur sendiri: mine=true kosong, tanpa mine tidak berubah
    for who in ("pm", "hr", "ops"):
        h = world.headers(client, who)
        full = client.get("/overtime", headers=h)
        if full.status_code != 200:
            continue
        assert client.get("/overtime", headers=h, params={"mine": "true"}).json() == []
        assert client.get("/overtime", headers=h, params={"mine": "true", "cursor": ""}).json() == []
    pm_full = client.get("/overtime", headers=world.headers(client, "pm"))
    assert pm_full.status_code == 200 and _ids(pm_full) >= (m | ld)


def test_mine_keyset_pages_no_dup_no_loss(client, world: World):
    plan_id = run_daily_to_ongoing(world)
    own = _seed_for(world, plan_id, "member", 5)
    _seed_for(world, plan_id, "leader", 3)
    seen = _walk(client, world.headers(client, "member"), {"mine": "true"}, 2)
    assert len(seen) == len(set(seen)) == 5 and set(seen) == own


def test_mine_cursor_cross_context_does_not_widen(client, world: World):
    plan_id = run_daily_to_ongoing(world)
    _seed_for(world, plan_id, "member", 3)
    other = _seed_for(world, plan_id, "leader", 3)
    h = world.headers(client, "member")
    r = client.get("/overtime", headers=h, params={"mine": "true", "cursor": "", "size": 1})
    cur = r.headers["x-next-cursor"]
    r2 = client.get("/overtime", headers=h, params={"cursor": cur, "size": 50})
    assert r2.status_code == 200 and not ({x["id"] for x in r2.json()} & other)
    assert client.get("/overtime", headers=h, params={"mine": "true", "cursor": "rusak!!"}).status_code == 422
