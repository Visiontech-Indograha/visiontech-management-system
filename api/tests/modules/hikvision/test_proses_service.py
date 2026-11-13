"""Pembentuk absen dari event Hikvision (`proses_event`): satu sesi per karyawan-hari lintas sumber. Butuh DB uji."""
from __future__ import annotations

import itertools
import uuid
from collections.abc import Callable, Iterator
from datetime import datetime, time, timedelta
from typing import Any

import pytest

from app.core.config import settings
from app.core.time import WIB
from app.database.session import make_engine
from app.modules.hikvision.services.proses_service import (
    DIABAIKAN,
    DUPLIKAT,
    LEMBUR_KANDIDAT,
    MASUK,
    PERLU_TINJAU,
    PULANG,
    PULANG_DIPERBARUI,
    RingkasProses,
    proses_event,
    putuskan,
)
from tests.conftest import SeededUser, login_headers, requires_db, sync_query

pytestmark = [requires_db]

HARI = "2026-03-02"  # Senin
_SERIAL = itertools.count(1)
JARAK = timedelta(minutes=30)
BATAS = time(19, 0)


def _t(jam: str, hari: str = HARI) -> datetime:
    return datetime.fromisoformat(f"{hari}T{jam}:00+07:00")


class Dunia:
    """Perangkat + karyawan terpetakan; membersihkan semuanya (urutan FK) saat selesai."""

    def __init__(self, make_user: Callable[..., SeededUser]) -> None:
        self.make_user = make_user
        self.devices: list[str] = []
        self.employees: list[str] = []
        self.users: list[SeededUser] = []

    def karyawan(self) -> tuple[SeededUser, str]:
        u = self.make_user("ADMIN")
        self.users.append(u)
        emp = str(sync_query("SELECT employee_id FROM users WHERE user_id = %s", (u.user_id,))[0][0])
        self.employees.append(emp)
        return u, emp

    def perangkat(self, office: str, mode: str = "AKTIF", aktif: bool = True) -> str:
        d = str(sync_query(
            "INSERT INTO hikvision_device (office_id, name, ip_address, serial_no, token_hash, mode, aktif) "
            "VALUES (%s, 'Pintu uji', '192.0.2.10', %s, %s, %s, %s) RETURNING device_id",
            (office, f"DS-PRS-{uuid.uuid4().hex[:8]}", uuid.uuid4().hex + uuid.uuid4().hex, mode, aktif))[0][0])
        self.devices.append(d)
        return d

    def petakan(self, device: str, no: str, emp: str) -> None:
        sync_query("INSERT INTO hikvision_employee_map (device_id, employee_no_string, employee_id) "
                   "VALUES (%s, %s, %s)", (device, no, emp))

    def tap(self, device: str, no: str, waktu: datetime, minor: int = 75) -> str:
        return str(sync_query(
            "INSERT INTO hikvision_event (device_id, serial_no_event, major_event_type, minor_event_type, "
            "event_time, employee_no_string, payload, sumber, employee_id) "
            "SELECT %s, %s, 5, %s, %s, %s, '{}'::jsonb, 'PULL', "
            "(SELECT employee_id FROM hikvision_employee_map WHERE device_id = %s AND employee_no_string = %s "
            "AND delete_at IS NULL) RETURNING event_id",
            (device, next(_SERIAL), minor, waktu, no, device, no))[0][0])

    def absen(self, emp: str) -> list[Any]:
        return sync_query(
            "SELECT clock_in_at, clock_out_at, source, face_photo_path, face_status, om_approval_status, "
            "office_id, meal_allowance_amount, attendance_date, device_event_id FROM attendance "
            "WHERE employee_id = %s AND delete_at IS NULL ORDER BY attendance_date, clock_in_at", (emp,))

    def sesi_aplikasi(self, emp: str, office: str, masuk: datetime, pulang: datetime | None,
                      status: str = "AUTO_VALID") -> None:
        sync_query(
            "INSERT INTO attendance (employee_id, attendance_date, target_location_type, office_id, scheduled_in, "
            "scheduled_out, clock_in_at, clock_out_at, in_lat, in_lng, face_match_score, face_photo_path, "
            "distance_to_target_m, is_within_attendance_radius, om_approval_status, distance_from_main_office_m, "
            "city_zone_status, meal_allowance_amount) VALUES (%s, %s, 'OFFICE', %s, '08:00', '17:00', %s, %s, "
            "-6.2, 106.8, 90, 'x/selfie.jpg', 0, TRUE, %s, 0, 'DALAM_KOTA', 35000)",
            (emp, masuk.astimezone(WIB).date(), office, masuk, pulang, status))

    def bersihkan(self) -> None:
        for emp in self.employees:
            sync_query("UPDATE attendance SET device_event_id = NULL WHERE employee_id = %s", (emp,))
            sync_query("DELETE FROM attendance WHERE employee_id = %s", (emp,))
        for d in self.devices:
            sync_query("DELETE FROM hikvision_event WHERE device_id = %s", (d,))
            sync_query("DELETE FROM hikvision_employee_map WHERE device_id = %s", (d,))
            sync_query("DELETE FROM hikvision_device WHERE device_id = %s", (d,))


@pytest.fixture()
def dunia(make_user: Callable[..., SeededUser]) -> Iterator[Dunia]:
    d = Dunia(make_user)
    try:
        yield d
    finally:
        d.bersihkan()


async def _jalan(dunia: Dunia, **kw: Any) -> RingkasProses:
    from sqlalchemy.ext.asyncio import AsyncSession

    engine = make_engine(settings.DATABASE_URL)
    try:
        async with AsyncSession(engine) as db:
            return await proses_event(db, perangkat=list(dunia.devices), **kw)
    finally:
        await engine.dispose()


def _siap(dunia: Dunia, mode: str = "AKTIF", aktif: bool = True) -> tuple[SeededUser, str, str]:
    u, emp = dunia.karyawan()
    dev = dunia.perangkat(u.org_id, mode, aktif)
    dunia.petakan(dev, "9001", emp)
    return u, emp, dev


# --- keputusan murni ---------------------------------------------------------------------------------------------

class _A:
    def __init__(self, masuk: datetime, pulang: datetime | None = None, status: str = "AUTO_VALID",
                 source: str | None = None) -> None:
        self.clock_in_at, self.clock_out_at, self.om_approval_status, self.source = masuk, pulang, status, source


def test_putuskan_tabel_keputusan() -> None:
    assert putuskan(None, _t("07:55"), JARAK, BATAS) == MASUK
    assert putuskan(None, _t("19:00"), JARAK, BATAS) == LEMBUR_KANDIDAT
    assert putuskan(_A(_t("08:00")), _t("08:29"), JARAK, BATAS) == DUPLIKAT
    assert putuskan(_A(_t("08:00")), _t("08:30"), JARAK, BATAS) == PULANG
    assert putuskan(_A(_t("08:00"), status="PENDING_OM"), _t("17:00"), JARAK, BATAS) == PERLU_TINJAU
    assert putuskan(_A(_t("08:00"), _t("17:00")), _t("17:30"), JARAK, BATAS) == DIABAIKAN
    assert putuskan(_A(_t("08:00"), _t("17:00"), source="HIKVISION"), _t("17:30"), JARAK, BATAS) == PULANG_DIPERBARUI


# --- terhadap DB --------------------------------------------------------------------------------------------------

@pytest.mark.anyio
async def test_masuk_pulang_normal_dan_idempoten(dunia: Dunia) -> None:
    u, emp, dev = _siap(dunia)
    dunia.tap(dev, "9001", _t("07:55"))
    dunia.tap(dev, "9001", _t("17:05"))
    r = await _jalan(dunia)
    assert (r.masuk_dibuat, r.pulang_diisi) == (1, 1)
    (a,) = dunia.absen(emp)
    assert a[0] == _t("07:55") and a[1] == _t("17:05")
    assert a[2] == "HIKVISION" and a[3] == "HIKVISION" and a[4] == "NOT_CHECKED" and a[5] == "AUTO_VALID"
    assert str(a[6]) == u.org_id and a[8].isoformat() == HARI and a[9] is not None
    r2 = await _jalan(dunia)  # diulang: tidak ada perubahan
    assert (r2.event_dibaca, r2.masuk_dibuat, r2.pulang_diisi) == (0, 0, 0)
    assert len(dunia.absen(emp)) == 1


@pytest.mark.anyio
async def test_dry_run_tidak_menyimpan(dunia: Dunia) -> None:
    _, emp, dev = _siap(dunia)
    dunia.tap(dev, "9001", _t("07:55"))
    r = await _jalan(dunia, dry_run=True)
    assert r.masuk_dibuat == 1
    assert dunia.absen(emp) == []
    assert sync_query("SELECT count(*) FROM hikvision_event WHERE device_id = %s AND diproses_at IS NULL",
                      (dev,))[0][0] == 1


@pytest.mark.anyio
async def test_campur_sumber_hp_masuk_mesin_pulang(dunia: Dunia) -> None:
    u, emp, dev = _siap(dunia)
    dunia.sesi_aplikasi(emp, u.org_id, _t("08:10"), None)
    dunia.tap(dev, "9001", _t("17:02"))
    r = await _jalan(dunia)
    assert (r.masuk_dibuat, r.pulang_diisi) == (0, 1)
    (a,) = dunia.absen(emp)
    assert a[0] == _t("08:10") and a[1] == _t("17:02") and a[2] is None  # sumber HP tidak ditimpa
    assert a[9] is not None


@pytest.mark.anyio
async def test_campur_lintas_hari_dan_sisi_hp_tidak_ditimpa(dunia: Dunia) -> None:
    u, emp, dev = _siap(dunia)
    hari2 = "2026-03-03"
    dunia.tap(dev, "9001", _t("07:50"))
    dunia.tap(dev, "9001", _t("17:10"))
    dunia.sesi_aplikasi(emp, u.org_id, _t("08:00", hari2), _t("16:00", hari2))  # HP lengkap
    dunia.tap(dev, "9001", _t("08:05", hari2))
    dunia.tap(dev, "9001", _t("17:30", hari2))
    r = await _jalan(dunia)
    assert (r.masuk_dibuat, r.pulang_diisi, r.diabaikan, r.duplikat) == (1, 1, 2, 0)
    d1, d2 = dunia.absen(emp)
    assert d1[2] == "HIKVISION" and d1[1] == _t("17:10")
    assert d2[2] is None and d2[0] == _t("08:00", hari2) and d2[1] == _t("16:00", hari2)


@pytest.mark.anyio
async def test_event_ganda_dan_jarak_minimum(dunia: Dunia) -> None:
    _, emp, dev = _siap(dunia)
    for jam in ("08:00", "08:02", "08:29"):
        dunia.tap(dev, "9001", _t(jam))
    r = await _jalan(dunia)
    assert (r.masuk_dibuat, r.duplikat, r.pulang_diisi) == (1, 2, 0)
    assert dunia.absen(emp)[0][1] is None
    dunia.tap(dev, "9001", _t("08:30"))
    r = await _jalan(dunia)
    assert r.pulang_diisi == 1 and dunia.absen(emp)[0][1] == _t("08:30")


@pytest.mark.anyio
async def test_pulang_terakhir_menang_untuk_sesi_mesin(dunia: Dunia) -> None:
    _, emp, dev = _siap(dunia)
    for jam in ("08:00", "16:00", "17:20"):
        dunia.tap(dev, "9001", _t(jam))
    r = await _jalan(dunia)
    assert (r.pulang_diisi, r.pulang_diperbarui) == (1, 1)
    assert dunia.absen(emp)[0][1] == _t("17:20")


@pytest.mark.anyio
async def test_setelah_jam_batas(dunia: Dunia) -> None:
    _, emp, dev = _siap(dunia)
    dunia.tap(dev, "9001", _t("19:30"))
    r = await _jalan(dunia)
    assert (r.lembur_kandidat, r.masuk_dibuat) == (1, 0) and dunia.absen(emp) == []


@pytest.mark.anyio
async def test_sesi_menunggu_om_tidak_ditutup_mesin(dunia: Dunia) -> None:
    u, emp, dev = _siap(dunia)
    dunia.sesi_aplikasi(emp, u.org_id, _t("08:10"), None, status="PENDING_OM")
    dunia.tap(dev, "9001", _t("17:02"))
    r = await _jalan(dunia)
    assert r.perlu_tinjau == 1 and dunia.absen(emp)[0][1] is None


@pytest.mark.anyio
async def test_shadow_tidak_membuat_absen_tetapi_bisa_disimulasi(dunia: Dunia) -> None:
    _, emp, dev = _siap(dunia, mode="SHADOW")
    dunia.tap(dev, "9001", _t("07:55"))
    r = await _jalan(dunia)
    assert (r.masuk_dibuat, r.event_dibaca) == (0, 0) and dunia.absen(emp) == []
    assert r.bayangan_tertunda >= 1
    sim = await _jalan(dunia, dry_run=True, sertakan_bayangan=True)
    assert sim.absen_dihasilkan >= 1 and dunia.absen(emp) == []
    assert sync_query("SELECT diproses_at FROM hikvision_event WHERE device_id = %s", (dev,))[0][0] is None


@pytest.mark.anyio
async def test_tak_terpetakan_diabaikan_dan_terhitung_lalu_dipetakan_ulang(dunia: Dunia) -> None:
    u, emp = dunia.karyawan()
    dev = dunia.perangkat(u.org_id)
    dunia.tap(dev, "7777", _t("08:00"))
    r = await _jalan(dunia)
    assert r.masuk_dibuat == 0 and r.tak_terpetakan >= 1 and dunia.absen(emp) == []
    dunia.petakan(dev, "7777", emp)
    r = await _jalan(dunia)
    assert r.dipetakan_ulang >= 1 and r.masuk_dibuat == 1


@pytest.mark.anyio
async def test_perangkat_nonaktif_diabaikan(dunia: Dunia) -> None:
    _, emp, dev = _siap(dunia, aktif=False)
    dunia.tap(dev, "9001", _t("08:00"))
    await _jalan(dunia)
    assert dunia.absen(emp) == []


@pytest.mark.anyio
async def test_kantor_perangkat_berbeda_dipakai(dunia: Dunia, make_user: Callable[..., SeededUser]) -> None:
    _, emp = dunia.karyawan()
    lain = make_user("ADMIN")  # kantor uji lain
    dev = dunia.perangkat(lain.org_id)
    dunia.petakan(dev, "9001", emp)
    dunia.tap(dev, "9001", _t("08:00"))
    await _jalan(dunia)
    assert str(dunia.absen(emp)[0][6]) == lain.org_id


@pytest.mark.anyio
async def test_rekap_dan_ekspor_membaca_absen_mesin(dunia: Dunia, client: Any) -> None:
    u, emp, dev = _siap(dunia)
    dunia.tap(dev, "9001", _t("07:55"))
    dunia.tap(dev, "9001", _t("17:05"))
    await _jalan(dunia)
    h = login_headers(client, u)
    rekap = client.get("/attendance/me/recap", params={"month": "2026-03"}, headers=h)
    assert rekap.status_code == 200, rekap.text
    teks = rekap.text
    assert HARI in teks
    uang = client.get("/attendance/meal-allowance", params={"start_date": HARI, "end_date": HARI}, headers=h)
    assert uang.status_code == 200, uang.text
    assert any(str(b.get("employee_id")) == emp for b in uang.json())
    daftar = client.get("/attendance", params={"from": HARI, "to": HARI, "employee_id": emp}, headers=h)
    assert daftar.status_code == 200, daftar.text
    ekspor = client.get("/attendance/export", params={"start_date": HARI, "end_date": HARI}, headers=h)
    assert ekspor.status_code == 200 and "HIKVISION" not in ekspor.text.split("\n", 1)[0]
