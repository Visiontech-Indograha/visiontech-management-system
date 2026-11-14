"""Servis `hikvision-impor-ekspor` terhadap DB uji: idempoten, rentang, tak terpetakan, dry-run."""
from __future__ import annotations

import uuid
from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path

import pytest

from app.core.config import settings
from app.database.session import make_engine
from app.modules.hikvision.services.impor_ekspor import ImporError
from app.modules.hikvision.services.impor_service import RingkasanImpor, jalankan_impor
from tests.conftest import SeededUser, requires_db, sync_query

pytestmark = [requires_db, pytest.mark.anyio]

FIX = Path(__file__).parents[2] / "fixtures" / "hikvision" / "ekspor_ivms"


@pytest.fixture()
def serial(make_user: Callable[..., SeededUser]) -> Iterator[str]:
    s = f"DS-IMP-{uuid.uuid4().hex[:8].upper()}"
    office = sync_query("SELECT office_id FROM office WHERE is_main_office AND delete_at IS NULL")[0][0]
    d = sync_query(
        "INSERT INTO hikvision_device (office_id, name, ip_address, serial_no, token_hash, mode) "
        "VALUES (%s, 'Pintu uji', '192.0.2.11', %s, %s, 'SHADOW') RETURNING device_id",
        (office, s, uuid.uuid4().hex + uuid.uuid4().hex))[0][0]
    u = make_user("ADMIN")
    emp = sync_query("SELECT employee_id FROM users WHERE user_id = %s", (u.user_id,))[0][0]
    sync_query("INSERT INTO hikvision_employee_map (device_id, employee_no_string, employee_id) "
               "VALUES (%s, '1001', %s)", (d, emp))
    yield s
    sync_query("DELETE FROM hikvision_event WHERE device_id = %s", (d,))
    sync_query("DELETE FROM hikvision_employee_map WHERE device_id = %s", (d,))
    sync_query("DELETE FROM hikvision_device WHERE device_id = %s", (d,))


async def _impor(serial: str, berkas: str, *, dry_run: bool, dari: date | None = None,
                 sampai: date | None = None) -> RingkasanImpor:
    engine = make_engine(settings.DATABASE_URL)
    try:
        return await jalankan_impor(engine, berkas=FIX / berkas, perangkat=serial, dry_run=dry_run,
                                  dari=dari, sampai=sampai)
    finally:
        await engine.dispose()


def _jumlah(serial: str) -> int:
    return int(sync_query("SELECT count(*) FROM hikvision_event e JOIN hikvision_device d USING (device_id) "
                          "WHERE d.serial_no = %s", (serial,))[0][0])


async def test_impor_lalu_ulang_idempoten(serial: str) -> None:
    r1 = await _impor(serial, "inggris_tanggal_jam.csv", dry_run=False)
    assert (r1.baris_dibaca, r1.event_baru, r1.duplikat) == (3, 3, 0)
    assert r1.event_tak_terpetakan == 1 and r1.id_tak_terpetakan == 1  # 1002 tak dipetakan
    assert r1.per_bulan == {"2026-10": 3} and r1.tanggal_tertua == "2026-10-01"
    r2 = await _impor(serial, "inggris_tanggal_jam.csv", dry_run=False)
    assert (r2.event_baru, r2.duplikat) == (0, 3)
    assert _jumlah(serial) == 3
    row = sync_query("SELECT sumber, employee_id IS NOT NULL, payload->>'impor' FROM hikvision_event e "
                     "JOIN hikvision_device d USING (device_id) WHERE d.serial_no = %s "
                     "AND employee_no_string = '1001' LIMIT 1", (serial,))[0]
    assert row[0] == "PULL" and row[1] is True and row[2] == "IVMS4200"


async def test_dry_run_tidak_menulis(serial: str) -> None:
    r = await _impor(serial, "inggris_tanggal_jam.csv", dry_run=True)
    assert r.event_baru == 3 and _jumlah(serial) == 0


async def test_rentang_tanggal(serial: str) -> None:
    r = await _impor(serial, "inggris_tanggal_jam.csv", dry_run=False, dari=date(2026, 10, 2),
                     sampai=date(2026, 10, 2))
    assert (r.baris_dibaca, r.di_luar_rentang, r.event_baru) == (1, 2, 1)
    with pytest.raises(ImporError, match="--dari"):
        await _impor(serial, "inggris_tanggal_jam.csv", dry_run=True, dari=date(2026, 11, 1),
                     sampai=date(2026, 10, 1))


async def test_perangkat_tak_terdaftar() -> None:
    with pytest.raises(ImporError, match="tidak terdaftar"):
        await _impor("TIDAK-ADA", "inggris_tanggal_jam.csv", dry_run=True)
