"""Parser event Hikvision: tanpa DB dan tanpa jaringan. Fixture berdasarkan dokumentasi, belum dari perangkat asli."""
from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.modules.hikvision.schemas import ParseStatus
from app.modules.hikvision.services import konstanta as k
from app.modules.hikvision.services import parse_acs_item, parse_push
from tests.fixtures.hikvision import push_generator as g

SEKARANG = datetime(2026, 11, 13, 2, 0, tzinfo=UTC)


def uraikan(body: bytes, ctype: str | None, **kw):
    return parse_push(body, ctype, device_serial="DS-SIM-0001", sekarang=lambda: SEKARANG, **kw)


def test_multipart_valid_dengan_gambar():
    body, ct = g.push_multipart()
    r = uraikan(body, ct)
    assert r.status is ParseStatus.OK and r.event is not None
    e = r.event
    assert (e.device_serial, e.serial_no_event, e.major_event_type, e.minor_event_type) == ("DS-SIM-0001", 1001, 5, 75)
    assert e.employee_no_string == "EMP0001" and e.verify_mode == "face" and e.ada_gambar is True
    assert e.event_time.utcoffset() == timedelta(hours=7)
    assert r.gambar is not None and r.gambar.startswith(k.MAGIC_JPEG)


def test_multipart_tanpa_gambar_tetap_ok():
    body, ct = g.push_multipart(sertakan_gambar=False)
    r = uraikan(body, ct)
    assert r.status is ParseStatus.OK and r.event is not None and r.event.ada_gambar is False


def test_json_murni_dan_xml_fallback():
    for body, ct in (g.push_json(), g.push_xml()):
        r = uraikan(body, ct)
        assert r.status is ParseStatus.OK and r.event is not None and r.event.employee_no_string == "EMP0001"
    # tanpa Content-Type: ditebak dari isi
    assert uraikan(g.push_json()[0], None).status is ParseStatus.OK


@pytest.mark.parametrize("minor,diterima", [(75, True), (1, True), (38, True), (76, False), (21, False)])
def test_filter_minor(minor, diterima):
    kartu = "998877" if minor == 1 else None
    body, ct = g.push_json(g.dokumen_event(minor=minor, kartu=kartu, karyawan=None if minor == 1 else "EMP0001"))
    r = uraikan(body, ct)
    assert (r.status is ParseStatus.OK) is diterima
    if not diterima:
        assert r.status is ParseStatus.DIABAIKAN and r.event is None


def test_major_lain_dan_heartbeat_diabaikan():
    assert uraikan(*g.push_json(g.dokumen_event(major=3))).status is ParseStatus.DIABAIKAN
    r = uraikan(*g.heartbeat())
    assert r.status is ParseStatus.DIABAIKAN and r.kode == "HEARTBEAT"


def test_jpeg_palsu_event_tetap_diolah_tanpa_gambar():
    body, ct = g.push_multipart(jpeg=b"\x89PNG bukan jpeg", sertakan_gambar=True)
    r = uraikan(body, ct)
    assert r.status is ParseStatus.OK and r.event is not None
    assert r.event.ada_gambar is False and r.gambar is None and r.catatan


def test_terlalu_besar():
    body, ct = g.push_multipart(jpeg=k.MAGIC_JPEG + b"\0" * (k.MAKS_BYTE_KIRIMAN + 1))
    r = uraikan(body, ct)
    assert r.status is ParseStatus.DITOLAK and r.kode == "TERLALU_BESAR"


def test_multipart_rusak():
    body, ct = g.push_multipart()
    assert uraikan(body, "multipart/form-data").kode == "FORMAT_RUSAK"            # tanpa pembatas
    assert uraikan(b"sampah tanpa pembatas", ct).kode == "FORMAT_RUSAK"          # tak ada bagian
    terpotong = body[: body.index(b'"eventType"')]                               # JSON terpotong
    assert uraikan(terpotong, ct).status is ParseStatus.DITOLAK
    assert uraikan(b"", ct).status is ParseStatus.DITOLAK


def test_tipe_tidak_didukung_dan_isi_bukan_json():
    assert uraikan(b"\x00\x01\x02", "image/png").kode == "TIPE_TIDAK_DIDUKUNG"
    assert uraikan(b"halo dunia", "text/plain").kode == "TIPE_TIDAK_DIDUKUNG"
    assert uraikan(b"{bukan json", "application/json").kode == "FORMAT_RUSAK"


def test_xml_dengan_entitas_ditolak():
    jahat = b'<?xml version="1.0"?><!DOCTYPE a [<!ENTITY x "y">]><a>&x;</a>'
    r = uraikan(jahat, "application/xml")
    assert r.status is ParseStatus.DITOLAK and r.kode == "FORMAT_RUSAK"


def test_waktu_tidak_wajar_dan_tanpa_offset():
    masa_depan = g.dokumen_event(waktu="2026-11-14T08:00:00+07:00")
    assert uraikan(*g.push_json(masa_depan)).kode == "WAKTU_TIDAK_WAJAR"
    kuno = g.dokumen_event(waktu="2001-01-01T08:00:00+07:00")
    assert uraikan(*g.push_json(kuno)).kode == "WAKTU_TIDAK_WAJAR"
    assert uraikan(*g.push_json(g.dokumen_event(waktu="bukan waktu"))).kode == "FORMAT_RUSAK"
    naif = uraikan(*g.push_json(g.dokumen_event(waktu="2026-11-13T08:01:05")))
    assert naif.event is not None and naif.event.event_time.utcoffset() == timedelta(hours=7)
    utc8 = uraikan(*g.push_json(g.dokumen_event(waktu="2026-11-13T08:01:05")), zona=timezone(timedelta(hours=8)))
    assert utc8.event is not None and utc8.event.event_time.utcoffset() == timedelta(hours=8)


def test_validasi_string_dan_pengenal():
    assert uraikan(*g.push_json(g.dokumen_event(karyawan="9" * 51))).kode == "DATA_TIDAK_VALID"
    assert uraikan(*g.push_json(g.dokumen_event(karyawan="A\x00B"))).kode == "DATA_TIDAK_VALID"
    assert uraikan(*g.push_json(g.dokumen_event(karyawan=None))).kode == "TANPA_PENGENAL"
    assert uraikan(*g.push_json(g.dokumen_event(mode="x" * 51))).kode == "DATA_TIDAK_VALID"
    assert uraikan(*g.push_json(g.dokumen_event(serial_no=None))).event.serial_no_event is None  # type: ignore[union-attr]


def test_perangkat_tak_dikenal_ditolak():
    body, ct = g.push_json()
    r = parse_push(body, ct, sekarang=lambda: SEKARANG)   # tanpa serial dari konfigurasi maupun isi
    assert r.status is ParseStatus.DITOLAK


def test_hasil_tidak_memuat_embedding():
    r = uraikan(*g.push_multipart())
    assert r.event is not None
    assert not any("embed" in f.lower() or "template" in f.lower() for f in r.event.__slots__)


def test_butir_hasil_tarik():
    item = {"major": 5, "minor": 75, "time": "2026-11-13T08:00:00+07:00", "serialNo": 7, "employeeNoString": "EMP0002"}
    r = parse_acs_item(item, device_serial="DS-SIM-0001")
    assert r.event is not None and r.event.serial_no_event == 7
    assert parse_acs_item("bukan dict", device_serial="x").status is ParseStatus.DITOLAK
    assert parse_acs_item({**item, "minor": 76}, device_serial="x").status is ParseStatus.DIABAIKAN
