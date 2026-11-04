"""
Balapan status jadwal harian (audit TOCTOU, skill vms-api §5): setujui/tolak membaca status lalu menulis,
tanpa kunci atau kondisi status. Tes ini memastikan:
- dua setujui bersamaan: tepat satu 200, yang lain 409 dengan status terkini;
- tolak yang menunggu kunci baris (sementara aksi lain mengubah status) tidak menimpa status itu, tetapi 409;
- urutan sah (setujui lalu tolak) tetap 200.
"""
from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from tests.conftest import World, _sync_conn, requires_db, sync_query
from tests.daily import add_item, make_daily_plan

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _status(plan: str) -> str:
    return sync_query("SELECT status FROM work_plan_daily WHERE daily_plan_id = %s", (plan,))[0][0]


def _tunggu_terkunci(batas: int = 200) -> None:
    """Tunggu sampai ada sesi yang menunggu kunci baris (permintaan tolak sudah masuk antrean)."""
    for _ in range(batas):
        if sync_query("SELECT count(*) FROM pg_stat_activity "
                      "WHERE wait_event_type = 'Lock' AND datname = current_database()")[0][0] > 0:
            return
        time.sleep(0.05)
    pytest.fail("Permintaan tolak tidak menunggu kunci baris; FOR UPDATE belum berjalan")


def test_dua_setujui_bersamaan_hanya_satu_sukses(client, world: World):
    plan = make_daily_plan(world, status="SUBMITTED", days_from_today=1)
    add_item(plan, world, "Titik CCTV uji")
    pm = world.headers(client, "pm")
    barrier = threading.Barrier(2)

    def setujui(_: int):
        barrier.wait()
        return client.post(f"/work-plans/daily/{plan}/approve", headers=pm)

    with ThreadPoolExecutor(max_workers=2) as pool:
        hasil = list(pool.map(setujui, range(2)))

    assert sorted(r.status_code for r in hasil) == [200, 409], [r.text for r in hasil]
    gagal = next(r for r in hasil if r.status_code == 409)
    assert "Disetujui" in gagal.text
    assert _status(plan) == "APPROVED"


def test_tolak_yang_menunggu_mulai_dapat_409_dan_tidak_menimpa(client, world: World):
    """Transaksi lain mengubah jadwal APPROVED menjadi ONGOING dan belum commit. Tolak harus menunggu,
    lalu membaca ONGOING dan menjawab 409 (sebelum perbaikan: menimpa ONGOING menjadi DRAFT)."""
    plan = make_daily_plan(world, status="APPROVED", days_from_today=0)
    pm = world.headers(client, "pm")
    conn = _sync_conn()
    conn.autocommit = False
    try:
        with conn.cursor() as cur:
            cur.execute("UPDATE work_plan_daily SET status = 'ONGOING' WHERE daily_plan_id = %s", (plan,))
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(client.post, f"/work-plans/daily/{plan}/reject", headers=pm,
                                 json={"reason": "Alasan uji"})
            _tunggu_terkunci()
            conn.commit()
            hasil = future.result(timeout=30)
    finally:
        conn.close()

    assert hasil.status_code == 409, hasil.text
    assert "Berjalan" in hasil.text
    assert _status(plan) == "ONGOING"


def test_setujui_ulang_setelah_disetujui_409(client, world: World):
    plan = make_daily_plan(world, status="SUBMITTED", days_from_today=1)
    add_item(plan, world, "Titik CCTV uji")
    pm = world.headers(client, "pm")
    assert client.post(f"/work-plans/daily/{plan}/approve", headers=pm).status_code == 200
    ulang = client.post(f"/work-plans/daily/{plan}/approve", headers=pm)
    assert ulang.status_code == 409, ulang.text
    assert "Disetujui" in ulang.text


def test_urutan_sah_setujui_lalu_tolak_tetap_200(client, world: World):
    """Tolak dari APPROVED termasuk aturan bisnis yang sah (require_daily_status): tetap 200, status kembali DRAFT."""
    plan = make_daily_plan(world, status="SUBMITTED", days_from_today=1)
    add_item(plan, world, "Titik CCTV uji")
    pm = world.headers(client, "pm")
    assert client.post(f"/work-plans/daily/{plan}/approve", headers=pm).status_code == 200
    tolak = client.post(f"/work-plans/daily/{plan}/reject", headers=pm, json={"reason": "Titik perlu dicek ulang"})
    assert tolak.status_code == 200, tolak.text
    assert _status(plan) == "DRAFT"
