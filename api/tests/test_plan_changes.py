"""
V-22 · Adendum perpanjangan & personel (`domain.js` REQUEST_CHANGE, REQUEST_PERSONNEL_CHANGE,
APPROVE_CHANGE, ACCEPT_CHANGE, REJECT_CHANGE, WITHDRAW_CHANGE; jalur dok 05 §3.4).
- Perpanjangan: ketua mengajukan → PM menyetujui (dokumen ADDENDUM menunggu) → ketua menerima →
  periode diperpanjang, hari baru dibuat, revisi naik. Rencana lama berlaku sampai diterima.
- Personel: PM mengajukan susunan baru (dokumen PERSONNEL_ADDENDUM) → KETUA BARU menerima → tim
  berganti (R3: ketua lama kehilangan hak ketua hari itu juga). PM dapat menarik; hanya ketua baru
  yang dapat menolak.
- Hanya satu usulan terbuka per SK; alasan wajib di setiap keputusan.
"""
from __future__ import annotations

from datetime import date, timedelta

from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import run_plan_to_in_progress

pytestmark = requires_db


def _end(plan_id: str) -> date:
    return sync_query("SELECT upper(period) - 1 FROM vms.work_plan WHERE id = %s", (plan_id,))[0][0]


def _extend(client, world: World, plan_id: str, who: str = "leader", days: int = 3, reason: str = "Material terlambat"):
    return client.post(f"/work-plans/{plan_id}/changes", headers=world.headers(client, who), json={
        "type": "EXTEND", "new_period_end": (_end(plan_id) + timedelta(days=days)).isoformat(), "reason": reason})


def _personnel(client, world: World, plan_id: str, leader: str, members: list[str], who: str = "pm"):
    return client.post(f"/work-plans/{plan_id}/changes", headers=world.headers(client, who), json={
        "type": "PERSONNEL", "leader_employee_id": world.employees[leader],
        "member_employee_ids": [world.employees[m] for m in members], "reason": "Ketua dipindahtugaskan"})


def _act(client, world: World, change_id: str, action: str, who: str, reason: str | None = "Sesuai kebutuhan lapangan"):
    body = {} if reason is None else {"reason": reason}
    return client.post(f"/changes/{change_id}/{action}", headers=world.headers(client, who), json=body)


def _change(change_id: str) -> tuple:
    return sync_query("SELECT status::text, decision_reason FROM vms.plan_change WHERE id = %s", (change_id,))[0]


def _documents(plan_id: str) -> list[tuple]:
    return sync_query("SELECT version, kind::text, status::text FROM vms.plan_document WHERE work_plan_id = %s "
                      "ORDER BY version", (plan_id,))


# ── Perpanjangan ──────────────────────────────────────────────────────────────────────────────
def test_extension_goes_leader_to_pm_to_leader(client, world):
    plan_id, day_ids = run_plan_to_in_progress(client, world)
    old_end = _end(plan_id)

    requested = _extend(client, world, plan_id)
    assert requested.status_code == 201, requested.text
    change_id = requested.json()["id"]
    assert requested.json()["status"] == "PENDING_PM"

    approved = _act(client, world, change_id, "approve", "pm", reason=None)
    assert approved.status_code == 200, approved.text
    assert _change(change_id)[0] == "AWAITING_LEADER_ACCEPTANCE"
    assert _documents(plan_id)[-1] == (2, "ADDENDUM", "AWAITING_ACCEPTANCE")
    assert _end(plan_id) == old_end                                   # rencana lama tetap berlaku

    accepted = _act(client, world, change_id, "accept", "leader", reason=None)
    assert accepted.status_code == 200, accepted.text
    assert _change(change_id)[0] == "EFFECTIVE"
    assert _documents(plan_id)[-1] == (2, "ADDENDUM", "EFFECTIVE")
    assert _end(plan_id) == old_end + timedelta(days=3)
    assert sync_query("SELECT revision FROM vms.work_plan WHERE id = %s", (plan_id,)) == [(2,)]
    new_days = sync_query("SELECT d.title, count(t.id) FROM vms.work_plan_day d LEFT JOIN vms.work_plan_task t "
                          "ON t.work_plan_day_id = d.id WHERE d.work_plan_id = %s AND d.work_date > %s "
                          "GROUP BY d.work_date, d.title ORDER BY d.work_date", (plan_id, old_end))
    assert len(new_days) == 3 and all(tasks == 2 for _, tasks in new_days)   # domain.js makeDay
    assert len(day_ids) == 2


def test_extension_request_rules(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)

    not_later = _extend(client, world, plan_id, days=0)
    assert not_later.status_code == 422
    assert not_later.json()["error"]["message"] == "Tanggal akhir baru harus setelah akhir rencana saat ini."
    no_reason = _extend(client, world, plan_id, reason=" ")
    assert no_reason.status_code == 422 and no_reason.json()["error"]["message"] == "Alasan perubahan wajib diisi."
    assert _extend(client, world, plan_id, who="member").status_code == 403
    assert _extend(client, world, plan_id, who="pm").status_code == 403          # perpanjangan diajukan ketua

    assert _extend(client, world, plan_id).status_code == 201
    second = _extend(client, world, plan_id)
    assert second.status_code == 409
    assert second.json()["error"]["message"] == "Masih ada perubahan yang menunggu penyelesaian."


def test_extension_can_be_rejected_with_a_reason(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)
    old_end = _end(plan_id)
    change_id = _extend(client, world, plan_id).json()["id"]
    assert _act(client, world, change_id, "approve", "pm", reason=None).status_code == 200

    assert _act(client, world, change_id, "reject", "leader", reason="").status_code == 422
    assert _act(client, world, change_id, "reject", "member").status_code == 403
    rejected = _act(client, world, change_id, "reject", "leader", reason="Anggaran tidak cukup")

    assert rejected.status_code == 200, rejected.text
    assert _change(change_id) == ("REJECTED", "Anggaran tidak cukup")
    assert _documents(plan_id)[-1] == (2, "ADDENDUM", "REJECTED")
    assert _end(plan_id) == old_end
    assert _extend(client, world, plan_id).status_code == 201                  # usulan baru boleh diajukan


# ── Personel ──────────────────────────────────────────────────────────────────────────────────
def test_personnel_change_takes_effect_when_the_new_leader_accepts(client, world):
    """R3 lewat alur sungguhan: ketua lama tetap anggota; kewenangan ketua pindah hari itu juga."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    world.add_person("leader2", None)

    requested = _personnel(client, world, plan_id, "leader2", ["member", "leader"])
    assert requested.status_code == 201, requested.text
    change_id = requested.json()["id"]
    assert requested.json()["status"] == "AWAITING_LEADER_ACCEPTANCE"
    assert _documents(plan_id)[-1] == (2, "PERSONNEL_ADDENDUM", "AWAITING_ACCEPTANCE")

    assert _act(client, world, change_id, "accept", "leader", reason=None).status_code == 403   # ketua lama
    accepted = _act(client, world, change_id, "accept", "leader2", reason=None)
    assert accepted.status_code == 200, accepted.text

    assert sync_query("SELECT leader_employee_id::text FROM vms.work_plan WHERE id = %s", (plan_id,)) \
        == [(world.employees["leader2"],)]
    extension = _extend(client, world, plan_id, who="leader")
    assert extension.status_code == 403                                       # ketua lama: bukan ketua lagi
    assert client.get(f"/work-plans/{plan_id}", headers=world.headers(client, "leader")).status_code == 200
    assert _extend(client, world, plan_id, who="leader2").status_code == 201


def test_removed_leader_loses_access_entirely(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)
    world.add_person("leader2", None)
    change_id = _personnel(client, world, plan_id, "leader2", ["member"]).json()["id"]

    assert _act(client, world, change_id, "accept", "leader2", reason=None).status_code == 200

    assert client.get(f"/work-plans/{plan_id}", headers=world.headers(client, "leader")).status_code == 404


def test_personnel_change_withdraw_and_reject_rules(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)
    world.add_person("leader2", None)
    assert _personnel(client, world, plan_id, "leader2", ["member"], who="leader").status_code == 403   # PM saja

    change_id = _personnel(client, world, plan_id, "leader2", ["member"]).json()["id"]
    assert _act(client, world, change_id, "reject", "leader").status_code == 403      # hanya ketua baru
    withdrawn = _act(client, world, change_id, "withdraw", "pm", reason="Salah pilih personel")
    assert withdrawn.status_code == 200, withdrawn.text
    assert _change(change_id) == ("WITHDRAWN", "Salah pilih personel")
    assert _documents(plan_id)[-1] == (2, "PERSONNEL_ADDENDUM", "WITHDRAWN")

    second = _personnel(client, world, plan_id, "leader2", ["member"]).json()["id"]
    rejected = _act(client, world, second, "reject", "leader2", reason="Masih bertugas di proyek lain")
    assert rejected.status_code == 200, rejected.text
    assert _change(second)[0] == "REJECTED"
    assert sync_query("SELECT leader_employee_id::text FROM vms.work_plan WHERE id = %s", (plan_id,)) \
        == [(world.employees["leader"],)]


def test_withdraw_is_only_for_personnel_changes(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)
    change_id = _extend(client, world, plan_id).json()["id"]

    response = _act(client, world, change_id, "withdraw", "pm")

    assert response.status_code == 409
    assert response.json()["error"]["message"] == "Penarikan hanya tersedia untuk adendum personel yang diajukan PM."


def test_changes_need_an_accepted_or_running_plan(client, world):
    plan_id, _ = run_plan_to_in_progress(client, world)
    sync_query("UPDATE vms.work_plan SET status = 'COMPLETED' WHERE id = %s", (plan_id,))

    response = _extend(client, world, plan_id)

    assert response.status_code == 409 and response.json()["error"]["code"] == "INVALID_STATE"


def _put_on_team(plan_id: str, employee_id: str) -> None:
    """Anggota yang dulu dipasang OPS (lintas unit) atau data lama sebelum R-26."""
    sync_query("INSERT INTO vms.work_plan_member (work_plan_id, employee_id, role_in_plan, valid_period) "
               "VALUES (%s, %s, 'MEMBER', daterange(current_date, NULL, '[)'))", (plan_id, employee_id))


def test_pm_personnel_change_keeps_cross_unit_members_but_cannot_add_new_ones(client, world):
    """R-26: cakupan unit PM hanya untuk orang yang BARU ditambahkan; anggota lintas unit pilihan OPS tetap boleh."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    other_unit = world.add_unit("OTHER_R26")
    world.add_person("kept_outsider", None, unit_id=other_unit)
    world.add_person("new_outsider", None, unit_id=other_unit)
    world.add_person("leader2", None)
    _put_on_team(plan_id, world.employees["kept_outsider"])

    added = _personnel(client, world, plan_id, "leader2", ["member", "leader", "kept_outsider", "new_outsider"])
    assert added.status_code == 422, added.text
    assert added.json()["error"]["code"] == "PERSONNEL_OUTSIDE_PM_UNIT"

    kept = _personnel(client, world, plan_id, "leader2", ["member", "leader", "kept_outsider"])
    assert kept.status_code == 201, kept.text


def test_personnel_change_cannot_keep_office_staff_on_the_team(client, world):
    """R-26: staf lapangan berlaku untuk seluruh tim hasil adendum, termasuk yang dipertahankan."""
    plan_id, _ = run_plan_to_in_progress(client, world)
    world.add_person("leader2", None)
    _put_on_team(plan_id, world.employees["finance"])

    response = _personnel(client, world, plan_id, "leader2", ["member", "leader", "finance"])

    assert response.status_code == 422, response.text
    assert response.json()["error"]["code"] == "PERSONNEL_NOT_FIELD_STAFF"
    assert _personnel(client, world, plan_id, "leader2", ["member", "leader"]).status_code == 201
