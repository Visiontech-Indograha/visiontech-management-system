"""Temuan uji nyata 29-10-2026: form web mengirim pm_id null saat ubah proyek -> 500 (UUID 'None')."""
from __future__ import annotations

import uuid

from tests.conftest import World, requires_db

pytestmark = requires_db


def _project(client, world: World) -> dict:
    pm = world.headers(client, "pm")
    tag = uuid.uuid4().hex[:6]
    made = client.post("/clients", headers=pm, json={"client_code": f"UJI-{tag}", "name": f"Klien uji {tag}"})
    assert made.status_code == 201, made.text
    body = {"client_id": made.json()["client_id"], "office_id": world.org_id, "division_id": world.unit_id,
            "spk_number": f"SPK/UJI/{tag}", "project_title": "Proyek uji ubah", "total_target_qty": "5",
            "unit_measure": "Unit", "start_date": "2026-11-01", "end_date": "2026-12-01"}
    created = client.post("/projects", headers=pm, json=body)
    assert created.status_code == 201, created.text
    return created.json()


def test_update_treats_explicit_null_uuid_fields_as_unchanged(client, world: World):
    before = _project(client, world)
    pid = before["project_id"]
    pm = world.headers(client, "pm")
    res = client.put(f"/projects/{pid}", headers=pm,
                     json={"project_title": "Judul baru", "pm_id": None, "client_id": None, "office_id": None})
    assert res.status_code == 200, res.text
    after = res.json()
    assert after["project_title"] == "Judul baru"
    assert after["pm_id"] == before["pm_id"] and after["client_id"] == before["client_id"]
