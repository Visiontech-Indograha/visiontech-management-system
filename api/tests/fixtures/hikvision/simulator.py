"""Simulator perangkat Hikvision untuk tes (transport httpx tiruan, tanpa jaringan).

CATATAN: berdasarkan dokumentasi Hikvision, belum dari perangkat; ganti dengan tangkapan asli.
Data sintetis deterministik: `karyawan` x `hari` x 4 tap/hari (masuk, istirahat, masuk, pulang). Nomor urut event
berurutan menurut waktu. Campuran: wajah (75), kartu (1), sidik jari (38), wajah tak dikenal (76, tanpa nomor karyawan),
dan event pintu (21). Semua nilai minor di sini PERLU VERIFIKASI dari perangkat asli.
"""
from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

import httpx

WIB = timezone(timedelta(hours=7))
REALM = "DS-K1T343MX-simulasi"
MINOR_TIDAK_DIKENAL = 76
MINOR_PINTU = 21
TAP_PER_HARI = 4
_JAM_TAP = (7 * 3600 + 30 * 60, 12 * 3600, 13 * 3600, 17 * 3600)   # detik sejak 00:00


@dataclass
class Gangguan:
    respons_rusak_pada: set[int] = field(default_factory=set)   # nomor permintaan (1-based) -> badan bukan JSON
    timeout_pada: set[int] = field(default_factory=set)
    status_5xx_pada: set[int] = field(default_factory=set)
    tolak_auth: bool = False          # selalu 401 walau kredensial benar
    duplikat_tiap: int = 0            # >0: setiap butir ke-N tampil dua kali berurutan (nomor urut sama)
    more_kosong: bool = False         # halaman kedua dst: MORE tetapi tanpa butir


class PerangkatSimulasi:
    def __init__(self, *, mulai: datetime, hari: int = 365, karyawan: int = 43, serial: str = "DS-SIM-0001",
                 user: str = "admin", password: str = "sandi-uji", batas_halaman: int = 30,
                 gangguan: Gangguan | None = None) -> None:
        self.mulai = mulai.astimezone(WIB).replace(hour=0, minute=0, second=0, microsecond=0)
        self.hari, self.karyawan = hari, karyawan
        self.serial, self._user, self._pw, self.batas = serial, user, password, batas_halaman
        self.g = gangguan or Gangguan()
        self.permintaan: list[dict[str, int | str]] = []
        self.jumlah = 0
        self._cache_hari: dict[int, list[dict[str, object]]] = {}
        self._cache_jendela: tuple[tuple[str, str, int], list[dict[str, object]]] | None = None

    # ---------------------------------------------------------------- data
    @property
    def total_event(self) -> int:
        return self.hari * self.karyawan * TAP_PER_HARI

    def _jenis(self, emp: int, hari: int, tap: int) -> tuple[int, bool]:
        """(minor, punya_nomor_karyawan) deterministik."""
        x = (emp * 7 + hari * 3 + tap) % 20
        if x == 0:
            return MINOR_TIDAK_DIKENAL, False
        if x == 1:
            return MINOR_PINTU, False
        if x % 5 == 2:
            return 1, True
        if x == 3:
            return 38, True
        return 75, True

    def _event_hari(self, h: int) -> list[dict[str, object]]:
        if h in self._cache_hari:
            return self._cache_hari[h]
        mentah = []
        for emp in range(1, self.karyawan + 1):
            for tap in range(TAP_PER_HARI):
                detik = _JAM_TAP[tap] + (emp * 37 + h * 11 + tap * 5) % 1800
                mentah.append((detik, emp, tap))
        mentah.sort()
        hasil: list[dict[str, object]] = []
        dasar = self.mulai + timedelta(days=h)
        for rank, (detik, emp, tap) in enumerate(mentah):
            minor, punya = self._jenis(emp, h, tap)
            item: dict[str, object] = {
                "major": 5, "minor": minor,
                "time": (dasar + timedelta(seconds=detik)).isoformat(timespec="seconds"),
                "serialNo": h * len(mentah) + rank + 1,
                "currentVerifyMode": "cardOrFace" if minor != 38 else "fp",
                "cardReaderNo": 1, "doorNo": 1,
            }
            if punya:
                item["employeeNoString"] = f"EMP{emp:04d}"
                item["name"] = f"Karyawan Uji {emp}"
                if minor == 1:
                    item["cardNo"] = f"{1000 + emp}"
            hasil.append(item)
        self._cache_hari = {h: hasil}   # simpan satu hari saja (memori kecil)
        return hasil

    def _cocok(self, a: datetime, b: datetime, minor: int, major: int) -> list[dict[str, object]]:
        kunci = (a.isoformat(), b.isoformat(), minor * 100 + major)
        if self._cache_jendela and self._cache_jendela[0] == kunci:
            return self._cache_jendela[1]
        hasil: list[dict[str, object]] = []
        h0 = max(0, (a.astimezone(WIB) - self.mulai).days)
        h1 = min(self.hari - 1, (b.astimezone(WIB) - self.mulai).days)
        for h in range(h0, h1 + 1):
            for it in self._event_hari(h):
                t = datetime.fromisoformat(str(it["time"]))
                if a <= t <= b and it["major"] == major and (minor == 0 or it["minor"] == minor):
                    hasil.append(it)
        if self.g.duplikat_tiap:
            ganda: list[dict[str, object]] = []
            for i, it in enumerate(hasil, 1):
                ganda.append(it)
                if i % self.g.duplikat_tiap == 0:
                    ganda.append(dict(it))
            hasil = ganda
        self._cache_jendela = (kunci, hasil)
        return hasil

    # ---------------------------------------------------------------- HTTP
    def _auth_ok(self, request: httpx.Request) -> bool:
        h = request.headers.get("authorization", "")
        if not h.lower().startswith("digest "):
            return False
        f = {m[0]: m[1] or m[2] for m in re.findall(r'(\w+)=(?:"([^"]*)"|([^,\s]+))', h)}
        md5 = lambda s: hashlib.md5(s.encode(), usedforsecurity=False).hexdigest()  # noqa: E731
        ha1 = md5(f"{self._user}:{REALM}:{self._pw}")
        ha2 = md5(f"{request.method}:{f.get('uri', '')}")
        ekspektasi = md5(f"{ha1}:{f.get('nonce')}:{f.get('nc')}:{f.get('cnonce')}:{f.get('qop')}:{ha2}")
        return f.get("username") == self._user and f.get("response") == ekspektasi

    def handler(self, request: httpx.Request) -> httpx.Response:
        if self.g.tolak_auth or not self._auth_ok(request):
            return httpx.Response(401, headers={
                "WWW-Authenticate": f'Digest realm="{REALM}", qop="auth", nonce="abc123nonce", algorithm=MD5'})
        self.jumlah += 1
        n = self.jumlah
        if n in self.g.timeout_pada:
            raise httpx.ReadTimeout("simulasi timeout", request=request)
        if n in self.g.status_5xx_pada:
            return httpx.Response(503, text="sibuk")
        if n in self.g.respons_rusak_pada:
            return httpx.Response(200, text="<html>bukan json{")
        cond = json.loads(request.content)["AcsEventCond"]
        a, b = datetime.fromisoformat(cond["startTime"]), datetime.fromisoformat(cond["endTime"])
        cocok = self._cocok(a, b, int(cond["minor"]), int(cond["major"]))
        pos, maks = int(cond["searchResultPosition"]), min(int(cond["maxResults"]), self.batas)
        self.permintaan.append({"n": n, "pos": pos, "maks": maks, "mulai": cond["startTime"], "akhir": cond["endTime"]})
        halaman = list(cocok[pos:pos + maks])
        if not cocok:
            status = "NO MATCH"
        elif pos + maks < len(cocok):
            status = "MORE"
        else:
            status = "OK"
        if self.g.more_kosong and pos > 0:
            status, halaman = "MORE", []
        return httpx.Response(200, json={"AcsEvent": {
            "searchID": cond["searchID"], "totalMatches": len(cocok), "responseStatusStrg": status,
            "numOfMatches": len(halaman), "InfoList": halaman}})

    def transport(self) -> httpx.MockTransport:
        return httpx.MockTransport(self.handler)
