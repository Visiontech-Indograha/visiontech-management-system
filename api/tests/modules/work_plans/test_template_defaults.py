"""
Bawaan jenis pekerjaan sebagai template (v2_0016): satuan & fase default terpakai saat item dibuat dari template;
PM multi-divisi boleh memakai template dari divisi lain miliknya tanpa salinan; divisi orang lain ditolak.
"""
from __future__ import annotations

import uuid

from tests.conftest import World, requires_db, sync_query
from tests.daily import make_daily_plan

pytestmark = requires_db


def _template(client, division_id: str, headers: dict, **extra) -> str:
    body = {"name": f"Bawaan {uuid.uuid4().hex[:6]}", "kind": "WORK",
            "division_id": division_id, **extra}
    created = client.post("/work-types", headers=headers, json=body)
    assert created.status_code == 201, created.text
    return created.json()["id"]


def test_item_from_template_takes_default_phase_and_unit(client, world: World):
    admin = world.headers(client, "admin")
    pm = world.headers(client, "pm")
    wt = _template(client, world.unit_id, admin, unit_measure="Meter", default_phase="REPLACEMENT")
    plan = make_daily_plan(world, status="DRAFT", days_from_today=1)

    item = client.post(f"/work-plans/daily/{plan}/items", headers=pm,
                       json={"work_type_id": wt, "title": "Titik bawaan"})

    assert item.status_code == 201, item.text
    assert item.json()["task_phase"] == "REPLACEMENT"
    assert item.json()["unit_measure"] == "Meter"


def test_explicit_phase_and_unit_override_template_defaults(client, world: World):
    admin = world.headers(client, "admin")
    pm = world.headers(client, "pm")
    wt = _template(client, world.unit_id, admin, unit_measure="Meter", default_phase="REPLACEMENT")
    plan = make_daily_plan(world, status="DRAFT", days_from_today=1)

    item = client.post(f"/work-plans/daily/{plan}/items", headers=pm,
                       json={"work_type_id": wt, "title": "Titik ganti", "task_phase": "MAINTENANCE",
                             "unit_measure": "Titik"})

    assert item.status_code == 201, item.text
    assert item.json()["task_phase"] == "MAINTENANCE"
    assert item.json()["unit_measure"] == "Titik"


def test_template_without_default_phase_follows_kind(client, world: World):
    admin = world.headers(client, "admin")
    pm = world.headers(client, "pm")
    wt = _template(client, world.unit_id, admin)
    plan = make_daily_plan(world, status="DRAFT", days_from_today=1)

    item = client.post(f"/work-plans/daily/{plan}/items", headers=pm, json={"work_type_id": wt, "title": "Titik biasa"})

    assert item.status_code == 201, item.text
    assert item.json()["task_phase"] == "INSTALLATION"
    assert item.json()["unit_measure"] == "Unit"


def test_survey_default_phase_needs_survey_kind(client, world: World):
    admin = world.headers(client, "admin")

    response = client.post("/work-types", headers=admin, json={
        "name": f"Survei salah {uuid.uuid4().hex[:6]}", "kind": "WORK", "division_id": world.unit_id,
        "default_phase": "SURVEY"})

    assert response.status_code == 422, response.text


def test_pm_with_two_divisions_uses_template_of_other_own_division(client, world: World):
    admin = world.headers(client, "admin")
    pm = world.headers(client, "pm")
    other = world.add_unit(f"Lintas {world.tag}")  # PM dunia uji juga PM divisi ini
    wt = _template(client, other, admin, unit_measure="Meter", default_phase="MAINTENANCE")
    plan = make_daily_plan(world, status="DRAFT", days_from_today=1)

    item = client.post(f"/work-plans/daily/{plan}/items", headers=pm,
                       json={"work_type_id": wt, "title": "Titik lintas"})

    assert item.status_code == 201, item.text
    assert item.json()["task_phase"] == "MAINTENANCE"
    # Tanpa duplikasi: jenis pekerjaan tetap satu dan milik divisi asalnya.
    count = sync_query(
        "SELECT COUNT(*) FROM work_type WHERE name = (SELECT name FROM work_type WHERE work_type_id = %s)",
        (wt,))[0][0]
    assert count == 1


def test_pm_cannot_use_template_of_division_that_is_not_theirs(client, world: World):
    admin = world.headers(client, "admin")
    pm = world.headers(client, "pm")
    foreign = world.add_unit(f"Asing {world.tag}")
    stranger = world.add_person(f"pm_asing_{world.tag}", "PM")
    sync_query("UPDATE division SET pm_id = %s WHERE division_id = %s", (stranger, foreign))
    wt = _template(client, foreign, admin)
    plan = make_daily_plan(world, status="DRAFT", days_from_today=1)

    item = client.post(f"/work-plans/daily/{plan}/items", headers=pm, json={"work_type_id": wt, "title": "Titik asing"})

    assert item.status_code == 422, item.text


def test_copy_to_division_keeps_unit_and_default_phase(client, world: World):
    admin = world.headers(client, "admin")
    source = _template(client, world.unit_id, admin, unit_measure="Meter", default_phase="PREPARATION")
    target = world.add_unit(f"Salinan {world.tag}")

    copied = client.post(f"/work-types/{source}/copy-to-division", headers=admin, json={"division_id": target})

    assert copied.status_code == 201, copied.text
    assert copied.json()["unit_measure"] == "Meter"
    assert copied.json()["default_phase"] == "PREPARATION"
