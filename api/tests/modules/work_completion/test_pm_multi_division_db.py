"""
Order klien oleh PM yang memimpin lebih dari satu divisi: divisi harus dipilih eksplisit (422 DIVISION_REQUIRED
dengan pilihan), tidak lagi masuk ke divisi yang kebetulan terpilih.
"""
from __future__ import annotations

from tests.conftest import World, requires_db
from tests.orders import make_client

pytestmark = requires_db


def _body(world: World, **extra: str) -> dict[str, str]:
    return {"client_id": make_client(), "project_title": "Pekerjaan uji", **extra}


def test_pm_with_one_division_gets_it_automatically(client, world: World, fake_storage):
    response = client.post("/work-completions", headers=world.headers(client, "pm"), json=_body(world))
    assert response.status_code in (200, 201), response.text
    assert response.json()["division_id"] == world.unit_id


def test_pm_with_two_divisions_must_choose_one(client, world: World, fake_storage):
    second = world.add_unit("Dua")
    headers = world.headers(client, "pm")

    refused = client.post("/work-completions", headers=headers, json=_body(world))
    assert refused.status_code == 422, refused.text
    payload = refused.json()["error"]
    assert payload["code"] == "DIVISION_REQUIRED"
    offered = {d["division_id"] for d in payload["details"]["divisions"]}
    assert offered == {world.unit_id, second}

    chosen = client.post("/work-completions", headers=headers, json=_body(world, division_id=second))
    assert chosen.status_code in (200, 201), chosen.text
    assert chosen.json()["division_id"] == second
