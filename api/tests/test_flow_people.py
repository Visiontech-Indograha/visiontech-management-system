"""
V-02 · Alur modul M2 (karyawan & dokumen pribadi) dan M4 (lokasi & absensi).
Setiap langkah tulis dibuktikan dengan membaca ulang dari DB lewat koneksi terpisah.
"""
from __future__ import annotations

import io

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
        "employee_no": "UJI-BARU", "full_name": "Karyawan Baru", "position": "Teknisi",
        "unit_id": world.unit_id, "join_date": "2026-02-01"})
    assert created.status_code == 201, created.text
    emp_id = created.json()["id"]
    assert sync_query("SELECT full_name FROM vms.employee WHERE id = %s", (emp_id,)) == [("Karyawan Baru",)]

    assert client.put(f"/employees/{emp_id}", headers=admin, json={"phone": "081200000000"}).status_code == 200
    assert sync_query("SELECT phone FROM vms.employee WHERE id = %s", (emp_id,)) == [("081200000000",)]

    promoted = client.post(f"/employees/{emp_id}/assignments", headers=admin,
                           json={"position": "Supervisor", "valid_from": "2026-09-01"})
    assert promoted.status_code == 200, promoted.text
    # Jabatan perdana (saat dibuat) ditutup, jabatan baru terbuka — riwayat tetap utuh.
    assert sync_query("SELECT count(*) FROM vms.employee_assignment WHERE employee_id = %s", (emp_id,)) == [(2,)]
    assert sync_query("SELECT position FROM vms.employee_assignment WHERE employee_id = %s AND valid_to IS NULL",
                      (emp_id,)) == [("Supervisor",)]

    listed = client.get("/employees", headers=admin).json()
    assert emp_id in {e["id"] for e in listed["items"]}

    off = client.post(f"/employees/{emp_id}/offboard", headers=admin, json={"reason": "Kontrak selesai"})
    assert off.status_code == 200, off.text
    assert sync_query("SELECT is_active FROM vms.employee WHERE id = %s", (emp_id,)) == [(False,)]


def test_personal_document_upload_and_hr_verification(client, world, fake_storage):
    member = world.headers(client, "member")
    own_emp = world.employees["member"]

    uploaded = client.post("/files/upload", headers=member, files={"file": ("ktp.png", _png(), "image/png")})
    assert uploaded.status_code == 200, uploaded.text
    file_id = uploaded.json()["file_id"]
    assert sync_query("SELECT count(*) FROM vms.file_object WHERE id = %s", (file_id,)) == [(1,)]
    assert fake_storage  # berkas benar-benar dikirim ke penyimpanan

    doc = client.post(f"/employees/{own_emp}/documents", headers=member,
                      json={"doc_type": "KTP", "number": "3201011234567890", "file_id": file_id})
    assert doc.status_code == 201, doc.text
    doc_id = doc.json()["id"]
    # Nomor asli tidak pernah disimpan — hanya bentuk tersamar (dok 03 M2).
    assert sync_query("SELECT number_masked, status::text FROM vms.employee_document WHERE id = %s", (doc_id,)) \
        == [("************7890", "PENDING")]

    verified = client.post(f"/employees/{own_emp}/documents/{doc_id}/verify", headers=world.headers(client, "hr"),
                           json={"is_approved": True})
    assert verified.status_code == 200, verified.text
    assert sync_query("SELECT status::text FROM vms.employee_document WHERE id = %s", (doc_id,)) == [("VERIFIED",)]


def test_site_and_attendance_day(client, world, fake_storage):
    pm = world.headers(client, "pm")
    member = world.headers(client, "member")

    # R-33: lokasi proyek dibuat PM untuk unitnya (bawahannya).
    site = client.post("/sites", headers=pm, json={
        "name": "Gedung uji", "location": {"lat": -6.21, "lng": 106.81}, "radius_m": 150})
    assert site.status_code == 201, site.text
    assert sync_query("SELECT radius_m FROM vms.site WHERE id = %s", (site.json()["id"],)) == [(150,)]

    # Di luar radius (±11 km) dengan swafoto → menunggu pemeriksaan Finance (domain.js CHECK_IN).
    selfie = client.post("/files/upload", headers=member, files={"file": ("swafoto.png", _png(), "image/png")})
    check_in = client.post("/attendance/check-in", headers=member, json={
        "site_id": world.site_id, "location": {"lat": -6.3, "lng": 106.8}, "location_origin": "GPS",
        "selfie_file_id": selfie.json()["file_id"], "explanation": "Survei titik baru"})
    assert check_in.status_code == 200, check_in.text
    att_id = check_in.json()["id"]
    # Jarak & status dihitung server (aturan inti #3), bukan dikirim perangkat.
    assert sync_query("SELECT status::text, distance_m > radius_m FROM vms.attendance WHERE id = %s", (att_id,)) \
        == [("NEEDS_REVIEW", True)]

    out_body = {"location": {"lat": -6.2, "lng": 106.8}, "location_origin": "GPS"}
    # R-33: belum valid → belum boleh absen pulang.
    assert client.post("/attendance/check-out", headers=member, json=out_body).status_code == 409

    explained = client.post(f"/attendance/{att_id}/explain", headers=member, json={"explanation": "Macet di tol"})
    assert explained.status_code == 200, explained.text
    assert sync_query("SELECT explanation FROM vms.attendance WHERE id = %s", (att_id,)) == [("Macet di tol",)]

    reviewed = client.post(f"/attendance/{att_id}/review", headers=pm,
                           json={"is_approved": True, "note": "Macet dibenarkan PM"})
    assert reviewed.status_code == 200, reviewed.text
    assert sync_query("SELECT status::text, reviewed_at IS NOT NULL, review_note FROM vms.attendance WHERE id = %s",
                      (att_id,)) == [("APPROVED", True, "Macet dibenarkan PM")]

    check_out = client.post("/attendance/check-out", headers=member, json=out_body)
    assert check_out.status_code == 200, check_out.text
    assert sync_query("SELECT check_out_at IS NOT NULL FROM vms.attendance WHERE id = %s", (att_id,)) == [(True,)]

    export = client.get("/attendance/export", headers=world.headers(client, "finance"),
                        params={"start_date": "2026-01-01", "end_date": "2026-12-31"})
    assert export.status_code == 200, export.text


def test_hr_cannot_verify_document_they_uploaded(client, world, fake_storage):
    hr = world.headers(client, "hr")
    emp = world.employees["member"]
    file_id = client.post("/files/upload", headers=hr, files={"file": ("sim.png", _png(), "image/png")}).json()["file_id"]
    doc_id = client.post(f"/employees/{emp}/documents", headers=hr,
                         json={"doc_type": "SIM A", "number": "123456789012", "file_id": file_id}).json()["id"]

    own = client.post(f"/employees/{emp}/documents/{doc_id}/verify", headers=hr, json={"is_approved": True})
    assert own.status_code == 409, own.text  # empat mata, bukan 500 dari CHECK basis data
    assert own.json()["error"]["code"] == "FOUR_EYES"
    assert sync_query("SELECT status::text FROM vms.employee_document WHERE id = %s", (doc_id,)) == [("PENDING",)]


def test_get_single_employee_for_direct_link(client, world, other_world):
    hr = world.headers(client, "hr")
    emp = world.employees["member"]
    got = client.get(f"/employees/{emp}", headers=hr)
    assert got.status_code == 200, got.text
    assert got.json()["id"] == str(emp)
    # Karyawan organisasi lain tidak bocor lewat tautan langsung.
    assert client.get(f"/employees/{other_world.employees['member']}", headers=hr).status_code == 404


def test_r8_renewed_document_supersedes_the_old_one_when_verified(client, world, fake_storage):
    """R8 / domain.js VERIFY_DOCUMENT: dokumen pengganti disetujui → dokumen lama berjenis sama
    menjadi SUPERSEDED, yang baru CURRENT. Dulu: indeks unik CURRENT per (karyawan, jenis) → 500."""
    member, hr = world.headers(client, "member"), world.headers(client, "hr")
    emp = world.employees["member"]

    def upload(color: int) -> str:
        buf = io.BytesIO()
        Image.new("RGB", (32, 32), (color, 10, 10)).save(buf, "PNG")
        return client.post("/files/upload", headers=member,
                           files={"file": ("sim.png", buf.getvalue(), "image/png")}).json()["file_id"]

    old = client.post(f"/employees/{emp}/documents", headers=member, json={
        "doc_type": "SIM A", "number": "111122223333", "expiry_date": "2026-10-01", "file_id": upload(1)}).json()["id"]
    assert client.post(f"/employees/{emp}/documents/{old}/verify", headers=hr,
                       json={"is_approved": True}).status_code == 200

    new = client.post(f"/employees/{emp}/documents", headers=member, json={
        "doc_type": "SIM A", "number": "111122223333", "expiry_date": "2031-10-01", "file_id": upload(2),
        "supersedes_id": old})
    assert new.status_code == 201, new.text
    verified = client.post(f"/employees/{emp}/documents/{new.json()['id']}/verify", headers=hr,
                           json={"is_approved": True})
    assert verified.status_code == 200, verified.text

    lifecycle = "SELECT lifecycle::text FROM vms.employee_document WHERE id = %s"
    assert sync_query(lifecycle, (old,)) == [("SUPERSEDED",)]
    assert sync_query(lifecycle, (new.json()["id"],)) == [("CURRENT",)]
