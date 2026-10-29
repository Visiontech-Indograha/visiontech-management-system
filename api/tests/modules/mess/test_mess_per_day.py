"""
Kapasitas mess dijaga per tanggal (bukan jumlah hunian yang beririsan dalam rentang), dan hunian dapat diikat ke tim.
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta

import pytest

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query

pytestmark = requires_db


def _day(offset: int) -> str:
    return (jakarta_now().date() + timedelta(days=offset)).isoformat()


@pytest.fixture
def place_two(client, world: World) -> Iterator[dict]:
    created = client.post("/mess/places", headers=world.headers(client, "hr"), json={
        "mess_name": f"Mess harian {world.tag}", "city": "Dumai", "address": "Jl. Harian 2", "capacity": 2,
    })
    assert created.status_code == 201, created.text
    data = created.json()
    yield data
    sync_query("DELETE FROM company_mess_stay WHERE mess_id = %s RETURNING 1", (data["mess_id"],))
    sync_query("DELETE FROM company_mess WHERE mess_id = %s RETURNING 1", (data["mess_id"],))


def _stay(client, world: World, place: dict, employee: str, start: int, end: int, team: str | None = None):
    body = {"employee_id": world.employees[employee], "mess_id": place["mess_id"],
            "stay_start_date": _day(start), "stay_end_date": _day(end)}
    if team:
        body["team_id"] = team
    return client.post("/mess", headers=world.headers(client, "hr"), json=body)


def test_full_day_is_refused_with_that_date(client, world: World, place_two):
    # kapasitas 2: dua hunian pada hari ke-1 sudah penuh bagi hunian ketiga yang menyentuh hari itu
    assert _stay(client, world, place_two, "member", 1, 1).status_code == 201
    assert _stay(client, world, place_two, "leader", 1, 1).status_code == 201
    third = _stay(client, world, place_two, "hr", 1, 2)

    assert third.status_code == 409, third.text
    assert third.json()["error"]["code"] == "MESS_FULL"
    assert f"{jakarta_now().date() + timedelta(days=1):%d-%m-%Y}" in third.json()["error"]["message"]


def test_stays_on_different_days_do_not_share_capacity(client, world: World, place_two):
    """Dua hunian pada hari terpisah tidak memakan kapasitas satu sama lain: hunian ketiga yang
    membentang kedua hari tetap diterima (per hari hanya 1 dari 2)."""
    assert _stay(client, world, place_two, "member", 1, 1).status_code == 201
    assert _stay(client, world, place_two, "leader", 3, 3).status_code == 201

    spanning = _stay(client, world, place_two, "hr", 1, 3)

    assert spanning.status_code == 201, spanning.text


def test_stay_can_be_bound_to_team(client, world: World, place_two):
    created = _stay(client, world, place_two, "member", 5, 5, team=world.team_id)

    assert created.status_code == 201, created.text
    stored = sync_query("SELECT team_id::text FROM company_mess_stay WHERE mess_stay_id = %s",
                        (created.json()["mess_stay_id"],))[0][0]
    assert stored == world.team_id
