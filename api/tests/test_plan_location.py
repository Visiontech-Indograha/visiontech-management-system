"""
Revisi PM 2026-09-26 · Lokasi penugasan SK lewat titik koordinat.
- GET /geo/search?q= (pengelola SK; Nominatim lewat backend, di-cache)
- GET/PUT /work-plans/{id}/location — PM unit, SK draf & berjalan; teks lokasi dokumen tetap,
  site lama tidak diubah (riwayat absensi tetap sah); SK selesai/batal → 409.
"""
from __future__ import annotations

import app.modules.work_plans.services.geocode_service as geocode
from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import create_draft_plan, run_plan_to_in_progress

pytestmark = requires_db

DUMAI = {"name": "Titik gudang Dumai", "address": "Dumai, Riau", "lat": 1.6656, "lng": 101.4476, "radius_m": 150}


def test_pm_sets_point_on_draft_then_reads_it_back(client, world: World):
    plan_id, _ = create_draft_plan(client, world)
    pm = world.headers(client, "pm")

    res = client.put(f"/work-plans/{plan_id}/location", headers=pm, json=DUMAI)
    assert res.status_code == 200, res.text
    assert res.json()["radius_m"] == 150 and abs(res.json()["lat"] - 1.6656) < 1e-6

    back = client.get(f"/work-plans/{plan_id}/location", headers=pm)
    assert back.status_code == 200 and back.json()["id"] == res.json()["id"]
    plan = client.get(f"/work-plans/{plan_id}", headers=pm).json()
    assert plan["site_id"] == res.json()["id"]


def test_running_plan_location_change_is_a_signed_revision(client, world: World):
    """2026-10-09: lokasi rencana yang sudah terbit berubah lewat revisi — alasan wajib, dokumen & riwayat baru."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    pm = world.headers(client, "pm")
    before = client.get(f"/work-plans/{plan_id}", headers=pm).json()

    missing = client.put(f"/work-plans/{plan_id}/location", headers=pm, json=DUMAI)
    assert missing.status_code == 422 and "Alasan perubahan lokasi wajib" in missing.json()["error"]["message"]

    res = client.put(f"/work-plans/{plan_id}/location", headers=pm, json={**DUMAI, "reason": "Lokasi klien pindah"})
    assert res.status_code == 200, res.text
    after = client.get(f"/work-plans/{plan_id}", headers=pm).json()
    assert after["site_id"] == res.json()["id"] != before["site_id"]
    assert after["location_text"] == DUMAI["name"] != before["location_text"] and after["status"] == "IN_PROGRESS"
    revisions = client.get(f"/work-plans/{plan_id}/revisions", headers=pm).json()
    assert revisions and revisions[0]["reason"] == "Lokasi klien pindah"
    assert any(d["field"] == "location_text" for d in revisions[0]["diff"])
    # Site lama tidak diubah (absensi lama tetap merujuk titik & radius saat itu).
    assert sync_query("SELECT count(*) FROM vms.site WHERE id = %s", (before["site_id"],)) == [(1,)]
    # Nama sama disimpan lagi (penyesuaian titik) → tidak 500; nama diberi nomor karena site unik per organisasi.
    again = client.put(f"/work-plans/{plan_id}/location", headers=pm,
                       json={**DUMAI, "lat": DUMAI["lat"] + 0.001, "reason": "Geser titik"})
    assert again.status_code == 200, again.text
    assert again.json()["name"] == f"{DUMAI['name']} (2)" and again.json()["id"] != res.json()["id"]


def test_same_point_saved_again_reuses_site_instead_of_numbering(client, world: World):
    """Temuan uji: menyimpan titik yang sama berulang membuat daftar lokasi menumpuk
    ("Gudang Dumai (2)", "(3)", …). Nama + titik (≤ 5 m) + radius sama → site dipakai ulang."""
    plan_id, _ = create_draft_plan(client, world)
    pm = world.headers(client, "pm")
    first = client.put(f"/work-plans/{plan_id}/location", headers=pm, json=DUMAI)
    again = client.put(f"/work-plans/{plan_id}/location", headers=pm,
                       json={**DUMAI, "lat": DUMAI["lat"] + 0.00001})  # ±1 m
    assert again.status_code == 200, again.text
    assert again.json()["id"] == first.json()["id"] and again.json()["name"] == DUMAI["name"]
    other_plan, _ = create_draft_plan(client, world)
    shared = client.put(f"/work-plans/{other_plan}/location", headers=pm, json=DUMAI)
    assert shared.json()["id"] == first.json()["id"]
    # Radius berbeda → site baru (riwayat absensi memakai radius saat itu).
    wider = client.put(f"/work-plans/{plan_id}/location", headers=pm, json={**DUMAI, "radius_m": 300})
    assert wider.json()["id"] != first.json()["id"]


def test_only_pm_unit_and_valid_radius(client, world: World):
    plan_id, _ = run_plan_to_in_progress(client, world)
    leader = client.put(f"/work-plans/{plan_id}/location", headers=world.headers(client, "leader"), json=DUMAI)
    assert leader.status_code == 403, leader.text
    bad = client.put(f"/work-plans/{plan_id}/location", headers=world.headers(client, "pm"),
                     json={**DUMAI, "radius_m": 5})
    assert bad.status_code == 422, bad.text


def test_closed_plan_rejected(client, world: World):
    plan_id, _ = create_draft_plan(client, world)
    sync_query("UPDATE vms.work_plan SET status = 'CANCELLED', cancellation_reason = 'uji' WHERE id = %s",
               (plan_id,))
    res = client.put(f"/work-plans/{plan_id}/location", headers=world.headers(client, "pm"), json=DUMAI)
    assert res.status_code == 409, res.text


def test_geo_search_uses_cache_and_requires_manager(client, world: World, monkeypatch):
    calls: list[str] = []

    async def fake_fetch(q: str):
        calls.append(q)
        return [{"display_name": "Dumai, Riau, Indonesia", "lat": "1.6656", "lon": "101.4476", "addresstype": "city"}]

    monkeypatch.setattr(geocode, "_fetch", fake_fetch)
    monkeypatch.setattr(geocode, "_cache", {})
    pm = world.headers(client, "pm")
    first = client.get("/geo/search", params={"q": "Dumai"}, headers=pm)
    assert first.status_code == 200, first.text
    assert first.json()[0]["name"].startswith("Dumai") and first.json()[0]["lng"] == 101.4476
    client.get("/geo/search", params={"q": "  dumai "}, headers=pm)
    assert calls == ["Dumai"]                                           # kedua dari cache
    member = client.get("/geo/search", params={"q": "Dumai"}, headers=world.headers(client, "member"))
    assert member.status_code == 403
    finance = client.get("/geo/search", params={"q": "Dumai"}, headers=world.headers(client, "finance"))
    assert finance.status_code == 200, finance.text                     # pengelola lokasi kantor juga boleh cari alamat
