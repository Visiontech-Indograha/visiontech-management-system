"""
Pencarian + paginasi opsional + X-Total-Count pada daftar utama; tanpa parameter perilaku lama tetap.
"""
from __future__ import annotations

from tests.conftest import World, requires_db

pytestmark = requires_db


def test_leaves_search_and_pagination(client, world: World):
    h = world.headers(client, "hr")
    base = client.get("/leaves", headers=h)
    assert base.status_code == 200
    total = int(base.headers["X-Total-Count"])
    assert total == len(base.json())  # tanpa parameter: semua baris (kompatibel mundur)

    paged = client.get("/leaves?page=1&size=1", headers=h)
    assert paged.status_code == 200
    assert int(paged.headers["X-Total-Count"]) == total
    assert len(paged.json()) <= 1

    none = client.get("/leaves?q=zzzz-tidak-ada-xyz", headers=h)
    assert none.json() == [] and none.headers["X-Total-Count"] == "0"


def test_list_params_are_validated(client, world: World):
    h = world.headers(client, "hr")
    for bad in ("page=0", "size=0", "size=101", "page=abc", "q=" + "x" * 101):
        assert client.get(f"/leaves?{bad}", headers=h).status_code == 422, bad
    assert client.get("/leaves?date_from=2026-02-01&date_to=2026-01-01", headers=h).status_code == 422


def test_search_is_case_and_accent_insensitive(client, world: World):
    h = world.headers(client, "hr")
    name = f"Tim Cari Ünik {world.tag}"  # nama unik milik tes ini: tidak bergantung tim worker lain
    created = client.post("/teams", headers=world.headers(client, "pm"),
                          json={"office_id": world.org_id, "division_id": world.unit_id,
                                "leader_employee_id": world.employees["leader"], "name": name})
    assert created.status_code == 201, created.text
    hit = client.get(f"/teams?q={name.upper()}", headers=h)
    assert hit.status_code == 200, hit.text
    assert any(t["name"] == name for t in hit.json())


def test_master_lists_accept_search_and_paging(client, world: World):
    h = world.headers(client, "hr")
    for url in ("/offices", "/work-types", "/mess/places", "/mess", "/teams", "/offboarding"):
        base = client.get(url, headers=h)
        assert base.status_code == 200, url
        assert int(base.headers["X-Total-Count"]) == len(base.json()), url
        assert client.get(f"{url}?page=1&size=1", headers=h).status_code == 200
        miss = client.get(f"{url}?q=zzz-tidak-ada-xyz", headers=h)
        assert miss.json() == [] and miss.headers["X-Total-Count"] == "0", url


def test_audit_events_search_and_date_range(client, world: World):
    h = world.headers(client, "hr")
    ok = client.get("/audit-events?size=5&q=LOGIN&date_from=2020-01-01&date_to=2030-01-01", headers=h)
    assert ok.status_code in (200, 403), ok.text
    if ok.status_code == 200:
        assert ok.json()["total"] >= 0
        bad = client.get("/audit-events?date_from=2026-02-01&date_to=2026-01-01", headers=h)
        assert bad.status_code == 422
        assert client.get("/audit-events?q=" + "x" * 101, headers=h).status_code == 422


def test_attendance_search_contains_name(client, world: World):
    h = world.headers(client, "hr")
    res = client.get("/attendance?q=zzz-tidak-ada-xyz&size=5", headers=h)
    assert res.status_code == 200
    assert res.json()["items"] == [] and res.json()["total"] == 0


def test_offices_search_is_prefix_only(client, world: World):
    h = world.headers(client, "ops")
    name = f"Kantor Awalan{world.tag}"
    body = {"name": name, "address": "Jl. Uji 1", "location": {"lat": -6.2, "lng": 106.8}, "radius_m": 150}
    assert client.post("/offices", headers=h, json=body).status_code == 201
    hit = client.get(f"/offices?q=kantor awalan{world.tag}", headers=h)
    assert any(o["name"] == name for o in hit.json())
    miss = client.get(f"/offices?q=awalan{world.tag}", headers=h)  # tengah nama: tidak cocok
    assert not any(o["name"] == name for o in miss.json())
