"""Bersihkan data uji survei & skenario lapangan (soft delete: delete_at diisi, data bisa dikembalikan).

Sasaran: order uji (WO-CCTV-*, WO-ACS-*, WO-SURVEI-UJI, order survei uji tanpa nomor), item yang menempel ke order
itu, dan semua jadwal tim uji survei ("Tim Uji Survei CCTV/ACS"). Tidak menyentuh order/jadwal lain.

    cd api
    .venv/Scripts/python.exe ../scripts/uji/bersihkan_uji_skenario.py --uji-kering   # hitung saja
    .venv/Scripts/python.exe ../scripts/uji/bersihkan_uji_skenario.py                # terapkan
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "api"))

from sqlalchemy import text  # noqa: E402

from app.database.session import engine  # noqa: E402

ORDERS = """
    SELECT completion_id FROM work_completion
    WHERE delete_at IS NULL AND (order_number LIKE 'WO-CCTV-%' OR order_number LIKE 'WO-ACS-%'
          OR order_number = 'WO-SURVEI-UJI'
          OR (order_number IS NULL AND project_title IN ('Survey New CCTV Installation', 'Assesment pemasangan ACS')))
"""
TEAMS = "SELECT team_id FROM team WHERE name IN ('Tim Uji Survei CCTV', 'Tim Uji Survei ACS')"
PLANS = f"SELECT daily_plan_id FROM work_plan_daily WHERE delete_at IS NULL AND team_id IN ({TEAMS})"


async def main(dry_run: bool) -> None:
    async with engine.connect() as conn:
        tx = await conn.begin()
        counts = {
            "order": (await conn.execute(text(f"SELECT count(*) FROM ({ORDERS}) o"))).scalar(),
            "jadwal": (await conn.execute(text(f"SELECT count(*) FROM ({PLANS}) p"))).scalar(),
            "item": (await conn.execute(text(
                f"SELECT count(*) FROM work_plan_item WHERE delete_at IS NULL "
                f"AND (completion_id IN ({ORDERS}) OR daily_plan_id IN ({PLANS}))"))).scalar(),
        }
        print("akan dihapus (soft):", counts)
        if not dry_run:
            await conn.execute(text(
                f"UPDATE work_plan_item SET delete_at = now() WHERE delete_at IS NULL "
                f"AND (completion_id IN ({ORDERS}) OR daily_plan_id IN ({PLANS}))"))
            await conn.execute(text(f"UPDATE work_plan_daily SET delete_at = now() WHERE daily_plan_id IN ({PLANS})"))
            await conn.execute(text(f"UPDATE work_completion SET delete_at = now() WHERE completion_id IN ({ORDERS})"))
            await tx.commit()
            print("selesai")
        else:
            await tx.rollback()
            print("uji kering: tidak ada yang diubah")


if __name__ == "__main__":
    asyncio.run(main("--uji-kering" in sys.argv))
