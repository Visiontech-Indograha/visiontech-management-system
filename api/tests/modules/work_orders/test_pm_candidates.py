"""
Calon PM untuk form Buat Tugas Klien (T-1). Akar masalah: GET /employees mengosongkan `system_role` karyawan lain
bagi PM (bukan HR/OM/SA), sehingga saringan web `system_role === "PROJECT_MANAGER"` kosong. Endpoint
GET /work-orders/pm-candidates menggantikannya: hanya id, nama, divisi; PM utama dan tambahan dihitung.

Aktor: `pm` (PM utama, memimpin divisi WO), `pmx` (PM utama kedua di divisi yang sama), `extra` (karyawan biasa +
peran tambahan PM), `pm2` (PM divisi lain), `staff` (karyawan biasa), `ops`, `admin`, `hr`, `leader`, `member`.
"""
from __future__ import annotations

import pytest

from app.core import system_settings
from tests.conftest import World, requires_db, sync_query
from tests.modules.role_assignments.test_role_assignments import _assign

pytestmark = requires_db

URL = "/work-orders/pm-candidates"


@pytest.fixture
def peran_ganda_aktif(monkeypatch):
    monkeypatch.setattr(system_settings, "role_assignment_enabled", lambda: True)


def _setup(client, world: World) -> dict[str, str]:
    unit2 = world.add_unit("Dua")
    pm2 = world.add_person("pm2", "PM", unit_id=unit2)
    sync_query("UPDATE division SET pm_id = %s WHERE division_id = %s", (pm2, unit2))
    pmx = world.add_person("pmx", "PM")
    extra = world.add_person("extra", None)
    world.add_person("staff", None)
    assert _assign(client, world, "extra", "PROJECT_MANAGER", world.org_id).status_code == 201
    # `add_person` tanpa unit_id memakai divisi dunia (unit_id) setelah dunia dibangun
    return {"unit2": unit2, "pm2": pm2, "pmx": pmx, "extra": extra}


def _ids(response) -> set[str]:
    assert response.status_code == 200, response.text
    return {row["employee_id"] for row in response.json()}


def test_akar_daftar_karyawan_menyembunyikan_peran_pm_dari_pm(client, world: World, peran_ganda_aktif):
    """Bukti akar: PM yang tak memimpin divisinya (`pm3`) melihat PM lain sedivisi di /employees, tetapi
    `system_role`-nya kosong (kolom sensitif hanya untuk jangkauan PM); PM tambahan terbaca EMPLOYEE."""
    s = _setup(client, world)
    world.add_person("pm3", "PM")
    rows = client.get("/employees", headers=world.headers(client, "pm3"), params={"size": 100}).json()["items"]
    by_id = {r["employee_id"]: r for r in rows}
    assert s["pmx"] in by_id and s["extra"] in by_id  # terlihat (sedivisi)...
    assert by_id[s["pmx"]]["system_role"] is None      # ...tetapi peran disembunyikan
    assert by_id[s["extra"]]["system_role"] in (None, "EMPLOYEE")
    saringan_web = [r for r in rows if r["system_role"] == "PROJECT_MANAGER"]
    assert not {r["employee_id"] for r in saringan_web} & {s["pmx"], s["extra"]}
    # kontrol: OM berhak kolom peran, jadi PM utama terbaca
    ops_rows = client.get("/employees", headers=world.headers(client, "ops"), params={"size": 100}).json()["items"]
    assert {r["employee_id"]: r["system_role"] for r in ops_rows}[s["pmx"]] == "PROJECT_MANAGER"


def test_pm_melihat_pm_utama_dan_tambahan_sedivisi(client, world: World, peran_ganda_aktif):
    s = _setup(client, world)
    r = client.get(URL, headers=world.headers(client, "pm"))
    ids = _ids(r)
    assert ids == {world.employees["pm"], s["pmx"], s["extra"]}
    assert world.employees["staff"] not in ids and s["pm2"] not in ids
    assert set(r.json()[0]) == {"employee_id", "full_name", "division_id", "division_name"}
    assert r.headers["X-Total-Count"] == "3"


def test_peran_tambahan_diabaikan_saat_fitur_peran_ganda_mati(client, world: World):
    s = _setup(client, world)
    assert s["extra"] not in _ids(client.get(URL, headers=world.headers(client, "pm")))


def test_peran_tambahan_dicabut_tidak_lagi_calon(client, world: World, peran_ganda_aktif):
    s = _setup(client, world)
    sync_query("UPDATE user_role_assignment SET delete_at = now() WHERE user_id = %s", (world.users["extra"],))
    assert s["extra"] not in _ids(client.get(URL, headers=world.headers(client, "pm")))


def test_karyawan_diarsipkan_atau_akun_nonaktif_bukan_calon(client, world: World):
    s = _setup(client, world)
    sync_query("UPDATE employee SET delete_at = now() WHERE employee_id = %s", (s["pmx"],))
    assert s["pmx"] not in _ids(client.get(URL, headers=world.headers(client, "ops")))
    sync_query("UPDATE users SET is_active = false WHERE employee_id = %s", (s["pm2"],))
    assert s["pm2"] not in _ids(client.get(URL, headers=world.headers(client, "ops")))


def test_om_dan_super_admin_melihat_semua_divisi_dan_bisa_menyaring(client, world: World, peran_ganda_aktif):
    s = _setup(client, world)
    for who in ("ops", "admin"):
        ids = _ids(client.get(URL, headers=world.headers(client, who)))
        assert {world.employees["pm"], s["pmx"], s["extra"], s["pm2"]} <= ids, who
        only2 = _ids(client.get(URL, headers=world.headers(client, who), params={"division_id": s["unit2"]}))
        assert only2 == {s["pm2"]}, who


def test_pm_divisi_di_luar_cakupan_atau_tak_ada_404(client, world: World):
    s = _setup(client, world)
    h = world.headers(client, "pm")
    assert client.get(URL, headers=h, params={"division_id": s["unit2"]}).status_code == 404
    assert client.get(URL, headers=h, params={"division_id": "00000000-0000-0000-0000-000000000000"}).status_code == 404
    assert client.get(URL, headers=world.headers(client, "ops"),
                      params={"division_id": "00000000-0000-0000-0000-000000000000"}).status_code == 404
    # PM divisi lain hanya melihat dirinya dan tidak bisa memilih divisi `pm`
    ids2 = _ids(client.get(URL, headers=world.headers(client, "pm2")))
    assert ids2 == {s["pm2"]}
    assert client.get(URL, headers=world.headers(client, "pm2"),
                      params={"division_id": world.unit_id}).status_code == 404


def test_pm_tambahan_tanpa_divisi_dipimpin_dapat_daftar_kosong(client, world: World, peran_ganda_aktif):
    _setup(client, world)
    sync_query("UPDATE employee SET division_id = NULL WHERE employee_id = %s", (world.employees["extra"],))
    r = client.get(URL, headers=world.headers(client, "extra"))
    assert r.status_code == 200 and r.json() == []


def test_pm_yang_tak_memimpin_divisinya_tetap_melihat_calon_sedivisi(client, world: World, peran_ganda_aktif):
    """Kasus akar di web: PM tanpa jangkauan kini tetap mendapat calon PM divisinya."""
    s = _setup(client, world)
    pm3 = world.add_person("pm3", "PM")
    assert _ids(client.get(URL, headers=world.headers(client, "pm3"))) == {
        world.employees["pm"], s["pmx"], s["extra"], pm3}


def test_peran_lain_ditolak_403(client, world: World):
    _setup(client, world)
    for who in ("hr", "leader", "member", "staff"):
        assert client.get(URL, headers=world.headers(client, who)).status_code == 403, who


def test_pencarian_awalan_dan_paginasi(client, world: World, peran_ganda_aktif):
    _setup(client, world)
    h = world.headers(client, "ops")
    r = client.get(URL, headers=h, params={"q": "Karyawan uji pm"})
    names = [row["full_name"] for row in r.json()]
    assert names and all(n.startswith("Karyawan uji pm") for n in names)
    assert client.get(URL, headers=h, params={"q": "uji pm"}).json() == []  # bukan "mengandung kata"
    page = client.get(URL, headers=h, params={"page": 1, "size": 2})
    assert len(page.json()) == 2 and int(page.headers["X-Total-Count"]) >= 4
    assert client.get(URL, headers=h, params={"size": 101}).status_code == 422
    assert client.get(URL, headers=h, params={"q": "x" * 101}).status_code == 422
