"""Klien ISAPI untuk MENARIK riwayat event dari perangkat Hikvision (hanya baca).

- HTTP Digest (kredensial dari argumen; tidak pernah dicetak/di-log, `repr` menyamarkan).
- Rentang dipotong jendela 7 hari, paginasi `searchResultPosition` sampai status bukan MORE, jeda antar permintaan,
  ulang+backoff untuk galat sementara, timeout eksplisit, bisa dilanjutkan lewat `PullCursor`.
- Berbentuk generator async: tidak pernah memuat seluruh riwayat (puluhan ribu event) sekaligus.
- `dry_run`: hanya menghitung dan mencari tanggal event tertua (mundur per jendela), tanpa menyimpan apa pun.
Nama field/path/status: PERLU VERIFIKASI dari perangkat asli (lihat `konstanta`).
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx

from ..schemas.event import ParsedEvent, ParseStatus
from ..schemas.tarik import DryRunResult, PullCursor
from . import konstanta as k
from .event_parser import parse_acs_item

log = logging.getLogger("vms.hikvision.tarik")

Sleep = Callable[[float], Awaitable[None]]


class IsapiError(Exception):
    """Galat tarik riwayat. `str(e)` aman dan berbahasa Indonesia awam."""


class IsapiAuthError(IsapiError):
    """Perangkat menolak nama pengguna/sandi (tidak diulang agar akun perangkat tidak terkunci)."""


class IsapiResponseError(IsapiError):
    """Jawaban perangkat rusak atau tidak masuk akal."""


class IsapiUnavailable(IsapiError):
    """Perangkat tidak terjangkau/lambat setelah beberapa kali mencoba."""


class PullClient:
    def __init__(
        self, base_url: str, username: str, password: str, *, device_serial: str,
        zona: timezone = k.ZONA_PERANGKAT_BAWAAN,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: httpx.Timeout | None = None,
        page_size: int = k.MAKS_HASIL_PER_HALAMAN,
        window_days: int = 7,
        delay_s: float = 1.0,
        max_retries: int = 3,
        backoff_base_s: float = 1.0,
        backoff_max_s: float = 30.0,
        sleep: Sleep = asyncio.sleep,
        minor: int = 0,
        minor_diizinkan: frozenset[int] = k.MINOR_VERIFIKASI_LOLOS,
    ) -> None:
        if not 1 <= page_size <= 1000 or not 1 <= window_days <= 31 or delay_s < 0 or max_retries < 0:
            raise ValueError("Pengaturan tarik riwayat tidak valid.")
        self._base_url = base_url.rstrip("/")
        self._auth = httpx.DigestAuth(username, password)
        self._device_serial = device_serial
        self._zona = zona
        self._transport = transport
        self._timeout = timeout or httpx.Timeout(15.0, connect=3.0)
        self._page_size = page_size
        self._window = timedelta(days=window_days)
        self._delay_s = delay_s
        self._max_retries = max_retries
        self._backoff_base_s = backoff_base_s
        self._backoff_max_s = backoff_max_s
        self._sleep = sleep
        self._minor = minor
        self._minor_ok = minor_diizinkan
        self._pertama = True
        self.jumlah_permintaan = 0
        self.kursor: PullCursor | None = None
        self.dilewati: dict[str, int] = {}   # kode alasan -> jumlah butir tidak diolah (bukan verifikasi/rusak)

    def __repr__(self) -> str:
        return f"PullClient(base_url={self._base_url!r}, device_serial={self._device_serial!r}, kredensial=***)"

    # ------------------------------------------------------------ permintaan
    async def _jeda_wajar(self) -> None:
        if not self._pertama and self._delay_s > 0:
            await self._sleep(self._delay_s)
        self._pertama = False

    async def _kirim(self, http: httpx.AsyncClient, tubuh: dict[str, Any]) -> dict[str, Any]:
        await self._jeda_wajar()
        galat: IsapiError | None = None
        for percobaan in range(self._max_retries + 1):
            if percobaan:
                await self._sleep(min(self._backoff_max_s, self._backoff_base_s * 2 ** (percobaan - 1)))
            self.jumlah_permintaan += 1
            try:
                resp = await http.post(k.PATH_ACS_EVENT, json=tubuh)
            except (httpx.TimeoutException, httpx.TransportError):
                galat = IsapiUnavailable("Perangkat absensi tidak menjawab. Periksa kabel jaringan dan daya perangkat.")
                continue
            if resp.status_code in (401, 403):
                raise IsapiAuthError("Perangkat menolak akun yang dipakai. Periksa nama pengguna dan sandi perangkat.")
            if resp.status_code >= 500 or resp.status_code == 429:
                galat = IsapiUnavailable("Perangkat absensi sedang sibuk atau bermasalah.")
                continue
            if resp.status_code != 200:
                raise IsapiResponseError("Perangkat menjawab dengan cara yang tidak dikenali.")
            try:
                data = resp.json()
                acs = data["AcsEvent"]
                if not isinstance(acs, dict):
                    raise TypeError
            except (ValueError, KeyError, TypeError):
                galat = IsapiResponseError("Jawaban perangkat rusak atau tidak lengkap.")
                continue
            return acs
        assert galat is not None
        raise galat

    def _tubuh(self, search_id: str, posisi: int, maks: int, mulai: datetime, akhir: datetime) -> dict[str, Any]:
        return {"AcsEventCond": {
            "searchID": search_id, "searchResultPosition": posisi, "maxResults": maks,
            "major": k.MAJOR_AKSES, "minor": self._minor,
            "startTime": mulai.astimezone(self._zona).isoformat(timespec="seconds"),
            "endTime": akhir.astimezone(self._zona).isoformat(timespec="seconds"),
        }}

    def _http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(base_url=self._base_url, auth=self._auth, timeout=self._timeout,
                                 transport=self._transport)

    # ------------------------------------------------------------ jendela
    def _jendela(self, mulai: datetime, akhir: datetime) -> list[tuple[datetime, datetime]]:
        hasil: list[tuple[datetime, datetime]] = []
        a = mulai
        while a < akhir:
            b = min(a + self._window, akhir)
            hasil.append((a, b))
            a = b
        return hasil

    @staticmethod
    def _akhir_inklusif(b: datetime) -> datetime:
        return b - timedelta(seconds=1)

    async def _halaman_jendela(
        self, http: httpx.AsyncClient, a: datetime, b: datetime, posisi: int, maks: int,
    ) -> AsyncIterator[tuple[list[Any], int, int]]:
        """Hasilkan (butir, posisi_berikut, total) per halaman sampai habis."""
        search_id = uuid.uuid4().hex
        while True:
            acs = await self._kirim(http, self._tubuh(search_id, posisi, maks, a, self._akhir_inklusif(b)))
            status = acs.get("responseStatusStrg")
            total = acs.get("totalMatches", 0)
            butir = acs.get("InfoList") or []
            if (not isinstance(total, int) or isinstance(total, bool) or not isinstance(butir, list)
                    or status not in (k.STATUS_LAGI, k.STATUS_SELESAI, k.STATUS_KOSONG)):
                raise IsapiResponseError("Jawaban perangkat rusak atau tidak lengkap.")
            if status == k.STATUS_KOSONG or (not butir and status == k.STATUS_SELESAI):
                return
            if not butir:   # MORE tetapi kosong: berhenti agar tidak berputar tanpa akhir
                raise IsapiResponseError("Perangkat menyatakan masih ada data tetapi tidak mengirimkannya.")
            posisi += len(butir)
            yield butir, posisi, total
            if status != k.STATUS_LAGI:
                return

    # ------------------------------------------------------------ tarik
    async def tarik(
        self, mulai: datetime, akhir: datetime, *, lanjut: PullCursor | None = None,
        sekarang: datetime | None = None,
    ) -> AsyncIterator[ParsedEvent]:
        """Hasilkan event verifikasi lolos satu per satu (urut waktu naik per jendela).

        `self.kursor` diperbarui setelah satu halaman selesai dihasilkan: bila terputus, panggil lagi dengan
        `lanjut=client.kursor`; paling banyak satu halaman terulang (aman karena kunci unik di penyimpanan).
        """
        if mulai.tzinfo is None or akhir.tzinfo is None:
            raise ValueError("Rentang waktu harus memuat zona waktu.")
        async with self._http() as http:
            for a, b in self._jendela(mulai, akhir):
                posisi = 0
                if lanjut is not None:
                    if b <= lanjut.window_start:
                        continue
                    if a == lanjut.window_start:
                        posisi = lanjut.position
                async for butir, berikut, _total in self._halaman_jendela(http, a, b, posisi, self._page_size):
                    for item in butir:
                        hasil = parse_acs_item(item, device_serial=self._device_serial, zona=self._zona,
                                               minor_diizinkan=self._minor_ok, sekarang=sekarang)
                        if hasil.status is ParseStatus.OK and hasil.event is not None:
                            yield hasil.event
                        else:
                            self.dilewati[hasil.kode] = self.dilewati.get(hasil.kode, 0) + 1
                    self.kursor = PullCursor(a, berikut)
                self.kursor = PullCursor(b, 0, selesai=b >= akhir)
        log.info("tarik selesai perangkat=%s permintaan=%d", self._device_serial, self.jumlah_permintaan)

    # ------------------------------------------------------------ dry-run
    async def dry_run(
        self, mulai: datetime, akhir: datetime, *, berhenti_setelah_kosong: int = 8,
    ) -> DryRunResult:
        """Hitung total event dan cari yang tertua, mundur per jendela dari `akhir`. Tidak menyimpan apa pun.

        Berhenti bila `berhenti_setelah_kosong` jendela berturut-turut kosong SETELAH ada data (atau mencapai `mulai`).
        """
        if mulai.tzinfo is None or akhir.tzinfo is None:
            raise ValueError("Rentang waktu harus memuat zona waktu.")
        total = diperiksa = 0
        kosong_berturut = 0
        jendela_terisi: tuple[datetime, datetime] | None = None
        awal_permintaan = self.jumlah_permintaan
        async with self._http() as http:
            for a, b in reversed(self._jendela(mulai, akhir)):
                diperiksa += 1
                cacah = 0
                async for _butir, _p, tot in self._halaman_jendela(http, a, b, 0, 1):
                    cacah = tot
                    break
                total += cacah
                if cacah:
                    jendela_terisi, kosong_berturut = (a, b), 0
                elif jendela_terisi is not None:
                    kosong_berturut += 1
                    if kosong_berturut >= berhenti_setelah_kosong:
                        break
            tertua: datetime | None = None
            if jendela_terisi is not None:
                a, b = jendela_terisi
                async for butir, _p, _t in self._halaman_jendela(http, a, b, 0, self._page_size):
                    for item in butir:
                        hasil = parse_acs_item(item, device_serial=self._device_serial, zona=self._zona,
                                               minor_diizinkan=self._minor_ok)
                        if hasil.event is not None and (tertua is None or hasil.event.event_time < tertua):
                            tertua = hasil.event.event_time
        return DryRunResult(total, tertua, diperiksa, self.jumlah_permintaan - awal_permintaan)
