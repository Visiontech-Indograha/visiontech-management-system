"""Banding mesin (GET /hikvision/devices/{id}/bayangan): baris "hanya di aplikasi", filter status, awalan nama, dan
paginasi di sisi server. Tanpa parameter = perilaku lama. Butuh DB uji."""
from __future__ import annotations

import uuid

import pytest

from tests.conftest import login_headers, requires_db, sync_query
from tests.modules.hikvision.test_admin_route import (  # noqa: F401  (fixture ctx dipakai pytest)
    Ctx,
    _device_in_other,
    _hdr,
    _mk,
    ctx,
)

pytestmark = requires_db

_TGL = "2026-02-10"  # 08:00 WIB = 01:00 UTC


def _tap(dev: str, emp: str, n: int, jam_utc: str = "01:00") -> None:
    sync_query(
        "INSERT INTO hikvision_event (device_id, serial_no_event, major_event_type, minor_event_type, event_time, "
        "employee_no_string, employee_id, payload, sumber) "
        "VALUES (%s, %s, 5, 75, %s::timestamptz, %s, %s, '{}'::jsonb, 'PUSH')",
        (dev, n, f"{_TGL} {jam_utc}+00", f"N{n}", emp))


def _absen_app(emp: str, office: str, masuk_wib: str, source: str | None = "APP_HP") -> None:
    sync_query(
        "INSERT INTO attendance (employee_id, attendance_date, target_location_type, office_id, scheduled_in, "
        "scheduled_out, clock_in_at, in_lat, in_lng, face_match_score, face_photo_path, distance_to_target_m, "
        "is_within_attendance_radius, om_approval_status, distance_from_main_office_m, city_zone_status, "
        "meal_allowance_amount, source) "
        "VALUES (%s, %s, 'OFFICE', %s, '07:00', '16:00', (%s::date + %s::time) AT TIME ZONE 'Asia/Jakarta', "
        "-6.2, 106.8, 0, 'uji.webp', 0, TRUE, 'AUTO_VALID', 0, 'DALAM_KOTA', 0, %s) RETURNING 1",
        (emp, _TGL, office, _TGL, masuk_wib, source))


def _karyawan(c: Ctx, nama: str, office: str | None = None) -> str:
    return str(sync_query(
        "INSERT INTO employee (office_id, full_name, employee_no, join_date) "
        "VALUES (%s, %s, %s, '2026-01-05') RETURNING employee_id",
        (office or c.office, f"{nama} {c.tag}", f"UJI-{uuid.uuid4().hex[:10]}"))[0][0])


@pytest.fixture()
def banding(client, make_user, ctx):  # noqa: F811
    """Satu perangkat SHADOW + karyawan kantor: cocok, waktu berbeda, hanya mesin, hanya aplikasi
    (+ satu karyawan kantor lain dengan absen aplikasi yang TIDAK boleh muncul)."""
    h = login_headers(client, make_user("HR"))
    dev = _mk(client, h, ctx, ctx.office)
    e = {k: _karyawan(ctx, k.capitalize()) for k in ("alfa", "bravo", "charlie", "delta")}
    lain = _karyawan(ctx, "Echo", ctx.other_office)
    _tap(dev, e["alfa"], 1)
    _absen_app(e["alfa"], ctx.office, "08:02")      # selisih -2 menit -> cocok
    _tap(dev, e["bravo"], 2)
    _absen_app(e["bravo"], ctx.office, "07:30")     # selisih 30 menit -> waktu_berbeda
    _tap(dev, e["charlie"], 3)                       # tanpa absen aplikasi -> hanya_mesin
    _absen_app(e["delta"], ctx.office, "08:00")     # tanpa tap -> hanya_aplikasi
    _absen_app(lain, ctx.other_office, "08:00")     # kantor lain: tidak muncul
    yield h, dev, e
    semua = [*e.values(), lain]
    sync_query("DELETE FROM attendance WHERE employee_id = ANY(%s::uuid[])", (semua,))
    sync_query("DELETE FROM hikvision_event WHERE device_id = %s", (dev,))
    sync_query("DELETE FROM employee WHERE employee_id = ANY(%s::uuid[])", (semua,))


def _get(client, h, dev, **p):
    return client.get(f"/hikvision/devices/{dev}/bayangan", params={"dari": _TGL, "sampai": _TGL, **p}, headers=h)


def test_banding_mode_lama_tanpa_parameter_tidak_berubah(client, banding) -> None:
    h, dev, e = banding
    r = _get(client, h, dev)
    j = r.json()
    assert r.status_code == 200 and "X-Total-Count" not in r.headers and j["total_baris"] is None
    assert {x["employee_id"] for x in j["items"]} == {e["alfa"], e["bravo"], e["charlie"]}  # tanpa hanya_aplikasi
    assert {x["status"] for x in j["items"]} == {"cocok", "waktu_berbeda", "hanya_mesin"}
    assert j["total_karyawan_hari"] == 3 and j["terpotong"] is False


def test_banding_mode_baru_semua_status_dan_header(client, banding) -> None:
    h, dev, e = banding
    r = _get(client, h, dev, page=1, size=50)
    j = r.json()
    assert r.status_code == 200 and r.headers["X-Total-Count"] == "4" and j["total_baris"] == 4
    peta = {x["employee_id"]: x for x in j["items"]}
    assert set(peta) == set(e.values())  # karyawan kantor lain tidak ikut
    assert [peta[e[k]]["status"] for k in ("alfa", "bravo", "charlie", "delta")] == [
        "cocok", "waktu_berbeda", "hanya_mesin", "hanya_aplikasi"]
    d = peta[e["delta"]]
    assert d["pertama"] is None and d["jumlah"] == 0 and d["clock_in_at"] is not None
    assert j["total_karyawan_hari"] == 3  # ringkasan mesin tidak berubah


@pytest.mark.parametrize("status,kunci", [
    ("cocok", ["alfa"]), ("waktu_berbeda", ["bravo"]), ("hanya_mesin", ["charlie"]), ("hanya_aplikasi", ["delta"])])
def test_banding_filter_status_di_sisi_server(client, banding, status, kunci) -> None:
    h, dev, e = banding
    r = _get(client, h, dev, status=status)  # tanpa page/size: tetap mode baru
    assert r.status_code == 200 and r.headers["X-Total-Count"] == "1"
    assert [x["employee_id"] for x in r.json()["items"]] == [e[k] for k in kunci]


def test_banding_q_awalan_nama_dan_paginasi(client, banding) -> None:
    h, dev, e = banding
    assert [x["employee_id"] for x in _get(client, h, dev, q="bra").json()["items"]] == [e["bravo"]]
    assert _get(client, h, dev, q="ravo").json()["items"] == []        # bukan awalan
    assert _get(client, h, dev, q="%").json()["items"] == []           # wildcard tidak berlaku
    p1 = _get(client, h, dev, page=1, size=3)
    p2 = _get(client, h, dev, page=2, size=3)
    p3 = _get(client, h, dev, page=3, size=3)
    assert p1.headers["X-Total-Count"] == p2.headers["X-Total-Count"] == p3.headers["X-Total-Count"] == "4"
    assert len(p1.json()["items"]) == 3 and len(p2.json()["items"]) == 1 and p3.json()["items"] == []
    ids = [x["employee_id"] for x in p1.json()["items"] + p2.json()["items"]]
    assert len(set(ids)) == 4


@pytest.mark.parametrize("role,kode", [(None, 403), ("PM", 403), ("HR", 200), ("OPS", 200), ("ADMIN", 200)])
def test_banding_mode_baru_matriks_peran(client, make_user, ctx, role, kode) -> None:  # noqa: F811
    dev = _mk(client, _hdr(client, make_user, "HR"), ctx, ctx.office)
    r = client.get(f"/hikvision/devices/{dev}/bayangan", params={"page": 1, "size": 5, "status": "cocok"},
                   headers=_hdr(client, make_user, role))
    assert r.status_code == kode, r.text


def test_banding_mode_baru_kantor_lain_404_dan_validasi(client, make_user, ctx) -> None:  # noqa: F811
    h = _hdr(client, make_user, "HR")
    assert client.get(f"/hikvision/devices/{_device_in_other(ctx)}/bayangan", params={"page": 1}, headers=h
                      ).status_code == 404
    dev = _mk(client, h, ctx, ctx.office)
    url = f"/hikvision/devices/{dev}/bayangan"
    assert client.get(url, params={"status": "ngawur"}, headers=h).status_code == 422
    assert client.get(url, params={"size": 101}, headers=h).status_code == 422
    assert client.get(url, params={"q": "x" * 101}, headers=h).status_code == 422
