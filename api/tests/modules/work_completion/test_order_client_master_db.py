"""
Order klien wajib memakai klien dari master: nama klien order diambil dari klien terpilih; teks bebas tidak lagi
membuat klien "hantu" yang tak terhubung ke master.
"""
from __future__ import annotations

import uuid

from tests.conftest import World, requires_db
from tests.orders import make_client

pytestmark = requires_db


def _order(client, world: World, **extra):
    return client.post("/work-completions", headers=world.headers(client, "pm"),
                       json={"division_id": world.unit_id, "project_title": "Pekerjaan klien master", **extra})


def test_order_without_master_client_is_refused(client, world: World, fake_storage):
    assert _order(client, world, client_name="Teks bebas").status_code == 422
    assert _order(client, world).status_code == 422
    assert _order(client, world, client_id=str(uuid.uuid4())).status_code == 422


def test_order_takes_client_name_from_master(client, world: World, fake_storage):
    name = f"Klien master {world.tag}"
    response = _order(client, world, client_id=make_client(name), client_name="Nama tulisan tangan")
    assert response.status_code in (200, 201), response.text
    assert response.json()["client_name"] == name
