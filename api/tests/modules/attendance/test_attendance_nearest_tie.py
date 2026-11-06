"""Jarak seri antar kantor (koordinat & radius sama) harus deterministik: kantor karyawan sendiri, lalu id terkecil.

Regresi flaky `attendance_office_id_fkey`: dulu pilihan acak, bisa jatuh ke kantor milik tes lain."""
from __future__ import annotations

import io
import uuid
from collections.abc import Iterator

import pytest
from PIL import Image

from tests.conftest import requires_db, sync_query
from tests.daily import make_daily_plan

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]

FAR = (-6.5, 107.0)


@pytest.fixture
def spot() -> Iterator[tuple[float, float]]:
    """Titik unik per tes (tak ada kantor lain di sana) agar seri hanya antar kantor buatan tes ini."""
    n = uuid.uuid4().int
    yield (-10.0 - (n % 10000) / 10000.0, 120.0 + ((n >> 20) % 10000) / 10000.0)


def _office(office_id: str, at: tuple[float, float]) -> None:
    sync_query("INSERT INTO office (office_id, name, address, latitude, longitude) VALUES (%s, %s, 'Jl. Uji', %s, %s)",
               (office_id, f"Kantor seri {office_id[-6:]}", at[0], at[1]))


def _check_in(client, world, at: tuple[float, float]) -> str:
    plan = make_daily_plan(world)  # lokasi tugas jauh -> lokasi terpilih di luar radius, jatuh ke "terdekat"
    sync_query("UPDATE work_plan_daily SET site_name = 'Tugas', site_lat = %s, site_lng = %s, "
               "attendance_radius_m = 150 WHERE daily_plan_id = %s", (*FAR, plan))
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (7, 77, 177)).save(buf, "PNG")
    up = client.post("/files/upload", headers=world.headers(client, "member"),
                     files={"file": ("swafoto.png", buf.getvalue(), "image/png")})
    body = {"site_id": world.site_id, "location": {"lat": at[0], "lng": at[1]}, "channel": "MOBILE",
            "selfie_file_id": up.json()["file_id"]}
    res = client.post("/attendance/check-in", headers=world.headers(client, "member"), json=body)
    assert res.status_code == 200, res.text
    return str(sync_query("SELECT office_id::text FROM attendance WHERE attendance_id = %s",
                          (res.json()["id"],))[0][0])


def test_tie_prefers_the_employees_own_office_even_if_other_has_smaller_id(client, world, spot):
    smaller = "00000000-0000-7000-8000-" + uuid.uuid4().hex[:12]  # lebih kecil dari UUIDv7 mana pun
    try:
        _office(smaller, spot)
        sync_query("UPDATE office SET latitude = %s, longitude = %s WHERE office_id = %s", (*spot, world.site_id))
        assert _check_in(client, world, spot) == world.site_id
    finally:
        sync_query("DELETE FROM attendance WHERE office_id = %s", (smaller,))
        sync_query("DELETE FROM office WHERE office_id = %s", (smaller,))


def test_tie_without_own_office_is_decided_by_smallest_id(client, world, spot):
    first = "00000000-0000-7000-8000-" + uuid.uuid4().hex[:12]
    second = "00000000-0000-7000-9000-" + uuid.uuid4().hex[:12]
    try:
        _office(second, spot)  # disisipkan lebih dulu, id lebih besar
        _office(first, spot)
        assert _check_in(client, world, spot) == first
    finally:
        sync_query("DELETE FROM attendance WHERE office_id IN (%s, %s)", (first, second))
        sync_query("DELETE FROM office WHERE office_id IN (%s, %s)", (first, second))
