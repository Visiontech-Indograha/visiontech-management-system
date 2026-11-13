"""Pengingat dokumen kendaraan/SIM: tahap, batas tanggal, idempotensi, penerima, dokumen diganti, dry-run."""
from __future__ import annotations

import asyncio
import uuid
from datetime import date, timedelta
from typing import Any

import pytest

from app.database.session import AsyncSessionLocal
from app.modules.vehicle_documents.services.reminder_service import Ringkasan, hitung_tahap, jalankan
from tests.conftest import World, requires_db, sync_query

HARI = date(2026, 12, 1)


@pytest.mark.parametrize(("sisa", "tahap"), [
    (45, None), (31, None), (30, "T30"), (29, None), (22, None), (21, "T21"), (15, None), (14, "T14"),
    (10, None), (8, None), (7, "DAILY"), (3, "DAILY"), (0, "DAILY"), (-1, "DAILY"), (-30, "DAILY"), (-31, None),
])
def test_tahap_dan_batas_tanggal(sisa: int, tahap: str | None) -> None:
    assert hitung_tahap(sisa, [30, 21, 14], 7) == tahap


def _jalankan(hari: date, kantor: str, dry: bool = False) -> Ringkasan:
    async def go() -> Ringkasan:
        async with AsyncSessionLocal() as s:
            r = await jalankan(s, today=hari, dry_run=dry, office_id=kantor)
            await s.commit()
            return r
    return asyncio.run(go())


def _kendaraan(world: World, tipe: str, jatuh_tempo: date, status: str = "active") -> str:
    vid = str(sync_query(
        "INSERT INTO vehicle (office_id, division_id, vehicle_type, name, number_plate) "
        "VALUES (%s, %s, 'Car', 'Mobil uji', %s) RETURNING vehicle_id",
        (world.org_id, world.unit_id, f"UJ{uuid.uuid4().hex[:8].upper()}"))[0][0])
    _dokumen(world, vid, tipe, jatuh_tempo, status)
    return vid


def _dokumen(world: World, vid: str, tipe: str, jatuh_tempo: date, status: str = "active") -> str:
    return str(sync_query(
        "INSERT INTO vehicle_document (office_id, vehicle_id, doc_type_code, expired_on, status) "
        "VALUES (%s, %s, %s, %s, %s) RETURNING vehicle_document_id",
        (world.org_id, vid, tipe, jatuh_tempo, status))[0][0])


def _notif(user_id: str) -> int:
    return int(sync_query("SELECT count(*) FROM notification WHERE user_id = %s AND kind = 'DOC_EXPIRY'",
                          (user_id,))[0][0])


@pytest.fixture
def siap(world: World, other_world: World) -> World:
    world.add_person("hse", "HSE")
    other_world.add_person("hse", "HSE")
    return world


@requires_db
def test_penerima_per_peran_dan_idempoten(siap: World, other_world: World) -> None:
    w = siap
    vid = _kendaraan(w, "STNK", HARI + timedelta(days=30))
    sync_query("INSERT INTO vehicle_driver (office_id, vehicle_id, employee_id) VALUES (%s, %s, %s)",
               (w.org_id, vid, w.employees["member"]))
    _jalankan(HARI, w.org_id)
    assert _notif(w.users["hse"]) == 1 and _notif(w.users["ops"]) == 1 and _notif(w.users["member"]) == 1
    assert _notif(w.users["hr"]) == 0 and _notif(w.users["leader"]) == 0 and _notif(w.users["admin"]) == 0
    assert _notif(other_world.users["hse"]) == 0 and _notif(other_world.users["ops"]) == 0
    ulang = _jalankan(HARI, w.org_id)  # jalan kedua di hari yang sama: tidak ada kiriman ganda
    assert _notif(w.users["hse"]) == 1 and _notif(w.users["member"]) == 1
    assert ulang.dilewati_sudah_terkirim >= 1
    assert sync_query("SELECT count(*) FROM document_reminder WHERE office_id = %s", (w.org_id,))[0][0] == 1


@requires_db
def test_harian_sekali_per_hari_dan_lewat_tempo(siap: World) -> None:
    w = siap
    _kendaraan(w, "KIR", HARI + timedelta(days=5))
    _jalankan(HARI, w.org_id)
    _jalankan(HARI, w.org_id)
    assert _notif(w.users["hse"]) == 1
    _jalankan(HARI + timedelta(days=1), w.org_id)
    assert _notif(w.users["hse"]) == 2
    _jalankan(HARI + timedelta(days=9), w.org_id)  # sudah lewat tempo 4 hari: tetap harian
    assert _notif(w.users["hse"]) == 3


@requires_db
def test_di_luar_hari_pengingat_tidak_mengirim(siap: World) -> None:
    w = siap
    _kendaraan(w, "PAJAK", HARI + timedelta(days=25))
    _jalankan(HARI, w.org_id)
    assert _notif(w.users["hse"]) == 0


@requires_db
def test_dokumen_diganti_berhenti_mengingatkan_dan_dry_run(siap: World) -> None:
    w = siap
    vid = _kendaraan(w, "STNK", HARI + timedelta(days=21), status="replaced")
    _dokumen(w, vid, "ASURANSI", HARI + timedelta(days=21))
    r = _jalankan(HARI, w.org_id, dry=True)
    assert r.kandidat >= 1 and _notif(w.users["hse"]) == 0
    assert sync_query("SELECT count(*) FROM document_reminder WHERE office_id = %s", (w.org_id,))[0][0] == 0
    _jalankan(HARI, w.org_id)
    assert _notif(w.users["hse"]) == 1  # hanya ASURANSI; STNK 'replaced' tidak
    rows: Any = sync_query("SELECT title FROM notification WHERE user_id = %s AND kind = 'DOC_EXPIRY'",
                           (w.users["hse"],))
    assert "Asuransi" in rows[0][0]


@requires_db
def test_sim_karyawan_ke_pemilik_dan_hse(siap: World) -> None:
    w = siap
    sync_query(
        "INSERT INTO employee_file (employee_id, type, path_file, active_at, expired_at) "
        "VALUES (%s, 'SIM_B', 'uji/sim.jpg', now(), %s)",
        (w.employees["member"], f"{(HARI + timedelta(days=14)).isoformat()} 12:00+07"))
    _jalankan(HARI, w.org_id)
    assert _notif(w.users["member"]) == 1 and _notif(w.users["hse"]) == 1 and _notif(w.users["leader"]) == 0
