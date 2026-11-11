"""Hapus terjadwal (PR-2): anonimisasi karyawan keluar >30 hari + hapus permanen arsip lewat retensi.

Waktu diinjeksi (`now`); baris uji bertanggal RELATIF terhadap `now` sehingga data tes lain tidak tersentuh.
Tes diserialkan dengan db_exclusive karena kebijakan retensi & jumlah kandidat bersifat global."""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import uuid
from collections.abc import Iterator
from datetime import timedelta

import pytest

from app.core import retention_job as service
from app.core.time import utcnow
from app.database.session import make_engine
from tests.conftest import _SETUP_URL, db_exclusive, requires_db, sync_query

pytestmark = requires_db

D = timedelta(days=1)


@pytest.fixture(autouse=True)
def _serial() -> Iterator[None]:
    with db_exclusive(7_300_001):
        before = sync_query("SELECT data_type, is_active FROM retention_policy")
        yield
        for dtype, aktif in before:
            sync_query("UPDATE retention_policy SET is_active = %s WHERE data_type = %s", (aktif, dtype))


@pytest.fixture
def office() -> Iterator[str]:
    oid = str(sync_query("INSERT INTO office (name, address, latitude, longitude) "
                         "VALUES (%s, 'Jl. Uji', -6.2, 106.8) RETURNING office_id",
                         (f"Kantor ret {uuid.uuid4().hex[:8]}",))[0][0])
    yield oid
    from tests.cleanup import purge_office
    from tests.conftest import _sync_conn
    with _sync_conn() as conn:
        purge_office(conn, oid)
        conn.commit()


def _aktif(*types: str, on: bool = True) -> None:
    for t in types:
        sync_query("UPDATE retention_policy SET is_active = %s WHERE data_type = %s", (on, t))


def _run(*, terapkan: bool, now=None, **kw) -> service.Summary:
    async def go() -> service.Summary:
        engine = make_engine(_SETUP_URL)
        try:
            return await service.jalankan(engine, terapkan=terapkan, now=now or utcnow(), pause=0, **kw)
        finally:
            await engine.dispose()

    return asyncio.run(go())


def _employee(office: str, *, separated: timedelta | None, archived: timedelta | None = None, files: bool = True,
              store: dict[str, bytes] | None = None, now=None) -> str:
    tag = uuid.uuid4().hex[:10]
    now = now or utcnow()
    eid = str(sync_query(
        "INSERT INTO employee (office_id, full_name, employee_no, join_date, phone_number, face_embedding, "
        "photo_path, separated_at, delete_at, offboarding_status) VALUES (%s, %s, %s, '2020-01-01', '0812345', "
        "'[0.1,0.2]'::jsonb, %s, %s, %s, 'offboarded') RETURNING employee_id",
        (office, f"Rahasia {tag}", f"RT-{tag}", f"{office}/foto-{tag}.jpg",
         now - separated if separated is not None else None, now - archived if archived is not None else None))[0][0])
    sync_query("INSERT INTO address (employee_id, address_line, city, postal_code) "
               "VALUES (%s, 'Jl Rahasia 1', 'Kota', '123')", (eid,))
    if files:
        key = f"{office}/ktp-{tag}.jpg"
        sync_query("INSERT INTO file_object (office_id, storage_key, file_name, mime_type, byte_size, sha256) "
                   "VALUES (%s, %s, 'ktp.jpg', 'image/jpeg', 3, '\\x00'::bytea)", (office, key))
        sync_query("INSERT INTO employee_file (employee_id, type, path_file, active_at) VALUES (%s, 'KTP', %s, now())",
                   (eid, key))
        if store is not None:
            store[key] = b"x"
            store[f"{office}/foto-{tag}.jpg"] = b"x"
    return eid


def test_tanpa_mode_galat() -> None:
    r = subprocess.run([sys.executable, "-m", "app.cli", "hapus-terjadwal"], capture_output=True, text=True)
    assert r.returncode != 0
    r = subprocess.run([sys.executable, "-m", "app.cli", "hapus-terjadwal", "--cek", "--terapkan"],
                       capture_output=True, text=True)
    assert r.returncode != 0


def test_kebijakan_nonaktif_tidak_menghapus(office, fake_storage) -> None:
    eid = _employee(office, separated=31 * D, store=fake_storage)
    s = _run(terapkan=True)
    assert s.jenis["employee_personal_files"].status == "nonaktif"
    assert sync_query("SELECT phone_number FROM employee WHERE employee_id = %s", (eid,))[0][0] == "0812345"
    assert len(fake_storage) == 2


def test_cek_tidak_mengubah_apa_pun(office, fake_storage) -> None:
    eid = _employee(office, separated=31 * D, store=fake_storage)
    _aktif("employee_personal_files")
    logs = sync_query("SELECT count(*) FROM retention_run_log")[0][0]
    s = _run(terapkan=False)
    assert s.jenis["employee_personal_files"].kandidat >= 1
    assert sync_query("SELECT phone_number FROM employee WHERE employee_id = %s", (eid,))[0][0] == "0812345"
    assert len(fake_storage) == 2
    assert sync_query("SELECT count(*) FROM retention_run_log")[0][0] == logs


@pytest.mark.parametrize(("umur", "kena"), [(29 * D + timedelta(hours=23), False), (30 * D, False),
                                            (31 * D, True), (40 * D, True)])
def test_batas_hari_anonimisasi(office, fake_storage, umur, kena) -> None:
    """29h23j & 30h tepat tak disentuh; 31h dan lompatan 10 hari (cron mati) tuntas."""
    now = utcnow()
    eid = _employee(office, separated=umur, store=fake_storage, now=now)
    _aktif("employee_personal_files")
    _run(terapkan=True, now=now)
    row = sync_query("SELECT phone_number, face_embedding, photo_path FROM employee WHERE employee_id = %s", (eid,))[0]
    assert (row[0] is None) is kena
    assert (row[1] is None) is kena
    assert (len(fake_storage) == 0) is kena


def test_anonimisasi_isi_dan_audit_tanpa_data_sensitif(office, fake_storage) -> None:
    eid = _employee(office, separated=35 * D, store=fake_storage)
    sync_query("INSERT INTO attendance (employee_id, attendance_date, target_location_type, office_id, scheduled_in, "
               "scheduled_out, clock_in_at, in_lat, in_lng, face_match_score, face_photo_path, distance_to_target_m, "
               "is_within_attendance_radius, distance_from_main_office_m, city_zone_status, meal_allowance_amount) "
               "VALUES (%s, '2026-01-05', 'OFFICE', %s, '08:00', '17:00', now(), -6.2, 106.8, 0.9, %s, 1, true, 1, "
               "'DALAM_KOTA', 0)", (eid, office, f"{office}/selfie.jpg"))
    fake_storage[f"{office}/selfie.jpg"] = b"x"
    _aktif("employee_personal_files")
    s = _run(terapkan=True)
    assert s.jenis["employee_personal_files"].diproses >= 1
    assert sync_query("SELECT address_line FROM address WHERE employee_id = %s", (eid,))[0][0] == "-"
    assert sync_query("SELECT count(*) FROM attendance WHERE employee_id = %s", (eid,))[0][0] == 1  # absensi tetap
    assert sync_query("SELECT full_name FROM employee WHERE employee_id = %s", (eid,))[0][0].startswith("Rahasia")
    assert fake_storage == {}
    audit = sync_query("SELECT changed_diff::text, actor_role FROM app_activity_logs "
                       "WHERE action = 'RETENTION_ANONYMIZE' AND entity_id = %s", (eid,))
    assert len(audit) == 1 and audit[0][1] == "SYSTEM"
    for sensitif in ("Rahasia", "0812345", "ktp-", "selfie", "0.1"):
        assert sensitif not in audit[0][0]
    # idempoten: jalan kedua tidak melakukan apa pun pada baris ini
    _run(terapkan=True)
    assert sync_query("SELECT count(*) FROM app_activity_logs WHERE action = 'RETENTION_ANONYMIZE' AND entity_id = %s",
                      (eid,))[0][0] == 1


def test_purge_klien_lewat_retensi_dan_idempoten(office) -> None:
    now = utcnow()
    lama = str(sync_query("INSERT INTO client (client_code, name, delete_at) VALUES (%s, 'Klien lama', %s) "
                          "RETURNING client_id", (f"K{uuid.uuid4().hex[:8]}", now - 1826 * D))[0][0])
    baru = str(sync_query("INSERT INTO client (client_code, name, delete_at) VALUES (%s, 'Klien baru', %s) "
                          "RETURNING client_id", (f"K{uuid.uuid4().hex[:8]}", now - 1824 * D))[0][0])
    _aktif("client")
    _run(terapkan=True, now=now)
    assert sync_query("SELECT count(*) FROM client WHERE client_id = %s", (lama,))[0][0] == 0
    assert sync_query("SELECT count(*) FROM client WHERE client_id = %s", (baru,))[0][0] == 1
    assert sync_query("SELECT count(*) FROM app_activity_logs WHERE action = 'RETENTION_PURGE' AND entity_id = %s",
                      (lama,))[0][0] == 1
    s2 = _run(terapkan=True, now=now)
    assert s2.jenis["client"].diproses == 0
    sync_query("DELETE FROM client WHERE client_id = %s", (baru,))
    assert sync_query("SELECT count(*) FROM retention_run_log WHERE mode = 'terapkan'")[0][0] >= 2


def test_pemutus_ambang_dan_paksa(office) -> None:
    now = utcnow()
    ids = [str(sync_query("INSERT INTO client (client_code, name, delete_at) VALUES (%s, 'K', %s) RETURNING client_id",
                          (f"K{uuid.uuid4().hex[:8]}", now - 1900 * D))[0][0]) for _ in range(3)]
    _aktif("client")
    s = _run(terapkan=True, now=now, max_per_type=1)
    assert s.jenis["client"].status == "diblokir" and s.bermasalah
    assert sync_query("SELECT count(*) FROM client WHERE client_id = ANY(%s::uuid[])", (ids,))[0][0] == 3
    _run(terapkan=True, now=now, max_per_type=1, paksa=True)
    assert sync_query("SELECT count(*) FROM client WHERE client_id = ANY(%s::uuid[])", (ids,))[0][0] == 0


def test_baris_dirujuk_ditahan_job_lanjut(office) -> None:
    """Karyawan arsip yang masih jadi PM/OM divisi ditahan (409 purge_row); baris lain tetap diproses."""
    now = utcnow()
    eid = _employee(office, separated=None, archived=1900 * D, files=False)
    div = str(sync_query("INSERT INTO division (om_id, pm_id, name) VALUES (%s, %s, 'Divisi ret') "
                         "RETURNING division_id", (eid, eid))[0][0])
    ok = str(sync_query("INSERT INTO client (client_code, name, delete_at) VALUES (%s, 'K', %s) RETURNING client_id",
                        (f"K{uuid.uuid4().hex[:8]}", now - 1900 * D))[0][0])
    _aktif("employee_row", "client")
    s = _run(terapkan=True, now=now)
    assert s.jenis["employee_row"].ditahan >= 1
    assert sync_query("SELECT count(*) FROM employee WHERE employee_id = %s", (eid,))[0][0] == 1
    assert sync_query("SELECT count(*) FROM client WHERE client_id = %s", (ok,))[0][0] == 0
    sync_query("DELETE FROM division WHERE division_id = %s", (div,))


def test_kegagalan_minio_db_tetap_benar(office, fake_storage, monkeypatch) -> None:
    import app.core.storage as storage_core

    monkeypatch.setattr(storage_core, "delete_object", lambda name: False)
    now = utcnow()
    eid = _employee(office, separated=None, archived=1900 * D, store=fake_storage)
    _aktif("employee_row")
    s = _run(terapkan=True, now=now)
    assert sync_query("SELECT count(*) FROM employee WHERE employee_id = %s", (eid,))[0][0] == 0
    assert s.jenis["employee_row"].berkas_gagal > 0 and s.bermasalah


def test_dua_proses_bersamaan_satu_jalan(office) -> None:
    from tests.concurrency import dua_bersamaan

    now = utcnow()
    lock = f"vms:uji:{uuid.uuid4().hex}"
    for _ in range(3):
        sync_query("INSERT INTO client (client_code, name, delete_at) VALUES (%s, 'K', %s)",
                   (f"K{uuid.uuid4().hex[:8]}", now - 1900 * D))
    _aktif("client")

    def aksi(_i: int) -> service.Summary:
        return _run(terapkan=True, now=now, lock_name=lock, max_per_type=10_000)

    hasil = dua_bersamaan(aksi)
    assert sorted(h.status for h in hasil).count("sedang_berjalan") <= 1
    # tidak ada audit ganda untuk id yang sama
    dup = sync_query("SELECT entity_id, count(*) FROM app_activity_logs WHERE action = 'RETENTION_PURGE' "
                     "AND entity_table = 'client' GROUP BY entity_id HAVING count(*) > 1")
    assert dup == []


def test_batas_waktu_total_berhenti(office) -> None:
    now = utcnow()
    for _ in range(3):
        sync_query("INSERT INTO client (client_code, name, delete_at) VALUES (%s, 'K', %s)",
                   (f"K{uuid.uuid4().hex[:8]}", now - 1900 * D))
    _aktif("client")
    s = _run(terapkan=True, now=now, max_seconds=-1)
    assert s.jenis["client"].status == "batas_waktu" and s.jenis["client"].diproses == 0
    _run(terapkan=True, now=now)  # esok hari lanjut
    assert sync_query("SELECT count(*) FROM client WHERE name = 'K' AND delete_at < %s", (now - 1825 * D,))[0][0] == 0


def test_arsip_kendaraan_ikut_arsipkan_berkas() -> None:
    from app.core.file_cleanup import KEY_COLUMNS

    cols = {(t, c): cond for t, c, cond in KEY_COLUMNS}
    assert cols[("vehicle_file", "path_file")] == "delete_at IS NULL"
    assert cols[("vehicle_inspection", "path_file")] == "delete_at IS NULL"


def test_arsip_kendaraan_mengarsipkan_berkas_dan_inspeksi(office) -> None:
    from sqlalchemy.ext.asyncio import AsyncSession

    from app.database.session import make_engine as _me
    from app.modules.assets.repositories.asset_repository import AssetRepository

    eid = _employee(office, separated=None, files=False)
    div = str(sync_query("INSERT INTO division (om_id, pm_id, name) VALUES (%s, %s, 'Div uji') RETURNING division_id",
                         (eid, eid))[0][0])
    vid = str(sync_query("INSERT INTO vehicle (office_id, division_id, vehicle_type, name, number_plate) "
                         "VALUES (%s, %s, 'Car', 'Mobil uji', %s) RETURNING vehicle_id",
                         (office, div, f"B{uuid.uuid4().hex[:6]}"))[0][0])
    sync_query("INSERT INTO vehicle_file (vehicle_id, type, path_file, active_at, expired_at) "
               "SELECT %s, enumlabel::vehicle_file_type_enum, 'x/y.jpg', now(), now() + interval '1 day' "
               "FROM pg_enum WHERE enumtypid = 'vehicle_file_type_enum'::regtype LIMIT 1", (vid,))

    async def go() -> None:
        engine = _me(_SETUP_URL)
        try:
            async with AsyncSession(engine) as db, db.begin():
                await AssetRepository(db).archive("VEHICLE", vid)
        finally:
            await engine.dispose()

    asyncio.run(go())
    assert sync_query("SELECT delete_at IS NOT NULL FROM vehicle_file WHERE vehicle_id = %s", (vid,))[0][0] is True


def test_restore_karyawan_ditolak_lewat_30_hari(client, office, make_user) -> None:
    from tests.conftest import login_headers

    hr = make_user("HR")
    h = login_headers(client, hr)
    lama = _employee(hr.org_id, separated=31 * D, archived=1 * D, files=False)
    baru = _employee(hr.org_id, separated=5 * D, archived=1 * D, files=False)
    r = client.post(f"/employees/{lama}/restore", headers=h, json={})
    assert r.status_code == 409 and "30 hari" in json.dumps(r.json())
    r = client.post(f"/employees/{baru}/restore", headers=h, json={})
    assert r.status_code == 200
