"""
GET /attendance/export (P4-5): CSV absensi untuk pemegang `export:attendance` (V2: admin).
Jam dalam WIB (dulu tercetak UTC); peran lain ditolak.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, time, timedelta

import pytest
from PIL import Image

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db

INSIDE = {"lat": -6.2, "lng": 106.8}
HEADER = ["Tanggal", "NIK", "Nama", "Lokasi", "Check In", "Check Out", "Terlambat", "Pulang Cepat", "Status",
          "Kategori", "Jarak pulang (m)", "Uang makan (Rp)"]


@pytest.fixture(autouse=True)
def _storage(fake_storage):
    return fake_storage


def _check_in(client, world: World, who: str) -> None:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (sum(map(ord, who)) % 255, 60, 90)).save(buf, "PNG")
    selfie = client.post("/files/upload", headers=world.headers(client, who),
                         files={"file": ("s.png", buf.getvalue(), "image/png")}).json()["file_id"]
    response = client.post("/attendance/check-in", headers=world.headers(client, who),
                           json={"site_id": world.site_id, "location": INSIDE, "selfie_file_id": selfie})
    assert response.status_code == 200, response.text


def _export(client, world: World, who: str):
    today = jakarta_now().date().isoformat()
    return client.get("/attendance/export", headers=world.headers(client, who),
                      params={"start_date": today, "end_date": today})


def test_admin_exports_in_local_time(client, world):
    _check_in(client, world, "member")
    _check_in(client, world, "leader")

    response = _export(client, world, "admin")
    assert response.status_code == 200, response.text
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == HEADER
    nik = {sync_query("SELECT employee_no FROM employee WHERE employee_id = %s", (world.employees[w],))[0][0]: w
           for w in ("member", "leader")}
    mine = [r for r in rows[1:] if r[1] in nik]
    assert sorted(nik[r[1]] for r in mine) == ["leader", "member"]

    member = next(r for r in mine if nik[r[1]] == "member")
    office = sync_query("SELECT name FROM office WHERE office_id = %s", (world.site_id,))[0][0]
    assert member[0] == jakarta_now().date().isoformat() and member[3] == office
    now = jakarta_now()
    stamped = datetime.combine(now.date(), time.fromisoformat(member[4]), tzinfo=now.tzinfo)
    assert abs(now - stamped) < timedelta(minutes=5)   # WIB, bukan UTC
    assert member[5] == "" and member[6] in {"Ya", "Tidak"}


def test_export_needs_export_permission(client, world):
    for who in ("member", "hr", "pm"):
        assert _export(client, world, who).status_code == 403, who
    assert _export(client, world, "admin").status_code == 200
