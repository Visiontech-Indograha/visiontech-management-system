"""Absen anggota/ketua memakai LOKASI JADWAL TIM hari itu (site, radius, koordinat), bukan kantor default.

Bila tim tak punya jadwal hari itu yang disetujui/berjalan, absen tetap memakai lokasi yang dipilih (kantor)."""
from __future__ import annotations

import io

import pytest
from PIL import Image

from tests.conftest import requires_db, sync_query
from tests.daily import make_daily_plan

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]

OFFICE = (-6.2, 106.8)  # kantor uji (world.site_id)
FAR = (-6.5, 107.0)  # lokasi tugas tim hari itu, ±40 km dari kantor uji


def _selfie(client, world, who: str) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (7, 77, 177)).save(buf, "PNG")
    res = client.post("/files/upload", headers=world.headers(client, who),
                      files={"file": ("swafoto.png", buf.getvalue(), "image/png")})
    assert res.status_code == 200, res.text
    return res.json()["file_id"]


def _day_site(world, lat: float, lng: float, status: str = "APPROVED") -> str:
    """Jadwal tim hari ini dengan lokasi tugas di (lat, lng). Kembali: daily_plan_id."""
    plan = make_daily_plan(world, status=status)
    sync_query("UPDATE work_plan_daily SET site_name = 'Lokasi tugas uji', site_lat = %s, site_lng = %s, "
               "attendance_radius_m = 150 WHERE daily_plan_id = %s", (lat, lng, plan))
    return plan


def _check_in(client, world, who: str, at: tuple[float, float]):
    body = {"site_id": world.site_id, "location": {"lat": at[0], "lng": at[1]}, "channel": "MOBILE",
            "selfie_file_id": _selfie(client, world, who)}
    return client.post("/attendance/check-in", headers=world.headers(client, who), json=body)


@pytest.mark.parametrize("who", ["member", "leader"])
def test_team_member_checks_in_at_the_day_site_though_office_is_selected(client, world, who):
    plan = _day_site(world, *FAR)

    res = _check_in(client, world, who, FAR)

    assert res.status_code == 200, res.text  # tanpa penjelasan: sudah di lokasi tugas hari itu
    assert sync_query("SELECT daily_plan_id::text FROM attendance WHERE attendance_id = %s",
                      (res.json()["id"],)) == [(plan,)]


def test_standing_inside_an_office_radius_is_still_accepted(client, world):
    """Keputusan 2026-10-09 tetap berlaku: berada dalam radius kantor mana pun → sah (tercatat di kantor itu)."""
    _day_site(world, *FAR)

    res = _check_in(client, world, "member", OFFICE)

    assert res.status_code == 200, res.text
    office, plan = sync_query("SELECT office_id, daily_plan_id FROM attendance WHERE attendance_id = %s",
                              (res.json()["id"],))[0]
    assert office is not None and plan is None  # tercatat di kantor, bukan lokasi tugas


def test_without_a_running_day_plan_the_office_stays_the_location(client, world):
    res = _check_in(client, world, "member", OFFICE)

    assert res.status_code == 200, res.text
    assert sync_query("SELECT office_id::text, daily_plan_id FROM attendance WHERE attendance_id = %s",
                      (res.json()["id"],)) == [(world.site_id, None)]


def test_draft_day_plan_is_not_a_check_in_site(client, world):
    _day_site(world, *FAR, status="DRAFT")

    res = _check_in(client, world, "member", OFFICE)

    assert res.status_code == 200, res.text
