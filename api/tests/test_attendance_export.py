"""
GET /attendance/export (P4-5): CSV absensi untuk Finance (`export:attendance`).
Jam dalam zona waktu organisasi (dulu tercetak UTC), hanya organisasi sendiri, peran lain ditolak.
"""
from __future__ import annotations

import csv
import io
from datetime import datetime, time, timedelta

from app.core.time import jakarta_now
from tests.conftest import World, requires_db

pytestmark = requires_db

INSIDE = {"lat": -6.2, "lng": 106.8}
HEADER = ["Tanggal", "NIK", "Nama", "Lokasi", "Check In", "Check Out", "Terlambat", "Pulang Cepat", "Status",
          "Kategori", "Jarak pulang (m)"]


def _check_in(client, world: World, who: str) -> None:
    response = client.post("/attendance/check-in", headers=world.headers(client, who),
                           json={"site_id": world.site_id, "location": INSIDE})
    assert response.status_code == 200, response.text


def _export(client, world: World, who: str):
    today = jakarta_now().date().isoformat()
    return client.get("/attendance/export", headers=world.headers(client, who),
                      params={"start_date": today, "end_date": today})


def test_finance_exports_own_organisation_in_local_time(client, world, other_world):
    _check_in(client, world, "member")
    _check_in(client, world, "leader")
    _check_in(client, other_world, "member")

    response = _export(client, world, "finance")
    assert response.status_code == 200, response.text
    rows = list(csv.reader(io.StringIO(response.text)))
    assert rows[0] == HEADER
    names = {r[2] for r in rows[1:]}
    assert names == {"Karyawan uji member", "Karyawan uji leader"}   # organisasi lain tidak ikut

    member = next(r for r in rows[1:] if r[2] == "Karyawan uji member")
    assert member[0] == jakarta_now().date().isoformat() and member[3] == "Gudang uji"
    now = jakarta_now()
    stamped = datetime.combine(now.date(), time.fromisoformat(member[4]), tzinfo=now.tzinfo)
    assert abs(now - stamped) < timedelta(minutes=5)   # WIB, bukan UTC
    assert member[5] == "" and member[6] in {"Ya", "Tidak"}


def test_export_needs_export_permission(client, world):
    for who in ("member", "hr", "admin"):
        assert _export(client, world, who).status_code == 403, who
