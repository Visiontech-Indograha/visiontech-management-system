"""
api/tests/modules/exports/test_completion_scope_db.py
Ekspor dokumen order (work completion) per peran: PM/OM divisi = penuh; ketua tim = hanya BAST/slide progres
yang berisi item timnya sendiri; peran lain 403. Unduh ulang berkas PM tidak boleh dibuka ketua tim.
"""
from __future__ import annotations

import io

import docx

from tests.conftest import World, requires_db, sync_query
from tests.daily import add_item, make_daily_plan
from tests.orders import make_client

pytestmark = requires_db

DOCX = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def _text(content: bytes) -> str:
    d = docx.Document(io.BytesIO(content))
    cells = [c.text for t in d.tables for r in t.rows for c in r.cells]
    return "\n".join([p.text for p in d.paragraphs] + cells)


def _export(client, headers: dict, completion_id: str, template: str):
    return client.post(f"/exports/work-completions/{completion_id}", headers=headers, json={"template": template})


def _two_team_order(client, world: World) -> tuple[str, str]:
    """Order PM dengan item tim ketua (Titik A) dan item tim lain (Titik B) pada jadwal yang sudah disetujui."""
    created = client.post("/work-completions", headers=world.headers(client, "pm"),
                          json={"division_id": world.unit_id, "client_id": make_client(f"Klien ekspor {world.tag}"),
                                "project_title": "Pekerjaan ekspor"})
    assert created.status_code in (200, 201), created.text
    cid = created.json().get("completion_id") or created.json().get("id")
    add_item(make_daily_plan(world, status="APPROVED"), world, "Titik A", completion_id=cid)
    other_team = str(sync_query(
        "INSERT INTO team (office_id, division_id, leader_employee_id, name) "
        "VALUES (%s, %s, %s, %s) RETURNING team_id",
        (world.org_id, world.unit_id, world.employees["hr"], f"Tim lain {world.tag}"))[0][0])
    add_item(make_daily_plan(world, status="APPROVED", team_id=other_team), world, "Titik B", completion_id=cid)
    return cid, other_team


def test_leader_gets_only_bast_and_only_own_team_items(client, world: World, fake_storage):
    cid, _ = _two_team_order(client, world)
    response = _export(client, world.headers(client, "leader"), cid, "BAST")
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == DOCX
    text = _text(response.content)
    assert "Titik A" in text
    assert "Titik B" not in text


def test_leader_cannot_export_templates_beyond_bast_and_slides(client, world: World, fake_storage):
    cid, _ = _two_team_order(client, world)
    for template in ("BOQ", "SURVEY_REPORT", "ORDER_SHEET", "BAST_PDF"):
        response = _export(client, world.headers(client, "leader"), cid, template)
        assert response.status_code == 403, (template, response.text)


def test_pm_gets_full_order_in_every_template(client, world: World, fake_storage):
    cid, _ = _two_team_order(client, world)
    full = _export(client, world.headers(client, "pm"), cid, "BAST")
    assert full.status_code == 200, full.text
    text = _text(full.content)
    assert "Titik A" in text and "Titik B" in text
    assert _export(client, world.headers(client, "pm"), cid, "BOQ").status_code == 200


def test_member_and_outsiders_are_forbidden_or_hidden(client, world: World, other_world: World, fake_storage):
    cid, _ = _two_team_order(client, world)
    # anggota biasa (bukan ketua) → 403
    assert _export(client, world.headers(client, "member"), cid, "BAST").status_code == 403
    # dunia lain tidak melihat order ini → 404
    assert _export(client, other_world.headers(client, "pm"), cid, "BAST").status_code == 404


def test_leader_cannot_download_pm_export_but_can_download_own(client, world: World, fake_storage, monkeypatch):
    import app.core.storage as storage_core

    monkeypatch.setattr(storage_core, "get_object_bytes", lambda name: fake_storage.get(name))
    cid, _ = _two_team_order(client, world)
    pm_headers = world.headers(client, "pm")
    assert _export(client, pm_headers, cid, "BOQ").status_code == 200
    assert _export(client, pm_headers, cid, "BAST").status_code == 200
    leader_headers = world.headers(client, "leader")
    pm_boq, pm_bast = (sync_query(
        "SELECT export_id FROM document_template_export WHERE completion_id = %s AND template_type = %s "
        "ORDER BY create_at DESC LIMIT 1", (cid, tpl))[0][0] for tpl in ("BOQ", "BAST"))
    # berkas BAST milik PM (templat boleh, tapi bukan buatan ketua) → 404
    assert client.get(f"/exports/{pm_bast}/file", headers=leader_headers).status_code == 404
    # berkas BOQ milik PM (templat di luar izin ketua) → 403
    assert client.get(f"/exports/{pm_boq}/file", headers=leader_headers).status_code == 403

    own = _export(client, leader_headers, cid, "BAST")
    assert own.status_code == 200, own.text
    own_export = sync_query(
        "SELECT export_id FROM document_template_export WHERE completion_id = %s AND template_type = 'BAST' "
        "ORDER BY create_at DESC LIMIT 1", (cid,))[0][0]
    assert client.get(f"/exports/{own_export}/file", headers=leader_headers).status_code == 200
