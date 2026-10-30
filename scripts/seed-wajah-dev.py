"""Seed wajah PALSU untuk akun uji DEV (@uji-nyata.test) agar alur absen dengan verifikasi wajah berlaku penuh.

Hanya untuk DB DEV LOKAL: skrip menolak jalan bila host DATABASE_URL bukan localhost/127.0.0.1, atau bila
mode wajah palsu belum aktif (FACE_FAKE_MODE=true dan APP_ENV=development). Idempoten: karyawan yang sudah punya
embedding (nyata maupun palsu) tidak ditimpa.

    cd api
    FACE_FAKE_MODE=true .venv/Scripts/python.exe ../scripts/seed-wajah-dev.py
"""
from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

from sqlalchemy import text
from sqlalchemy.engine import make_url

from app.core.config import settings

LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
DOMAIN = "uji-nyata.test"
ACCOUNTS = ["ketua11", "anggota111", "anggota112", "anggota113", "pm1", "pm2", "hr", "om", "finance"]


def db_host_is_local(database_url: str) -> bool:
    """True hanya bila host DB adalah mesin lokal."""
    return (make_url(database_url).host or "") in LOCAL_HOSTS


def guard() -> None:
    if not db_host_is_local(settings.DATABASE_URL):
        raise SystemExit("Ditolak: skrip ini hanya untuk DB dev lokal (host harus localhost/127.0.0.1).")
    if not (settings.FACE_FAKE_MODE and settings.APP_ENV.strip().lower() == "development"):
        raise SystemExit("Ditolak: jalankan dengan FACE_FAKE_MODE=true dan APP_ENV=development.")


async def main() -> None:
    from app.database.session import engine
    from app.modules.face.services.face_service import FAKE_MODEL, fake_embedding

    guard()
    emails = [f"{name}@{DOMAIN}" for name in ACCOUNTS]
    now = datetime.now().astimezone().isoformat(timespec="seconds")
    async with engine.begin() as conn:
        rows = (await conn.execute(text(
            "SELECT e.employee_id FROM users u JOIN employee e USING (employee_id) "
            "WHERE lower(u.email) = ANY(:m) AND u.delete_at IS NULL AND e.delete_at IS NULL "
            "AND e.face_embedding IS NULL"), {"m": emails})).all()
        for (employee_id,) in rows:
            payload = {"vector": fake_embedding(employee_id), "model": FAKE_MODEL, "version": "0",
                       "enrolled_at": now}
            await conn.execute(text(
                "UPDATE employee SET face_embedding = CAST(:f AS jsonb), update_at = now() "
                "WHERE employee_id = CAST(:e AS uuid) AND face_embedding IS NULL"),
                {"f": json.dumps(payload), "e": str(employee_id)})
    print(f"wajah palsu disuntikkan ke {len(rows)} akun uji ({len(emails)} akun dicek)")


if __name__ == "__main__":
    asyncio.run(main())
