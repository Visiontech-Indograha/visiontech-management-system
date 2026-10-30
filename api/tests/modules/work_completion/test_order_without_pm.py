"""
Order proyek klien tanpa PM (dibuat Super Admin) dan penandatanganan di luar urutan:
semua jalur harus menjawab 2xx/4xx yang jelas, tidak pernah 500.
"""
from __future__ import annotations

import base64
import io

from PIL import Image

from tests.conftest import World, requires_db
from tests.orders import make_client

pytestmark = requires_db


def _png_data_url() -> str:
    buf = io.BytesIO()
    Image.new("RGB", (40, 20), (0, 0, 0)).save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def _create(client, world: World) -> dict:
    created = client.post(
        "/work-completions", headers=world.headers(client, "admin"),
        json={"division_id": world.unit_id, "client_id": make_client("Klien Uji"), "project_title": "Pekerjaan Uji"},
    )
    assert created.status_code in (200, 201), created.text
    return created.json()


def test_order_without_pm_can_be_created_listed_and_read(client, world: World, fake_storage):
    order = _create(client, world)
    order_id = order.get("completion_id") or order.get("id")
    headers = world.headers(client, "admin")
    assert client.get("/work-completions", headers=headers).status_code == 200
    assert client.get(f"/work-completions/{order_id}", headers=headers).status_code == 200


def test_pm_cannot_sign_before_the_team_leader(client, world: World, fake_storage):
    order = _create(client, world)
    order_id = order.get("completion_id") or order.get("id")
    signed = client.post(f"/work-completions/{order_id}/sign", headers=world.headers(client, "admin"),
                         json={"signature_data_url": _png_data_url()})
    assert signed.status_code == 409, signed.text
    assert signed.json().get("code") == "LEADER_SIGNATURE_REQUIRED" or "Ketua tim" in signed.text
