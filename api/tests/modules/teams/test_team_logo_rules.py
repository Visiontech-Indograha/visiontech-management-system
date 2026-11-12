"""
Logo tim (DB uji): hanya ketua tim yang boleh mengganti/menghapus logo (SUPER_ADMIN darurat); validasi berkas;
unduh logo mengikuti akses tim; dan dokumen harian memakai logo tim (fallback ke default bila berkas hilang).
"""
from __future__ import annotations

import io
import zipfile
from datetime import timedelta

import docx
import pytest
from PIL import Image

from app.shared.documents.branding import COMPANY_BOX_PX
from tests.conftest import World, requires_db, sync_query
from tests.daily import make_daily_plan

pytestmark = requires_db

PNG = "image/png"


def _png(size: tuple[int, int] = (300, 120)) -> bytes:
    buf = io.BytesIO()
    Image.new("RGBA", size, (30, 120, 200, 255)).save(buf, "PNG")
    return buf.getvalue()


@pytest.fixture
def stored(monkeypatch, fake_storage):
    """Baca balik objek yang disimpan `fake_storage` (MinIO diganti memori)."""
    import app.core.storage as storage_core

    monkeypatch.setattr(storage_core, "get_object_bytes", lambda key: fake_storage.get(key))
    return fake_storage


def _put(client, headers, team_id: str, raw: bytes, name: str = "logo.png", mime: str = PNG):
    return client.put(f"/teams/{team_id}/logo", headers=headers, files={"file": (name, raw, mime)})


def _second_team(world: World, tag: str) -> tuple[str, str]:
    """Ketua kedua (TEAM_LEADER lain) dengan timnya sendiri di kantor yang sama."""
    world.add_person(f"leader2_{tag}", "LEADER")
    team_id = str(sync_query(
        "INSERT INTO team (office_id, division_id, leader_employee_id, name) "
        "VALUES (%s, %s, %s, %s) RETURNING team_id",
        (world.org_id, world.unit_id, world.employees[f"leader2_{tag}"], f"Tim dua {tag}"))[0][0])
    return team_id, world.employees[f"leader2_{tag}"]


def _logo_column(team_id: str):
    return sync_query("SELECT logo_file_id FROM team WHERE team_id = %s", (team_id,))[0][0]


# ── siapa boleh mengganti ────────────────────────────────────────────────────────────────────
def test_team_leader_sets_logo_and_it_is_exposed_on_team(client, world: World, stored):
    response = _put(client, world.headers(client, "leader"), world.team_id, _png())
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["team_id"] == world.team_id
    assert body["logo_url"] == f"/api/v1/teams/{world.team_id}/logo"
    assert str(_logo_column(world.team_id)) == body["logo_file_id"]

    pm = world.headers(client, "pm")
    detail = client.get(f"/teams/{world.team_id}", headers=pm).json()
    assert detail["logo_file_id"] == body["logo_file_id"]
    assert detail["logo_url"] == body["logo_url"]
    listed = next(t for t in client.get("/teams", headers=pm).json() if t["team_id"] == world.team_id)
    assert listed["logo_url"] == body["logo_url"]


def test_only_this_teams_leader_may_change_logo(client, world: World, other_world: World, stored):
    team2, _ = _second_team(world, world.tag)
    raw = _png()
    denied = {
        "anggota tim": (world.headers(client, "member"), world.team_id),
        "PM divisi": (world.headers(client, "pm"), world.team_id),
        "ketua tim lain": (world.headers(client, "leader"), team2),
    }
    for label, (headers, target) in denied.items():
        response = _put(client, headers, target, raw)
        assert response.status_code == 403, (label, response.text)
        assert response.json()["error"]["code"] == "FORBIDDEN", label
    assert _logo_column(world.team_id) is None
    # Lintas organisasi: tim tak terlihat sama sekali.
    assert _put(client, other_world.headers(client, "pm"), world.team_id, raw).status_code == 404


def test_super_admin_may_change_logo_in_emergency(client, world: World, stored):
    assert _put(client, world.headers(client, "admin"), world.team_id, _png()).status_code == 200


# ── validasi berkas ──────────────────────────────────────────────────────────────────────────
def test_rejects_non_image_truncated_and_oversized_files(client, world: World, stored):
    leader = world.headers(client, "leader")
    pdf = _put(client, leader, world.team_id, b"%PDF-1.4 bukan logo", "logo.pdf", "application/pdf")
    assert pdf.status_code == 415
    assert _put(client, leader, world.team_id, _png()[:-120]).status_code == 422
    assert _put(client, leader, world.team_id, _png() + b"\0" * (2 * 1024 * 1024)).status_code == 413
    assert _logo_column(world.team_id) is None


def test_same_logo_uploaded_twice_reuses_one_file(client, world: World, stored):
    leader = world.headers(client, "leader")
    first = _put(client, leader, world.team_id, _png((400, 200))).json()["logo_file_id"]
    second = _put(client, leader, world.team_id, _png((400, 200))).json()["logo_file_id"]
    assert first == second


# ── hapus & unduh ────────────────────────────────────────────────────────────────────────────
def test_leader_removes_logo_and_team_returns_to_default(client, world: World, stored):
    leader = world.headers(client, "leader")
    _put(client, leader, world.team_id, _png())
    assert client.delete(f"/teams/{world.team_id}/logo", headers=leader).status_code == 204
    assert _logo_column(world.team_id) is None
    assert client.get(f"/teams/{world.team_id}", headers=world.headers(client, "pm")).json()["logo_url"] is None
    assert client.get(f"/teams/{world.team_id}/logo", headers=leader).status_code == 404


def test_member_cannot_remove_logo(client, world: World, stored):
    _put(client, world.headers(client, "leader"), world.team_id, _png())
    member = world.headers(client, "member")
    assert client.delete(f"/teams/{world.team_id}/logo", headers=member).status_code == 403
    assert _logo_column(world.team_id) is not None


def test_logo_download_follows_team_access(client, world: World, other_world: World, stored):
    raw = _png((320, 90))
    _put(client, world.headers(client, "leader"), world.team_id, raw)
    url = f"/teams/{world.team_id}/logo"

    for who in ("leader", "member", "pm", "hr"):
        response = client.get(url, headers=world.headers(client, who))
        assert response.status_code == 200, (who, response.text)
        assert response.content == raw
        assert response.headers["content-type"] == PNG
        assert response.headers["x-content-type-options"] == "nosniff"

    world.add_person("outsider", None)  # karyawan kantor yang bukan anggota tim ini
    assert client.get(url, headers=world.headers(client, "outsider")).status_code == 404
    assert client.get(url, headers=other_world.headers(client, "pm")).status_code == 404


def test_download_without_logo_is_not_found(client, world: World, stored):
    response = client.get(f"/teams/{world.team_id}/logo", headers=world.headers(client, "leader"))
    assert response.status_code == 404


# ── dokumen harian memakai logo tim ──────────────────────────────────────────────────────────
def _media(content: bytes) -> list[bytes]:
    with zipfile.ZipFile(io.BytesIO(content)) as z:
        return [z.read(n) for n in z.namelist() if n.startswith("word/media/")]


def _export_daily(client, headers, plan_id: str):
    return client.post("/exports/daily-report", headers=headers, json={"daily_plan_id": plan_id})


def test_daily_report_uses_team_logo_in_letterhead(client, world: World, stored):
    _put(client, world.headers(client, "leader"), world.team_id, _png((500, 500)))
    pid = make_daily_plan(world, status="APPROVED")
    response = _export_daily(client, world.headers(client, "leader"), pid)
    assert response.status_code == 200, response.text
    sizes = [Image.open(io.BytesIO(b)).size for b in _media(response.content)]
    assert COMPANY_BOX_PX in sizes
    cells = [c.text for t in docx.Document(io.BytesIO(response.content)).tables for r in t.rows for c in r.cells]
    assert any(f"Tim uji {world.tag}" in c for c in cells)  # isi kop (nama tim) tetap ada


def test_daily_report_falls_back_to_default_when_logo_file_is_missing(client, world: World, stored):
    _put(client, world.headers(client, "leader"), world.team_id, _png())
    stored.clear()  # berkas logo hilang dari storage
    pid = make_daily_plan(world, status="APPROVED")
    response = _export_daily(client, world.headers(client, "leader"), pid)
    assert response.status_code == 200, response.text
    assert _media(response.content)  # tetap terbit dengan logo default


def test_logo_is_stored_under_office_and_team_prefix(client, world: World, stored):
    body = _put(client, world.headers(client, "leader"), world.team_id, _png()).json()
    key = sync_query("SELECT storage_key FROM file_object WHERE id = %s", (body["logo_file_id"],))[0][0]
    assert key.startswith(f"{world.org_id}/team-logo/{world.team_id}/")


def test_team_week_export_uses_team_logo(client, world: World, stored):
    from pptx import Presentation

    from app.core.time import jakarta_now
    from tests.daily import add_item

    _put(client, world.headers(client, "leader"), world.team_id, _png((500, 500)))
    add_item(make_daily_plan(world, status="APPROVED"), world, "Pasang kamera")
    today = jakarta_now().date()
    monday = today - timedelta(days=today.weekday())  # minggu harus mulai Senin
    response = client.post("/exports/team-week", headers=world.headers(client, "leader"),
                           json={"team_id": world.team_id, "start_date": monday.isoformat()})
    assert response.status_code == 200, response.text
    prs = Presentation(io.BytesIO(response.content))
    sizes = [sh.image.size for s in prs.slides for sh in s.shapes if sh.shape_type == 13]
    team = [size for size in sizes if size == COMPANY_BOX_PX]
    assert team, "logo tim tidak tampil di kepala/sampul"  # logo tim di kanvas kotak standar
    assert len(sizes) > len(team), "logo Visiontech harus tetap tampil di samping logo tim"
