"""
Tests for employee emergency contacts and complete employee creation fields.
"""
from __future__ import annotations

import datetime

from tests.conftest import requires_db, sync_query

pytestmark = requires_db


def test_employee_creation_with_all_fields_and_emergency_contacts(client, world):
    admin = world.headers(client, "admin")

    created = client.post(
        "/employees",
        headers=admin,
        json={
            "employee_no": "UJI-LENGKAP-01",
            "full_name": "Karyawan Lengkap",
            "position": "Staff Ahli",
            "unit_id": world.unit_id,
            "join_date": "2026-03-01",
            "birth_date": "1995-05-15",
            "address": "Jl. Merdeka No. 10",
            "attendance_mode": "OFFICE",
            "emergency_contacts": [
                {
                    "name": "Siti Rahma",
                    "relationship": "Istri",
                    "phone": "08123456789",
                    "address": "Jl. Merdeka No. 10",
                    "is_primary": True,
                }
            ],
        },
    )
    assert created.status_code == 201, created.text
    emp_id = created.json()["id"]

    # Periksa vms.employee
    emp_rows = sync_query(
        "SELECT attendance_mode, birth_date, address FROM vms.employee WHERE id = %s",
        (emp_id,),
    )
    assert len(emp_rows) == 1
    assert emp_rows[0][0] == "OFFICE"
    assert emp_rows[0][1] == datetime.date(1995, 5, 15)
    assert emp_rows[0][2] == "Jl. Merdeka No. 10"

    # Periksa vms.employee_emergency_contact
    contact_rows = sync_query(
        "SELECT name, relationship, phone, is_primary FROM vms.employee_emergency_contact WHERE employee_id = %s",
        (emp_id,),
    )
    assert len(contact_rows) == 1
    assert contact_rows[0] == ("Siti Rahma", "Istri", "08123456789", True)


def test_emergency_contact_crud_and_privacy(client, world):
    admin = world.headers(client, "admin")
    hr = world.headers(client, "hr")
    member = world.headers(client, "member")

    created = client.post(
        "/employees",
        headers=admin,
        json={
            "employee_no": "UJI-KONTAK-02",
            "full_name": "Karyawan Kontak",
            "position": "Teknisi",
            "unit_id": world.unit_id,
            "join_date": "2026-03-01",
        },
    )
    assert created.status_code == 201, created.text
    emp_id = created.json()["id"]

    # HR menambah kontak darurat
    add_res = client.post(
        f"/employees/{emp_id}/emergency-contacts",
        headers=hr,
        json={
            "name": "Ibu Maryam",
            "relationship": "Ibu",
            "phone": "0811223344",
            "address": "Bandung",
            "is_primary": True,
        },
    )
    assert add_res.status_code == 201, add_res.text
    contact_id = add_res.json()["id"]
    assert add_res.json()["name"] == "Ibu Maryam"
    assert add_res.json()["is_primary"] is True

    # HR melihat daftar kontak darurat
    list_hr = client.get(f"/employees/{emp_id}/emergency-contacts", headers=hr)
    assert list_hr.status_code == 200
    assert len(list_hr.json()) == 1
    assert list_hr.json()[0]["id"] == contact_id

    # Rekan kerja biasa (bukan HR & bukan pemilik) tidak dapat melihat kontak darurat (M2-01)
    list_member = client.get(f"/employees/{emp_id}/emergency-contacts", headers=member)
    assert list_member.status_code == 200
    assert list_member.json() == []

    # Rekan kerja biasa mencoba menambah kontak darurat -> 403
    forbidden_add = client.post(
        f"/employees/{emp_id}/emergency-contacts",
        headers=member,
        json={
            "name": "Budi",
            "relationship": "Teman",
            "phone": "0899999",
        },
    )
    assert forbidden_add.status_code == 403

    # HR mengubah kontak darurat
    update_res = client.put(
        f"/employees/{emp_id}/emergency-contacts/{contact_id}",
        headers=hr,
        json={"phone": "081299998888"},
    )
    assert update_res.status_code == 200, update_res.text
    assert update_res.json()["phone"] == "081299998888"

    # HR menambah kontak ke-2
    add_second = client.post(
        f"/employees/{emp_id}/emergency-contacts",
        headers=hr,
        json={
            "name": "Kakak Rudi",
            "relationship": "Saudara",
            "phone": "0855555555",
            "is_primary": False,
        },
    )
    assert add_second.status_code == 201
    second_id = add_second.json()["id"]

    list_hr2 = client.get(f"/employees/{emp_id}/emergency-contacts", headers=hr)
    assert len(list_hr2.json()) == 2

    # HR menghapus kontak ke-2
    del_res = client.delete(f"/employees/{emp_id}/emergency-contacts/{second_id}", headers=hr)
    assert del_res.status_code == 200

    list_hr3 = client.get(f"/employees/{emp_id}/emergency-contacts", headers=hr)
    assert len(list_hr3.json()) == 1
    assert list_hr3.json()[0]["id"] == contact_id
