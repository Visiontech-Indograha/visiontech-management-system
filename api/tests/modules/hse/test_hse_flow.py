"""
api/tests/modules/hse/test_hse_flow.py

Pengujian alur lengkap modul HSE (Health, Safety & Environment / HES):
1. Pembuatan materi/kampanye K3 oleh pengguna HSE/Admin.
2. Popup gate wajib baca untuk pengguna yang login.
3. Konfirmasi baca (acknowledgment) dengan pelacakan durasi & platform.
4. Audit jejak pembaca materi K3 oleh HSE/Admin.
5. Inspeksi keselamatan kendaraan dan verifikasi status oleh HSE/Admin.
"""
from __future__ import annotations

from collections.abc import Iterator
from datetime import timedelta

import pytest

from app.core.time import jakarta_now
from tests.conftest import World, db_exclusive, requires_db, sync_query

pytestmark = requires_db


def _today() -> str:
    return jakarta_now().date().isoformat()


def _future(days: int = 7) -> str:
    return (jakarta_now().date() + timedelta(days=days)).isoformat()


@pytest.fixture
def hse_world(client, world: World) -> Iterator[World]:
    # Pintu popup K3 memilih kampanye aktif GLOBAL: tes yang membuat kampanye diserialkan lintas worker xdist.
    with db_exclusive(727302):
        world.add_person("hse", "HSE")
        yield world


@pytest.fixture
def test_vehicle(world: World) -> str:
    vehicle_id = str(sync_query(
        """
        INSERT INTO vehicle (office_id, division_id, vehicle_type, name, number_plate, status)
        VALUES (%s, %s, 'Car', 'Mobil Operasional Lapangan 01', %s, 'ready')
        RETURNING vehicle_id;
        """,
        (world.org_id, world.unit_id, f"B {world.tag[:4]} VMS"),
    )[0][0])
    yield vehicle_id
    sync_query("DELETE FROM vehicle_safety_inspections WHERE vehicle_id = %s;", (vehicle_id,))
    sync_query("DELETE FROM vehicle WHERE vehicle_id = %s;", (vehicle_id,))


def test_hse_campaign_lifecycle_and_popup_gate(client, hse_world: World):
    # 1. Non-HSE/Non-Admin (misal: member) dilarang membuat kampanye K3
    forbidden = client.post(
        "/hse/campaigns",
        headers=hse_world.headers(client, "member"),
        json={
            "title": "Sosialisasi APD Ketinggian",
            "content_html": "<p>Wajib menggunakan full body harness saat bekerja di ketinggian > 1.8m.</p>",
            "start_date": _today(),
            "end_date": _future(5),
            "is_mandatory": True,
            "cooldown_seconds": 3,
        },
    )
    assert forbidden.status_code == 403

    # 2. HSE membuat kampanye K3 wajib
    created = client.post(
        "/hse/campaigns",
        headers=hse_world.headers(client, "hse"),
        json={
            "title": "Sosialisasi APD Ketinggian & Safety Helmet",
            "summary": "Briefing wajib seluruh personel lapangan sebelum memulai aktivitas tiang/tower.",
            "content_html": "<p>Wajib menggunakan full body harness dan helm bersertifikat SNI/EN.</p>",
            "target_audience": "ALL",
            "is_mandatory": True,
            "cooldown_seconds": 5,
            "start_date": _today(),
            "end_date": _future(5),
            "is_active": True,
        },
    )
    assert created.status_code == 201, created.text
    campaign = created.json()
    campaign_id = campaign["campaign_id"]
    assert campaign["title"] == "Sosialisasi APD Ketinggian & Safety Helmet"
    assert campaign["is_mandatory"] is True

    try:
        # 3. Karyawan lapangan (member) login dan mengecek popup gate aktif
        popup_resp = client.get(
            "/hse/campaigns/active-popup",
            headers=hse_world.headers(client, "member"),
        )
        assert popup_resp.status_code == 200, popup_resp.text
        popup_data = popup_resp.json()
        assert popup_data["campaign"] is not None
        assert popup_data["campaign"]["campaign_id"] == campaign_id
        assert popup_data["campaign"]["is_mandatory"] is True

        # 4. Karyawan menyelesaikan scroll dan cooldown, lalu mengirim konfirmasi baca
        ack_resp = client.post(
            f"/hse/campaigns/{campaign_id}/acknowledge",
            headers=hse_world.headers(client, "member"),
            json={
                "platform": "mobile",
                "device_info": "Realme RMX3933 Android 14",
                "scroll_completed": True,
                "read_duration_seconds": 12,
            },
        )
        assert ack_resp.status_code == 200, ack_resp.text
        assert ack_resp.json()["acknowledged"] is True

        # 5. Cek ulang popup gate untuk karyawan yang sama -> harus sudah bersih (None)
        popup_after = client.get(
            "/hse/campaigns/active-popup",
            headers=hse_world.headers(client, "member"),
        )
        assert popup_after.status_code == 200
        assert popup_after.json()["campaign"] is None

        # 6. HSE memeriksa rekap pembaca (Audit Tracking)
        readers_resp = client.get(
            f"/hse/campaigns/{campaign_id}/readers",
            headers=hse_world.headers(client, "hse"),
        )
        assert readers_resp.status_code == 200, readers_resp.text
        readers_data = readers_resp.json()
        assert readers_data["total_acknowledged"] >= 1
        reader_emails = [r["email"] for r in readers_data["readers"]]
        assert hse_world.logins["member"] in reader_emails

    finally:
        # Cleanup
        sync_query("DELETE FROM hse_campaign_acknowledgments WHERE campaign_id = %s;", (campaign_id,))
        sync_query("DELETE FROM hse_campaigns WHERE campaign_id = %s;", (campaign_id,))


def test_vehicle_safety_inspection_flow(client, hse_world: World, test_vehicle: str):
    # 1. HSE (pemegang manage:vehicle_inspections) mengirimkan form inspeksi kendaraan harian
    inspection_payload = {
        "vehicle_id": test_vehicle,
        "inspector_id": hse_world.employees["leader"],
        "period_type": "DAILY",
        "inspection_date": _today(),
        "odometer_km": 45200,
        "checklist_json": {
            "rem_depan_belakang": "GOOD",
            "tekanan_ban": "GOOD",
            "oli_mesin": "GOOD",
            "lampu_sign_utama": "GOOD",
            "apar": "AVAILABLE",
        },
        "photos_json": ["/uploads/inspeksi_depan.jpg", "/uploads/inspeksi_odometer.jpg"],
        "notes": "Kendaraan dalam kondisi prima, siap berangkat ke lokasi kerja.",
    }
    create_resp = client.post(
        "/hse/inspections",
        headers=hse_world.headers(client, "hse"),
        json=inspection_payload,
    )
    assert create_resp.status_code == 201, create_resp.text
    inspection = create_resp.json()
    inspection_id = inspection["inspection_id"]
    assert inspection["status"] == "SUBMITTED"
    assert inspection["odometer_km"] == 45200

    # 2. HSE melihat daftar inspeksi kendaraan
    list_resp = client.get(
        "/hse/inspections",
        headers=hse_world.headers(client, "hse"),
        params={"vehicle_id": test_vehicle},
    )
    assert list_resp.status_code == 200, list_resp.text
    inspections = list_resp.json()
    assert any(i["inspection_id"] == inspection_id for i in inspections)

    # 3. HSE memverifikasi kelayakan kendaraan
    verify_resp = client.patch(
        f"/hse/inspections/{inspection_id}/verify",
        headers=hse_world.headers(client, "hse"),
        json={
            "status": "VERIFIED",
            "notes": "Telah diverifikasi oleh tim HSE. Kendaraan layak jalan.",
        },
    )
    assert verify_resp.status_code == 200, verify_resp.text
    verified_data = verify_resp.json()
    assert verified_data["status"] == "VERIFIED"
    assert verified_data["verified_by_id"] is not None



def _payload(vehicle: str, **extra) -> dict:
    return {"vehicle_id": vehicle, "period_type": "DAILY", "checklist_json": {"rem": "BAIK"}, **extra}


def test_inspection_create_role_matrix(client, hse_world: World, test_vehicle: str):
    world = hse_world
    world.add_person("sopir", "EMPLOYEE")
    other = str(sync_query(
        "INSERT INTO vehicle (office_id, division_id, vehicle_type, name, number_plate, status) "
        "VALUES (%s, %s, 'Car', 'Mobil lain', %s, 'ready') RETURNING vehicle_id;",
        (world.org_id, world.unit_id, f"B {world.tag[:4]} LAIN"),
    )[0][0])
    sync_query("INSERT INTO vehicle_driver (office_id, vehicle_id, employee_id) VALUES (%s, %s, %s)",
               (world.org_id, test_vehicle, world.employees["sopir"]))
    try:
        # member (bukan pengemudi, bukan ketua tim, bukan HSE): 403
        resp = client.post("/hse/inspections", headers=world.headers(client, "member"), json=_payload(test_vehicle))
        assert resp.status_code == 403, resp.text
        # pengemudi terdaftar: 201, atas nama sendiri walau inspector_id orang lain
        mine = client.post("/hse/inspections", headers=world.headers(client, "sopir"),
                           json=_payload(test_vehicle, inspector_id=world.employees["hse"]))
        assert mine.status_code == 201, mine.text
        assert mine.json()["inspector_id"] == world.employees["sopir"]
        # pengemudi untuk kendaraan lain: 404
        assert client.post("/hse/inspections", headers=world.headers(client, "sopir"),
                           json=_payload(other)).status_code == 404
        # ketua tim: kendaraan di kantornya 201
        assert client.post("/hse/inspections", headers=world.headers(client, "leader"),
                           json=_payload(other)).status_code == 201
        # HSE: 201; kendaraan tak ada: 404
        hse = world.headers(client, "hse")
        assert client.post("/hse/inspections", headers=hse, json=_payload(test_vehicle)).status_code == 201
        assert client.post("/hse/inspections", headers=hse,
                           json=_payload("00000000-0000-0000-0000-000000000001")).status_code == 404
        # /mine: pengemudi melihat inspeksi kendaraannya (termasuk yang dikirim HSE), bukan kendaraan lain
        lst = client.get("/hse/inspections/mine", headers=world.headers(client, "sopir"))
        assert lst.status_code == 200 and lst.headers["X-Total-Count"] == "2", lst.text
        assert {i["vehicle_id"] for i in lst.json()} == {test_vehicle}
        # ketua tim hanya melihat kiriman sendiri; member kosong
        lead = client.get("/hse/inspections/mine", headers=world.headers(client, "leader"))
        assert {i["vehicle_id"] for i in lead.json()} == {other}
        assert client.get("/hse/inspections/mine", headers=world.headers(client, "member")).json() == []
        # template terbuka untuk pengemudi (butuh untuk layar Buat)
        tpl = client.get("/hse/inspections/checklist-template", headers=world.headers(client, "sopir"))
        assert tpl.status_code == 200
    finally:
        sync_query("DELETE FROM vehicle_safety_inspections WHERE vehicle_id = %s;", (other,))
        sync_query("DELETE FROM vehicle_driver WHERE vehicle_id IN (%s, %s);", (test_vehicle, other))
        sync_query("DELETE FROM vehicle WHERE vehicle_id = %s;", (other,))


def test_inspection_list_view_permission_and_validation(client, hse_world: World, test_vehicle: str):
    assert client.get("/hse/inspections", headers=hse_world.headers(client, "member")).status_code == 403
    hse = hse_world.headers(client, "hse")
    tpl = client.get("/hse/inspections/checklist-template", headers=hse)
    assert tpl.status_code == 200 and tpl.json()["items"]
    bad_period = client.post("/hse/inspections", headers=hse, json={**_payload(test_vehicle), "period_type": "HARIAN"})
    assert bad_period.status_code == 422
    too_many = client.post("/hse/inspections", headers=hse, json=_payload(test_vehicle, photos_json=["a"] * 11))
    assert too_many.status_code == 422
    assert client.get("/hse/inspections", headers=hse, params={"from_date": "2026-02-02", "to_date": "2026-01-01"}
                      ).status_code == 422
    assert client.get("/hse/inspections", headers=hse, params={"status": "APA_SAJA"}).status_code == 422


def test_inspection_list_paging_total_and_prefix_search(client, hse_world: World, test_vehicle: str):
    hse = hse_world.headers(client, "hse")
    for i in range(3):
        r = client.post("/hse/inspections", headers=hse, json=_payload(test_vehicle, odometer_km=100 + i))
        assert r.status_code == 201, r.text
    page = client.get("/hse/inspections", headers=hse, params={"vehicle_id": test_vehicle, "page": 1, "size": 2})
    assert page.status_code == 200 and len(page.json()) == 2
    assert page.headers["X-Total-Count"] == "3"
    last = client.get("/hse/inspections", headers=hse, params={"vehicle_id": test_vehicle, "page": 2, "size": 2})
    assert len(last.json()) == 1 and last.headers["X-Total-Count"] == "3"
    beyond = client.get("/hse/inspections", headers=hse, params={"vehicle_id": test_vehicle, "page": 9, "size": 2})
    assert beyond.json() == [] and beyond.headers["X-Total-Count"] == "3"
    plate = client.get("/hse/inspections", headers=hse, params={"vehicle_id": test_vehicle}).json()[0]["number_plate"]
    hit = client.get("/hse/inspections", headers=hse, params={"vehicle_id": test_vehicle, "q": plate[:3]})
    assert hit.headers["X-Total-Count"] == "3"
    mid = client.get("/hse/inspections", headers=hse, params={"vehicle_id": test_vehicle, "q": plate[2:5]})
    assert mid.json() == []  # bukan "mengandung": hanya awalan
    wild = client.get("/hse/inspections", headers=hse, params={"vehicle_id": test_vehicle, "q": "%"})
    assert wild.json() == []
    legacy = client.get("/hse/inspections", headers=hse, params={"vehicle_id": test_vehicle})
    assert len(legacy.json()) == 3


def _create(client, world: World, vehicle: str, notes: str) -> str:
    resp = client.post("/hse/inspections", headers=world.headers(client, "hse"),
                       json=_payload(vehicle, notes=notes))
    assert resp.status_code == 201, resp.text
    return resp.json()["inspection_id"]


def test_reject_keeps_inspector_notes_and_stores_reason(client, hse_world: World, test_vehicle: str):
    hse = hse_world.headers(client, "hse")
    iid = _create(client, hse_world, test_vehicle, "Catatan awal pemeriksa")
    resp = client.patch(f"/hse/inspections/{iid}/verify", headers=hse,
                        json={"status": "REJECTED", "reject_reason": "Foto buram"})
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "REJECTED"
    assert body["notes"] == "Catatan awal pemeriksa"
    assert body["reject_reason"] == "Foto buram"
    detail = client.get(f"/hse/inspections/{iid}", headers=hse).json()
    assert detail["notes"] == "Catatan awal pemeriksa" and detail["reject_reason"] == "Foto buram"
    listed = client.get("/hse/inspections", headers=hse, params={"vehicle_id": test_vehicle}).json()
    row = next(i for i in listed if i["inspection_id"] == iid)
    assert row["reject_reason"] == "Foto buram" and row["notes"] == "Catatan awal pemeriksa"


def test_reject_legacy_notes_field_becomes_reason_not_overwrite(client, hse_world: World, test_vehicle: str):
    hse = hse_world.headers(client, "hse")
    iid = _create(client, hse_world, test_vehicle, "Catatan awal")
    body = client.patch(f"/hse/inspections/{iid}/verify", headers=hse,
                        json={"status": "REJECTED", "notes": "Odometer salah"}).json()
    assert body["notes"] == "Catatan awal" and body["reject_reason"] == "Odometer salah"


def test_verify_does_not_touch_notes(client, hse_world: World, test_vehicle: str):
    hse = hse_world.headers(client, "hse")
    iid = _create(client, hse_world, test_vehicle, "Catatan awal")
    body = client.patch(f"/hse/inspections/{iid}/verify", headers=hse,
                        json={"status": "VERIFIED", "notes": "OK"}).json()
    assert body["notes"] == "Catatan awal" and body["reject_reason"] is None


def test_verify_role_matrix(client, hse_world: World, test_vehicle: str):
    # kantor lain 404: test_pm_hse_extra_roles.py::test_hse_extra_scoped_to_assigned_office (HSE utama = semua kantor)
    iid = _create(client, hse_world, test_vehicle, "Catatan awal")
    path = f"/hse/inspections/{iid}/verify"
    payload = {"status": "REJECTED", "reject_reason": "x"}
    assert client.patch(path, headers=hse_world.headers(client, "member"), json=payload).status_code == 403
    assert client.patch(path, headers=hse_world.headers(client, "hse"),
                        json={"status": "REJECTED", "reject_reason": "y" * 1001}).status_code == 422
    assert client.get(f"/hse/inspections/{iid}", headers=hse_world.headers(client, "hse")).json()[
        "reject_reason"] is None
