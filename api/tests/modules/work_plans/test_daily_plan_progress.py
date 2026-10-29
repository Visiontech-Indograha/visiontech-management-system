"""
Ringkasan progres jadwal harian di daftar (GET /work-plans/daily): persen tidak boleh 100 bila masih ada item
yang belum selesai (item yang dipindah hari tidak dihitung di persen, tetapi tetap ada di jumlah item).
"""
from __future__ import annotations

from app.core.time import jakarta_now
from tests.conftest import World, requires_db
from tests.daily import add_item, make_daily_plan

pytestmark = requires_db


def _row(client, world: World, plan_id: str) -> dict:
    today = str(jakarta_now().date())
    rows = client.get("/work-plans/daily", params={"start": today, "end": today},
                      headers=world.headers(client, "pm")).json()
    return next(r for r in rows if r["daily_plan_id"] == plan_id)


def test_progress_not_100_while_shifted_item_remains(client, world: World):
    plan = make_daily_plan(world, status="ONGOING", days_from_today=0)
    add_item(plan, world, "Tuntas", status="DONE", completed_qty="1", target_qty="1")
    add_item(plan, world, "Digeser", status="SHIFTED_DAY", completed_qty="1", target_qty="3")
    row = _row(client, world, plan)
    assert (row["item_count"], row["done_count"]) == (2, 1)
    assert row["progress_pct"] == 99


def test_progress_100_only_when_every_item_done(client, world: World):
    plan = make_daily_plan(world, status="ONGOING", days_from_today=0)
    add_item(plan, world, "Tuntas A", status="DONE", completed_qty="1", target_qty="1")
    add_item(plan, world, "Tuntas B", status="DONE", completed_qty="3", target_qty="3")
    row = _row(client, world, plan)
    assert (row["item_count"], row["done_count"]) == (2, 2)
    assert row["progress_pct"] == 100
