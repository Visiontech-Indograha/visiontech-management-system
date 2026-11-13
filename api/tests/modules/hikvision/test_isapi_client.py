"""Klien tarik ISAPI terhadap simulator (tanpa jaringan, tanpa tidur nyata: jam/sleep disuntikkan)."""
from __future__ import annotations

import inspect
import tracemalloc
from datetime import timedelta

import pytest

from app.modules.hikvision.schemas import PullCursor
from app.modules.hikvision.services import (
    IsapiAuthError,
    IsapiResponseError,
    IsapiUnavailable,
    PullClient,
)
from tests.fixtures.hikvision.simulator import WIB, Gangguan, PerangkatSimulasi

pytestmark = pytest.mark.anyio

from datetime import datetime  # noqa: E402

MULAI = datetime(2025, 11, 14, tzinfo=WIB)


class JamPalsu:
    def __init__(self) -> None:
        self.tidur: list[float] = []

    async def sleep(self, d: float) -> None:
        self.tidur.append(d)


def buat(sim: PerangkatSimulasi, jam: JamPalsu, **kw) -> PullClient:
    opsi = {"device_serial": sim.serial, "transport": sim.transport(), "sleep": jam.sleep, "delay_s": 1.0,
            "backoff_base_s": 1.0, **kw}
    return PullClient("http://192.0.2.10", "admin", "sandi-uji", **opsi)  # type: ignore[arg-type]


def diharapkan(sim: PerangkatSimulasi, hari: int | None = None) -> int:
    n = 0
    for h in range(hari if hari is not None else sim.hari):
        for it in sim._event_hari(h):
            n += it["minor"] in (75, 1, 38)
    return n


async def test_paginasi_penuh_365_hari_dan_jeda():
    sim = PerangkatSimulasi(mulai=MULAI)
    jam = JamPalsu()
    c = buat(sim, jam)
    akhir = MULAI + timedelta(days=365)
    serial: list[int] = []
    async for e in c.tarik(MULAI, akhir):
        assert e.device_serial == sim.serial and e.major_event_type == 5
        serial.append(e.serial_no_event or 0)
    assert sim.total_event == 62780
    assert len(serial) == len(set(serial)) == diharapkan(sim)
    assert serial == sorted(serial)
    assert c.kursor is not None and c.kursor.selesai
    assert sum(c.dilewati.values()) == sim.total_event - len(serial)   # wajah tak dikenal/pintu disaring
    assert len({(p["mulai"]) for p in sim.permintaan}) == 53            # jendela 7 hari
    assert c.jumlah_permintaan == sim.jumlah
    assert jam.tidur == [1.0] * (c.jumlah_permintaan - 1)               # jeda diterapkan, tanpa tidur nyata


async def test_memori_aliran_bukan_daftar():
    sim = PerangkatSimulasi(mulai=MULAI)
    c = buat(sim, JamPalsu(), delay_s=0)
    gen = c.tarik(MULAI, MULAI + timedelta(days=365))
    assert inspect.isasyncgen(gen)
    tracemalloc.start()
    n = 0
    async for _ in gen:
        n += 1
    _, puncak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    assert n == diharapkan(sim)
    assert puncak < 20 * 1024 * 1024    # menyimpan 60 ribu event akan jauh di atas ini


async def test_resume_dari_kursor_tanpa_kehilangan():
    sim = PerangkatSimulasi(mulai=MULAI, hari=30)
    akhir = MULAI + timedelta(days=30)
    c1 = buat(sim, JamPalsu(), delay_s=0)
    sebagian: list[int] = []
    async for e in c1.tarik(MULAI, akhir):
        sebagian.append(e.serial_no_event or 0)
        if len(sebagian) == 500:
            break
    kursor = c1.kursor
    assert kursor is not None and not kursor.selesai and kursor.position > 0
    c2 = buat(sim, JamPalsu(), delay_s=0)
    sisa = [e.serial_no_event or 0 async for e in c2.tarik(MULAI, akhir, lanjut=kursor)]
    semua = set(sebagian) | set(sisa)
    assert len(semua) == diharapkan(sim)                 # tidak ada yang hilang
    assert len(set(sebagian) & set(sisa)) <= 30          # tumpang tindih paling banyak satu halaman
    assert isinstance(kursor, PullCursor)


async def test_dry_run_total_dan_tanggal_tertua_tanpa_menyimpan():
    sim = PerangkatSimulasi(mulai=MULAI)
    jam = JamPalsu()
    c = buat(sim, jam)
    akhir = MULAI + timedelta(days=365)
    hasil = await c.dry_run(MULAI - timedelta(days=500), akhir, berhenti_setelah_kosong=4)
    assert hasil.total_event == 62780
    pertama = min(e["time"] for e in sim._event_hari(0))
    assert hasil.event_tertua is not None and hasil.event_tertua.isoformat() >= pertama[:10]
    assert hasil.event_tertua.date() == MULAI.date()
    assert hasil.jendela_diperiksa == 53 + 4
    assert hasil.jumlah_permintaan < 200                  # hitung ringan, bukan membaca semua event


async def test_dry_run_tanpa_data():
    sim = PerangkatSimulasi(mulai=MULAI, hari=1)
    hasil = await buat(sim, JamPalsu()).dry_run(MULAI + timedelta(days=100), MULAI + timedelta(days=130))
    assert hasil.total_event == 0 and hasil.event_tertua is None


async def test_backoff_eksponensial_lalu_pulih():
    sim = PerangkatSimulasi(mulai=MULAI, hari=2, gangguan=Gangguan(status_5xx_pada={1, 2}))
    jam = JamPalsu()
    c = buat(sim, jam, delay_s=0)
    n = [e async for e in c.tarik(MULAI, MULAI + timedelta(days=2))]
    assert len(n) == diharapkan(sim)
    assert jam.tidur[:2] == [1.0, 2.0]


async def test_ulang_habis_menjadi_galat_ramah():
    sim = PerangkatSimulasi(mulai=MULAI, hari=2, gangguan=Gangguan(status_5xx_pada={1, 2, 3}))
    c = buat(sim, JamPalsu(), max_retries=2)
    with pytest.raises(IsapiUnavailable) as e:
        _ = [x async for x in c.tarik(MULAI, MULAI + timedelta(days=2))]
    assert "Perangkat" in str(e.value) and "Traceback" not in str(e.value)


async def test_timeout_dipulihkan_dan_habis():
    sim = PerangkatSimulasi(mulai=MULAI, hari=2, gangguan=Gangguan(timeout_pada={1}))
    n = [e async for e in buat(sim, JamPalsu(), delay_s=0).tarik(MULAI, MULAI + timedelta(days=2))]
    assert len(n) == diharapkan(sim)
    sim2 = PerangkatSimulasi(mulai=MULAI, hari=2, gangguan=Gangguan(timeout_pada=set(range(1, 50))))
    with pytest.raises(IsapiUnavailable):
        _ = [e async for e in buat(sim2, JamPalsu(), max_retries=2).tarik(MULAI, MULAI + timedelta(days=2))]


async def test_respons_rusak_diulang_dan_more_kosong_dihentikan():
    sim = PerangkatSimulasi(mulai=MULAI, hari=2, gangguan=Gangguan(respons_rusak_pada={1}))
    n = [e async for e in buat(sim, JamPalsu(), delay_s=0).tarik(MULAI, MULAI + timedelta(days=2))]
    assert len(n) == diharapkan(sim)
    sim2 = PerangkatSimulasi(mulai=MULAI, hari=2, gangguan=Gangguan(more_kosong=True))
    with pytest.raises(IsapiResponseError):
        _ = [e async for e in buat(sim2, JamPalsu(), delay_s=0).tarik(MULAI, MULAI + timedelta(days=2))]


async def test_401_tidak_diulang_dan_sandi_tidak_bocor():
    jam = JamPalsu()
    sim = PerangkatSimulasi(mulai=MULAI, hari=2, gangguan=Gangguan(tolak_auth=True))
    with pytest.raises(IsapiAuthError) as e:
        _ = [x async for x in buat(sim, jam).tarik(MULAI, MULAI + timedelta(days=2))]
    assert "sandi-uji" not in str(e.value) and jam.tidur == []
    salah = PerangkatSimulasi(mulai=MULAI, hari=2, password="lain")
    with pytest.raises(IsapiAuthError):
        _ = [x async for x in buat(salah, JamPalsu()).tarik(MULAI, MULAI + timedelta(days=2))]
    assert "sandi-uji" not in repr(buat(sim, jam)) and "admin" not in repr(buat(sim, jam))


async def test_duplikat_dari_perangkat_unik_di_penyimpanan():
    sim = PerangkatSimulasi(mulai=MULAI, hari=3, gangguan=Gangguan(duplikat_tiap=5))
    serial = [e.serial_no_event async for e in buat(sim, JamPalsu(), delay_s=0).tarik(MULAI, MULAI + timedelta(days=3))]
    assert len(serial) > len(set(serial))                 # klien tidak menyembunyikan duplikat
    assert len(set(serial)) == diharapkan(sim)            # kunci (serial, serialNo) cukup untuk dedup


async def test_pengaturan_tidak_valid():
    sim = PerangkatSimulasi(mulai=MULAI, hari=1)
    with pytest.raises(ValueError):
        buat(sim, JamPalsu(), page_size=0)
    with pytest.raises(ValueError):
        c = buat(sim, JamPalsu())
        _ = [e async for e in c.tarik(datetime(2025, 1, 1), datetime(2025, 2, 1))]  # noqa: DTZ001
