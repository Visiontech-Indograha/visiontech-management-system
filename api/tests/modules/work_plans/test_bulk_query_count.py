"""
Jumlah kueri alokasi massal (POST /work-plans/daily/bulk) tidak tumbuh dengan jumlah sel (tim x tanggal).

Tes menghitung pernyataan SQL yang dikirim engine aplikasi selama satu permintaan. Kode lama menjalankan beberapa
kueri per sel (team_of_division, team_day_taken, leader_on_leave, asset_loan_conflict, insert, set_status), sehingga
jumlahnya ikut tumbuh; kode baru memakai kueri per jenis data, sehingga jumlahnya tetap.
"""
from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from datetime import timedelta
from typing import Any
from uuid import uuid4

import pytest
from sqlalchemy import event

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


@contextmanager
def _hitung_sql() -> Iterator[list[int]]:
    """Menghitung pernyataan SQL ke engine aplikasi selama blok ini (kembalian: penghitung dalam daftar satu elemen)."""
    import app.database.session as db_session

    engine = db_session.engine.sync_engine
    hitung = [0]

    def _tambah(*_args: object) -> None:
        hitung[0] += 1

    event.listen(engine, "before_cursor_execute", _tambah)
    try:
        yield hitung
    finally:
        event.remove(engine, "before_cursor_execute", _tambah)


def _tim_tambahan(world: World, jumlah: int) -> list[str]:
    return [str(sync_query(
        "INSERT INTO team (office_id, division_id, leader_employee_id, name) VALUES (%s, %s, %s, %s) RETURNING team_id",
        (world.org_id, world.unit_id, world.employees["member"], f"Tim N1 {world.tag} {uuid4().hex[:6]}"),
    )[0][0]) for _ in range(jumlah)]


def _tanggal(mulai: int, jumlah: int) -> list[str]:
    hari_ini = jakarta_now().date()
    return [str(hari_ini + timedelta(days=mulai + i)) for i in range(jumlah)]


def _bulk(client: Any, headers: dict[str, str], world: World, tim: list[str], tanggal: list[str],
          target: str) -> tuple[int, dict[str, Any]]:
    # Satu aset acak (tanpa peminjaman) ikut diperiksa agar jalur bentrok aset juga dihitung.
    # APPROVED hanya untuk siaga (kind STANDBY), sesuai aturan skema DailyBulkIn.
    kind = "STANDBY" if target == "APPROVED" else "WORK"
    with _hitung_sql() as hitung:
        response = client.post("/work-plans/daily/bulk", headers=headers, json={
            "division_id": world.unit_id, "team_ids": tim, "work_dates": tanggal, "target": target, "kind": kind,
            "assets": [{"asset_type": "TOOL", "asset_id": str(uuid4())}],
        })
    assert response.status_code == 200, response.text
    return hitung[0], response.json()


@pytest.mark.parametrize(("target", "mulai"), [("DRAFT", 20), ("APPROVED", 40)])
def test_bulk_jumlah_kueri_tidak_tumbuh_dengan_jumlah_sel(client, world: World, target: str, mulai: int) -> None:
    pm = world.headers(client, "pm")
    kecil_kueri, kecil = _bulk(client, pm, world, [world.team_id], _tanggal(mulai, 2), target)
    assert kecil["created"] == 2

    besar_tim = [world.team_id, *_tim_tambahan(world, 4)]
    besar_kueri, besar = _bulk(client, pm, world, besar_tim, _tanggal(mulai + 10, 10), target)
    assert besar["created"] == 50 and besar["skipped"] == 0

    # 2 sel dan 50 sel memakai jumlah kueri yang sama: tidak ada kueri per sel.
    assert besar_kueri == kecil_kueri, f"kueri 2 sel={kecil_kueri}, 50 sel={besar_kueri}"


def _survei_disetujui(client: Any, world: World, hari: int, jumlah_titik: int,
                      jenis: tuple[str, str] | None = None) -> tuple[str, list[str], tuple[str, str]]:
    """Tugas survei yang sudah disetujui PM (kedudukan APPROVED) dengan `jumlah_titik` titik.
    `jenis` = (work type tugas, work type titik) yang dipakai ulang antarpanggilan agar jumlah jenis titik di divisi
    sama; kembalian: (task_id, titik, jenis)."""
    from tests.daily import make_daily_plan
    from tests.orders import make_client

    pm = world.headers(client, "pm")
    created = client.post("/work-completions", headers=pm, json={
        "division_id": world.unit_id, "client_id": make_client(), "project_title": f"Survei {hari}",
        "total_target_unit": 100})
    assert created.status_code in (200, 201), created.text
    cid = created.json()["completion_id"]
    plan = make_daily_plan(world, status="APPROVED", days_from_today=hari)
    tag = uuid4().hex[:6]
    if jenis is None:
        wt_tugas = str(sync_query("INSERT INTO work_type (division_id, name, kind) VALUES (%s, %s, 'SURVEY_TASK') "
                                  "RETURNING work_type_id", (world.unit_id, f"Survei {tag}"))[0][0])
        wt_pasang = str(sync_query("INSERT INTO work_type (division_id, name, kind) VALUES (%s, %s, 'INSTALLATION') "
                                   "RETURNING work_type_id", (world.unit_id, f"Pasang {tag}"))[0][0])
        wt_titik = str(sync_query(
            "INSERT INTO work_type (division_id, name, kind, follow_up_work_type_id) "
            "VALUES (%s, %s, 'SURVEY_POINT', %s) RETURNING work_type_id",
            (world.unit_id, f"Titik {tag}", wt_pasang))[0][0])
        jenis = (wt_tugas, wt_titik)
    wt_tugas, wt_titik = jenis
    task = str(sync_query(
        "INSERT INTO work_plan_item (daily_plan_id, work_type_id, title, task_phase, completion_id, status, "
        "approved_by_pm_id, target_qty) VALUES (%s, %s, 'Survei uji', 'SURVEY', %s, 'DONE', %s, 1) RETURNING item_id",
        (plan, wt_tugas, cid, world.employees["pm"]))[0][0])
    titik = [str(sync_query(
        "INSERT INTO work_plan_item (daily_plan_id, work_type_id, title, task_phase, depends_on_item_id, status, "
        "site_lat, site_lng, target_qty) VALUES (%s, %s, %s, 'SURVEY', %s, 'DONE', -6.2, 106.8, 1) RETURNING item_id",
        (plan, wt_titik, f"Titik {i}", task))[0][0]) for i in range(jumlah_titik)]
    return task, titik, jenis


def test_survei_jumlah_kueri_tidak_tumbuh_dengan_jumlah_titik(client, world: World, fake_storage) -> None:
    """plan_from_survey: item lanjutan per titik ditulis dalam satu INSERT, bukan satu INSERT per titik."""
    pm = world.headers(client, "pm")
    hasil: list[tuple[int, dict[str, Any], list[str], str]] = []
    jenis: tuple[str, str] | None = None
    for hari, jumlah in ((50, 1), (60, 6)):
        task, titik, jenis = _survei_disetujui(client, world, hari, jumlah, jenis)
        target = str(jakarta_now().date() + timedelta(days=hari + 3))
        with _hitung_sql() as hitung:
            response = client.post(f"/work-plans/surveys/{task}/plan", headers=pm, json={
                "work_date": target, "task_phase": "INSTALLATION"})
        assert response.status_code == 201, response.text
        hasil.append((hitung[0], response.json(), titik, task))

    (kecil_kueri, kecil, _, _), (besar_kueri, besar, titik_besar, _) = hasil
    assert len(kecil["created_item_ids"]) == 1
    assert len(besar["created_item_ids"]) == 6
    # Setiap titik mendapat item pemasangan (INSTALLATION) yang menunjuk titik itu, berurutan sesuai titik.
    baris = sync_query(
        "SELECT depends_on_item_id::text, task_phase FROM work_plan_item WHERE item_id = ANY(%s::uuid[]) "
        "ORDER BY create_at, item_id",
        (besar["created_item_ids"],))
    assert sorted(b[0] for b in baris) == sorted(titik_besar)
    assert {b[1] for b in baris} == {"INSTALLATION"}
    assert besar_kueri == kecil_kueri, f"kueri 1 titik={kecil_kueri}, 6 titik={besar_kueri}"


def test_jadwal_order_jumlah_kueri_tidak_tumbuh_dengan_jumlah_jadwal(client, world: World, fake_storage) -> None:
    """plans_of_order: kedudukan semua jadwal dibaca sekali, bukan satu kueri per jadwal."""
    from tests.daily import add_item, make_daily_plan
    from tests.orders import make_client

    pm = world.headers(client, "pm")
    created = client.post("/work-completions", headers=pm, json={
        "division_id": world.unit_id, "client_id": make_client(), "project_title": "Hitung kueri",
        "total_target_unit": 100})
    assert created.status_code in (200, 201), created.text
    cid = created.json()["completion_id"]

    def _jadwal_order() -> tuple[int, dict[str, Any]]:
        with _hitung_sql() as hitung:
            response = client.get(f"/work-plans/orders/{cid}/schedule", headers=pm)
        assert response.status_code == 200, response.text
        return hitung[0], response.json()

    add_item(make_daily_plan(world, status="APPROVED", days_from_today=30), world, "Titik awal",
             completion_id=cid, target_qty=1)
    kecil_kueri, kecil = _jadwal_order()
    assert len(kecil["plans"]) == 1

    for hari in range(31, 41):
        add_item(make_daily_plan(world, status="APPROVED", days_from_today=hari), world, f"Titik {hari}",
                 completion_id=cid, target_qty=1)
    besar_kueri, besar = _jadwal_order()
    assert len(besar["plans"]) == 11

    assert besar_kueri == kecil_kueri, f"kueri 1 jadwal={kecil_kueri}, 11 jadwal={besar_kueri}"
