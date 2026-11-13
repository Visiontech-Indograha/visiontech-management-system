"""Parser event Hikvision (push multipart/JSON/XML dan butir hasil tarik ISAPI) menjadi `ParsedEvent`.

Murni (tanpa DB/jaringan), toleran terhadap variasi bentuk, ketat pada batas. Tidak pernah memegang embedding wajah.
Seluruh nama field/nilai berasal dari `konstanta` (PERLU VERIFIKASI dari tangkapan perangkat asli).
"""
from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable, Iterable
from datetime import UTC, datetime, timezone
from typing import Any

from app.core.time import utcnow

from ..schemas.event import ParsedEvent, ParseOutcome, ParseStatus
from . import konstanta as k

_BOUNDARY = re.compile(r'boundary="?([^";\s]+)"?', re.IGNORECASE)
_KONTROL = re.compile(r"[\x00-\x1f\x7f]")


class _Tolak(Exception):
    def __init__(self, kode: str, pesan: str) -> None:
        super().__init__(pesan)
        self.kode, self.pesan = kode, pesan


def _tolak(kode: str, pesan: str) -> ParseOutcome:
    return ParseOutcome(ParseStatus.DITOLAK, kode, pesan)


def _abaikan(kode: str, pesan: str) -> ParseOutcome:
    return ParseOutcome(ParseStatus.DIABAIKAN, kode, pesan)


# ---------------------------------------------------------------- pengambilan nilai
def _ambil(d: dict[str, Any], nama: Iterable[str]) -> Any:
    for n in nama:
        if n in d and d[n] not in (None, ""):
            return d[n]
    return None


def _ke_int(nilai: Any, label: str) -> int | None:
    if nilai is None:
        return None
    if isinstance(nilai, bool):
        raise _Tolak("DATA_TIDAK_VALID", f"Nilai {label} tidak valid.")
    if isinstance(nilai, int):
        return nilai
    if isinstance(nilai, str) and re.fullmatch(r"-?\d{1,18}", nilai.strip()):
        return int(nilai.strip())
    raise _Tolak("DATA_TIDAK_VALID", f"Nilai {label} tidak valid.")


def _ke_teks(nilai: Any, label: str, maks: int) -> str | None:
    if nilai is None:
        return None
    if isinstance(nilai, bool) or not isinstance(nilai, (str, int)):
        raise _Tolak("DATA_TIDAK_VALID", f"Nilai {label} tidak valid.")
    teks = str(nilai).strip()
    if not teks:
        return None
    if len(teks) > maks or _KONTROL.search(teks):
        raise _Tolak("DATA_TIDAK_VALID", f"Nilai {label} terlalu panjang atau berisi karakter tidak wajar.")
    return teks


def _ke_waktu(nilai: Any, zona: timezone, sekarang: datetime | None) -> datetime:
    if not isinstance(nilai, str) or not nilai.strip():
        raise _Tolak("FORMAT_RUSAK", "Waktu kejadian tidak ada.")
    try:
        waktu = datetime.fromisoformat(nilai.strip())
    except ValueError:
        raise _Tolak("FORMAT_RUSAK", "Format waktu kejadian tidak dikenali.") from None
    if waktu.tzinfo is None:
        waktu = waktu.replace(tzinfo=zona)
    terawal = datetime(*k.WAKTU_TERAWAL, tzinfo=UTC)
    if waktu < terawal or (sekarang is not None and waktu > sekarang + k.TOLERANSI_MASA_DEPAN):
        raise _Tolak("WAKTU_TIDAK_WAJAR", "Waktu kejadian tidak masuk akal (terlalu lama atau di masa depan).")
    return waktu


# ---------------------------------------------------------------- normalisasi
def _normalisasi(
    atas: dict[str, Any], blok: dict[str, Any], *, device_serial: str | None, ada_gambar: bool,
    zona: timezone, sekarang: datetime | None, minor_diizinkan: frozenset[int], gambar: bytes | None,
    catatan: list[str],
) -> ParseOutcome:
    jenis = _ambil(atas, k.F_JENIS_EVENT)
    if isinstance(jenis, str) and jenis.lower() in k.JENIS_HEARTBEAT:
        return _abaikan("HEARTBEAT", "Sinyal hidup perangkat, bukan absensi.")
    major = _ke_int(_ambil(blok, k.F_MAJOR), "jenis utama")
    minor = _ke_int(_ambil(blok, k.F_MINOR), "jenis rinci")
    if major is None or minor is None:
        return _abaikan("BUKAN_VERIFIKASI", "Event bukan verifikasi akses.")
    if major != k.MAJOR_AKSES or minor not in minor_diizinkan:
        return _abaikan("BUKAN_VERIFIKASI", "Event bukan verifikasi wajah, kartu, atau sidik jari yang lolos.")
    # Serial dari konfigurasi (token/klien) lebih tepercaya daripada isi kiriman.
    serial_perangkat = _ke_teks(
        device_serial or _ambil(atas, k.F_SERIAL_PERANGKAT) or _ambil(blok, k.F_SERIAL_PERANGKAT),
        "nomor seri perangkat", k.MAKS_PANJANG_SERIAL_PERANGKAT,
    )
    if not serial_perangkat:
        return _tolak("DATA_TIDAK_VALID", "Perangkat pengirim tidak dikenali.")
    karyawan = _ke_teks(_ambil(blok, k.F_KARYAWAN), "nomor karyawan", k.MAKS_PANJANG_PENGENAL)
    kartu = _ke_teks(_ambil(blok, k.F_KARTU), "nomor kartu", k.MAKS_PANJANG_PENGENAL)
    if not karyawan and not kartu:
        return _tolak("TANPA_PENGENAL", "Event tidak memuat nomor karyawan maupun nomor kartu.")
    waktu = _ke_waktu(_ambil(blok, k.F_WAKTU) or _ambil(atas, k.F_WAKTU), zona, sekarang)
    event = ParsedEvent(
        device_serial=serial_perangkat,
        serial_no_event=_ke_int(_ambil(blok, k.F_SERIAL_EVENT), "nomor urut event"),
        major_event_type=major, minor_event_type=minor, event_time=waktu,
        employee_no_string=karyawan, card_no=kartu,
        verify_mode=_ke_teks(_ambil(blok, k.F_MODE), "mode verifikasi", k.MAKS_PANJANG_MODE),
        ada_gambar=ada_gambar,
    )
    return ParseOutcome(ParseStatus.OK, "OK", "Event verifikasi diterima.", event, gambar, catatan)


def parse_acs_item(
    item: Any, *, device_serial: str, zona: timezone = k.ZONA_PERANGKAT_BAWAAN,
    minor_diizinkan: frozenset[int] = k.MINOR_VERIFIKASI_LOLOS, sekarang: datetime | None = None,
) -> ParseOutcome:
    """Satu butir `InfoList` hasil pencarian AcsEvent (bentuk datar: major, minor, time, ...)."""
    if not isinstance(item, dict):
        return _tolak("FORMAT_RUSAK", "Butir event dari perangkat tidak berbentuk benar.")
    try:
        return _normalisasi(item, item, device_serial=device_serial, ada_gambar=False, zona=zona,
                            sekarang=sekarang, minor_diizinkan=minor_diizinkan, gambar=None, catatan=[])
    except _Tolak as e:
        return _tolak(e.kode, e.pesan)


# ---------------------------------------------------------------- bentuk kiriman
def _xml_ke_dict(teks: bytes) -> dict[str, Any]:
    if b"<!doctype" in teks.lower() or b"<!entity" in teks.lower():
        raise _Tolak("FORMAT_RUSAK", "Kiriman XML ditolak karena memuat deklarasi yang tidak diizinkan.")
    try:
        akar = ET.fromstring(teks)  # DOCTYPE/ENTITY sudah ditolak di atas
    except ET.ParseError:
        raise _Tolak("FORMAT_RUSAK", "Kiriman XML rusak.") from None

    def bersih(tag: str) -> str:
        return tag.rsplit("}", 1)[-1]

    def ke(el: ET.Element) -> Any:
        anak = list(el)
        if not anak:
            return (el.text or "").strip()
        return {bersih(a.tag): ke(a) for a in anak}

    hasil = ke(akar)
    if not isinstance(hasil, dict):
        raise _Tolak("FORMAT_RUSAK", "Kiriman XML kosong.")
    if bersih(akar.tag) == k.BLOK_EVENT:
        hasil = {k.BLOK_EVENT: hasil}
    return hasil


def _teks_ke_dict(data: bytes) -> dict[str, Any]:
    awal = data.lstrip()[:1]
    try:
        if awal == b"{":
            hasil = json.loads(data.decode("utf-8"))
        elif awal == b"<":
            hasil = _xml_ke_dict(data)
        else:
            raise _Tolak("TIPE_TIDAK_DIDUKUNG", "Jenis kiriman tidak didukung (bukan JSON atau XML).")
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise _Tolak("FORMAT_RUSAK", "Isi kiriman rusak atau terpotong.") from None
    if not isinstance(hasil, dict):
        raise _Tolak("FORMAT_RUSAK", "Isi kiriman tidak berbentuk benar.")
    return hasil


def _pisah_multipart(body: bytes, boundary: str) -> list[tuple[dict[str, str], bytes]]:
    pemisah = b"--" + boundary.encode("ascii", "ignore")
    bagian: list[tuple[dict[str, str], bytes]] = []
    for potong in body.split(pemisah)[1:]:
        if potong.startswith(b"--"):
            break
        if potong.startswith(b"\r\n"):
            potong = potong[2:]
        elif potong.startswith(b"\n"):
            potong = potong[1:]
        kepala = data = b""
        for sep in (b"\r\n\r\n", b"\n\n"):
            i = potong.find(sep)
            if i >= 0:
                kepala, data = potong[:i], potong[i + len(sep):]
                break
        else:
            raise _Tolak("FORMAT_RUSAK", "Bagian kiriman tidak punya kepala yang benar.")
        data = data.removesuffix(b"\r\n") if data.endswith(b"\r\n") else data.removesuffix(b"\n")
        header: dict[str, str] = {}
        for baris in kepala.decode("latin-1").splitlines():
            nama, sep_, nilai = baris.partition(":")
            if sep_:
                header[nama.strip().lower()] = nilai.strip()
        bagian.append((header, data))
        if len(bagian) > k.MAKS_BAGIAN_MULTIPART:
            raise _Tolak("FORMAT_RUSAK", "Kiriman memuat terlalu banyak bagian.")
    if not bagian:
        raise _Tolak("FORMAT_RUSAK", "Kiriman multipart tidak memuat bagian apa pun.")
    return bagian


def parse_push(
    body: bytes, content_type: str | None, *, device_serial: str | None = None,
    zona: timezone = k.ZONA_PERANGKAT_BAWAAN,
    minor_diizinkan: frozenset[int] = k.MINOR_VERIFIKASI_LOLOS,
    sekarang: Callable[[], datetime] = utcnow,
) -> ParseOutcome:
    """Uraikan satu kiriman push. Tidak melempar galat karena isi kiriman; hasil selalu `ParseOutcome`."""
    if len(body) > k.MAKS_BYTE_KIRIMAN:
        return _tolak("TERLALU_BESAR", "Kiriman terlalu besar (maksimum 2 MiB).")
    if not body.strip():
        return _tolak("FORMAT_RUSAK", "Kiriman kosong.")
    tipe = (content_type or "").lower()
    catatan: list[str] = []
    gambar: bytes | None = None
    try:
        if tipe.startswith("multipart/"):
            m = _BOUNDARY.search(content_type or "")
            if not m:
                return _tolak("FORMAT_RUSAK", "Kiriman multipart tanpa pembatas.")
            dokumen: dict[str, Any] | None = None
            for header, data in _pisah_multipart(body, m.group(1)):
                jenis = header.get("content-type", "").lower()
                disposisi = header.get("content-disposition", "").lower()
                if data.startswith(k.MAGIC_JPEG) or jenis.startswith("image/") or ".jp" in disposisi:
                    if gambar is None and data.startswith(k.MAGIC_JPEG):
                        gambar = data
                    elif gambar is None:
                        catatan.append("Gambar ditolak: bukan JPEG yang sah.")
                    continue
                if dokumen is None:
                    if len(data) > k.MAKS_BYTE_JSON:
                        return _tolak("TERLALU_BESAR", "Bagian data event terlalu besar.")
                    dokumen = _teks_ke_dict(data)
            if dokumen is None:
                return _tolak("FORMAT_RUSAK", "Kiriman tidak memuat data event.")
            atas = dokumen
        elif "json" in tipe or "xml" in tipe or not tipe or tipe.startswith(("text/", "application/octet")):
            atas = _teks_ke_dict(body)
        else:
            return _tolak("TIPE_TIDAK_DIDUKUNG", "Jenis kiriman tidak didukung.")
        blok = atas.get(k.BLOK_EVENT)
        if blok is None:
            jenis_event = _ambil(atas, k.F_JENIS_EVENT)
            if isinstance(jenis_event, str) and jenis_event.lower() in k.JENIS_HEARTBEAT:
                return _abaikan("HEARTBEAT", "Sinyal hidup perangkat, bukan absensi.")
            return _abaikan("BUKAN_VERIFIKASI", "Kiriman bukan event akses.")
        if not isinstance(blok, dict):
            return _tolak("FORMAT_RUSAK", "Isi event akses tidak berbentuk benar.")
        return _normalisasi(atas, blok, device_serial=device_serial, ada_gambar=gambar is not None, zona=zona,
                            sekarang=sekarang(), minor_diizinkan=minor_diizinkan, gambar=gambar, catatan=catatan)
    except _Tolak as e:
        return _tolak(e.kode, e.pesan)
