"""
Cakupan & hak aksi Work Order (audit cakupan). Per aksi:
- peran/keanggotaan yang sah → berhasil;
- peran lain di dalam cakupan → 403;
- WO di luar cakupan (atau id acak) → 404, agar keberadaannya tidak bocor.

Aktor di dunia uji: `admin` (SA), `ops` (OM), `pm` (PM divisi WO), `pm2` (PM divisi lain), `leader` (ketua tim WO),
`member` (anggota tim WO), `hr` (HR/GA), `outsider` (karyawan tanpa tim di divisi WO).
"""
from __future__ import annotations

import uuid

from tests.conftest import World, requires_db, sync_query
from tests.orders import make_client

pytestmark = requires_db

SURVEY_BODY = {"narrative": "Survei uji", "format": "CCTV", "points": [], "general_bom": []}


def _setup_scope(world: World) -> None:
    """PM divisi lain (`pm2`) dan karyawan tanpa tim di divisi WO (`outsider`)."""
    unit2 = world.add_unit("Dua")
    pm2 = world.add_person("pm2", "PM", unit_id=unit2)
    sync_query("UPDATE division SET pm_id = %s WHERE division_id = %s", (pm2, unit2))
    world.add_person("outsider", None)


def _work_order(world: World, *, status: str = "WAITING_SURVEY", team: bool = True, items_done: bool = False) -> dict:
    """WO uji beserta satu item dan satu baris BoM (lewat SQL, tanpa API)."""
    tag = uuid.uuid4().hex[:8]
    wo_id = str(sync_query(
        "INSERT INTO client_work_orders (wo_number, client_id, division_id, pm_id, lead_team_id, title, status) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s) RETURNING work_order_id",
        (f"UJI-WO-{tag}", make_client(), world.unit_id, world.employees["pm"],
         world.team_id if team else None, f"WO uji {tag}", status))[0][0])
    work_type = sync_query(
        "INSERT INTO work_type (division_id, name) VALUES (%s, %s) RETURNING work_type_id",
        (world.unit_id, f"Jenis uji {tag}"))[0][0]
    item_id = str(sync_query(
        "INSERT INTO work_order_items (work_order_id, work_type_id, title, status) "
        "VALUES (%s, %s, %s, %s) RETURNING item_id",
        (wo_id, work_type, f"Item uji {tag}", "DONE" if items_done else "PENDING"))[0][0])
    bom_id = str(sync_query(
        "INSERT INTO work_order_bom (work_order_id, work_order_item_id, item_name) "
        "VALUES (%s, %s, %s) RETURNING bom_id", (wo_id, item_id, f"Kabel uji {tag}"))[0][0])
    return {"work_order_id": wo_id, "item_id": item_id, "bom_id": bom_id}


def _post(client, world: World, who: str, path: str, body: dict | None = None):
    return client.post(path, headers=world.headers(client, who), json=body or {})


def test_assign_survey_only_managers_in_scope(client, world: World):
    _setup_scope(world)
    body = {"lead_team_id": world.team_id}
    for who in ("ops", "pm", "admin"):
        wo = _work_order(world, team=False)
        ok = _post(client, world, who, f"/work-orders/{wo['work_order_id']}/assign-survey", body)
        assert ok.status_code == 200, (who, ok.text)
    for who in ("member", "leader", "hr", "outsider"):
        wo = _work_order(world, team=False)
        denied = _post(client, world, who, f"/work-orders/{wo['work_order_id']}/assign-survey", body)
        assert denied.status_code == 403, (who, denied.text)
    wo = _work_order(world, team=False)
    other_pm = _post(client, world, "pm2", f"/work-orders/{wo['work_order_id']}/assign-survey", body)
    assert other_pm.status_code == 404, other_pm.text


def test_submit_survey_only_assigned_team_members(client, world: World):
    _setup_scope(world)
    for who in ("member", "leader"):
        wo = _work_order(world)
        ok = _post(client, world, who, f"/work-orders/{wo['work_order_id']}/submit-survey", SURVEY_BODY)
        assert ok.status_code == 200, (who, ok.text)
    for who in ("pm", "admin"):
        wo = _work_order(world)
        denied = _post(client, world, who, f"/work-orders/{wo['work_order_id']}/submit-survey", SURVEY_BODY)
        assert denied.status_code == 403, (who, denied.text)
    for who in ("pm2", "outsider", "hr"):
        wo = _work_order(world)
        hidden = _post(client, world, who, f"/work-orders/{wo['work_order_id']}/submit-survey", SURVEY_BODY)
        assert hidden.status_code == 404, (who, hidden.text)


def test_apply_survey_pm_or_om_in_scope(client, world: World):
    _setup_scope(world)
    for who in ("ops", "pm"):
        wo = _work_order(world, status="SURVEY_SUBMITTED")
        ok = _post(client, world, who, f"/work-orders/{wo['work_order_id']}/apply-survey")
        assert ok.status_code == 200, (who, ok.text)
    wo = _work_order(world, status="SURVEY_SUBMITTED")
    for who in ("member", "leader"):
        denied = _post(client, world, who, f"/work-orders/{wo['work_order_id']}/apply-survey")
        assert denied.status_code == 403, (who, denied.text)
    other_pm = _post(client, world, "pm2", f"/work-orders/{wo['work_order_id']}/apply-survey")
    assert other_pm.status_code == 404, other_pm.text


def _put(client, world: World, who: str, path: str, body: dict):
    return client.put(path, headers=world.headers(client, who), json=body)


def test_item_progress_team_or_manager_in_scope(client, world: World):
    _setup_scope(world)
    for who in ("member", "leader", "pm", "ops", "admin"):
        wo = _work_order(world)
        ok = _put(client, world, who, f"/work-orders/items/{wo['item_id']}/progress",
                  {"completed_qty": 1, "status": "DONE"})
        assert ok.status_code == 200, (who, ok.text)
    wo = _work_order(world)
    for who in ("pm2", "outsider", "hr"):
        hidden = _put(client, world, who, f"/work-orders/items/{wo['item_id']}/progress",
                      {"completed_qty": 1, "status": "DONE"})
        assert hidden.status_code == 404, (who, hidden.text)
    random_item = _put(client, world, "member", f"/work-orders/items/{uuid.uuid4()}/progress",
                       {"completed_qty": 1, "status": "DONE"})
    assert random_item.status_code == 404, random_item.text


def test_bom_actual_team_or_manager_in_scope(client, world: World):
    _setup_scope(world)
    for who in ("member", "leader", "pm", "ops", "admin"):
        wo = _work_order(world)
        ok = _put(client, world, who, f"/work-orders/bom/{wo['bom_id']}/actual", {"actual_qty": 2})
        assert ok.status_code == 200, (who, ok.text)
    wo = _work_order(world)
    for who in ("pm2", "outsider", "hr"):
        hidden = _put(client, world, who, f"/work-orders/bom/{wo['bom_id']}/actual", {"actual_qty": 2})
        assert hidden.status_code == 404, (who, hidden.text)
    random_bom = _put(client, world, "member", f"/work-orders/bom/{uuid.uuid4()}/actual", {"actual_qty": 2})
    assert random_bom.status_code == 404, random_bom.text


def _code(resp) -> str:
    return resp.json()["error"]["code"]


def _sign(client, world: World, who: str, wo_id: str, name: str = "Budi Uji"):
    return _post(client, world, who, f"/work-orders/{wo_id}/sign-bast", {"signer_name": name})


def test_bast_leader_signs_first_then_manager_approves(client, world: World):
    _setup_scope(world)
    wo_id = _work_order(world, status="IN_PROGRESS", items_done=True)["work_order_id"]

    # Sebelum ketua tim: PM/OM tidak bisa mengesahkan; anggota 403; di luar cakupan 404.
    early = _sign(client, world, "pm", wo_id)
    assert early.status_code == 409 and _code(early) == "LEADER_SIGNATURE_REQUIRED", early.text
    assert _sign(client, world, "admin", wo_id).status_code == 409
    assert _sign(client, world, "member", wo_id).status_code == 403
    assert _sign(client, world, "pm2", wo_id).status_code == 404
    assert _sign(client, world, "outsider", wo_id).status_code == 404

    # Ketua tim menandatangani lebih dulu: status menjadi COMPLETED (menunggu persetujuan).
    led = _sign(client, world, "leader", wo_id, "Ketua Uji")
    assert led.status_code == 200, led.text
    assert led.json()["status"] == "COMPLETED"
    assert led.json()["leader_signed_at"] is not None
    assert led.json()["leader_signer_name"] == "Ketua Uji"
    assert led.json()["bast_signed_at"] is None

    # Ketua tim tidak bisa menandatangani dua kali.
    again = _sign(client, world, "leader", wo_id)
    assert again.status_code == 409 and _code(again) == "BAST_ALREADY_SIGNED", again.text

    # Persetujuan final PM dalam cakupan: status 'selesai' (BAST_SIGNED).
    final = _sign(client, world, "pm", wo_id, "PM Uji")
    assert final.status_code == 200, final.text
    assert final.json()["status"] == "BAST_SIGNED"
    assert final.json()["bast_signed_at"] is not None
    assert final.json()["bast_signer_name"] == "PM Uji"

    # Sudah disahkan: tidak bisa diulang.
    twice = _sign(client, world, "pm", wo_id)
    assert twice.status_code == 409, twice.text


def test_bast_final_by_om_or_sa_after_leader(client, world: World):
    _setup_scope(world)
    for who in ("ops", "admin"):
        wo_id = _work_order(world, status="READY_TO_EXECUTE", items_done=True)["work_order_id"]
        assert _sign(client, world, "leader", wo_id).status_code == 200
        ok = _sign(client, world, who, wo_id)
        assert ok.status_code == 200, (who, ok.text)
        assert ok.json()["status"] == "BAST_SIGNED", who


def test_bast_leader_step_rules(client, world: World):
    _setup_scope(world)
    # Anggota biasa (bukan ketua) 403, walau sudah di dalam cakupan.
    wo_id = _work_order(world, status="IN_PROGRESS", items_done=True)["work_order_id"]
    assert _sign(client, world, "member", wo_id).status_code == 403
    # Item belum semua DONE: ketua tim tidak bisa menandatangani.
    pending = _work_order(world, status="IN_PROGRESS", items_done=False)["work_order_id"]
    blocked = _sign(client, world, "leader", pending)
    assert blocked.status_code == 422 and "belum selesai" in blocked.text, blocked.text
    # Status sebelum persetujuan survei: ditolak dengan status 409.
    early = _work_order(world, status="WAITING_SURVEY", items_done=True)["work_order_id"]
    not_ready = _sign(client, world, "leader", early)
    assert not_ready.status_code == 409 and _code(not_ready) == "INVALID_STATE", not_ready.text


def test_bast_same_person_cannot_sign_both_steps(client, world: World):
    _setup_scope(world)
    # PM yang juga ketua tim WO tidak boleh menandatangani kedua langkah sendiri.
    sync_query("UPDATE team SET leader_employee_id = %s WHERE team_id = %s",
               (world.employees["pm"], world.team_id))
    wo_id = _work_order(world, status="IN_PROGRESS", items_done=True)["work_order_id"]
    assert _sign(client, world, "pm", wo_id).status_code == 200
    self_final = _sign(client, world, "pm", wo_id)
    assert self_final.status_code == 409 and _code(self_final) == "SAME_SIGNER", self_final.text


def test_bast_out_of_scope_is_not_found(client, world: World):
    _setup_scope(world)
    wo_id = _work_order(world, status="IN_PROGRESS", items_done=True)["work_order_id"]
    for who in ("pm2", "outsider", "hr"):
        assert _sign(client, world, who, wo_id).status_code == 404, who
    assert _sign(client, world, "leader", wo_id).status_code == 200
    for who in ("pm2", "outsider", "hr"):
        assert _sign(client, world, who, wo_id).status_code == 404, who


def test_export_document_managers_in_scope_only(client, world: World):
    _setup_scope(world)
    wo = _work_order(world, status="IN_PROGRESS", items_done=True)
    path = f"/work-orders/{wo['work_order_id']}/export/DOCX"
    for who in ("member", "leader"):
        denied = client.get(path, headers=world.headers(client, who))
        assert denied.status_code == 403, (who, denied.text)
    other_pm = client.get(path, headers=world.headers(client, "pm2"))
    assert other_pm.status_code == 404, other_pm.text
    ok = client.get(path, headers=world.headers(client, "pm"))
    assert ok.status_code == 200, ok.text


def test_detail_and_list_follow_scope(client, world: World):
    _setup_scope(world)
    wo = _work_order(world)
    path = f"/work-orders/{wo['work_order_id']}"
    assert client.get(path, headers=world.headers(client, "member")).status_code == 200
    assert client.get(path, headers=world.headers(client, "pm")).status_code == 200
    for who in ("pm2", "outsider", "hr"):
        assert client.get(path, headers=world.headers(client, who)).status_code == 404, who
        listed = client.get("/work-orders", headers=world.headers(client, who), params={"limit": 200})
        assert listed.status_code == 200, listed.text
        assert wo["work_order_id"] not in {row["work_order_id"] for row in listed.json()}, who
