"""Pembaca ekspor laporan absensi iVMS-4200 (CSV/XLSX) menjadi event verifikasi lolos (cadangan tarik ISAPI).

Dialirkan baris demi baris (memori terbatas). Tidak membaca nama orang dan tidak menyimpan foto. Isi baris tidak
pernah dicetak/dicatat. Nama kolom dicocokkan lewat SINONIM_KOLOM di bawah."""
from __future__ import annotations

import codecs
import csv
import hashlib
import re
import zipfile
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any

from app.core.time import WIB, utcnow
from app.modules.hikvision.services import konstanta as hk

MAKS_BYTE_BERKAS = 100 * 1024 * 1024
MAKS_BARIS_JUDUL = 40          # baris awal yang dipindai untuk mencari judul kolom
SUMBER_IMPOR = "IVMS4200"      # penanda di payload (kolom sumber tetap 'PULL', tanpa migrasi)

# PERLU VERIFIKASI dari ekspor asli iVMS-4200: nama kolom di bawah dari dokumentasi/ingatan, BELUM dari berkas
# asli pemilik. Nama dinormalkan (huruf kecil, tanpa spasi/tanda baca). Tambah sinonim di sini saja.
SINONIM_KOLOM: dict[str, tuple[str, ...]] = {
    "id": ("personid", "employeeid", "employeeno", "empno", "personno", "personnumber", "userid", "id",
           "nopegawai", "idorang", "idkaryawan"),
    "waktu": ("datetime", "checktime", "attendancetime", "authenticationdatetime", "eventtime", "waktu",
              "tanggalwaktu", "tanggaljam"),
    "tanggal": ("date", "attendancedate", "authenticationdate", "tanggal", "tgl"),
    "jam": ("time", "authenticationtime", "jam", "waktuabsen"),
    "status": ("attendancestatus", "checkinout", "checkinoutstatus", "status", "statusabsen"),
    "perangkat": ("devicename", "checkpoint", "checkpointname", "device", "reader", "namaperangkat"),
    "kartu": ("cardno", "card", "cardnumber", "nokartu"),
}

_FORMAT_TANGGAL = ("%Y-%m-%d", "%Y/%m/%d", "%d/%m/%Y", "%d-%m-%Y", "%d.%m.%Y", "%m/%d/%Y", "%d/%m/%y")
_FORMAT_JAM = ("%H:%M:%S", "%H:%M", "%I:%M:%S %p", "%I:%M %p", "%I:%M:%S%p", "%I:%M%p")


class ImporError(Exception):
    """Galat yang aman ditampilkan ke operator (bahasa awam, tanpa isi berkas)."""


@dataclass(frozen=True, slots=True)
class EventImpor:
    waktu: datetime               # beroffset WIB
    employee_no: str
    card_no: str | None
    status: str | None


def normalkan(judul: Any) -> str:
    return re.sub(r"[^a-z0-9]", "", str(judul or "").lower())


def _peta_kolom(baris: Sequence[Any]) -> dict[str, int] | None:
    """Indeks kolom per bidang bila baris ini berupa judul yang memadai, selain itu None."""
    nama = [normalkan(c) for c in baris]
    peta: dict[str, int] = {}
    for bidang, daftar in SINONIM_KOLOM.items():
        for sinonim in daftar:
            if sinonim in nama:
                peta[bidang] = nama.index(sinonim)
                break
    punya_waktu = "waktu" in peta or "jam" in peta
    return peta if "id" in peta and punya_waktu else None


def kunci_impor(device_id: Any, employee_no: str, waktu: datetime) -> str:
    mentah = "|".join(["IMPOR", str(device_id), employee_no, waktu.astimezone(UTC).isoformat()])
    return hashlib.sha256(mentah.encode()).hexdigest()


def _tanggal(v: Any) -> date | None:
    if isinstance(v, datetime):
        return v.date()
    if isinstance(v, date):
        return v
    if not isinstance(v, str) or not v.strip():
        return None
    for f in _FORMAT_TANGGAL:
        try:
            return datetime.strptime(v.strip(), f).replace(tzinfo=WIB).date()
        except ValueError:
            continue
    return None


def _jam(v: Any) -> time | None:
    if isinstance(v, datetime):
        return v.time().replace(microsecond=0)
    if isinstance(v, time):
        return v.replace(microsecond=0)
    if isinstance(v, (int, float)) and not isinstance(v, bool) and 0 <= v < 1:
        detik = round(v * 86400)
        return time(detik // 3600 % 24, detik // 60 % 60, detik % 60)
    if not isinstance(v, str) or not v.strip():
        return None
    teks = re.sub(r"\.\d+", "", v.strip().upper()).replace("A.M.", "AM").replace("P.M.", "PM")
    for f in _FORMAT_JAM:
        try:
            return datetime.strptime(teks, f).replace(tzinfo=WIB).time()
        except ValueError:
            continue
    return None


def _penuh(v: Any) -> datetime | None:
    if isinstance(v, datetime):
        return v.replace(microsecond=0)
    if not isinstance(v, str) or not v.strip():
        return None
    teks = re.sub(r"(?<=\d)T(?=\d)", " ", v.strip())
    bagian = teks.split(None, 1)
    if len(bagian) != 2:
        return None
    t, j = _tanggal(bagian[0]), _jam(bagian[1])
    return datetime.combine(t, j) if t and j else None


def _pengenal(v: Any) -> str | None:
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, float) and v.is_integer():
        v = int(v)
    teks = str(v).strip()
    return teks or None


def waktu_baris(baris: Sequence[Any], peta: dict[str, int]) -> datetime | None:
    def sel(bidang: str) -> Any:
        i = peta.get(bidang)
        return baris[i] if i is not None and i < len(baris) else None

    w: datetime | None = None
    if "waktu" in peta:
        w = _penuh(sel("waktu"))
    if w is None and "tanggal" in peta:
        t, j = _tanggal(sel("tanggal")), _jam(sel("jam"))
        w = datetime.combine(t, j) if t and j else None
    if w is None and "tanggal" not in peta and "jam" in peta:
        w = _penuh(sel("jam"))
    if w is None:
        return None
    return w.replace(tzinfo=WIB) if w.tzinfo is None else w.astimezone(WIB)


def _waktu_masuk_akal(w: datetime) -> bool:
    awal = datetime(*hk.WAKTU_TERAWAL, tzinfo=WIB)
    return awal <= w <= utcnow() + hk.TOLERANSI_MASA_DEPAN


def _baris_csv(path: Path) -> Iterator[Sequence[Any]]:
    with path.open("rb") as f:
        sampel = f.read(1024 * 1024)
    if sampel[:2] in (b"\xff\xfe", b"\xfe\xff"):
        enc = "utf-16"
    else:
        try:
            codecs.getincrementaldecoder("utf-8-sig")().decode(sampel, final=False)
            enc = "utf-8-sig"
        except UnicodeDecodeError:
            enc = "cp1252"
    teks = sampel.decode(enc, errors="replace").splitlines()[:10]
    pemisah = max((",", ";", "\t"), key=lambda p: sum(b.count(p) for b in teks))
    with path.open("r", encoding=enc, newline="") as f:
        yield from csv.reader(f, delimiter=pemisah)


def _lembar_xlsx(path: Path) -> Iterator[Iterator[Sequence[Any]]]:
    from openpyxl import load_workbook

    try:
        wb = load_workbook(path, read_only=True, data_only=True)
    except Exception:  # noqa: BLE001 - pustaka melempar banyak jenis; pesan awam di bawah
        raise ImporError("Berkas Excel tidak bisa dibuka. Pastikan berkasnya utuh dan berformat .xlsx "
                         "(bukan .xls lama), lalu coba ekspor ulang dari iVMS-4200.") from None
    try:
        for ws in wb.worksheets:
            yield ws.iter_rows(values_only=True)
    finally:
        wb.close()


def periksa_berkas(path: Path) -> str:
    """Kembalikan 'csv' atau 'xlsx'; galat Indonesia awam bila berkas tak layak."""
    if not path.is_file():
        raise ImporError("Berkas tidak ditemukan. Periksa lokasi dan nama berkasnya.")
    ukuran = path.stat().st_size
    if ukuran == 0:
        raise ImporError("Berkas kosong. Ekspor ulang laporan dari iVMS-4200.")
    if ukuran > MAKS_BYTE_BERKAS:
        raise ImporError(f"Berkas terlalu besar (maksimum {MAKS_BYTE_BERKAS // (1024 * 1024)} MB). "
                         "Ekspor per bulan atau per beberapa bulan, lalu impor satu per satu.")
    ekstensi = path.suffix.lower()
    if ekstensi == ".xlsx":
        if not zipfile.is_zipfile(path):
            raise ImporError("Berkas berekstensi .xlsx tetapi bukan berkas Excel yang sah. Ekspor ulang dari iVMS-4200.")  # noqa: E501
        return "xlsx"
    if ekstensi in (".csv", ".txt"):
        return "csv"
    raise ImporError("Format berkas tidak dikenali. Gunakan ekspor Excel (.xlsx) atau CSV (.csv) dari iVMS-4200.")


def _dari_tabel(baris: Iterator[Sequence[Any]], ketemu: dict[str, bool]) -> Iterator[EventImpor | None]:
    peta: dict[str, int] | None = None
    for n, b in enumerate(baris):
        if peta is None:
            if n >= MAKS_BARIS_JUDUL:
                return
            peta = _peta_kolom(b)
            ketemu["judul"] = ketemu["judul"] or peta is not None
            continue
        if not any(c not in (None, "") for c in b):
            continue
        no = _pengenal(b[peta["id"]]) if peta["id"] < len(b) else None
        w = waktu_baris(b, peta)
        if no is None or w is None or len(no) > hk.MAKS_PANJANG_PENGENAL or not _waktu_masuk_akal(w):
            yield None  # judul ulang, baris ringkasan, atau isi tak masuk akal
            continue
        kartu = _pengenal(b[peta["kartu"]]) if "kartu" in peta and peta["kartu"] < len(b) else None
        status = _pengenal(b[peta["status"]]) if "status" in peta and peta["status"] < len(b) else None
        yield EventImpor(w, no, kartu[: hk.MAKS_PANJANG_PENGENAL] if kartu else None, status[:30] if status else None)


def baca_ekspor(path: Path) -> Iterator[EventImpor | None]:
    """Alirkan event dari berkas. None = baris tak valid (dihitung pemanggil). Galat bila judul kolom tak ada."""
    jenis = periksa_berkas(path)
    status = {"judul": False}
    sumber = _lembar_xlsx(path) if jenis == "xlsx" else iter([_baris_csv(path)])
    for lembar in sumber:
        yield from _dari_tabel(iter(lembar), status)
    if not status["judul"]:
        raise ImporError("Kolom yang dibutuhkan tidak ditemukan. Berkas harus punya kolom ID orang "
                         "(mis. Person ID / Employee ID) dan tanggal serta jam (mis. Date, Time). "
                         "Pastikan ini ekspor laporan absensi dari iVMS-4200.")
