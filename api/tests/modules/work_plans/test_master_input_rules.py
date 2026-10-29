"""
A9 · Batas input master & item selaras dengan kolom DB (W2/W3/W7/W8/W11):
- target item NUMERIC(10,2): maks dua desimal, maks 99999999.99;
- fase item kosong → mengikuti jenis pekerjaan (template work type);
- nama klien di-strip (spasi saja = ditolak);
- total target proyek NUMERIC(12,2): maks dua desimal;
- bahan bawaan: nama di-strip dan wajib, jumlah > 0 (maks dua desimal), satuan wajib.
"""
from __future__ import annotations

import uuid

from tests.conftest import World, requires_db
from tests.daily import make_daily_plan

pytestmark = requires_db


def _client(client, world: World, name: str) -> dict:
    tag = uuid.uuid4().hex[:8]
    response = client.post("/clients", headers=world.headers(client, "pm"),
                           json={"client_code": f"UJI-{tag}", "name": name})
    return response


def test_client_name_is_trimmed_and_blank_name_is_refused(client, world: World):
    assert _client(client, world, "      ").status_code == 422
    tag = uuid.uuid4().hex[:8]
    made = _client(client, world, f"  Klien Uji Spasi {tag}  ")
    assert made.status_code == 201, made.text
    assert made.json()["name"] == f"Klien Uji Spasi {tag}"


def test_project_total_target_keeps_two_decimals(client, world: World):
    pm = world.headers(client, "pm")
    client_id = _client(client, world, f"Klien proyek uji {uuid.uuid4().hex[:8]}").json()["client_id"]
    body = {"client_id": client_id, "office_id": world.org_id, "division_id": world.unit_id,
            "spk_number": f"SPK/UJI/{uuid.uuid4().hex[:6]}", "project_title": "Proyek uji desimal",
            "unit_measure": "Unit", "start_date": "2026-11-01", "end_date": "2026-12-01"}

    assert client.post("/projects", headers=pm, json={**body, "total_target_qty": "1.234"}).status_code == 422
    assert client.post("/projects", headers=pm, json={**body, "total_target_qty": "2.50"}).status_code == 201


def test_plan_item_target_has_column_limits(client, world: World):
    pm = world.headers(client, "pm")
    plan = make_daily_plan(world, status="DRAFT", days_from_today=1)
    wt = client.post("/work-types", headers=pm, json={"name": f"Jenis uji {world.tag}", "kind": "WORK"})
    assert wt.status_code == 201, wt.text
    body = {"work_type_id": wt.json()["id"], "title": "Titik target uji", "target_qty": "1.234"}

    assert client.post(f"/work-plans/daily/{plan}/items", headers=pm, json=body).status_code == 422
    assert client.post(f"/work-plans/daily/{plan}/items", headers=pm,
                       json={**body, "target_qty": "100000000"}).status_code == 422
    assert client.post(f"/work-plans/daily/{plan}/items", headers=pm,
                       json={**body, "target_qty": "99999999.99"}).status_code == 201


def test_item_phase_defaults_from_work_type_kind(client, world: World):
    pm = world.headers(client, "pm")
    plan = make_daily_plan(world, status="DRAFT", days_from_today=1)
    expected = {"SURVEY_TASK": "SURVEY", "REPLACEMENT": "REPLACEMENT", "WORK": "INSTALLATION"}
    for kind, phase in expected.items():
        wt = client.post("/work-types", headers=pm, json={"name": f"{kind} {world.tag}", "kind": kind})
        assert wt.status_code == 201, wt.text
        item = client.post(f"/work-plans/daily/{plan}/items", headers=pm,
                           json={"work_type_id": wt.json()["id"], "title": f"Item {kind}"})
        assert item.status_code == 201, item.text
        assert item.json()["task_phase"] == phase, kind


def test_default_material_rules(client, world: World):
    pm = world.headers(client, "pm")
    wt = client.post("/work-types", headers=pm, json={"name": f"Jenis bahan {world.tag}", "kind": "WORK"})
    assert wt.status_code == 201, wt.text
    url = f"/work-types/{wt.json()['id']}/materials"
    valid = {"material_name": "Kabel UTP", "default_qty": 2, "unit": "Meter"}

    assert client.post(url, headers=pm, json={**valid, "material_name": "   "}).status_code == 422
    assert client.post(url, headers=pm, json={**valid, "default_qty": 0}).status_code == 422
    assert client.post(url, headers=pm, json={**valid, "default_qty": 1.555}).status_code == 422
    assert client.post(url, headers=pm, json={**valid, "unit": ""}).status_code == 422

    created = client.post(url, headers=pm, json={**valid, "material_name": "  Kabel UTP  "})
    assert created.status_code == 201, created.text
    assert created.json()["material_name"] == "Kabel UTP"
