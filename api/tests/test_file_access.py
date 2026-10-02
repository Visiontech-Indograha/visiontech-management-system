"""
V-17 · Kebijakan akses berkas. URL bertanda tangan dibuat hanya setelah otorisasi per berkas
(dok 13 §7); berkas yang tidak boleh dilihat → 404, bukan 403 (dok 08). Dokumen pribadi hanya
pemilik & HR (dok 08 ancaman "mengintip data rekan"); swafoto hanya pemilik & peninjau absensi;
bukti pekerjaan mengikuti siapa yang melihat SK-nya (V-07).
"""
from __future__ import annotations

import io
import uuid

import pytest
from PIL import Image

from app.core.time import jakarta_now
from tests.conftest import World, requires_db, sync_query
from tests.test_flow_plans import run_plan_to_in_progress

pytestmark = requires_db


def _upload(client, world: World, who: str, colour: tuple[int, int, int]) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), colour).save(buf, "PNG")
    uploaded = client.post("/files/upload", headers=world.headers(client, who),
                           files={"file": ("berkas.png", buf.getvalue(), "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    return uploaded.json()["file_id"]


def _status(client, world: World, who: str, file_id: str) -> int:
    return client.get(f"/files/{file_id}/url", headers=world.headers(client, who)).status_code


def _expect(client, world: World, file_id: str, allowed: set[str], denied: set[str]) -> None:
    got = {who: _status(client, world, who, file_id) for who in allowed | denied}
    assert got == {**{w: 200 for w in allowed}, **{w: 404 for w in denied}}


def test_personal_document_is_only_for_its_owner_and_hr(client, world, other_world, fake_storage):
    # HR mengunggah atas nama anggota: pemilik tetap boleh, pengunggah (HR) tetap boleh.
    file_id = _upload(client, world, "hr", (10, 20, 30))
    doc = client.post(f"/employees/{world.employees['member']}/documents", headers=world.headers(client, "hr"),
                      json={"doc_type": "KTP", "number": "3201011234567890", "file_id": file_id})
    assert doc.status_code == 201, doc.text

    _expect(client, world, file_id, allowed={"member", "hr", "admin"},
            denied={"leader", "pm", "ops", "finance", "asset"})
    assert _status(client, other_world, "hr", file_id) == 404


def test_attendance_selfie_is_only_for_its_owner_and_reviewers(client, world, fake_storage):
    file_id = _upload(client, world, "member", (40, 50, 60))
    check_in = client.post("/attendance/check-in", headers=world.headers(client, "member"), json={
        "site_id": world.site_id, "location": {"lat": -6.2, "lng": 106.8}, "selfie_file_id": file_id})
    assert check_in.status_code == 200, check_in.text

    # R-33: swafoto terlihat oleh yang boleh melihat absensinya — pemilik, PM unitnya, Finance & OPS.
    _expect(client, world, file_id, allowed={"member", "pm", "finance", "ops"},
            denied={"leader", "hr", "asset", "admin"})


def test_incident_evidence_follows_plan_visibility(client, world, fake_storage):
    unit = world.add_unit("WALL_DISPLAY")
    world.add_person("pm_other", "PM", unit, per_unit=True)
    plan_id, _ = run_plan_to_in_progress(client, world)
    file_id = _upload(client, world, "member", (70, 80, 90))
    incident = client.post("/hse/incidents", headers=world.headers(client, "member"), json={
        "work_plan_id": plan_id, "occurred_on": jakarta_now().date().isoformat(), "category": "K3_RINGAN",
        "severity": "RENDAH", "description": "Tangga licin di area kerja", "evidence_file_ids": [file_id]})
    assert incident.status_code == 201, incident.text

    _expect(client, world, file_id, allowed={"member", "leader", "pm", "ops", "admin", "asset"},
            denied={"pm_other", "hr", "finance"})


def test_unattached_upload_is_only_for_its_uploader(client, world, other_world, fake_storage):
    file_id = _upload(client, world, "member", (100, 110, 120))

    _expect(client, world, file_id, allowed={"member"},
            denied={"leader", "pm", "ops", "hr", "finance", "asset", "admin"})
    assert _status(client, other_world, "member", file_id) == 404
    # Kontrak: jenis berkas dikirim server (magic bytes saat unggah), bukan ditebak klien dari URL.
    body = client.get(f"/files/{file_id}/url", headers=world.headers(client, "member")).json()
    assert body["mime_type"] == "image/png" and body["url"]


@pytest.mark.parametrize("file_id", [str(uuid.uuid4()), "bukan-uuid"])
def test_unknown_or_malformed_file_id_never_crashes(client, world, file_id):
    assert _status(client, world, "admin", file_id) in (404, 422)


def test_upload_fails_and_leaves_no_record_when_storage_is_down(client, world, monkeypatch):
    """Temuan uji HP: MinIO mati → dulu 200 + file_id berkas yang tidak ada. Kini 503 dan tanpa baris."""
    import app.api.v1.endpoints.files as files_api

    monkeypatch.setattr(files_api, "upload_file", lambda name, data, content_type: False)
    before = sync_query("SELECT count(*) FROM vms.file_object WHERE organization_id = %s", (world.org_id,))[0][0]
    res = client.post("/files/upload", headers=world.headers(client, "member"),
                      files={"file": ("catatan.pdf", b"%PDF-1.4 penyimpanan mati", "application/pdf")})
    assert res.status_code == 503 and res.json()["error"]["code"] == "STORAGE_UNAVAILABLE"
    after = sync_query("SELECT count(*) FROM vms.file_object WHERE organization_id = %s", (world.org_id,))[0][0]
    assert after == before


def test_upload_over_the_limit_is_rejected_without_reading_it_whole(client, world, fake_storage, monkeypatch):
    """O-12 · batas ukuran diperiksa dengan membaca paling banyak batas + 1 bita."""
    from starlette.datastructures import UploadFile

    import app.api.v1.endpoints.files as files_api

    monkeypatch.setattr(files_api, "MAX_FILE_SIZE", 64)
    sizes: list[int] = []
    real_read = UploadFile.read

    async def spy_read(self: UploadFile, size: int = -1) -> bytes:
        sizes.append(size)
        return await real_read(self, size)

    monkeypatch.setattr(UploadFile, "read", spy_read)
    big = b"%PDF-1.7\n" + b"0" * 5000
    too_large = client.post("/files/upload", headers=world.headers(client, "member"),
                            files={"file": ("besar.pdf", big, "application/pdf")})
    assert too_large.status_code == 413, too_large.text
    assert "FILE_TOO_LARGE" in too_large.text
    assert sizes == [65]                                   # tidak pernah read() tanpa batas

    empty = client.post("/files/upload", headers=world.headers(client, "member"),
                        files={"file": ("kosong.pdf", b"", "application/pdf")})
    assert empty.status_code == 400 and "FILE_EMPTY" in empty.text
