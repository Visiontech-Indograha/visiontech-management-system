"""Data master survei ACS & CCTV (docs/37): divisi ACS + jenis pekerjaan survei, slot foto, katalog material.

Aman diulang (idempoten): baris yang sudah ada (berdasarkan nama) tidak diduplikasi. Tidak menghapus apa pun.

    cd api
    .venv/Scripts/python.exe ../scripts/seed_survei_acs_cctv.py            # terapkan
    .venv/Scripts/python.exe ../scripts/seed_survei_acs_cctv.py --uji-kering   # jalankan lalu batalkan
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

from sqlalchemy import text  # noqa: E402

from app.database.session import engine  # noqa: E402

CCTV_DIVISION = "Divisi CCTV & Keamanan Elektronik"
ACS_DIVISION = "Divisi Access Control System (ACS)"

# (nama work type, divisi, deskripsi, slot foto [(nama, wajib, petunjuk)], material [(nama, qty, satuan, kategori)])
SURVEYS = [
    (
        "Survei ACS", ACS_DIVISION,
        "Assessment pemasangan ACS per pintu: tampak luar & dalam, remark, material per pintu, Bill of Material.",
        [("Tampak Luar", False, "Foto pintu dari luar (posisi reader/breakglass)."),
         ("Tampak Dalam", False, "Foto pintu dari dalam (posisi exit button/maglock).")],
        [("Lenel 1320", 1, "Unit", "MATERIAL"), ("Power Supply", 1, "Unit", "MATERIAL"),
         ("Battrey backup", 1, "Unit", "MATERIAL"), ("Box Panel", 1, "Unit", "MATERIAL"),
         ("Reader Multiclass", 1, "Unit", "MATERIAL"), ("Emergency Breakglass", 1, "Unit", "MATERIAL"),
         ("Sirine", 1, "Unit", "MATERIAL"), ("Door Contact", 1, "Pasang", "MATERIAL"),
         ("Magnetic Lock", 1, "Pasang", "MATERIAL"), ("Kabel ACS", 1, "Meter", "MATERIAL"),
         ("Pipa Conduit", 1, "Batang", "MATERIAL")],
    ),
    (
        "Survei CCTV", CCTV_DIVISION,
        "Survei titik pemasangan CCTV: posisi kamera & view, remark, hitungan kabel FO, Bill of Material.",
        [("Posisi CCTV", True, "Foto rencana posisi pemasangan kamera."),
         ("View CCTV Camera", True, "Foto area yang akan ditangkap/ditampilkan kamera.")],
        [("CCTV PTZ Outdoor", 1, "Unit", "MATERIAL"), ("CCTV Fix Indoor", 1, "Unit", "MATERIAL"),
         ("Box Panel CCTV Stainless", 1, "Unit", "MATERIAL"), ("POE 30W", 1, "Unit", "MATERIAL"),
         ("Power Suplay PoE", 1, "Unit", "MATERIAL"), ("MCB", 1, "Unit", "MATERIAL"),
         ("FO Converter", 1, "Unit", "MATERIAL"), ("FO Cassette", 1, "Unit", "MATERIAL"),
         ("SFP", 1, "Unit", "MATERIAL"), ("Kabel STP", 1, "Meter", "MATERIAL"),
         ("Box Panel ukuran 60x40x20", 1, "Unit", "MATERIAL"), ("LAN Arester", 1, "Unit", "MATERIAL"),
         ("Busbar", 1, "Unit", "MATERIAL"), ("Outlet 1 lobang", 1, "Unit", "MATERIAL"),
         ("Kabel LAN STP CAT 5E", 1, "Meter", "MATERIAL"), ("Kabel Grounding 1,5mm", 1, "Meter", "MATERIAL"),
         ("Pipa Galvanis 3/4 Inch Panjang 1,5 m", 1, "Batang", "MATERIAL"),
         ("Pipa Galvanis 3/4 Inch Panjang 3 m", 1, "Batang", "MATERIAL"),
         ("Pipa Conduit + Socket", 1, "Batang", "MATERIAL")],
    ),
]


async def main(dry_run: bool) -> None:
    async with engine.connect() as conn:
        tx = await conn.begin()
        cctv = (await conn.execute(text(
            "SELECT division_id, om_id, pm_id FROM division WHERE name = :n AND delete_at IS NULL"),
            {"n": CCTV_DIVISION})).first()
        if cctv is None:
            raise SystemExit(f"Divisi '{CCTV_DIVISION}' tidak ditemukan — seed DB V2 belum dimuat?")
        acs_id = (await conn.execute(text(
            "SELECT division_id FROM division WHERE name = :n AND delete_at IS NULL"), {"n": ACS_DIVISION})).scalar()
        if acs_id is None:
            acs_id = (await conn.execute(text(
                "INSERT INTO division (om_id, pm_id, name, status) VALUES (:om, :pm, :n, TRUE) RETURNING division_id"),
                {"om": cctv.om_id, "pm": cctv.pm_id, "n": ACS_DIVISION})).scalar()
            print(f"+ divisi {ACS_DIVISION} (PM sama dengan divisi CCTV)")
        divisions = {CCTV_DIVISION: cctv.division_id, ACS_DIVISION: acs_id}

        for name, division, desc, slots, materials in SURVEYS:
            div_id = divisions[division]
            wt = (await conn.execute(text(
                "SELECT work_type_id FROM work_type WHERE name = :n AND division_id = :d AND delete_at IS NULL"),
                {"n": name, "d": div_id})).scalar()
            if wt is None:
                wt = (await conn.execute(text(
                    "INSERT INTO work_type (name, description, division_id) VALUES (:n, :desc, :d) "
                    "RETURNING work_type_id"), {"n": name, "desc": desc, "d": div_id})).scalar()
                print(f"+ work type {name}")
            for order, (slot, mandatory, hint) in enumerate(slots, start=1):
                exists = (await conn.execute(text(
                    "SELECT 1 FROM image_requirement WHERE work_type_id = :w AND name = :n AND delete_at IS NULL"),
                    {"w": wt, "n": slot})).first()
                if not exists:
                    await conn.execute(text(
                        "INSERT INTO image_requirement (work_type_id, name, path_image, is_mandatory, sort_order, "
                        "description) VALUES (:w, :n, '', :m, :o, :h)"),
                        {"w": wt, "n": slot, "m": mandatory, "o": order, "h": hint})
                    print(f"  + slot foto {slot}")
            for order, (mat, qty, unit, cat) in enumerate(materials, start=1):
                exists = (await conn.execute(text(
                    "SELECT 1 FROM work_type_default_materials WHERE work_type_id = :w AND material_name = :n "
                    "AND delete_at IS NULL"), {"w": wt, "n": mat})).first()
                if not exists:
                    await conn.execute(text(
                        "INSERT INTO work_type_default_materials (work_type_id, material_name, default_qty, unit, "
                        "category, sort_order) VALUES (:w, :n, :q, :u, :c, :o)"),
                        {"w": wt, "n": mat, "q": qty, "u": unit, "c": cat, "o": order})
            print(f"  material katalog {name}: {len(materials)} baris dicek")

        if dry_run:
            await tx.rollback()
            print("uji kering: dibatalkan")
        else:
            await tx.commit()
            print("selesai")


if __name__ == "__main__":
    asyncio.run(main("--uji-kering" in sys.argv))
