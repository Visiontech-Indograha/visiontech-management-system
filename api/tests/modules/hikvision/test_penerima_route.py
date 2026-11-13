"""Penerima push Hikvision (POST /hikvision/events/{token}): token, IP, batas, idempotensi, SHADOW. Butuh DB uji."""
from __future__ import annotations

import hashlib
import secrets
import uuid
from collections.abc import Iterator
from dataclasses import dataclass

import pytest
from fastapi.testclient import TestClient

from app.core import rate_limit
from app.main import API_PREFIX, app
from app.modules.hikvision.services import konstanta as k
from tests.conftest import requires_db, sync_query
from tests.fixtures.hikvision import push_generator as g

pytestmark = requires_db

IP_PERANGKAT = "192.0.2.10"


@dataclass
class Perangkat:
    device_id: str
    serial: str
    token: str


def _buat_perangkat(*, aktif: bool = True, mode: str = "SHADOW") -> Perangkat:
    tag = uuid.uuid4().hex[:10].upper()
    token = secrets.token_urlsafe(32)
    office = sync_query("SELECT office_id FROM office WHERE is_main_office AND delete_at IS NULL")[0][0]
    row = sync_query(
        "INSERT INTO hikvision_device (office_id, name, ip_address, serial_no, token_hash, mode, aktif) "
        "VALUES (%s, 'Pintu uji', %s, %s, %s, %s, %s) RETURNING device_id",
        (office, IP_PERANGKAT, f"DS-SIM-{tag}", hashlib.sha256(token.encode()).hexdigest(), mode, aktif),
    )
    return Perangkat(str(row[0][0]), f"DS-SIM-{tag}", token)


def _hapus(p: Perangkat) -> None:
    sync_query("DELETE FROM hikvision_event WHERE device_id = %s", (p.device_id,))
    sync_query("DELETE FROM hikvision_employee_map WHERE device_id = %s", (p.device_id,))
    sync_query("DELETE FROM hikvision_device WHERE device_id = %s", (p.device_id,))


@pytest.fixture()
def perangkat() -> Iterator[Perangkat]:
    p = _buat_perangkat()
    yield p
    _hapus(p)


@pytest.fixture()
def klien() -> Iterator[TestClient]:
    rate_limit.set_limiter(None)
    with TestClient(app, base_url=f"http://testserver{API_PREFIX}", client=(IP_PERANGKAT, 50000)) as c:
        yield c
    rate_limit.set_limiter(None)


def _jumlah(p: Perangkat) -> int:
    return int(sync_query("SELECT count(*) FROM hikvision_event WHERE device_id = %s", (p.device_id,))[0][0])


def _kirim(c: TestClient, token: str, body: bytes, ctype: str):
    return c.post(f"/hikvision/events/{token}", content=body, headers={"Content-Type": ctype})


def test_token_valid_menyimpan_event_mentah_tanpa_biometrik(klien, perangkat) -> None:
    body, ct = g.push_multipart()
    r = _kirim(klien, perangkat.token, body, ct)
    assert r.status_code == 200 and r.json() == {"status": "diterima", "kode": "OK"}  # tanpa login sama sekali
    baris = sync_query(
        "SELECT sumber, serial_no_event, employee_no_string, employee_id, picture_path, payload::text "
        "FROM hikvision_event WHERE device_id = %s", (perangkat.device_id,))
    assert len(baris) == 1
    sumber, serial, emp_no, emp_id, gambar, payload = baris[0]
    assert (sumber, serial, emp_no, emp_id, gambar) == ("PUSH", 1001, "EMP0001", None, None)
    assert "ada_gambar" in payload and "Picture" not in payload and "FFD8" not in payload.upper()


def test_token_salah_dan_tak_dikenal_sama_tanpa_bocoran(klien, perangkat) -> None:
    body, ct = g.push_json()
    salah = _kirim(klien, secrets.token_urlsafe(32), body, ct)
    pendek = _kirim(klien, "x", body, ct)
    assert salah.status_code == pendek.status_code == 404
    assert salah.json() == pendek.json()
    assert perangkat.serial not in salah.text and _jumlah(perangkat) == 0


def test_ip_tak_diizinkan_dijawab_404_dan_tidak_menyimpan(perangkat) -> None:
    rate_limit.set_limiter(None)
    body, ct = g.push_json()
    with TestClient(app, base_url=f"http://testserver{API_PREFIX}", client=("203.0.113.7", 1)) as asing:
        r = _kirim(asing, perangkat.token, body, ct)
    assert r.status_code == 404 and _jumlah(perangkat) == 0


def test_perangkat_nonaktif_404(klien) -> None:
    p = _buat_perangkat(aktif=False)
    try:
        assert _kirim(klien, p.token, *g.push_json()).status_code == 404
    finally:
        _hapus(p)


def test_terlalu_besar_413(klien, perangkat) -> None:
    besar = b"{" + b" " * (k.MAKS_BYTE_KIRIMAN + 10) + b"}"
    r = _kirim(klien, perangkat.token, besar, "application/json")
    assert r.status_code == 413 and r.json()["error"]["code"] == "PAYLOAD_TOO_LARGE"
    assert _jumlah(perangkat) == 0


def test_jpeg_palsu_event_tetap_disimpan_tanpa_gambar(klien, perangkat) -> None:
    body, ct = g.push_multipart(jpeg=b"\x89PNG bukan jpeg")
    r = _kirim(klien, perangkat.token, body, ct)
    assert r.status_code == 200 and r.json()["status"] == "diterima"
    ada = sync_query("SELECT payload->>'ada_gambar' FROM hikvision_event WHERE device_id = %s", (perangkat.device_id,))
    assert ada == [("false",)]


def test_event_ganda_idempoten(klien, perangkat) -> None:
    body, ct = g.push_multipart()
    a, b = _kirim(klien, perangkat.token, body, ct), _kirim(klien, perangkat.token, body, ct)
    assert (a.json()["status"], b.json()["status"]) == ("diterima", "duplikat")
    assert a.status_code == b.status_code == 200 and _jumlah(perangkat) == 1


def test_heartbeat_dan_bukan_verifikasi_diabaikan_cepat(klien, perangkat) -> None:
    r = _kirim(klien, perangkat.token, *g.heartbeat())
    assert r.status_code == 200 and r.json() == {"status": "diabaikan", "kode": "HEARTBEAT"}
    tak_dikenal = _kirim(klien, perangkat.token, *g.push_json(g.dokumen_event(minor=76, karyawan=None)))
    assert tak_dikenal.status_code == 200 and tak_dikenal.json()["status"] == "diabaikan"
    assert _jumlah(perangkat) == 0


def test_kiriman_rusak_422(klien, perangkat) -> None:
    r = _kirim(klien, perangkat.token, b"{bukan json", "application/json")
    assert r.status_code == 422 and _jumlah(perangkat) == 0


def test_metode_lain_tidak_diizinkan(klien, perangkat) -> None:
    assert klien.get(f"/hikvision/events/{perangkat.token}").status_code == 405


def test_pemetaan_karyawan_bila_ada_dan_kosong_bila_tidak(klien, perangkat, make_user) -> None:
    user = make_user(None)
    emp = sync_query("SELECT employee_id FROM users WHERE user_id = %s", (user.user_id,))[0][0]
    sync_query("INSERT INTO hikvision_employee_map (device_id, employee_no_string, employee_id) "
               "VALUES (%s, 'EMP0001', %s)", (perangkat.device_id, emp))
    assert _kirim(klien, perangkat.token, *g.push_json(g.dokumen_event(serial_no=2001))).status_code == 200
    asing = g.dokumen_event(serial_no=2002, karyawan="EMP0999")
    assert _kirim(klien, perangkat.token, *g.push_json(asing)).status_code == 200
    hasil = dict(sync_query(
        "SELECT serial_no_event, employee_id FROM hikvision_event WHERE device_id = %s", (perangkat.device_id,)))
    assert str(hasil[2001]) == str(emp) and hasil[2002] is None


def test_rate_limit_selalu_ditegakkan(klien, perangkat) -> None:
    rate_limit.set_limiter(rate_limit.TokenBucketLimiter({rate_limit.GROUP_HIKVISION: 2}))
    kode = [_kirim(klien, perangkat.token, *g.heartbeat()).status_code for _ in range(4)]
    assert kode[:2] == [200, 200] and kode[-1] == 429


def test_mode_aktif_juga_hanya_menyimpan_mentah(klien) -> None:
    p = _buat_perangkat(mode="AKTIF")
    try:
        assert _kirim(klien, p.token, *g.push_json()).status_code == 200
        assert _jumlah(p) == 1
        assert sync_query(
            "SELECT count(*) FROM attendance a JOIN hikvision_event e ON e.event_id = a.device_event_id "
            "WHERE e.device_id = %s", (p.device_id,))[0][0] == 0   # tanpa absen resmi di PR ini
    finally:
        _hapus(p)
