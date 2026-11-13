"""CLI/servis `hikvision-tarik` terhadap simulator (62 ribu event, tanpa jaringan). Butuh DB uji."""
from __future__ import annotations

import uuid
from collections.abc import Iterator
from datetime import datetime, timedelta

import pytest

from app.core.config import settings
from app.database.session import make_engine
from app.modules.hikvision.repositories.hikvision_repository import HikvisionRepository
from app.modules.hikvision.services import IsapiUnavailable
from app.modules.hikvision.services.tarik_service import (
    UKURAN_KELOMPOK,
    TarikError,
    kredensial,
    nama_variabel,
    tarik_riwayat,
)
from tests.conftest import requires_db, sync_query
from tests.fixtures.hikvision.simulator import WIB, Gangguan, PerangkatSimulasi

pytestmark = [requires_db, pytest.mark.anyio]

MULAI = datetime(2025, 11, 14, tzinfo=WIB)
AKHIR = MULAI + timedelta(days=365)


class JamPalsu:
    def __init__(self) -> None:
        self.tidur: list[float] = []

    async def sleep(self, d: float) -> None:
        self.tidur.append(d)


@pytest.fixture()
def serial() -> Iterator[str]:
    s = f"DS-SIM-{uuid.uuid4().hex[:8].upper()}"
    office = sync_query("SELECT office_id FROM office WHERE is_main_office AND delete_at IS NULL")[0][0]
    row = sync_query(
        "INSERT INTO hikvision_device (office_id, name, ip_address, serial_no, token_hash, mode) "
        "VALUES (%s, 'Pintu uji', '192.0.2.10', %s, %s, 'SHADOW') RETURNING device_id",
        (office, s, uuid.uuid4().hex + uuid.uuid4().hex))
    yield s
    d = row[0][0]
    sync_query("DELETE FROM hikvision_event WHERE device_id = %s", (d,))
    sync_query("DELETE FROM hikvision_employee_map WHERE device_id = %s", (d,))
    sync_query("DELETE FROM hikvision_device WHERE device_id = %s", (d,))


def _env(s: str) -> dict[str, str]:
    return {nama_variabel(s, "USER"): "admin", nama_variabel(s, "PASS"): "sandi-uji"}


def _tersimpan(s: str) -> int:
    return int(sync_query(
        "SELECT count(*) FROM hikvision_event e JOIN hikvision_device d USING (device_id) WHERE d.serial_no = %s",
        (s,))[0][0])


def _diharapkan(sim: PerangkatSimulasi) -> int:
    return sum(1 for h in range(sim.hari) for it in sim._event_hari(h) if it["minor"] in (75, 1, 38))


async def _jalan(s: str, sim: PerangkatSimulasi, jam: JamPalsu, **kw):
    engine = make_engine(settings.DATABASE_URL)
    try:
        opsi = {"serial": s, "mulai": MULAI, "akhir": AKHIR, "dry_run": False, "jeda": 1.0, "lanjutkan": False,
                "env": _env(s), "transport": sim.transport(), "base_url": "http://192.0.2.10", "sleep": jam.sleep}
        opsi.update(kw)
        return await tarik_riwayat(engine, **opsi)
    finally:
        await engine.dispose()


def test_nama_variabel_dan_kredensial_tidak_bocor() -> None:
    assert nama_variabel("DS-K1T343MX/01", "USER") == "HIKVISION_DS_K1T343MX_01_USER"
    with pytest.raises(TarikError) as e:
        kredensial("DS-X", {})
    assert "HIKVISION_DS_X_USER" in str(e.value) and "sandi" not in str(e.value).lower().replace("sandi perangkat", "")


async def test_dry_run_hitung_dan_tanggal_tertua_tanpa_simpan(serial) -> None:
    sim = PerangkatSimulasi(mulai=MULAI, serial=serial)
    hasil = await _jalan(serial, sim, JamPalsu(), dry_run=True)
    assert hasil.dry_run and hasil.total_event == sim.total_event == 62780
    assert hasil.event_tertua is not None
    tertua = datetime.fromisoformat(hasil.event_tertua)
    assert MULAI <= tertua < MULAI + timedelta(days=7)
    assert _tersimpan(serial) == 0


async def test_tarik_penuh_batch_idempoten_dan_ulang_tidak_menggandakan(serial, monkeypatch) -> None:
    ukuran: list[int] = []
    asli = HikvisionRepository.insert_events

    async def catat(self, device_id, sumber, rows):
        ukuran.append(len(rows))
        return await asli(self, device_id, sumber, rows)

    monkeypatch.setattr(HikvisionRepository, "insert_events", catat)
    sim = PerangkatSimulasi(mulai=MULAI, serial=serial)
    jam = JamPalsu()
    h1 = await _jalan(serial, sim, jam)
    n = _diharapkan(sim)
    assert (h1.baru, h1.duplikat) == (n, 0) and _tersimpan(serial) == n
    assert h1.dilewati == sim.total_event - n
    assert len(ukuran) > 1 and max(ukuran) <= UKURAN_KELOMPOK      # berkelompok dan memori terbatas
    assert len(ukuran) < n / 100                                   # bukan per baris
    assert jam.tidur and set(jam.tidur) == {1.0}                   # jeda dipakai (jam palsu, tanpa tidur nyata)
    h2 = await _jalan(serial, PerangkatSimulasi(mulai=MULAI, serial=serial), JamPalsu())
    assert (h2.baru, h2.duplikat) == (0, n) and _tersimpan(serial) == n
    assert sync_query("SELECT DISTINCT sumber FROM hikvision_event e JOIN hikvision_device d USING (device_id) "
                      "WHERE d.serial_no = %s", (serial,)) == [("PULL",)]


async def test_lanjutkan_setelah_putus(serial) -> None:
    rusak = PerangkatSimulasi(mulai=MULAI, serial=serial,
                              gangguan=Gangguan(status_5xx_pada=set(range(900, 910))))
    with pytest.raises(IsapiUnavailable):
        await _jalan(serial, rusak, JamPalsu())
    sebagian = _tersimpan(serial)
    assert 0 < sebagian < _diharapkan(rusak)
    sim = PerangkatSimulasi(mulai=MULAI, serial=serial)
    h = await _jalan(serial, sim, JamPalsu(), lanjutkan=True)
    assert h.dilanjutkan_dari is not None and _tersimpan(serial) == _diharapkan(sim)
    assert h.permintaan < 1700                                      # tidak mengulang dari awal tahun


async def test_perangkat_tak_terdaftar_dan_tanpa_kredensial(serial) -> None:
    sim = PerangkatSimulasi(mulai=MULAI, serial=serial)
    with pytest.raises(TarikError):
        await _jalan("DS-TAK-ADA", sim, JamPalsu())
    with pytest.raises(TarikError):
        await _jalan(serial, sim, JamPalsu(), env={})
