"""
Skenario E2E P1 lewat API: PM menugaskan survei WO ke tim (ketua TEAM_LEADER + 2 anggota) dengan data
persis seperti web (tanggal default hari ini, lead_team_id), lalu ketua & anggota membuka daftar survei HP.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime

from tests.conftest import World, requires_db, sync_query
from tests.orders import make_client

pytestmark = requires_db


def test_pm_assigns_survey_created_via_api_leader_and_members_see_it(client, world: World):
    tag = uuid.uuid4().hex[:6]
    ops = world.headers(client, "admin")
    tl = world.add_person("tl1", "LEADER")
    techs = [world.add_person(f"tek{i}", None) for i in (1, 2)]
    team = client.post("/teams", headers=ops, json={
        "office_id": world.org_id, "division_id": world.unit_id, "leader_employee_id": tl,
        "name": f"Tim-Riau-{tag}"})
    assert team.status_code == 201, team.text
    team_id = team.json()["team_id"]
    for emp in techs:
        added = client.post(f"/teams/{team_id}/members", headers=ops, json={"employee_id": emp})
        assert added.status_code == 201, added.text

    client_id = make_client()
    site_id = str(sync_query(
        "INSERT INTO client_sites (client_id, site_name, address, latitude, longitude) "
        "VALUES (%s, 'Site uji', 'Jl. Uji', -6.2, 106.8) RETURNING site_id", (client_id,))[0][0])
    pm = world.headers(client, "pm")
    # Seperti web: WO dibuat tanpa tim; tim dipilih di dialog "Tugaskan survei".
    created = client.post("/work-orders", headers=pm, json={
        "client_id": client_id, "client_site_id": site_id, "division_id": world.unit_id,
        "pm_id": world.employees["pm"], "title": f"WO CCTV {tag}"})
    assert created.status_code == 201, created.text
    wo = created.json()["work_order_id"]
    assert created.json()["status"] == "WAITING_SURVEY"

    today = datetime.now(UTC).date().isoformat()  # web: new Date().toISOString().split("T")[0]
    res = client.post(f"/work-orders/{wo}/assign-survey", headers=pm,
                      json={"lead_team_id": team_id, "survey_date": today})
    assert res.status_code == 200, res.text
    body = res.json()
    assert body["status"] == "SURVEY_IN_PROGRESS" and body["lead_team_id"] == team_id
    assert f"Tim-Riau-{tag}" in body["survey_assignment_summary"]

    for who in ("tl1", "tek1", "tek2"):
        rows = client.get("/work-orders/team-surveys", headers=world.headers(client, who))
        assert rows.status_code == 200, rows.text
        data = rows.json()
        assert [r["work_order_id"] for r in data] == [wo], who
        assert data[0]["survey_date"] == today and data[0]["site_name"] == "Site uji"
        assert data[0]["surveyor_team_id"] == team_id

    # Penugasan ulang (dua kali) tidak membuat survei tanpa tim.
    again = client.post(f"/work-orders/{wo}/assign-survey", headers=pm,
                        json={"lead_team_id": team_id, "survey_date": today})
    assert again.status_code == 200, again.text
    assert tuple(sync_query(
        "SELECT COUNT(*), COUNT(surveyor_team_id) FROM work_order_surveys WHERE work_order_id = %s",
        (wo,))[0]) == (1, 1)
    assert len(client.get("/work-orders/team-surveys", headers=world.headers(client, "tl1")).json()) == 1
