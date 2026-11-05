"""Transisi status order lewat HTTP (PM override, PUT, keputusan ACC): 409 INVALID_STATE, audit mundur, dan
konkurensi dua override serentak (tepat satu menang, satu 409)."""
from __future__ import annotations

import pytest

from tests.concurrency import dua_bersamaan
from tests.conftest import World, requires_db, sync_query
from tests.orders import make_client

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _order(client, world: World) -> str:
    created = client.post(
        "/work-completions", headers=world.headers(client, "pm"),
        json={"division_id": world.unit_id, "client_id": make_client(f"Klien transisi {world.tag}"),
              "project_title": "Pekerjaan transisi"},
    )
    assert created.status_code in (200, 201), created.text
    body = created.json()
    return str(body.get("completion_id") or body.get("id"))


def _status(order: str) -> str:
    return sync_query("SELECT order_status FROM work_completion WHERE completion_id = %s", (order,))[0][0]


def _patch(client, world: World, order: str, status: str):
    return client.patch(f"/work-completions/{order}/status", headers=world.headers(client, "pm"),
                        json={"order_status": status})


def test_transisi_tidak_sah_lewat_override_dapat_409_dan_status_tetap(client, world: World):
    order = _order(client, world)
    assert _patch(client, world, order, "CANCELLED").status_code == 200
    hasil = _patch(client, world, order, "URGENT")  # dari CANCELLED hanya boleh ke ONGOING
    assert hasil.status_code == 409, hasil.text
    assert hasil.json()["error"]["code"] == "INVALID_STATE", hasil.text
    assert _status(order) == "CANCELLED"


def test_keputusan_acc_tanpa_menunggu_acc_dapat_409(client, world: World):
    order = _order(client, world)  # ONGOING: DITERIMA hanya sah dari WAITING_ACC
    hasil = client.post(f"/work-completions/{order}/acc-decision", headers=world.headers(client, "pm"),
                        json={"decision": "DITERIMA"})
    assert hasil.status_code == 409, hasil.text
    assert hasil.json()["error"]["code"] == "INVALID_STATE", hasil.text
    assert _status(order) == "ONGOING"


def test_mundur_tercatat_di_audit(client, world: World):
    order = _order(client, world)
    assert _patch(client, world, order, "CANCELLED").status_code == 200
    assert _patch(client, world, order, "ONGOING").status_code == 200  # membuka lagi = memundurkan
    jumlah = sync_query(
        "SELECT count(*) FROM app_activity_logs WHERE action = 'ORDER_STATUS_MUNDUR' "
        "AND entity_table = 'work_completion' AND entity_id = %s", (order,))[0][0]
    assert jumlah == 1


def test_maju_biasa_tidak_masuk_audit_mundur(client, world: World):
    order = _order(client, world)
    assert _patch(client, world, order, "URGENT").status_code == 200  # ONGOING -> URGENT: maju/samping
    jumlah = sync_query(
        "SELECT count(*) FROM app_activity_logs WHERE action = 'ORDER_STATUS_MUNDUR' AND entity_id = %s",
        (order,))[0][0]
    assert jumlah == 0


def test_dua_override_serentak_tepat_satu_menang_dan_satu_409(client, world: World):
    """Dua override dari ONGOING yang sama-sama sah di peta: satu 200, satu 409 INVALID_STATE. Tidak ada 500."""
    order = _order(client, world)
    pm = world.headers(client, "pm")
    badan = [{"order_status": "CANCELLED"}, {"order_status": "COMPLETED"}]
    hasil = dua_bersamaan(lambda i: client.patch(f"/work-completions/{order}/status", headers=pm, json=badan[i]))
    assert sorted(r.status_code for r in hasil) == [200, 409], [r.text for r in hasil]
    gagal = next(r for r in hasil if r.status_code == 409)
    assert gagal.json()["error"]["code"] == "INVALID_STATE", gagal.text
    assert _status(order) in ("CANCELLED", "COMPLETED")
