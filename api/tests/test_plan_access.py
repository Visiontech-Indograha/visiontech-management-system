"""
V-07 · Penjaga keterlibatan pekerjaan. Kewenangan mengikuti SK, bukan jabatan:
SK tak terlihat / organisasi lain → 404; terlihat tetapi tak berwenang → 403.
Terlihat & mengelola mengikuti `domain.js` visiblePlans & permissions (OPS = PM lintas unit).
"""
from __future__ import annotations

from datetime import timedelta

import pytest

from app.core.time import jakarta_now
from app.services.access_service import PlanNeed, satisfies
from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import create_draft_plan, run_plan_to_in_progress

pytestmark = requires_db


def _rv(plan_id: str) -> int:
    return sync_query("SELECT row_version FROM vms.work_plan WHERE id = %s", (plan_id,))[0][0]


def _add_other_unit_pm(world: World) -> str:
    """PM unit lain di organisasi yang sama. → unit_id."""
    unit = world.add_unit("WALL_DISPLAY")
    world.add_person("pm_other", "PM", unit, per_unit=True)
    return unit


def _extension(client, world, plan_id, who):
    end = jakarta_now().date() + timedelta(days=5)
    return client.post(f"/work-plans/{plan_id}/changes", headers=world.headers(client, who),
                       json={"type": "EXTEND", "new_period_end": end.isoformat(), "reason": "Material terlambat"})


# ── Aturan murni ───────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize(("need", "manages", "leader", "member", "allowed"), [
    (PlanNeed.VIEW, False, False, False, True),
    (PlanNeed.PM_UNIT, True, False, False, True),
    (PlanNeed.PM_UNIT, False, True, True, False),
    (PlanNeed.LEADER, True, False, True, False),     # PM/OPS/anggota bukan ketua
    (PlanNeed.LEADER, False, True, True, True),
    (PlanNeed.MEMBER, True, False, False, False),
    (PlanNeed.MEMBER, False, False, True, True),
    (PlanNeed.LEADER_OR_MEMBER, False, True, False, True),
    (PlanNeed.LEADER_OR_MEMBER, False, False, True, True),
    (PlanNeed.LEADER_OR_MEMBER, True, False, False, False),
])
def test_needs(need, manages, leader, member, allowed):
    assert satisfies(need, manages=manages, is_leader=leader, is_member=member) is allowed


# ── SK draf: hanya pengelola unit yang melihat & mengubah ─────────────────────────────────────
@pytest.mark.parametrize(("who", "expected"), [
    ("pm", 200), ("ops", 200), ("admin", 200),
    ("pm_other", 404),                    # PM unit lain: SK draf unit ini tidak terlihat
    ("leader", 404), ("member", 404),     # draf belum terlihat oleh tim (visiblePlans)
    ("asset", 404), ("hr", 404), ("finance", 404),
])
def test_draft_plan_is_managed_only_by_its_unit(client, world, who, expected):
    _add_other_unit_pm(world)
    plan_id, _ = create_draft_plan(client, world)
    headers = world.headers(client, who)

    assert client.get(f"/work-plans/{plan_id}", headers=headers).status_code == expected
    response = client.put(f"/work-plans/{plan_id}/members", headers=headers, json={
        "leader_employee_id": world.employees["leader"],
        "member_employee_ids": [world.employees["member"]], "row_version": _rv(plan_id)})
    assert response.status_code == expected, response.text
    if expected == 200:  # tulis → baca ulang
        assert sync_query("SELECT count(*) FROM vms.work_plan_member WHERE work_plan_id = %s", (plan_id,)) == [(2,)]


# ── SK berjalan: terlihat oleh tim & ASSET; tindakan tetap sesuai kedudukan ───────────────────
@pytest.mark.parametrize(("who", "view", "publish", "extension"), [
    ("pm", 200, 409, 403),        # boleh mengelola (status sudah bukan DRAFT → 409), bukan ketua
    ("ops", 200, 409, 403),
    ("admin", 200, 409, 403),
    ("leader", 200, 403, 201),    # hanya ketua menurut SK yang mengajukan perpanjangan
    ("member", 200, 403, 403),
    ("asset", 200, 403, 403),
    ("pm_other", 404, 404, 404),
    ("hr", 404, 404, 404),
    ("finance", 404, 404, 404),
])
def test_running_plan_actions_follow_standing(client, world, who, view, publish, extension):
    _add_other_unit_pm(world)
    plan_id, _ = run_plan_to_in_progress(client, world)
    headers = world.headers(client, who)

    assert client.get(f"/work-plans/{plan_id}", headers=headers).status_code == view
    published = client.post(f"/work-plans/{plan_id}/publish", headers=headers, json={"row_version": _rv(plan_id)})
    assert published.status_code == publish, published.text
    requested = _extension(client, world, plan_id, who)
    assert requested.status_code == extension, requested.text
    stored = sync_query("SELECT count(*) FROM vms.plan_change WHERE work_plan_id = %s", (plan_id,))[0][0]
    assert stored == (1 if extension == 201 else 0)


def test_plan_of_another_organisation_is_404(client, world, other_world):
    foreign_id, _ = create_draft_plan(client, other_world)

    for who in ("admin", "ops", "pm"):
        headers = world.headers(client, who)
        assert client.get(f"/work-plans/{foreign_id}", headers=headers).status_code == 404
        response = client.put(f"/work-plans/{foreign_id}/members", headers=headers, json={
            "leader_employee_id": None, "member_employee_ids": [], "row_version": _rv(foreign_id)})
        assert response.status_code == 404, response.text
        assert foreign_id not in {p["id"] for p in client.get("/work-plans", headers=headers).json()}
    assert sync_query("SELECT count(*) FROM vms.work_plan_member WHERE work_plan_id = %s", (foreign_id,)) == [(1,)]


def test_plan_list_shows_only_visible_plans(client, world):
    other_unit = _add_other_unit_pm(world)
    own_id, _ = create_draft_plan(client, world)
    start = jakarta_now().date()
    other = client.post("/work-plans", headers=world.headers(client, "pm_other"), json={
        "title": "Pasang videowall", "unit_id": other_unit, "location_text": "Lobi",
        "period_start": start.isoformat(), "period_end": start.isoformat(),
        "pm_employee_id": world.employees["pm_other"]})
    assert other.status_code == 201, other.text
    other_id = other.json()["id"]

    def listed(who: str) -> set[str]:
        response = client.get("/work-plans", headers=world.headers(client, who))
        assert response.status_code == 200, response.text
        return {p["id"] for p in response.json()} & {own_id, other_id}

    assert listed("pm") == {own_id}
    assert listed("pm_other") == {other_id}
    assert listed("ops") == listed("admin") == {own_id, other_id}
    assert listed("leader") == listed("asset") == listed("hr") == set()   # keduanya masih draf


@pytest.mark.parametrize(("who", "expected"), [("pm", 403), ("ops", 201), ("admin", 201), ("pm_other", 201)])
def test_plan_is_created_only_by_a_manager_of_its_unit(client, world, who, expected):
    other_unit = _add_other_unit_pm(world)
    start = jakarta_now().date()
    response = client.post("/work-plans", headers=world.headers(client, who), json={
        "title": "Pasang videowall", "unit_id": other_unit, "location_text": "Lobi",
        "period_start": start.isoformat(), "period_end": start.isoformat(),
        "pm_employee_id": world.employees["pm_other"]})

    assert response.status_code == expected, response.text
    assert sync_query("SELECT count(*) FROM vms.work_plan WHERE unit_id = %s", (other_unit,)) \
        == [(1 if expected == 201 else 0,)]


def test_plan_cannot_be_created_for_a_unit_of_another_organisation(client, world, other_world):
    start = jakarta_now().date()
    response = client.post("/work-plans", headers=world.headers(client, "ops"), json={
        "title": "Pasang videowall", "unit_id": other_world.unit_id, "location_text": "Lobi",
        "period_start": start.isoformat(), "period_end": start.isoformat(),
        "pm_employee_id": world.employees["pm"]})

    assert response.status_code == 404, response.text


# ── R3 · ketua diganti lewat adendum personel ─────────────────────────────────────────────────
@pytest.mark.parametrize("old_leader_stays_member", [True, False])
def test_replaced_leader_loses_leader_rights_and_keeps_member_rights_only_if_listed(
        client, world, old_leader_stays_member):
    """Dok 07 R3. Adendum berlaku di hari pertama SK — baris ketua lama ditutup pada hari yang sama."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    new_leader = world.add_person("leader2", None)
    members = [world.employees["member"]] + ([world.employees["leader"]] if old_leader_stays_member else [])
    # Alur sungguhan (V-22): PM mengajukan adendum personel → ketua baru menerimanya.
    requested = client.post(f"/work-plans/{plan_id}/changes", headers=world.headers(client, "pm"), json={
        "type": "PERSONNEL", "leader_employee_id": new_leader, "member_employee_ids": members,
        "reason": "Ketua dipindahtugaskan"})
    assert requested.status_code == 201, requested.text
    accepted = client.post(f"/changes/{requested.json()['id']}/accept", headers=world.headers(client, "leader2"),
                           json={})
    assert accepted.status_code == 200, accepted.text

    # Ketua baru memegang hak ketua hari itu juga; ketua lama ditolak.
    assert _extension(client, world, plan_id, "leader2").status_code == 201
    assert _extension(client, world, plan_id, "leader").status_code == (403 if old_leader_stays_member else 404)
    # Hak anggota (melihat SK) tetap ada hanya bila masih terdaftar.
    assert client.get(f"/work-plans/{plan_id}", headers=world.headers(client, "leader")).status_code \
        == (200 if old_leader_stays_member else 404)


def test_day_of_another_plan_is_404_under_this_plan_path(client, world):
    """V-16 · `/work-plans/{id}/days/{day_id}`: hari harus milik SK di jalur, walau keduanya boleh dikelola."""
    plan_a, _ = create_draft_plan(client, world)
    world.add_person("other_leader", None)  # R-26: ketua harus staf lapangan, bukan peran kantor
    _, days_b = create_draft_plan(client, world, start_offset_days=30, leader="other_leader")

    response = client.post(f"/work-plans/{plan_a}/days/{days_b[0]}/tasks", headers=world.headers(client, "pm"),
                           json={"title": "Tugas nyasar"})

    assert response.status_code == 404, response.text
    assert sync_query("SELECT count(*) FROM vms.work_plan_task WHERE title = 'Tugas nyasar'") == [(0,)]
