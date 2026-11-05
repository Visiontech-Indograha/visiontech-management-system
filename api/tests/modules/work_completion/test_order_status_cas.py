"""Status order proyek bersamaan (audit F-13/F-14): PM override (PATCH /status) dan ubah order (PUT).

Perubahan status hanya berlaku bila status saat UPDATE masih sama dengan yang dibaca (compare-and-set).
Bila tidak, jawab 409 INVALID_STATE dan jangan menimpa status yang sudah diubah pihak lain.
"""
from __future__ import annotations

import pytest

from tests.concurrency import dua_bersamaan, tahan_lalu_ubah
from tests.conftest import World, requires_db, sync_query
from tests.orders import make_client

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _order(client, world: World) -> str:
    created = client.post(
        "/work-completions", headers=world.headers(client, "pm"),
        json={"division_id": world.unit_id, "client_id": make_client(f"Klien CAS {world.tag}"),
              "project_title": "Pekerjaan CAS"},
    )
    assert created.status_code in (200, 201), created.text
    body = created.json()
    return str(body.get("completion_id") or body.get("id"))


def _status(order: str) -> str:
    return sync_query("SELECT order_status FROM work_completion WHERE completion_id = %s", (order,))[0][0]


def test_ubah_status_bersamaan_tidak_menimpa_diam_diam(client, world: World):
    """Dua override serentak dari status yang sama: salah satu boleh 409, dan tidak ada jawaban 500."""
    order = _order(client, world)
    pm = world.headers(client, "pm")
    badan = [{"order_status": "CANCELLED"}, {"order_status": "COMPLETED"}]
    hasil = dua_bersamaan(lambda i: client.patch(f"/work-completions/{order}/status", headers=pm, json=badan[i]))
    kode = sorted(r.status_code for r in hasil)
    assert kode in ([200, 200], [200, 409]), [r.text for r in hasil]
    for r in hasil:
        if r.status_code == 409:
            assert r.json()["error"]["code"] == "INVALID_STATE", r.text
    assert _status(order) in ("CANCELLED", "COMPLETED")


def test_ubah_status_yang_tertahan_dapat_409_dan_tidak_menimpa(client, world: World):
    order = _order(client, world)
    pm = world.headers(client, "pm")
    hasil = tahan_lalu_ubah(
        "UPDATE work_completion SET order_status = 'URGENT' WHERE completion_id = %s", (order,),
        lambda: client.patch(f"/work-completions/{order}/status", headers=pm,
                             json={"order_status": "CANCELLED"}),
    )
    assert hasil.status_code == 409, hasil.text
    assert hasil.json()["error"]["code"] == "INVALID_STATE", hasil.text
    assert _status(order) == "URGENT"


def test_ubah_order_dengan_status_yang_tertahan_dapat_409_dan_tidak_menimpa(client, world: World):
    order = _order(client, world)
    pm = world.headers(client, "pm")
    hasil = tahan_lalu_ubah(
        "UPDATE work_completion SET order_status = 'URGENT' WHERE completion_id = %s", (order,),
        lambda: client.put(f"/work-completions/{order}", headers=pm, json={"order_status": "CANCELLED"}),
    )
    assert hasil.status_code == 409, hasil.text
    assert hasil.json()["error"]["code"] == "INVALID_STATE", hasil.text
    assert _status(order) == "URGENT"
