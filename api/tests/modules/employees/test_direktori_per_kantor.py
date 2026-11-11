"""
Direktori karyawan difilter per kantor tugas (ADR 0002 bagian 12c, B-03) dan K3 per kantor penerbit (B-16).
Matriks peran x kantor: HR kantor A tidak melihat karyawan kantor B; SA/OM tetap lintas kantor; HR yang punya
penugasan aktif di kantor B melihat keduanya; detail lintas kantor 404; HSE tambahan hanya menerbitkan K3 sasaran
perorangan di kantor penugasannya.
"""
from __future__ import annotations

import pytest

from app.core.config import settings
from tests.conftest import World, requires_db
from tests.modules.role_assignments.test_role_assignments import _assign

pytestmark = requires_db


def _ids(client, world: World, who: str) -> set[str]:
    r = client.get("/employees", headers=world.headers(client, who), params={"size": 100})
    assert r.status_code == 200, r.text
    return {i["employee_id"] for i in r.json()["items"]}


def test_hr_sees_only_own_office(client, world: World, other_world: World):
    seen = _ids(client, world, "hr")
    assert set(world.employees.values()) <= seen
    assert not (set(other_world.employees.values()) & seen)
    for emp in other_world.employees.values():
        assert client.get(f"/employees/{emp}", headers=world.headers(client, "hr")).status_code == 404
    assert client.get(f"/employees/{world.employees['member']}", headers=world.headers(client, "hr")).status_code == 200


@pytest.mark.parametrize("who", ["admin", "ops"])
def test_sa_and_om_stay_cross_office(client, world: World, other_world: World, who: str):
    r = client.get("/employees", headers=world.headers(client, who), params={"office_id": other_world.org_id})
    assert r.status_code == 200, r.text
    assert set(other_world.employees.values()) <= {i["employee_id"] for i in r.json()["items"]}
    emp = other_world.employees["member"]
    assert client.get(f"/employees/{emp}", headers=world.headers(client, who)).status_code == 200


def test_hr_with_active_assignment_in_other_office_sees_both(client, world: World, other_world: World, monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", True)
    world.add_person("x", None)
    assert _assign(client, world, "x", "ADMIN_HR_GA", other_world.org_id).status_code == 201
    seen = _ids(client, world, "x")
    assert set(other_world.employees.values()) <= seen and world.employees["x"] in seen


def test_employee_role_scope_unchanged(client, world: World, other_world: World):
    seen = _ids(client, world, "member")
    assert not (set(other_world.employees.values()) & seen)


# ── K3 per kantor penerbit (B-16) ─────────────────────────────────────────────
def _payload(**extra):
    return {"title": "K3 uji", "content_html": "<p>isi</p>", "start_date": "2026-11-01",
            "end_date": "2026-12-01", "cooldown_seconds": 5, **extra}


def test_extra_hse_cannot_publish_k3_to_other_office(client, world: World, other_world: World, monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", True)
    world.add_person("x", None)
    assert _assign(client, world, "x", "HSE", world.org_id).status_code == 201
    h = world.headers(client, "x")
    mine, theirs = world.users["member"], other_world.users["member"]
    # audiens luas menjangkau kantor lain -> ditolak
    assert client.post("/hse/campaigns", headers=h, json=_payload(target_audience="ALL")).status_code == 403
    # sasaran perorangan kantor lain -> ditolak; campuran juga
    for ids in ([theirs], [mine, theirs]):
        r = client.post("/hse/campaigns", headers=h,
                        json=_payload(target_audience="INDIVIDUAL", target_user_ids=ids))
        assert r.status_code == 403, r.text
    ok = client.post("/hse/campaigns", headers=h, json=_payload(target_audience="INDIVIDUAL", target_user_ids=[mine]))
    assert ok.status_code == 201, ok.text
    cid = ok.json()["campaign_id"]
    # ubah sasaran ke kantor lain ditolak
    r = client.put(f"/hse/campaigns/{cid}", headers=h, json={"target_user_ids": [theirs]})
    assert r.status_code == 403
    # kampanye luas milik admin: 404 untuk ubah dan hapus (IDOR)
    wide = client.post("/hse/campaigns", headers=world.headers(client, "admin"), json=_payload(target_audience="ALL"))
    assert wide.status_code == 201, wide.text
    wid = wide.json()["campaign_id"]
    assert client.put(f"/hse/campaigns/{wid}", headers=h, json={"title": "x"}).status_code == 404
    assert client.delete(f"/hse/campaigns/{wid}", headers=h).status_code == 404
    assert client.delete(f"/hse/campaigns/{cid}", headers=h).status_code == 200


def test_primary_hse_and_flag_off_unrestricted(client, world: World, other_world: World, monkeypatch):
    monkeypatch.setattr(settings, "ROLE_ASSIGNMENT_ENABLED", False)
    world.add_person("h", "HSE")
    r = client.post("/hse/campaigns", headers=world.headers(client, "h"), json=_payload(target_audience="ALL"))
    assert r.status_code == 201, r.text


def test_finance_gets_no_office_wide_directory(client, world: World, other_world: World):
    """B-32: izin FIN ke Direktori: Finance tidak membawa izin direktori penuh, dan tak pernah lintas kantor."""
    world.add_person("fin", "FINANCE")
    seen = _ids(client, world, "fin")
    assert not (set(other_world.employees.values()) & seen)
    emp = other_world.employees["member"]
    assert client.get(f"/employees/{emp}", headers=world.headers(client, "fin")).status_code == 404
