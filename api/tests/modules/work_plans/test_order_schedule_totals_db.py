"""
Ringkasan target order di jadwal order: total, sudah dijadwalkan (jumlah target item), dan sisa yang belum
dijadwalkan. Dipakai form alokasi agar tidak melebihi target order.
"""
from __future__ import annotations

from tests.conftest import World, requires_db
from tests.daily import add_item, make_daily_plan
from tests.orders import make_client

pytestmark = requires_db


def test_order_schedule_reports_total_scheduled_and_unscheduled_target(client, world: World, fake_storage):
    created = client.post("/work-completions", headers=world.headers(client, "pm"),
                          json={"division_id": world.unit_id, "client_id": make_client(),
                                "project_title": "Pekerjaan jadwal", "total_target_unit": 10})
    assert created.status_code in (200, 201), created.text
    cid = created.json()["completion_id"]

    add_item(make_daily_plan(world, status="APPROVED"), world, "Titik 1", completion_id=cid, target_qty=4)
    add_item(make_daily_plan(world, status="APPROVED", days_from_today=1), world, "Titik 2",
             completion_id=cid, target_qty=3)

    response = client.get(f"/work-plans/orders/{cid}/schedule", headers=world.headers(client, "pm"))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total_target_unit"] == 10
    assert body["scheduled_target_qty"] == 7
    assert body["unscheduled_target_qty"] == 3
    assert len(body["plans"]) == 2


def test_order_schedule_without_plans_has_full_unscheduled_target(client, world: World, fake_storage):
    created = client.post("/work-completions", headers=world.headers(client, "pm"),
                          json={"division_id": world.unit_id, "client_id": make_client(),
                                "project_title": "Pekerjaan kosong", "total_target_unit": 5})
    cid = created.json()["completion_id"]
    body = client.get(f"/work-plans/orders/{cid}/schedule", headers=world.headers(client, "pm")).json()
    assert body["plans"] == []
    assert body["unscheduled_target_qty"] == 5
