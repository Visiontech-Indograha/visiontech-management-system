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
    # 1. Teknisi/Ketua tim lapangan mengirimkan form inspeksi kendaraan harian
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
        headers=hse_world.headers(client, "leader"),
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

