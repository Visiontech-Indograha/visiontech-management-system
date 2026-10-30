"""
Ikatan aset ke tim (butir 7): alat & kendaraan dapat menyebut tim pemakai bawaan; tim harus ada di kantor yang sama.
"""
from __future__ import annotations

import uuid

import pytest

from tests.conftest import World, requires_db

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def test_tool_created_with_default_team_reports_team_name(client, world: World):
    created = client.post("/assets/tools", headers=world.headers(client, "hr"), json={
        "office_id": world.org_id, "division_id": world.unit_id, "ownership_type": "SHARED_TOOL",
        "category": "BOR", "name": "Bor tim", "tool_code": f"tl-tim-{world.tag}",
        "team_id": world.team_id})

    assert created.status_code == 201, created.text
    assert created.json()["team_id"] == world.team_id
    assert created.json()["team_name"] == f"Tim uji {world.tag}"


def test_vehicle_team_can_be_set_and_is_listed(client, world: World):
    created = client.post("/assets/vehicles", headers=world.headers(client, "hr"), json={
        "office_id": world.org_id, "division_id": world.unit_id, "vehicle_type": "Car",
        "name": "Mobil tim", "number_plate": f"B {world.tag[:4]} TIM", "team_id": None})
    assert created.status_code == 201, created.text
    vehicle_id = created.json()["vehicle_id"]

    updated = client.put(f"/assets/vehicles/{vehicle_id}", headers=world.headers(client, "hr"),
                         json={"team_id": world.team_id})

    assert updated.status_code == 200, updated.text
    listed = [v for v in client.get("/assets/vehicles", headers=world.headers(client, "hr")).json()
              if v["vehicle_id"] == vehicle_id]
    assert listed[0]["team_id"] == world.team_id


def test_unknown_team_is_refused(client, world: World):
    response = client.post("/assets/tools", headers=world.headers(client, "hr"), json={
        "office_id": world.org_id, "division_id": world.unit_id, "ownership_type": "SHARED_TOOL",
        "category": "BOR", "name": "Bor salah", "tool_code": f"tl-salah-{world.tag}",
        "team_id": str(uuid.uuid4())})

    assert response.status_code == 422, response.text
