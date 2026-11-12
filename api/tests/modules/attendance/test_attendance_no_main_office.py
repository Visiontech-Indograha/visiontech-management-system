"""Instalasi baru tanpa kantor utama: absen tidak boleh 500 (temuan E2E A5) dan kantor pertama otomatis jadi utama.

Tes memakai transaksi yang di-rollback: hanya sesi ini yang "tidak melihat" kantor utama, tes lain (xdist) aman."""
from __future__ import annotations

import asyncio
import io
import uuid
from datetime import UTC, datetime

import pytest
from PIL import Image

from app.database.session import AsyncSessionLocal
from app.modules.attendance.repositories.attendance_session_repository import AttendanceSessionRepository
from app.modules.offices.repositories.office_repository import OfficeRepository
from app.modules.offices.schemas.office_schema import OfficeCreate
from app.modules.offices.services.office_service import OfficeService
from tests.conftest import requires_db, sync_query

pytestmark = [requires_db, pytest.mark.usefixtures("fake_storage")]


def _selfie(client, world) -> str:
    buf = io.BytesIO()
    Image.new("RGB", (32, 32), (7, 77, 177)).save(buf, "PNG")
    up = client.post("/files/upload", headers=world.headers(client, "member"),
                     files={"file": ("swafoto.png", buf.getvalue(), "image/png")})
    assert up.status_code == 200, up.text
    return str(up.json()["file_id"])


def test_check_in_insert_without_main_office_does_not_fail(client, world):
    selfie = _selfie(client, world)
    lat, lng = sync_query("SELECT latitude, longitude FROM office WHERE office_id = %s", (world.site_id,))[0]

    async def run():
        async with AsyncSessionLocal() as session:
            try:
                await session.execute(__import__("sqlalchemy").text("UPDATE office SET is_main_office = FALSE"))
                repo = AttendanceSessionRepository(session)
                return await repo.insert(
                    org_id=world.org_id, employee_id=world.employees["member"], work_date=datetime.now(UTC).date(),
                    site_id=uuid.UUID(world.site_id), site_label="Kantor", lng=float(lng), lat=float(lat),
                    origin="GPS", selfie_file_id=uuid.UUID(selfie), face_result="MATCH", face_similarity=0.99,
                    face_status="MATCHED", source="MOBILE")
            finally:
                await session.rollback()

    row = asyncio.run(run())
    assert row is not None


def test_first_office_becomes_main_when_none_exists():
    async def run():
        async with AsyncSessionLocal() as session:
            try:
                sa = __import__("sqlalchemy")
                await session.execute(sa.text("UPDATE office SET is_main_office = FALSE"))
                svc = OfficeService.__new__(OfficeService)
                svc.repo = OfficeRepository(session)
                svc._audit = _noop  # type: ignore[method-assign]
                row = await svc.create_office(
                    None, OfficeCreate(name="Kantor Pertama", address="Jl. A", location={"lat": 0.5, "lng": 101.4}))  # type: ignore[arg-type]
                return row.is_main_office
            finally:
                await session.rollback()

    assert asyncio.run(run()) is True


async def _noop(*_a, **_k) -> None:
    return None
