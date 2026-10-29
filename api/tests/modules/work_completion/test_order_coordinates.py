"""
Koordinat lokasi order klien: rentang latitude -90..90 dan longitude -180..180 ditegakkan API.
Dulu nilai di luar rentang diskalakan diam-diam (123 → 0.000123).
"""
from __future__ import annotations

from tests.conftest import World, requires_db

pytestmark = requires_db


def _post(client, world: World, **coords):
    return client.post("/work-completions", headers=world.headers(client, "admin"),
                       json={"division_id": world.unit_id, "client_name": "Klien Koordinat",
                             "project_title": "Pekerjaan Koordinat", **coords})


def test_out_of_range_latitude_is_rejected_not_rescaled(client, world: World, fake_storage):
    response = _post(client, world, site_lat=123, site_lng=106.8)
    assert response.status_code == 422, response.text


def test_out_of_range_longitude_is_rejected(client, world: World, fake_storage):
    response = _post(client, world, site_lat=-6.2, site_lng=1068)
    assert response.status_code == 422, response.text


def test_valid_coordinates_are_stored_as_given(client, world: World, fake_storage):
    response = _post(client, world, site_lat=-6.2, site_lng=106.8)
    assert response.status_code in (200, 201), response.text
    order_id = response.json().get("completion_id") or response.json().get("id")
    body = client.get(f"/work-completions/{order_id}", headers=world.headers(client, "admin")).json()
    assert round(body["site_lat"], 4) == -6.2 and round(body["site_lng"], 4) == 106.8
