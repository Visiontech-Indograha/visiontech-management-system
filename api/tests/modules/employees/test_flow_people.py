"""
V-02 · Alur modul M2 (karyawan & dokumen pribadi) dan M4 (lokasi & absensi).
Setiap langkah tulis dibuktikan dengan membaca ulang dari DB lewat koneksi terpisah.
"""
from __future__ import annotations

import io
import uuid

from PIL import Image

from tests.conftest import requires_db, sync_query

pytestmark = requires_db


def _png() -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (64, 64), (20, 80, 60)).save(buf, "PNG")
    return buf.getvalue()


def test_employee_lifecycle(client, world):
    admin = world.headers(client, "admin")

    created = client.post("/employees", headers=admin, json={
        "employee_no": "UJI-BARU", "full_name": "Karyawan Baru", "office_id": world.org_id,
        "division_id": world.unit_id, "join_date": "2026-02-01",
        "address": {"address_line": "Jl. Uji Baru 1", "city": "Pekanbaru", "postal_code": "28111"}})
    assert created.status_code == 201, created.text
    emp_id = created.json()["employee_id"]
    assert created.json()["addresses"][0]["city"] == "Pekanbaru"
    assert sync_query("SELECT full_name FROM employee WHERE employee_id = %s", (emp_id,)) == [("Karyawan Baru",)]

    updated = client.put(f"/employees/{emp_id}", headers=admin, json={"pkwt_end_date": "2027-02-01"})
    assert updated.status_code == 200, updated.text
    assert updated.json()["pkwt_end_date"] == "2027-02-01"

    address = client.post(f"/employees/{emp_id}/addresses", headers=admin,
                          json={"address_line": "Jl. Kedua 2", "city": "Duri", "postal_code": "28884"})
    assert address.status_code == 201, address.text
    assert len(client.get(f"/employees/{emp_id}", headers=admin).json()["addresses"]) == 2

    listed = client.get("/employees", headers=admin, params={"status": "active"}).json()
    assert emp_id in {e["employee_id"] for e in listed["items"]}


def _upload(client, headers, color: int = 60) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (color, 10, 10)).save(buf, "PNG")
    uploaded = client.post("/files/upload", headers=headers, files={"file": ("dok.png", buf.getvalue(), "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    return uploaded.json()["file_id"]


def test_personal_document_is_managed_by_hr_and_seen_by_its_owner(client, world, fake_storage):
    hr, member = world.headers(client, "hr"), world.headers(client, "member")
    own_emp = world.employees["member"]

    file_id = _upload(client, hr)
    assert sync_query("SELECT count(*) FROM file_object WHERE id = %s", (file_id,)) == [(1,)]
    assert fake_storage  # berkas benar-benar dikirim ke penyimpanan

    doc = client.post(f"/employees/{own_emp}/documents", headers=hr, json={"doc_type": "KTP", "file_id": file_id})
    assert doc.status_code == 201, doc.text
    doc_id = doc.json()["id"]
    assert sync_query("SELECT type, status::text FROM employee_file WHERE employee_file_id = %s", (doc_id,))         == [("KTP", "active")]

    mine = client.get(f"/employees/{own_emp}/documents", headers=member)
    assert mine.status_code == 200 and doc_id in [d["id"] for d in mine.json()["items"]]
    # Dokumen rekan → 404 (keberadaan data tidak dibocorkan).
    assert client.get(f"/employees/{own_emp}/documents", headers=world.headers(client, "leader")).status_code == 404


def test_employee_cannot_upload_documents_themselves(client, world, fake_storage):
    member = world.headers(client, "member")
    file_id = _upload(client, member)
    response = client.post(f"/employees/{world.employees['member']}/documents", headers=member,
                           json={"doc_type": "SIM A", "file_id": file_id})
    assert response.status_code == 403, response.text


def test_site_and_attendance_day(client, world, fake_storage):
    ops, pm, member = (world.headers(client, w) for w in ("ops", "pm", "member"))

    # Master kantor dikelola OM (docs/35 §2); PM tidak.
    body = {"name": f"Gedung uji {world.tag}", "address": "Jl. Uji", "location": {"lat": -6.21, "lng": 106.81},
            "radius_m": 150}
    assert client.post("/offices", headers=pm, json=body).status_code == 403
    site = client.post("/offices", headers=ops, json=body)
    assert site.status_code == 201, site.text
    office_id = site.json()["id"]
    try:
        assert sync_query("SELECT attendance_radius_m FROM office WHERE office_id = %s", (office_id,)) == [(150,)]

        # Di luar radius (±11 km) dengan swafoto + penjelasan → menunggu pemeriksaan.
        check_in = client.post("/attendance/check-in", headers=member, json={
            "site_id": world.site_id, "location": {"lat": -6.3, "lng": 106.8}, "location_origin": "GPS",
            "selfie_file_id": _upload(client, member), "explanation": "Survei titik baru"})
        assert check_in.status_code == 200, check_in.text
        att_id = check_in.json()["id"]
        # Jarak & status dihitung server (aturan inti #3), bukan dikirim perangkat.
        assert sync_query("SELECT om_approval_status, is_within_attendance_radius FROM attendance "
                          "WHERE attendance_id = %s", (att_id,)) == [("PENDING_OM", False)]

        out_body = {"location": {"lat": -6.2, "lng": 106.8}, "location_origin": "GPS"}
        # R-33: belum valid → belum boleh absen pulang.
        assert client.post("/attendance/check-out", headers=member, json=out_body).status_code == 409

        explained = client.post(f"/attendance/{att_id}/explain", headers=member, json={"explanation": "Macet di tol"})
        assert explained.status_code == 200, explained.text

        reviewed = client.post(f"/attendance/{att_id}/review", headers=pm,
                               json={"is_approved": True, "note": "Macet dibenarkan PM"})
        assert reviewed.status_code == 200, reviewed.text
        status, note = sync_query("SELECT om_approval_status, out_of_radius_note FROM attendance "
                                  "WHERE attendance_id = %s", (att_id,))[0]
        assert status == "APPROVED_BY_OM" and "Macet di tol" in note and "Macet dibenarkan PM" in note

        check_out = client.post("/attendance/check-out", headers=member, json=out_body)
        assert check_out.status_code == 200, check_out.text
        assert sync_query("SELECT clock_out_at IS NOT NULL FROM attendance WHERE attendance_id = %s",
                          (att_id,)) == [(True,)]

        export = client.get("/attendance/export", headers=world.headers(client, "admin"),
                            params={"start_date": "2026-01-01", "end_date": "2026-12-31"})
        assert export.status_code == 200, export.text
    finally:
        from tests.cleanup import purge_office
        from tests.conftest import _sync_conn
        with _sync_conn() as conn:
            purge_office(conn, office_id)


def test_get_single_employee_for_direct_link(client, world):
    hr = world.headers(client, "hr")
    emp = world.employees["member"]
    got = client.get(f"/employees/{emp}", headers=hr)
    assert got.status_code == 200, got.text
    assert got.json()["employee_id"] == str(emp)
    assert client.get(f"/employees/{uuid.uuid4()}", headers=hr).status_code == 404


def test_new_document_of_the_same_type_replaces_the_old_one(client, world, fake_storage):
    """Dokumen sejenis yang baru menggantikan yang berlaku: lama → `extended`, baru → `active`."""
    hr = world.headers(client, "hr")
    emp = world.employees["member"]

    old = client.post(f"/employees/{emp}/documents", headers=hr, json={
        "doc_type": "SIM A", "expired_at": "2026-10-01", "file_id": _upload(client, hr, 1)})
    assert old.status_code == 201, old.text
    new = client.post(f"/employees/{emp}/documents", headers=hr, json={
        "doc_type": "SIM A", "expired_at": "2031-10-01", "file_id": _upload(client, hr, 2)})
    assert new.status_code == 201, new.text

    status = "SELECT status::text FROM employee_file WHERE employee_file_id = %s"
    assert sync_query(status, (old.json()["id"],)) == [("extended",)]
    assert sync_query(status, (new.json()["id"],)) == [("active",)]
