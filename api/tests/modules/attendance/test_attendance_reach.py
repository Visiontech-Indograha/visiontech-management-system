"""
A7 · Jangkauan PM atas absensi (lanjutan A1) dan peran FINANCE.

PM berwenang atas absensi karyawan divisinya (division.pm_id) DAN anggota/ketua tim pada jadwal harian yang
proyeknya ia kelola (project.pm_id). PM lain yang tidak berhubungan tetap tidak melihat, tidak meninjau, dan
tidak membuka swafoto. FINANCE melihat, meninjau, dan mengekspor absensi seluruh karyawan.
"""
from __future__ import annotations

import io
import uuid

import pytest
from PIL import Image

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.daily import make_daily_plan

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _check_in(client, world: World, who: str, lat: float, explanation: str | None) -> tuple[str, str]:
    """Absen masuk karyawan `who` dengan swafoto → (attendance_id, file_id swafoto)."""
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (7, 77, 177)).save(buf, "PNG")
    selfie = client.post("/files/upload", headers=world.headers(client, who),
                         files={"file": ("swafoto.png", buf.getvalue(), "image/png")})
    assert selfie.status_code == 200, selfie.text
    body = {"site_id": world.site_id, "location": {"lat": lat, "lng": 106.8}, "channel": "MOBILE",
            "selfie_file_id": selfie.json()["file_id"]}
    if explanation:
        body["explanation"] = explanation
    check_in = client.post("/attendance/check-in", headers=world.headers(client, who), json=body)
    assert check_in.status_code == 200, check_in.text
    return check_in.json()["id"], selfie.json()["file_id"]


def _member_check_in(client, world: World) -> tuple[str, str]:
    """Absen anggota di luar radius (menunggu peninjauan)."""
    return _check_in(client, world, "member", -6.3, "Survei titik di luar lokasi")


def _unrelated_pm(world: World, who: str) -> None:
    """PM yang memimpin divisi lain tanpa jadwal/proyek yang bersinggungan dengan tim uji."""
    unit = world.add_unit(f"Lepas {who}")
    emp = world.add_person(who, "PM", unit_id=unit)
    sync_query("UPDATE division SET pm_id = %s WHERE division_id = %s", (emp, unit))


def _managed_project_plan(world: World, pm_who: str) -> str:
    """Jadwal harian tim uji (divisi dunia uji) yang proyeknya dikelola `pm_who` (bukan PM divisi itu)."""
    unit = world.add_unit(f"Proyek {pm_who}")
    emp = world.add_person(pm_who, "PM", unit_id=unit)
    sync_query("UPDATE division SET pm_id = %s WHERE division_id = %s", (emp, unit))
    tag = uuid.uuid4().hex[:10]
    client_id = sync_query(
        "INSERT INTO client (client_code, name) VALUES (%s, %s) RETURNING client_id", (f"UJI-{tag}", f"Klien {tag}")
    )[0][0]
    project_id = sync_query(
        "INSERT INTO project (client_id, office_id, division_id, pm_id, spk_number, project_title, "
        "start_date, end_date) VALUES (%s, %s, %s, %s, %s, 'Proyek uji jangkauan', '2026-01-01', '2026-12-31') "
        "RETURNING project_id",
        (client_id, world.org_id, unit, emp, f"SPK/UJI/{tag}"))[0][0]
    plan = make_daily_plan(world, status="ONGOING")
    sync_query("UPDATE work_plan_daily SET project_id = %s WHERE daily_plan_id = %s", (project_id, plan))
    return plan


def jakarta_now_month() -> str:
    return jakarta_now().date().strftime("%Y-%m")


def _listed(client, world: World, who: str) -> set[str]:
    response = client.get("/attendance", headers=world.headers(client, who))
    assert response.status_code == 200, response.text
    return {row["id"] for row in response.json()["items"]}


def test_pm_of_managed_project_sees_and_reviews_team_member_attendance(client, world: World):
    att_id, file_id = _member_check_in(client, world)
    _managed_project_plan(world, "pm_proyek")
    # Anggota tim uji ada di jadwal yang proyeknya dikelola pm_proyek → terlihat dan bisa ditinjau.
    assert att_id in _listed(client, world, "pm_proyek")
    reviewed = client.post(f"/attendance/{att_id}/review", headers=world.headers(client, "pm_proyek"),
                           json={"is_approved": True, "note": "Diperiksa PM proyek"})
    assert reviewed.status_code == 200, reviewed.text
    assert client.get(f"/files/{file_id}/url", headers=world.headers(client, "pm_proyek")).status_code == 200


def test_pm_of_managed_project_sees_team_leader_attendance_too(client, world: World):
    _managed_project_plan(world, "pm_proyek2")
    leader_att_id, _ = _check_in(client, world, "leader", -6.3, "Pengecekan lokasi ketua")
    assert leader_att_id in _listed(client, world, "pm_proyek2")


def test_unrelated_pm_does_not_see_or_review_or_open_selfie(client, world: World):
    att_id, file_id = _member_check_in(client, world)
    _unrelated_pm(world, "pm_lepas")
    assert att_id not in _listed(client, world, "pm_lepas")
    denied = client.post(f"/attendance/{att_id}/review", headers=world.headers(client, "pm_lepas"),
                         json={"is_approved": True})
    assert denied.status_code in (403, 404), denied.text
    assert client.get(f"/files/{file_id}/url", headers=world.headers(client, "pm_lepas")).status_code == 404


def test_finance_sees_reviews_and_exports_all_attendance(client, world: World):
    att_id, _ = _member_check_in(client, world)
    world.add_person("fin", "FINANCE")
    assert att_id in _listed(client, world, "fin")
    reviewed = client.post(f"/attendance/{att_id}/review", headers=world.headers(client, "fin"),
                           json={"is_approved": True, "note": "Diperiksa Finance"})
    assert reviewed.status_code == 200, reviewed.text
    export = client.get("/attendance/export", params={"start_date": "2026-01-01", "end_date": "2026-12-31"},
                        headers=world.headers(client, "fin"))
    assert export.status_code == 200, export.text


def test_monitor_recap_follows_the_same_reach(client, world: World):
    """Rekap bulanan (monitor) memakai jangkauan yang sama: anggota tim pada proyek PM terlihat, PM lain tidak."""
    _check_in(client, world, "member", -6.3, "Survei titik di luar lokasi")
    _managed_project_plan(world, "pm_rekap")
    _unrelated_pm(world, "pm_rekap_lepas")
    month = jakarta_now_month()

    def _employees(who: str) -> set[str]:
        response = client.get("/recaps/attendance", headers=world.headers(client, who), params={"month": month})
        assert response.status_code == 200, response.text
        return {row["employee_id"] for row in response.json()["employees"]}

    assert world.employees["member"] in _employees("pm_rekap")
    assert world.employees["member"] not in _employees("pm_rekap_lepas")
