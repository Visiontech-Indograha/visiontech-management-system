"""Temuan E2E A4: setelah survei WO disetujui PM, order muncul di pilihan Alokasi (form-options) dan item jadwal
yang memakai order itu membawa work_order_id (jalur HP). Dulu kosong: WO tak membuat work_completion."""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from tests.conftest import World, requires_db, sync_query
from tests.orders import make_client

pytestmark = requires_db


def test_approved_survey_makes_order_available_for_allocation(client, world: World):
    tag = uuid.uuid4().hex[:6]
    pm = world.headers(client, "pm")
    wo = client.post("/work-orders", headers=pm, json={
        "client_id": make_client(), "division_id": world.unit_id, "pm_id": world.employees["pm"],
        "title": f"WO alokasi {tag}"})
    assert wo.status_code == 201, wo.text
    wo_id, wo_number = wo.json()["work_order_id"], wo.json()["wo_number"]

    def orders() -> list[dict]:
        res = client.get("/work-plans/form-options", headers=pm)
        assert res.status_code == 200, res.text
        return [o for o in res.json()["orders"] if o["project_title"] == f"WO alokasi {tag}"]

    assert orders() == []  # belum ada survei disetujui -> belum jadi order
    today = datetime.now(UTC).date().isoformat()
    assert client.post(f"/work-orders/{wo_id}/assign-survey", headers=pm,
                       json={"lead_team_id": world.team_id, "survey_date": today}).status_code == 200
    work_type = str(sync_query("INSERT INTO work_type (division_id, name) VALUES (%s, %s) RETURNING work_type_id",
                               (world.unit_id, f"Jenis {tag}"))[0][0])
    sent = client.post(f"/work-orders/{wo_id}/submit-survey", headers=world.headers(client, "member"), json={
        "narrative": "ok", "format": "CCTV",
        "points": [{"point_name": "Titik 1", "recommended_work_type_id": work_type}], "general_bom": []})
    assert sent.status_code == 200, sent.text
    assert orders() == []  # survei terkirim tapi belum disetujui
    assert client.post(f"/work-orders/{wo_id}/apply-survey", headers=pm).status_code == 200

    found = orders()
    assert len(found) == 1 and found[0]["order_number"] == wo_number
    assert str(found[0]["division_id"]) == world.unit_id
    # Persetujuan diulang (409) / balapan tidak menggandakan order.
    assert client.post(f"/work-orders/{wo_id}/apply-survey", headers=pm).status_code == 409
    assert len(orders()) == 1

    # Jadwal + item memakai order itu -> item membawa work_order_id (dipakai tampilan eksekusi HP).
    plan = client.post("/work-plans/daily", headers=pm, json={
        "division_id": world.unit_id, "team_id": world.team_id, "work_date": today, "site_name": "Site",
        "site_lat": -6.2, "site_lng": 106.8})
    assert plan.status_code in (200, 201), plan.text
    item = client.post(f"/work-plans/daily/{plan.json()['daily_plan_id']}/items", headers=pm, json={
        "work_type_id": work_type, "title": "Pasang kamera", "completion_id": found[0]["completion_id"]})
    assert item.status_code in (200, 201), item.text
    linked = sync_query("SELECT work_order_id::text FROM work_plan_item WHERE item_id = %s",
                        (item.json()["item_id"],))[0][0]
    assert linked == wo_id
