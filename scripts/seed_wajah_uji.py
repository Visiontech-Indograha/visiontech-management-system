"""Uji lokal: salin data wajah yang sudah terdaftar ke semua akun uji (PM, ketua, anggota) yang belum punya.

Hanya untuk DB uji — supaya akun uji bisa langsung membuka aplikasi tanpa pendaftaran wajah.

    cd api
    .venv/Scripts/python.exe ../scripts/seed_wajah_uji.py
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from sqlalchemy import text  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.database.session import engine  # noqa: E402
from seed_tim_lapangan import PMS, TEAMS  # noqa: E402


async def main() -> None:
    if settings.APP_ENV == "production":
        raise SystemExit("Ditolak: hanya untuk DB uji.")
    mails = list(PMS.values()) + [m for _, lead, mem in TEAMS.values() for m in [lead, *mem]]
    async with engine.begin() as conn:
        src = (await conn.execute(text(
            "SELECT face_embedding FROM employee WHERE face_embedding IS NOT NULL AND delete_at IS NULL LIMIT 1"
        ))).scalar()
        if src is None:  # belum ada wajah sama sekali → vektor uji (absen wajah tidak akan cocok; hanya untuk UI)
            src = {"vector": [0.0441941738] * 512, "model": "uji-lokal", "version": "0",
                   "enrolled_at": "2026-10-22T00:00:00+07:00"}
        n = (await conn.execute(text(
            "UPDATE employee e SET face_embedding = CAST(:f AS jsonb) FROM users u "
            "WHERE u.employee_id = e.employee_id AND lower(u.email) = ANY(:m) AND e.face_embedding IS NULL"),
            {"f": src if isinstance(src, str) else __import__("json").dumps(src), "m": [m.lower() for m in mails]},
        )).rowcount
    print(f"wajah disalin ke {n} akun uji")


if __name__ == "__main__":
    asyncio.run(main())
