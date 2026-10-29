"""
Rekap uang makan untuk PM yang memimpin dua divisi: tiap divisi yang ia pimpin bisa direkap (sebelumnya hanya
satu divisi yang diambil, sisanya 403).
"""
from __future__ import annotations

from datetime import timedelta

from app.core.time import jakarta_now
from tests.conftest import World, requires_db

pytestmark = requires_db


def _range() -> dict[str, str]:
    today = jakarta_now().date()
    return {"start_date": (today - timedelta(days=3)).isoformat(), "end_date": today.isoformat()}


def test_pm_with_two_divisions_can_recap_each_division(client, world: World, fake_storage):
    second = world.add_unit("Dua")
    headers = world.headers(client, "pm")
    for division in (world.unit_id, second):
        response = client.get("/attendance/meal-allowance", headers=headers,
                              params={**_range(), "division_id": division})
        assert response.status_code == 200, (division, response.text)
    combined = client.get("/attendance/meal-allowance", headers=headers, params=_range())
    assert combined.status_code == 200, combined.text
