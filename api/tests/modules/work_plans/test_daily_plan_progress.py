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
    """A 2/2 (selesai) + B pindah hari 0/1 = 50%: item pindah hari dihitung 0% sampai selesai di hari baru."""
    plan = make_daily_plan(world, status="ONGOING", days_from_today=0)
    add_item(plan, world, "Tuntas", status="DONE", completed_qty="2", target_qty="2")
    add_item(plan, world, "Digeser", status="SHIFTED_DAY", completed_qty="0", target_qty="1")
    row = _row(client, world, plan)
    assert (row["item_count"], row["done_count"]) == (2, 1)
    assert row["progress_pct"] == 50


def test_progress_is_average_of_active_items(client, world: World):
    """Satu item A 1/2 dikerjakan = 50%."""
    plan = make_daily_plan(world, status="ONGOING", days_from_today=0)
    add_item(plan, world, "Setengah", status="IN_PROGRESS", completed_qty="1", target_qty="2")
    assert _row(client, world, plan)["progress_pct"] == 50


def test_progress_rounds_down_to_98_when_almost_done(client, world: World):
    """98,9% dibulatkan ke bawah (98), bukan 99: 99 hanya untuk 'hampir' yang belum selesai."""
    plan = make_daily_plan(world, status="ONGOING", days_from_today=0)
    add_item(plan, world, "Hampir", status="IN_PROGRESS", completed_qty="989", target_qty="1000")
    assert _row(client, world, plan)["progress_pct"] == 98


def test_progress_caps_at_99_until_every_item_done(client, world: World):
    """99,95% belum sama dengan selesai: tetap 99, tidak pernah 100 sebelum semua item DONE."""
    plan = make_daily_plan(world, status="ONGOING", days_from_today=0)
    add_item(plan, world, "Sangat hampir", status="IN_PROGRESS", completed_qty="9995", target_qty="10000")
    assert _row(client, world, plan)["progress_pct"] == 99


def test_progress_100_only_when_every_item_done(client, world: World):
    plan = make_daily_plan(world, status="ONGOING", days_from_today=0)
    add_item(plan, world, "Tuntas A", status="DONE", completed_qty="1", target_qty="1")
    add_item(plan, world, "Tuntas B", status="DONE", completed_qty="3", target_qty="3")
    row = _row(client, world, plan)
    assert (row["item_count"], row["done_count"]) == (2, 2)
    assert row["progress_pct"] == 100
