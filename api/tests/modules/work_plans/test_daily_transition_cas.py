"""Transisi status jadwal harian bersamaan (audit F-12/F-14): ajukan, mulai, tutup, dan setujui massal.

Setiap transisi diuji dua cara: (1) dua permintaan serentak (Barrier) menghasilkan tepat satu 200 dan satu 409;
(2) transaksi lain menahan baris lalu commit; permintaan harus 409 dan tidak menimpa status itu.
"""
from __future__ import annotations

import pytest

from tests.concurrency import dua_bersamaan, tahan_lalu_ubah
from tests.conftest import World, requires_db, sync_query
from tests.daily import add_item, check_in, make_daily_plan

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _status(plan: str) -> str:
    return sync_query("SELECT status FROM work_plan_daily WHERE daily_plan_id = %s", (plan,))[0][0]


def _satu_200_satu_409(hasil: list) -> None:
    assert sorted(r.status_code for r in hasil) == [200, 409], [r.text for r in hasil]
    gagal = next(r for r in hasil if r.status_code == 409)
    assert gagal.json()["error"]["code"] == "INVALID_STATE", gagal.text


def _draf_berisi_item(world: World) -> str:
    plan = make_daily_plan(world, status="DRAFT", days_from_today=1)
    add_item(plan, world, "Titik uji")
    return plan


def test_ajukan_bersamaan_hanya_satu_sukses(client, world: World):
    plan = _draf_berisi_item(world)
    pm = world.headers(client, "pm")
    hasil = dua_bersamaan(lambda _: client.post(f"/work-plans/daily/{plan}/submit", headers=pm))
    _satu_200_satu_409(hasil)
    assert _status(plan) == "SUBMITTED"


def test_ajukan_yang_tertahan_dapat_409_dan_tidak_menimpa(client, world: World):
    plan = _draf_berisi_item(world)
    pm = world.headers(client, "pm")
    hasil = tahan_lalu_ubah(
        "UPDATE work_plan_daily SET status = 'ONGOING' WHERE daily_plan_id = %s", (plan,),
        lambda: client.post(f"/work-plans/daily/{plan}/submit", headers=pm),
    )
    assert hasil.status_code == 409, hasil.text
    assert _status(plan) == "ONGOING"


def test_mulai_bersamaan_hanya_satu_sukses(client, world: World):
    plan = make_daily_plan(world, status="APPROVED", days_from_today=0)
    check_in(client, world, "leader")
    leader = world.headers(client, "leader")
    hasil = dua_bersamaan(lambda _: client.post(f"/work-plans/daily/{plan}/start", headers=leader))
    _satu_200_satu_409(hasil)
    assert _status(plan) == "ONGOING"


def test_mulai_yang_tertahan_dapat_409_dan_tidak_menimpa(client, world: World):
    plan = make_daily_plan(world, status="APPROVED", days_from_today=0)
    check_in(client, world, "leader")
    leader = world.headers(client, "leader")
    hasil = tahan_lalu_ubah(
        "UPDATE work_plan_daily SET status = 'COMPLETED' WHERE daily_plan_id = %s", (plan,),
        lambda: client.post(f"/work-plans/daily/{plan}/start", headers=leader),
    )
    assert hasil.status_code == 409, hasil.text
    assert _status(plan) == "COMPLETED"


def _siap_ditutup(client, world: World) -> str:
    plan = make_daily_plan(world, status="ONGOING", days_from_today=0)
    report = client.post(f"/work-plans/daily/{plan}/report", headers=world.headers(client, "leader"),
                         json={"summary": "Pekerjaan selesai", "photos_json": []})
    assert report.status_code == 201, report.text
    return plan


def test_tutup_bersamaan_hanya_satu_sukses(client, world: World):
    plan = _siap_ditutup(client, world)
    leader = world.headers(client, "leader")
    hasil = dua_bersamaan(lambda _: client.post(f"/work-plans/daily/{plan}/complete", headers=leader))
    _satu_200_satu_409(hasil)
    assert _status(plan) == "COMPLETED"


def test_tutup_yang_tertahan_dapat_409_dan_tidak_menimpa(client, world: World):
    plan = _siap_ditutup(client, world)
    leader = world.headers(client, "leader")
    hasil = tahan_lalu_ubah(
        "UPDATE work_plan_daily SET status = 'DRAFT' WHERE daily_plan_id = %s", (plan,),
        lambda: client.post(f"/work-plans/daily/{plan}/complete", headers=leader),
    )
    assert hasil.status_code == 409, hasil.text
    assert _status(plan) == "DRAFT"


def test_setujui_massal_bersamaan_tiap_jadwal_disetujui_sekali(client, world: World):
    plans = [make_daily_plan(world, status="SUBMITTED", days_from_today=hari) for hari in (1, 2)]
    for nomor, plan in enumerate(plans):
        add_item(plan, world, f"Titik uji {nomor}")
    pm = world.headers(client, "pm")
    hasil = dua_bersamaan(lambda _: client.post("/work-plans/daily/approve", headers=pm,
                                                json={"daily_plan_ids": plans}))
    assert all(r.status_code == 200 for r in hasil), [r.text for r in hasil]
    disetujui = [pid for r in hasil for pid in r.json()["approved"]]
    assert sorted(disetujui) == sorted(plans), hasil[0].text + hasil[1].text
    assert all(_status(plan) == "APPROVED" for plan in plans)
