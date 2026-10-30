"""
BoM default jenis pekerjaan otomatis masuk ke order klien saat item jadwal dibuat dari template; tidak digandakan
bila item kedua dengan template yang sama dibuat.
"""
from __future__ import annotations

from tests.conftest import World, requires_db
from tests.daily import make_daily_plan

pytestmark = requires_db


def _order(client, world: World) -> str:
    admin = world.headers(client, "admin")
    made = client.post("/clients", headers=admin,
                       json={"client_code": f"BOM-{world.tag}", "name": f"Klien BoM {world.tag}", "pic_name": "Budi"})
    assert made.status_code == 201, made.text
    created = client.post(
        "/work-completions", headers=admin,
        json={"division_id": world.unit_id, "client_id": made.json()["client_id"], "project_title": f"BoM {world.tag}"},
    )
    assert created.status_code in (200, 201), created.text
    return created.json().get("completion_id") or created.json()["id"]


def test_item_from_template_copies_default_bom_into_order_once(client, world: World):
    admin = world.headers(client, "admin")
    pm = world.headers(client, "pm")
    wt = client.post("/work-types", headers=admin, json={"name": f"BoM otomatis {world.tag}", "kind": "WORK"})
    assert wt.status_code == 201, wt.text
    wt_id = wt.json()["id"]
    material = client.post(f"/work-types/{wt_id}/materials", headers=admin,
                           json={"material_name": "Kabel UTP", "default_qty": 2, "unit": "Meter"})
    assert material.status_code == 201, material.text
    order = _order(client, world)
    plan = make_daily_plan(world, status="DRAFT", days_from_today=1)

    for title in ("Titik A", "Titik B"):
        item = client.post(f"/work-plans/daily/{plan}/items", headers=pm,
                           json={"work_type_id": wt_id, "title": title, "completion_id": order})
        assert item.status_code == 201, item.text

    bom = client.get(f"/work-completions/{order}/bom", headers=admin)
    assert bom.status_code == 200, bom.text
    names = [row["material_name"] for row in bom.json()]
    assert names == ["Kabel UTP"]
