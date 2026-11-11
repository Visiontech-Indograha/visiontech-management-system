"""B-22: judul WO yang sama untuk klien yang sama memberi PERINGATAN (WO tetap dibuat), bukan blokir."""
from __future__ import annotations

import uuid

from tests.conftest import World, requires_db, sync_query
from tests.orders import make_client

pytestmark = requires_db


def _create(client, world: World, client_id: str, title: str):
    return client.post("/work-orders", headers=world.headers(client, "pm"), json={
        "client_id": client_id, "division_id": world.unit_id, "pm_id": world.employees["pm"], "title": title})


def test_same_title_same_client_warns_but_still_creates(client, world: World):
    title = f"Pasang CCTV gudang {uuid.uuid4().hex[:6]}"
    client_id = make_client()
    first = _create(client, world, client_id, title)
    assert first.status_code == 201, first.text
    assert first.json()["duplicate_title_warning"] is None

    second = _create(client, world, client_id, f"  {title.upper()} ")  # beda huruf besar/kecil dan spasi tepi
    assert second.status_code == 201, second.text
    warning = second.json()["duplicate_title_warning"]
    assert warning and first.json()["wo_number"] in warning
    assert second.json()["wo_number"] != first.json()["wo_number"]
    count = sync_query("SELECT count(*) FROM client_work_orders WHERE client_id = %s", (client_id,))[0][0]
    assert count == 2

    # Tidak disimpan: GET berikutnya tidak lagi memuat peringatan.
    again = client.get(f"/work-orders/{second.json()['work_order_id']}", headers=world.headers(client, "pm"))
    assert again.json()["duplicate_title_warning"] is None


def test_same_title_other_client_or_cancelled_wo_does_not_warn(client, world: World):
    title = f"Servis alarm {uuid.uuid4().hex[:6]}"
    client_a, client_b = make_client(), make_client()
    first = _create(client, world, client_a, title)
    assert first.status_code == 201, first.text
    other_client = _create(client, world, client_b, title)
    assert other_client.status_code == 201 and other_client.json()["duplicate_title_warning"] is None

    sync_query("UPDATE client_work_orders SET status = 'CANCELLED' WHERE work_order_id = %s",
               (first.json()["work_order_id"],))
    after_cancel = _create(client, world, client_a, title)
    assert after_cancel.status_code == 201 and after_cancel.json()["duplicate_title_warning"] is None


def test_concurrent_creates_get_distinct_wo_numbers(client, world: World):
    """Nomor WO dikunci: dua pembuatan serentak tidak bentrok (dulu 409 'Data yang sama sudah ada')."""
    from tests.concurrency import dua_bersamaan

    client_id = make_client()
    tag = uuid.uuid4().hex[:6]
    results = dua_bersamaan(lambda i: _create(client, world, client_id, f"WO serentak {i} {tag}"))
    assert [r.status_code for r in results] == [201, 201], [r.text for r in results]
    assert len({r.json()["wo_number"] for r in results}) == 2
