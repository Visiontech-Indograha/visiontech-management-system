"""Admin perangkat Hikvision: CRUD, token sekali tampil, pemetaan, usulan otomatis, status, izin per peran dan kantor.
Butuh DB uji."""
from __future__ import annotations

import hashlib
import json
import uuid
from collections.abc import Callable, Iterator
from dataclasses import dataclass

import pytest

from app.core.time import utcnow
from tests.conftest import SeededUser, login_headers, requires_db, sync_query

pytestmark = requires_db


@dataclass
class Ctx:
    tag: str
    office: str  # kantor milik akun uji (kantor HR)
    other_office: str  # kantor lain

    def serial(self, n: int = 1) -> str:
        return f"UJI{self.tag}{n}"


@pytest.fixture()
def ctx(make_user: Callable[..., SeededUser]) -> Iterator[Ctx]:
    tag = uuid.uuid4().hex[:8].upper()
    other = str(sync_query(
        "INSERT INTO office (name, address, latitude, longitude) VALUES (%s, 'Jl. Lain', -6.3, 106.9) "
        "RETURNING office_id", (f"Kantor lain {tag}",))[0][0])
    probe = make_user("HR")
    c = Ctx(tag, probe.org_id, other)
    yield c
    ids = [r[0] for r in sync_query("SELECT device_id FROM hikvision_device WHERE serial_no LIKE %s", (f"UJI{tag}%",))]
    for d in ids:
        sync_query("DELETE FROM hikvision_event WHERE device_id = %s", (d,))
        sync_query("DELETE FROM hikvision_employee_map WHERE device_id = %s", (d,))
        sync_query("DELETE FROM hikvision_device WHERE device_id = %s", (d,))
    sync_query("DELETE FROM office WHERE office_id = %s", (other,))


def _hdr(client, make_user, role):
    return login_headers(client, make_user(role))


def _body(c: Ctx, office: str | None = None, n: int = 1, **extra):
    return {"office_id": office or c.office, "name": "Pintu depan", "ip_address": "192.0.2.20",
            "serial_no": c.serial(n), "model": "DS-K1T", **extra}


def _device_in_other(c: Ctx) -> str:
    return str(sync_query(
        "INSERT INTO hikvision_device (office_id, name, ip_address, serial_no, token_hash) "
        "VALUES (%s, 'Lain', '192.0.2.30', %s, %s) RETURNING device_id",
        (c.other_office, c.serial(9), hashlib.sha256(uuid.uuid4().bytes).hexdigest()))[0][0])


def _mk(client, h, ctx: Ctx, office: str) -> str:
    r = client.post("/hikvision/devices", json=_body(ctx, office=office), headers=h)
    return str(r.json()["perangkat"]["device_id"])


def _map(client, h, dev: str, no: str, emp: str):
    return client.post(
        f"/hikvision/devices/{dev}/mappings", json={"employee_no_string": no, "employee_id": emp}, headers=h)


def _event(device_id: str, no: str | None, n: int, minutes_ago: int = 5) -> None:
    from datetime import timedelta

    sync_query(
        "INSERT INTO hikvision_event (device_id, serial_no_event, major_event_type, minor_event_type, event_time, "
        "employee_no_string, payload, sumber) VALUES (%s, %s, 5, 75, %s, %s, %s::jsonb, 'PUSH')",
        (device_id, n, utcnow() - timedelta(minutes=minutes_ago), no, json.dumps({})))


@pytest.mark.parametrize("role,kode", [(None, 403), ("PM", 403), ("HR", 200), ("OPS", 200), ("ADMIN", 200)])
def test_matriks_peran_daftar(client, make_user, ctx, role, kode) -> None:
    assert client.get("/hikvision/devices", headers=_hdr(client, make_user, role)).status_code == kode


def test_buat_perangkat_token_sekali_dan_hash_saja(client, make_user, ctx) -> None:
    h = _hdr(client, make_user, "HR")
    r = client.post("/hikvision/devices", json=_body(ctx), headers=h)
    assert r.status_code == 201, r.text
    j = r.json()
    token = j["penerima"]["token"]
    assert len(token) >= 32 and j["penerima"]["receiver_path"] == f"/api/v1/hikvision/events/{token}"
    assert j["penerima"]["receiver_url"].endswith(j["penerima"]["receiver_path"])
    assert j["perangkat"]["mode"] == "SHADOW" and j["perangkat"]["office_id"] == ctx.office
    dev = j["perangkat"]["device_id"]
    simpan = sync_query("SELECT token_hash FROM hikvision_device WHERE device_id = %s", (dev,))[0][0].strip()
    assert simpan == hashlib.sha256(token.encode()).hexdigest()
    for jalur in (f"/hikvision/devices/{dev}", "/hikvision/devices"):
        assert token not in client.get(jalur, headers=h).text  # token tidak pernah muncul lagi


def test_ganti_token_membatalkan_yang_lama(client, make_user, ctx) -> None:
    h = _hdr(client, make_user, "HR")
    j = client.post("/hikvision/devices", json=_body(ctx), headers=h).json()
    dev, lama = j["perangkat"]["device_id"], j["penerima"]["token"]
    r = client.post(f"/hikvision/devices/{dev}/token", headers=h)
    assert r.status_code == 200 and r.json()["token"] != lama
    simpan = sync_query("SELECT token_hash FROM hikvision_device WHERE device_id = %s", (dev,))[0][0].strip()
    assert simpan == hashlib.sha256(r.json()["token"].encode()).hexdigest() != hashlib.sha256(lama.encode()).hexdigest()


def test_validasi_dan_serial_ganda(client, make_user, ctx) -> None:
    h = _hdr(client, make_user, "HR")
    assert client.post("/hikvision/devices", json=_body(ctx, ip_address="bukan-ip"), headers=h).status_code == 422
    assert client.post("/hikvision/devices", json=_body(ctx, http_port=70000), headers=h).status_code == 422
    assert client.post("/hikvision/devices", json=_body(ctx, mode="LAIN"), headers=h).status_code == 422
    assert client.post("/hikvision/devices", json=_body(ctx), headers=h).status_code == 201
    dua = client.post("/hikvision/devices", json=_body(ctx), headers=h)
    assert dua.status_code == 409 and "Nomor seri" in dua.text


def test_ubah_dan_hapus_perangkat(client, make_user, ctx) -> None:
    h = _hdr(client, make_user, "HR")
    dev = client.post("/hikvision/devices", json=_body(ctx), headers=h).json()["perangkat"]["device_id"]
    client.post("/hikvision/devices", json=_body(ctx, n=2), headers=h)
    r = client.patch(f"/hikvision/devices/{dev}", json={"mode": "AKTIF", "aktif": False, "http_port": 8080}, headers=h)
    assert r.status_code == 200 and r.json()["mode"] == "AKTIF" and r.json()["aktif"] is False
    assert client.patch(f"/hikvision/devices/{dev}", json={"serial_no": ctx.serial(2)}, headers=h).status_code == 409
    assert client.delete(f"/hikvision/devices/{dev}", headers=h).status_code == 204
    assert client.get(f"/hikvision/devices/{dev}", headers=h).status_code == 404


def test_hr_hanya_kantor_sendiri_dan_om_semua(client, make_user, ctx) -> None:
    lain = _device_in_other(ctx)
    hr = _hdr(client, make_user, "HR")
    mine = client.post("/hikvision/devices", json=_body(ctx), headers=hr).json()["perangkat"]["device_id"]
    ids = [d["device_id"] for d in client.get("/hikvision/devices", headers=hr).json()]
    assert mine in ids and lain not in ids
    luar = client.post("/hikvision/devices", json=_body(ctx, office=ctx.other_office, n=3), headers=hr)
    assert luar.status_code == 404
    for metode, jalur, kw in [
        ("get", f"/hikvision/devices/{lain}", {}), ("patch", f"/hikvision/devices/{lain}", {"json": {"aktif": False}}),
        ("delete", f"/hikvision/devices/{lain}", {}), ("post", f"/hikvision/devices/{lain}/token", {}),
        ("get", f"/hikvision/devices/{lain}/status", {}), ("get", f"/hikvision/devices/{lain}/mappings", {}),
        ("get", f"/hikvision/devices/{lain}/mappings/suggestions", {}),
        ("post", f"/hikvision/devices/{lain}/mappings/auto", {}),
    ]:
        assert getattr(client, metode)(jalur, headers=hr, **kw).status_code == 404, (metode, jalur)
    om = _hdr(client, make_user, "OPS")
    assert client.get(f"/hikvision/devices/{lain}", headers=om).status_code == 200
    assert lain in [d["device_id"] for d in client.get("/hikvision/devices", headers=om).json()]


def test_daftar_paginasi_dan_cari(client, make_user, ctx) -> None:
    h = _hdr(client, make_user, "HR")
    for n in (1, 2, 3):
        client.post("/hikvision/devices", json=_body(ctx, n=n), headers=h)
    r = client.get("/hikvision/devices", params={"page": 1, "size": 2}, headers=h)
    assert len(r.json()) == 2 and r.headers["X-Total-Count"] == "3"
    assert len(client.get("/hikvision/devices", params={"q": ctx.serial(2)}, headers=h).json()) == 1


def test_pemetaan_crud_dan_batas_kantor(client, make_user, ctx) -> None:
    hr_user = make_user("HR")
    h = login_headers(client, hr_user)
    dev = _mk(client, h, ctx, hr_user.org_id)
    emp = str(sync_query("SELECT employee_id FROM users WHERE user_id = %s", (hr_user.user_id,))[0][0])
    r = _map(client, h, dev, "77", emp)
    assert r.status_code == 201 and r.json()["employee_id"] == emp
    mid = r.json()["map_id"]
    dup = _map(client, h, dev, "77", emp)
    assert dup.status_code == 409
    asing = str(sync_query(
        "INSERT INTO employee (office_id, full_name, employee_no, join_date) "
        "VALUES (%s, 'Orang lain', %s, '2026-01-05') "
        "RETURNING employee_id", (ctx.other_office, f"ZZ{ctx.tag}"))[0][0])
    try:
        ubah = client.patch(f"/hikvision/devices/{dev}/mappings/{mid}", json={"employee_id": asing}, headers=h)
        assert ubah.status_code == 404
        assert _map(client, h, dev, "78", asing).status_code == 404
        assert [m["map_id"] for m in client.get(f"/hikvision/devices/{dev}/mappings", headers=h).json()] == [mid]
        assert client.delete(f"/hikvision/devices/{dev}/mappings/{mid}", headers=h).status_code == 204
        assert client.delete(f"/hikvision/devices/{dev}/mappings/{mid}", headers=h).status_code == 404
        assert client.get(f"/hikvision/devices/{dev}/mappings", headers=h).json() == []
    finally:
        sync_query("DELETE FROM employee WHERE employee_id = %s", (asing,))


def test_usulan_otomatis_dan_terapkan_ke_event_lama(client, make_user, ctx) -> None:
    hr_user = make_user("HR")
    h = login_headers(client, hr_user)
    dev = _mk(client, h, ctx, hr_user.org_id)
    emp_id, emp_no = sync_query(
        "SELECT e.employee_id, e.employee_no FROM employee e JOIN users u ON u.employee_id = e.employee_id "
        "WHERE u.user_id = %s", (hr_user.user_id,))[0]
    _event(dev, emp_no, 1)
    _event(dev, emp_no, 2)
    _event(dev, "TAKDIKENAL", 3)
    u = client.get(f"/hikvision/devices/{dev}/mappings/suggestions", headers=h).json()
    assert [c["employee_no_string"] for c in u["cocok"]] == [emp_no] and u["cocok"][0]["jumlah_event"] == 2
    assert [t["employee_no_string"] for t in u["tidak_cocok"]] == ["TAKDIKENAL"]
    r = client.post(f"/hikvision/devices/{dev}/mappings/auto", headers=h).json()
    assert r["dibuat"] == 1 and r["event_diperbarui"] == 2 and r["masih_ada_sisa"] is False
    assert [t["employee_no_string"] for t in r["tidak_cocok"]] == ["TAKDIKENAL"]
    terisi = sync_query(
        "SELECT count(*) FROM hikvision_event WHERE device_id = %s AND employee_id = %s", (dev, emp_id))[0][0]
    assert terisi == 2
    ulang = client.post(f"/hikvision/devices/{dev}/mappings/auto", headers=h).json()
    assert ulang["dibuat"] == 0 and ulang["event_diperbarui"] == 0


def test_terapkan_pemetaan_manual_ke_event_kosong(client, make_user, ctx) -> None:
    hr_user = make_user("HR")
    h = login_headers(client, hr_user)
    dev = _mk(client, h, ctx, hr_user.org_id)
    emp = str(sync_query("SELECT employee_id FROM users WHERE user_id = %s", (hr_user.user_id,))[0][0])
    _event(dev, "55", 1)
    client.post(f"/hikvision/devices/{dev}/mappings", json={"employee_no_string": "55", "employee_id": emp}, headers=h)
    r = client.post(f"/hikvision/devices/{dev}/mappings/apply", headers=h)
    assert r.status_code == 200 and r.json() == {"event_diperbarui": 1, "masih_ada_sisa": False}


def test_status_perangkat(client, make_user, ctx) -> None:
    h = _hdr(client, make_user, "HR")
    dev = client.post("/hikvision/devices", json=_body(ctx), headers=h).json()["perangkat"]["device_id"]
    kosong = client.get(f"/hikvision/devices/{dev}/status", headers=h).json()
    assert kosong["event_24_jam"] == 0 and kosong["event_terakhir_diterima"] is None
    _event(dev, "1", 1, minutes_ago=5)
    _event(dev, "2", 2, minutes_ago=60 * 24 * 3)
    s = client.get(f"/hikvision/devices/{dev}/status", headers=h).json()
    assert s["event_24_jam"] == 1 and s["event_7_hari"] == 2 and s["belum_terpetakan_7_hari"] == 2
    assert s["event_terakhir_diterima"] is not None and s["kemungkinan_duplikat_7_hari"] == 0


@pytest.mark.parametrize("role,kode", [(None, 403), ("PM", 403), ("HR", 200), ("OPS", 200), ("ADMIN", 200)])
def test_bayangan_matriks_peran(client, make_user, ctx, role, kode) -> None:
    dev = _mk(client, _hdr(client, make_user, "HR"), ctx, ctx.office)
    r = client.get(f"/hikvision/devices/{dev}/bayangan", headers=_hdr(client, make_user, role))
    assert r.status_code == kode, r.text


def test_bayangan_hitung_cakupan_dan_rentang(client, make_user, ctx) -> None:
    hr = make_user("HR")
    h = login_headers(client, hr)
    dev = _mk(client, h, ctx, ctx.office)
    emp = str(sync_query("SELECT employee_id FROM users WHERE user_id = %s", (hr.user_id,))[0][0])
    assert _map(client, h, dev, "77", emp).status_code == 201
    _event(dev, "77", 1)   # tap terpetakan
    _event(dev, "99", 2)   # nomor tak dikenal
    sync_query("UPDATE hikvision_event SET employee_id = %s WHERE device_id = %s AND employee_no_string = '77'",
               (emp, dev))
    r = client.get(f"/hikvision/devices/{dev}/bayangan", headers=h)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["mode"] == "SHADOW" and j["akan_menghasilkan_absen"] == 1 and j["total_karyawan_hari"] == 1
    assert j["tak_terpetakan"] == 1 and j["terpotong"] is False
    assert j["items"][0]["clock_in_at"] is None and j["items"][0]["selisih_masuk_menit"] is None
    # di luar cakupan HR = 404; rentang > 31 hari atau terbalik = 422
    assert client.get(f"/hikvision/devices/{_device_in_other(ctx)}/bayangan", headers=h).status_code == 404
    assert client.get(f"/hikvision/devices/{dev}/bayangan", params={"dari": "2026-01-01", "sampai": "2026-03-01"},
                      headers=h).status_code == 422
    assert client.get(f"/hikvision/devices/{dev}/bayangan", params={"dari": "2026-02-02", "sampai": "2026-02-01"},
                      headers=h).status_code == 422
