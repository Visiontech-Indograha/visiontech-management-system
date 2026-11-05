"""Ajukan pindah hari tidak menimpa status item yang diubah pihak lain (compare-and-set)."""
from __future__ import annotations

from tests.concurrency import tahan_lalu_ubah
from tests.conftest import World, requires_db, sync_query
from tests.daily import add_item, make_daily_plan

pytestmark = requires_db


def test_ajukan_pindah_hari_saat_item_berubah_dapat_409_dan_tidak_menimpa(client, world: World):
    plan = make_daily_plan(world, status="ONGOING", days_from_today=0)
    item = add_item(plan, world, target_qty="10", completed_qty="0")
    hasil = tahan_lalu_ubah(
        "UPDATE work_plan_item SET status = 'IN_PROGRESS' WHERE item_id = %s", (item,),
        lambda: client.post(f"/work-plans/items/{item}/request-rollover", headers=world.headers(client, "leader"),
                            json={"delay_reason": "Hujan deras", "completed_qty": "2"}),
    )
    assert hasil.status_code == 409, hasil.text
    assert hasil.json()["error"]["code"] == "INVALID_STATE", hasil.text
    row = sync_query("SELECT status, rollover_approval_status::text FROM work_plan_item WHERE item_id = %s",
                     (item,))[0]
    assert row[0] == "IN_PROGRESS" and row[1] != "WAITING_PM"
