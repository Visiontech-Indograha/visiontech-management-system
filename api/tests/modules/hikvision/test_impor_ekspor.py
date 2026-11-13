"""Pembaca ekspor iVMS-4200 (tanpa DB): varian header, format tanggal/jam, berkas rusak."""
from __future__ import annotations

import csv
from datetime import datetime, time
from pathlib import Path

import pytest
from openpyxl import Workbook

from app.core.time import WIB
from app.modules.hikvision.services.impor_ekspor import (
    EventImpor,
    ImporError,
    baca_ekspor,
    kunci_impor,
)

FIX = Path(__file__).parents[2] / "fixtures" / "hikvision" / "ekspor_ivms"


def _hasil(path: Path) -> list[EventImpor | None]:
    return list(baca_ekspor(path))


def _valid(path: Path) -> list[EventImpor]:
    return [e for e in _hasil(path) if e is not None]


def test_csv_inggris_tanggal_dan_jam_terpisah() -> None:
    ev = _valid(FIX / "inggris_tanggal_jam.csv")
    assert (ev[0].employee_no, ev[0].waktu) == ("1001", datetime(2026, 10, 1, 7, 55, 10, tzinfo=WIB))
    assert len(ev) == 3
    assert ev[2].card_no == "12345" and ev[0].card_no is None


def test_csv_titik_koma_baris_judul_ringkasan_dan_12_jam() -> None:
    hasil = _hasil(FIX / "titik_koma_ringkasan_12jam.csv")
    ev = [e for e in hasil if e]
    assert [e.waktu.time() for e in ev] == [time(7, 55, 10), time(17, 5, 0)]
    assert ev[0].waktu.date().isoformat() == "2026-10-01"  # dd/MM/yyyy
    assert hasil.count(None) == 1  # baris "Total"


def test_csv_tab_dan_waktu_gabungan() -> None:
    ev = _valid(FIX / "tab_gabungan.csv")
    assert len(ev) == 1 and ev[0].employee_no == "1003" and ev[0].waktu.hour == 8


def test_xlsx_sel_tanggal_asli_dan_id_angka(tmp_path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.append(["Laporan"])
    ws.append(["Person ID", "Name", "Date", "Time"])
    ws.append([1001.0, "X", datetime(2026, 10, 5), time(8, 30, 0)])  # noqa: DTZ001
    ws.append(["0042", "Y", "2026-10-05", "9:15 AM"])
    ws.append([None, None, None, None])
    p = tmp_path / "e.xlsx"
    wb.save(p)
    ev = _valid(p)
    assert [(e.employee_no, e.waktu.hour, e.waktu.minute) for e in ev] == [("1001", 8, 30), ("0042", 9, 15)]


def test_csv_utf16_bom(tmp_path: Path) -> None:
    p = tmp_path / "u.csv"
    p.write_bytes("Person ID,Date,Time\n7,2026-10-06,08:00:00\n".encode("utf-16"))
    assert len(_valid(p)) == 1


def test_mm_dd_dipakai_bila_dd_mm_mustahil(tmp_path: Path) -> None:
    p = tmp_path / "m.csv"
    with p.open("w", newline="") as f:
        csv.writer(f).writerows([["Person ID", "Date", "Time"], ["1", "10/25/2026", "08:00"]])
    assert _valid(p)[0].waktu.day == 25


def test_baris_tak_valid_dihitung_bukan_galat(tmp_path: Path) -> None:
    p = tmp_path / "t.csv"
    p.write_text("Person ID,Date,Time\n1,bukan-tanggal,08:00\n,2026-10-01,08:00\n2,2026-10-01,08:00\n"
                 "3,2999-01-01,08:00\n")
    assert _hasil(p).count(None) == 3 and len(_valid(p)) == 1


@pytest.mark.parametrize("nama,isi,kata", [
    ("kosong.csv", b"", "kosong"),
    ("salah.pdf", b"x", "Format berkas"),
    ("palsu.xlsx", b"bukan zip", "bukan berkas Excel"),
    ("tanpa_judul.csv", b"a,b,c\n1,2,3\n", "Kolom yang dibutuhkan"),
])
def test_berkas_rusak_pesan_awam(tmp_path: Path, nama: str, isi: bytes, kata: str) -> None:
    p = tmp_path / nama
    p.write_bytes(isi)
    with pytest.raises(ImporError, match=kata):
        list(baca_ekspor(p))


def test_berkas_tak_ada_dan_terlalu_besar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with pytest.raises(ImporError, match="tidak ditemukan"):
        list(baca_ekspor(tmp_path / "tidak-ada.csv"))
    p = tmp_path / "b.csv"
    p.write_text("Person ID,Date,Time\n")
    monkeypatch.setattr("app.modules.hikvision.services.impor_ekspor.MAKS_BYTE_BERKAS", 5)
    with pytest.raises(ImporError, match="terlalu besar"):
        list(baca_ekspor(p))


def test_kunci_stabil_dan_berbeda_per_orang() -> None:
    w = datetime(2026, 10, 1, 8, tzinfo=WIB)
    assert kunci_impor("d", "1", w) == kunci_impor("d", "1", w.astimezone())
    assert kunci_impor("d", "1", w) != kunci_impor("d", "2", w)
    assert len(kunci_impor("d", "1", w)) == 64
