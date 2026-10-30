"""
Jenis jadwal harian `kind` (Service by request, v2_0014): jadwal STANDBY (tim siaga menunggu perintah PM) boleh
diajukan dan disetujui tanpa item, jadwal WORK tetap wajib berisi pekerjaan (PLAN_EMPTY), dan `kind` ikut
terbaca di detail serta tersalin saat jadwal disalin.
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.time import jakarta_now
from tests.conftest import World, requires_db
from tests.daily import add_item, make_daily_plan

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def test_standby_plan_is_approved_without_items(client, world: World):
    pm = world.headers(client, "pm")
    created = client.post("/work-plans/daily", headers=pm, json={
        "division_id": world.unit_id, "team_id": world.team_id,
        "work_date": str(jakarta_now().date() + timedelta(days=2)), "kind": "STANDBY",
    })
    assert created.status_code == 201, created.text
    standby = created.json()["daily_plan_id"]
    assert created.json()["kind"] == "STANDBY"

    submitted = client.post(f"/work-plans/daily/{standby}/submit", headers=pm)
    assert submitted.status_code == 200, submitted.text
    approved = client.post(f"/work-plans/daily/{standby}/approve", headers=pm)
    assert approved.status_code == 200, approved.text
    assert approved.json()["status"] == "APPROVED"
    assert approved.json()["kind"] == "STANDBY"


def test_work_plan_without_items_is_still_refused(client, world: World):
    plan = make_daily_plan(world, status="DRAFT", days_from_today=1)
    pm = world.headers(client, "pm")

    refused = client.post(f"/work-plans/daily/{plan}/submit", headers=pm)
    assert refused.status_code == 422, refused.text
    assert "PLAN_EMPTY" in refused.text

    add_item(plan, world, "Titik CCTV uji")
    detail = client.get(f"/work-plans/daily/{plan}", headers=pm)
    assert detail.status_code == 200, detail.text
    assert detail.json()["kind"] == "WORK"


def test_kind_rejects_unknown_value(client, world: World):
    pm = world.headers(client, "pm")
    response = client.post("/work-plans/daily", headers=pm, json={
        "division_id": world.unit_id, "team_id": world.team_id,
        "work_date": str(jakarta_now().date() + timedelta(days=2)), "kind": "LAIN",
    })
    assert response.status_code == 422, response.text
