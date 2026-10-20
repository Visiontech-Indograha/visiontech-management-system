"""
R-20 · Aturan dokumen pribadi (domain.js UPLOAD_DOCUMENT / VERIFY_DOCUMENT) dan batas organisasi.
Dulu: HR organisasi lain bisa membaca & memutus dokumen lewat UUID (tanpa cek organisasi), dokumen
yang sudah diputus bisa diputus ulang, pemilik bisa memverifikasi dokumennya sendiri bila diunggah
orang lain, dan pengajuan kedua berjenis sama berakhir "DB_ERROR" mentah.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from tests.conftest import World, requires_db, sync_query

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _file(client, world: World, who: str, colour: int) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (24, 24), (colour, 40, 90)).save(buf, "PNG")
    uploaded = client.post("/files/upload", headers=world.headers(client, who),
                           files={"file": ("dok.png", buf.getvalue(), "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    return uploaded.json()["file_id"]


def _submit(client, world: World, who: str, owner: str, doc_type: str = "SIM A", colour: int = 1):
    return client.post(f"/employees/{world.employees[owner]}/documents", headers=world.headers(client, who),
                       json={"doc_type": doc_type, "number": "998877665544", "expiry_date": "2030-01-01",
                             "file_id": _file(client, world, who, colour)})


def _status(doc_id: str) -> tuple:
    return sync_query("SELECT status::text, lifecycle::text FROM vms.employee_document WHERE id = %s", (doc_id,))[0]


def test_other_organisation_hr_cannot_read_or_decide(client, world: World, other_world: World):
    doc = _submit(client, world, "member", "member")
    assert doc.status_code == 201, doc.text
    emp, doc_id = world.employees["member"], doc.json()["id"]
    outsider = other_world.headers(client, "hr")

    assert client.get(f"/employees/{emp}/documents", headers=outsider).status_code == 404
    decided = client.post(f"/employees/{emp}/documents/{doc_id}/verify", headers=outsider,
                          json={"is_approved": True})
    assert decided.status_code == 404, decided.text
    assert _status(doc_id) == ("PENDING", "PENDING")

    # HR organisasinya sendiri tetap bisa.
    assert client.get(f"/employees/{emp}/documents", headers=world.headers(client, "hr")).status_code == 200


def test_only_pending_documents_can_be_decided(client, world: World):
    doc_id = _submit(client, world, "member", "member").json()["id"]
    hr = world.headers(client, "hr")
    url = f"/employees/{world.employees['member']}/documents/{doc_id}/verify"
    assert client.post(url, headers=hr, json={"is_approved": True}).status_code == 200

    again = client.post(url, headers=hr, json={"is_approved": False, "review_note": "Ubah pikiran"})
    assert again.status_code == 409, again.text
    assert again.json()["error"]["code"] == "NOT_PENDING"
    assert _status(doc_id) == ("VERIFIED", "CURRENT")


def test_owner_cannot_verify_own_document_even_if_uploaded_by_someone_else(client, world: World):
    # Admin mengunggah dokumen milik petugas HR → HR itu tetap tidak boleh memverifikasinya.
    doc = _submit(client, world, "admin", "hr")
    assert doc.status_code == 201, doc.text
    own = client.post(f"/employees/{world.employees['hr']}/documents/{doc.json()['id']}/verify",
                      headers=world.headers(client, "hr"), json={"is_approved": True})
    assert own.status_code == 409, own.text
    assert own.json()["error"]["code"] == "FOUR_EYES"
    assert _status(doc.json()["id"]) == ("PENDING", "PENDING")


def test_second_pending_upload_of_the_same_type_is_a_clear_409(client, world: World):
    assert _submit(client, world, "member", "member", colour=3).status_code == 201
    second = _submit(client, world, "member", "member", colour=4)
    assert second.status_code == 409, second.text
    body = second.json()["error"]
    assert body["code"] == "DOCUMENT_PENDING"
    assert body["message"] == "Masih ada dokumen jenis ini menunggu pemeriksaan."
    # Jenis lain tetap boleh.
    assert _submit(client, world, "member", "member", doc_type="KTP", colour=5).status_code == 201
