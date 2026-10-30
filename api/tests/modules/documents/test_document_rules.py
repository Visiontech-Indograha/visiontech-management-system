"""
Milestone 3 · Dokumen karyawan (employee 1─N employee_file). HR/GA mencatat dokumen dari berkas yang
sudah diunggah; karyawan hanya melihat dokumennya sendiri; dokumen sejenis yang baru menggantikan yang lama.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from tests.conftest import World, requires_db, sync_query

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _file(client, world: World, colour: int) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (24, 24), (colour, 40, 90)).save(buf, "PNG")
    uploaded = client.post("/files/upload", headers=world.headers(client, "hr"),
                           files={"file": ("dok.png", buf.getvalue(), "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    return uploaded.json()["file_id"]


def _upload(client, world: World, owner: str = "member", doc_type: str = "SIM A", colour: int = 1, who: str = "hr"):
    return client.post(f"/employees/{world.employees[owner]}/documents", headers=world.headers(client, who),
                       json={"doc_type": doc_type, "file_id": _file(client, world, colour),
                             "expired_at": "2030-01-01"})


def _status(doc_id: str) -> str:
    return sync_query("SELECT status::text FROM employee_file WHERE employee_file_id = %s", (doc_id,))[0][0]


def test_hr_records_document_and_owner_sees_it(client, world: World):
    created = _upload(client, world)
    assert created.status_code == 201, created.text
    doc = created.json()
    assert (doc["doc_type"], doc["status"], doc["expired_at"]) == ("SIM_A", "active", "2030-01-01")
    assert doc["file_id"] is not None

    mine = client.get(f"/employees/{world.employees['member']}/documents", headers=world.headers(client, "member"))
    assert [d["id"] for d in mine.json()["items"]] == [doc["id"]]


def _file_as(client, world: World, who: str, body: bytes, mime: str, name: str) -> str:
    uploaded = client.post("/files/upload", headers=world.headers(client, who),
                           files={"file": (name, body, mime)})
    assert uploaded.status_code == 200, uploaded.text
    return uploaded.json()["file_id"]


def test_employee_records_own_document_but_cannot_see_or_change_others(client, world: World):
    foreign = _upload(client, world, owner="leader").json()["id"]
    assert client.get(f"/employees/{world.employees['leader']}/documents",
                      headers=world.headers(client, "member")).status_code == 404
    base = f"/employees/{world.employees['member']}/documents"
    assert client.post(f"/employees/{world.employees['leader']}/documents", headers=world.headers(client, "member"),
                       json={"doc_type": "KTP", "file_id": _file(client, world, 9)}).status_code == 404
    buf = io.BytesIO()
    Image.new("RGB", (24, 24), (9, 90, 40)).save(buf, "PNG")
    file_id = _file_as(client, world, "member", buf.getvalue(), "image/png", "ktp.png")
    created = client.post(base, headers=world.headers(client, "member"), json={"doc_type": "KTP", "file_id": file_id})
    assert created.status_code == 201, created.text
    assert created.json()["file_mime"] == "image/png"
    own = created.json()["id"]
    member = world.headers(client, "member")
    assert client.post(f"{base}/{own}/deactivate", headers=member).status_code == 403
    assert client.delete(f"{base}/{own}", headers=member).status_code == 403
    assert client.delete(f"{base}/{foreign}", headers=member).status_code == 403


def test_employee_pdf_upload_reports_mime_for_icon(client, world: World):
    file_id = _file_as(client, world, "member", b"%PDF-1.4\n%%EOF\n", "application/pdf", "sim.pdf")
    created = client.post(f"/employees/{world.employees['member']}/documents", headers=world.headers(client, "member"),
                          json={"doc_type": "sim a", "file_id": file_id, "expired_at": "2031-01-01"})
    assert created.status_code == 201, created.text
    assert (created.json()["doc_type"], created.json()["file_mime"]) == ("SIM_A", "application/pdf")
    listed = client.get(f"/employees/{world.employees['member']}/documents", headers=world.headers(client, "member"))
    assert listed.json()["items"][0]["file_mime"] == "application/pdf"


def test_new_document_of_same_type_extends_the_old_one(client, world: World):
    old = _upload(client, world, colour=1).json()["id"]
    new = _upload(client, world, colour=2).json()["id"]
    other = _upload(client, world, doc_type="KTP", colour=3).json()["id"]
    assert (_status(old), _status(new), _status(other)) == ("extended", "active", "active")


def test_unknown_file_is_rejected(client, world: World):
    response = client.post(f"/employees/{world.employees['member']}/documents", headers=world.headers(client, "hr"),
                           json={"doc_type": "KTP", "file_id": "01a0dd8d-b442-7c07-91b8-5d8ac8f059fb"})
    assert response.status_code == 422


def test_deactivate_and_delete(client, world: World):
    hr = world.headers(client, "hr")
    base = f"/employees/{world.employees['member']}/documents"
    doc_id = _upload(client, world).json()["id"]
    assert client.post(f"{base}/{doc_id}/deactivate", headers=hr).json()["status"] == "not_active"
    assert client.delete(f"{base}/{doc_id}", headers=hr).status_code == 200
    assert client.get(base, headers=hr).json()["total"] == 0
    # Dokumen karyawan lain tidak bisa diubah lewat URL karyawan ini.
    foreign = _upload(client, world, owner="leader").json()["id"]
    assert client.delete(f"{base}/{foreign}", headers=hr).status_code == 404


def test_hr_cannot_attach_someone_elses_file(client, world: World):
    """Berkas milik pengguna lain (di sini: pengunggah = karyawan lain) tidak boleh dilampirkan HR."""
    buf = io.BytesIO()
    Image.new("RGB", (24, 24), (7, 40, 90)).save(buf, "PNG")
    uploaded = client.post("/files/upload", headers=world.headers(client, "pm"),
                           files={"file": ("pm.png", buf.getvalue(), "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    response = client.post(f"/employees/{world.employees['member']}/documents", headers=world.headers(client, "hr"),
                           json={"doc_type": "KTP", "file_id": uploaded.json()["file_id"]})
    assert response.status_code == 422, response.text
    assert client.get(f"/employees/{world.employees['member']}/documents",
                      headers=world.headers(client, "hr")).json()["total"] == 0


def test_employee_own_file_can_be_attached_by_hr(client, world: World):
    buf = io.BytesIO()
    Image.new("RGB", (24, 24), (9, 90, 40)).save(buf, "PNG")
    uploaded = client.post("/files/upload", headers=world.headers(client, "member"),
                           files={"file": ("ktp.png", buf.getvalue(), "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    response = client.post(f"/employees/{world.employees['member']}/documents", headers=world.headers(client, "hr"),
                           json={"doc_type": "KTP", "file_id": uploaded.json()["file_id"]})
    assert response.status_code == 201, response.text
