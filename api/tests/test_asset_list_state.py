"""
R-19 · M6/R9 dari layar: daftar aset membawa alokasi yang sedang berjalan dan pengajuan pengembalian
yang menunggu — tanpa ini web tidak tahu `alloc_id`/`return_id`, sehingga ketua tidak bisa
mengembalikan aset dan petugas aset tidak bisa memeriksanya (siklus hanya bisa lewat API).
"""
from __future__ import annotations

from tests.conftest import World, requires_db
from tests.test_flow_plans import run_plan_to_in_progress

pytestmark = requires_db


def _item(client, world: World, asset_id: str, who: str = "leader") -> dict:
    listed = client.get("/assets", headers=world.headers(client, who))
    assert listed.status_code == 200, listed.text
    return next(a for a in listed.json() if a["id"] == asset_id)


def test_asset_list_carries_allocation_and_pending_return(client, world: World):
    plan_id, _ = run_plan_to_in_progress(client, world)
    officer, leader = world.headers(client, "asset"), world.headers(client, "leader")
    asset_id = client.post("/assets", headers=officer, json={
        "kind": "TOOL", "code": "TL-L1", "name": "Tangga lipat", "condition": "Baik"}).json()["id"]

    idle = _item(client, world, asset_id)
    assert idle["allocation_id"] is None and idle["pending_return_id"] is None

    alloc = client.post(f"/assets/{asset_id}/reserve", headers=officer, json={"work_plan_id": plan_id}).json()
    held = _item(client, world, asset_id)
    assert (held["allocation_id"], held["work_plan_id"], held["leader_employee_id"]) == \
        (alloc["id"], plan_id, world.employees["leader"])
    assert held["plan_number"] and held["pending_return_id"] is None

    ret = client.post(f"/assets/allocations/{alloc['id']}/return", headers=leader,
                      json={"condition_on_return": "Baik", "note": "Selesai dipakai"}).json()
    pending = _item(client, world, asset_id, "asset")
    assert pending["status"] == "RETURN_PENDING"
    assert (pending["pending_return_id"], pending["return_condition"], pending["return_note"],
            pending["return_requested_by_name"]) == (ret["id"], "Baik", "Selesai dipakai", "Karyawan uji leader")

    assert client.post(f"/assets/returns/{ret['id']}/verify", headers=officer,
                       json={"is_accepted": True, "note": "Lengkap"}).status_code == 200
    back = _item(client, world, asset_id)
    assert back["status"] == "AVAILABLE" and back["allocation_id"] is None and back["pending_return_id"] is None


# ── Riwayat pengembalian & BAST (P6-4 "berita acara") ─────────────────────────────────────────
def _cycle(client, world: World) -> tuple[str, str]:
    plan_id, _ = run_plan_to_in_progress(client, world)
    officer, leader = world.headers(client, "asset"), world.headers(client, "leader")
    asset_id = client.post("/assets", headers=officer, json={
        "kind": "TOOL", "code": "TL-B1", "name": "Bor listrik", "condition": "Baik"}).json()["id"]
    alloc = client.post(f"/assets/{asset_id}/reserve", headers=officer, json={"work_plan_id": plan_id}).json()
    ret = client.post(f"/assets/allocations/{alloc['id']}/return", headers=leader,
                      json={"condition_on_return": "Baik", "note": "Lengkap dengan mata bor"}).json()
    assert client.post(f"/assets/returns/{ret['id']}/verify", headers=officer,
                       json={"is_accepted": True, "note": "Diterima utuh"}).status_code == 200
    return asset_id, ret["id"]


def test_return_history_and_bast_pdf(client, world: World, other_world, monkeypatch):
    import app.api.assets as assets_api

    asset_id, return_id = _cycle(client, world)
    history = client.get(f"/assets/{asset_id}/returns", headers=world.headers(client, "member"))
    assert history.status_code == 200, history.text
    row = history.json()[0]
    assert (row["id"], row["is_accepted"], row["condition_on_return"]) == (return_id, True, "Baik")
    assert row["plan_number"] and row["requested_by_name"] == "Karyawan uji leader"
    assert row["verified_by_name"] == "Karyawan uji asset"

    rendered: dict[str, str] = {}

    def fake_pdf(html: str) -> bytes:
        rendered["html"] = html
        return b"%PDF-1.7 uji"

    monkeypatch.setattr(assets_api, "html_to_pdf", fake_pdf)
    pdf = client.get(f"/assets/returns/{return_id}/pdf", headers=world.headers(client, "asset"))
    assert pdf.status_code == 200, pdf.text
    html = rendered["html"]
    assert "Berita Acara Serah Terima" in html and "Bor listrik" in html and "TL-B1" in html
    assert "Karyawan uji leader" in html and "Karyawan uji asset" in html and "Diterima" in html

    assert client.get(f"/assets/returns/{return_id}/pdf", headers=other_world.headers(client, "asset")).status_code == 404
    assert client.get(f"/assets/{asset_id}/returns", headers=other_world.headers(client, "asset")).status_code == 404


def test_bast_needs_a_verified_return(client, world: World):
    plan_id, _ = run_plan_to_in_progress(client, world)
    officer = world.headers(client, "asset")
    asset_id = client.post("/assets", headers=officer, json={
        "kind": "TOOL", "code": "TL-B2", "name": "Gerinda", "condition": "Baik"}).json()["id"]
    alloc = client.post(f"/assets/{asset_id}/reserve", headers=officer, json={"work_plan_id": plan_id}).json()
    ret = client.post(f"/assets/allocations/{alloc['id']}/return", headers=world.headers(client, "leader"),
                      json={"condition_on_return": "Baik"}).json()
    assert client.get(f"/assets/returns/{ret['id']}/pdf", headers=officer).status_code == 409
