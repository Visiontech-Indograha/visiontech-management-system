"""Jenis titik survei dinamis (docs/37 §9): peran work type survei, jenis titik ACS/CCTV + pemasangan lanjutannya.

- "Survei ACS" / "Survei CCTV" → kind SURVEY_TASK.
- Jenis titik (SURVEY_POINT) per divisi, masing-masing dengan slot foto, katalog material (+ jumlah bawaan), dan
  work type pemasangan lanjutan (WORK) yang dibuat bila belum ada.
- Titik survei lama yang masih memakai work type tugas survei dipindahkan ke jenis titik pertama divisinya
  (nama slot foto sama, jadi foto lama tetap cocok).

Aman diulang (idempoten): baris yang sudah ada (berdasarkan nama) tidak diduplikasi. Tidak menghapus apa pun.
Jalankan setelah scripts/seed_survei_acs_cctv.py.

    cd api
    .venv/Scripts/python.exe ../scripts/seed_jenis_titik_survei.py            # terapkan
    .venv/Scripts/python.exe ../scripts/seed_jenis_titik_survei.py --uji-kering   # jalankan lalu batalkan
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
SURVEY_TASKS = [("Survei ACS", ACS_DIVISION), ("Survei CCTV", CCTV_DIVISION)]

# (nama jenis titik, divisi, deskripsi, pemasangan lanjutan, slot [(nama, wajib, petunjuk)],
#  material [(nama, jumlah bawaan, satuan)])
POINT_TYPES = [
    (
        "Pintu Akses", ACS_DIVISION, "Pintu yang dipasang reader akses (kartu/sidik jari).", "Instalasi ACS Pintu",
        [("Tampak Luar", True, "Foto pintu dari luar (posisi reader)."),
         ("Tampak Dalam", True, "Foto pintu dari dalam (posisi exit button/maglock).")],
        [("Lenel 1320", 1, "Unit"), ("Reader Multiclass", 1, "Unit"), ("Magnetic Lock", 1, "Pasang"),
         ("Door Contact", 1, "Pasang"), ("Exit Button", 1, "Unit"), ("Power Supply", 1, "Unit"),
         ("Battrey backup", 1, "Unit"), ("Box Panel", 1, "Unit"), ("Kabel ACS", 30, "Meter"),
         ("Pipa Conduit", 5, "Batang")],
    ),
    (
        "Pintu Emergency + Alarm", ACS_DIVISION, "Pintu darurat dengan breakglass & alarm emergency exit.",
        "Instalasi Emergency Alarm",
        [("Tampak Luar", True, "Foto pintu darurat (satu sisi cukup).")],
        [("Emergency Breakglass", 1, "Unit"), ("Sirine", 1, "Unit"), ("Door Contact", 1, "Pasang"),
         ("Magnetic Lock", 1, "Pasang"), ("Kabel ACS", 30, "Meter"), ("Pipa Conduit", 5, "Batang")],
    ),
    (
        "Barrier Gate", ACS_DIVISION, "Palang pintu kendaraan otomatis.", "Instalasi Barrier Gate",
        [("Area Gate", True, "Foto area jalur kendaraan & posisi palang."),
         ("Posisi Tiang & Reader", True, "Foto posisi tiang barrier dan reader/loop detector.")],
        [("Barrier Gate Motor", 1, "Unit"), ("Boom Arm", 1, "Unit"), ("Loop Detector", 1, "Unit"),
         ("Reader UHF Long Range", 1, "Unit"), ("Kabel Loop", 20, "Meter"), ("Kabel Power 3x2,5mm", 30, "Meter"),
         ("Pipa Galvanis 3/4 Inch Panjang 3 m", 4, "Batang")],
    ),
    (
        "Titik Kamera CCTV", CCTV_DIVISION, "Posisi pemasangan satu kamera CCTV.", "Instalasi CCTV",
        [("Posisi CCTV", True, "Foto rencana posisi pemasangan kamera."),
         ("View CCTV Camera", True, "Foto area yang akan ditangkap kamera.")],
        [("CCTV PTZ Outdoor", 1, "Unit"), ("CCTV Fix Indoor", 1, "Unit"), ("Box Panel CCTV Stainless", 1, "Unit"),
         ("POE 30W", 1, "Unit"), ("FO Converter", 1, "Unit"), ("SFP", 1, "Unit"), ("Kabel STP", 30, "Meter"),
         ("Kabel Grounding 1,5mm", 10, "Meter"), ("Pipa Conduit + Socket", 5, "Batang")],
    ),
]


async def _work_type(conn, name: str, div_id, kind: str, desc: str, follow_up=None):
    wt = (await conn.execute(text(
        "SELECT work_type_id FROM work_type WHERE lower(name) = lower(:n) AND division_id = :d AND delete_at IS NULL"),
        {"n": name, "d": div_id})).scalar()
    if wt is None:
        wt = (await conn.execute(text(
            "INSERT INTO work_type (name, description, division_id, kind, follow_up_work_type_id) "
            "VALUES (:n, :desc, :d, :k, :f) RETURNING work_type_id"),
            {"n": name, "desc": desc, "d": div_id, "k": kind, "f": follow_up})).scalar()
        print(f"+ work type {name} ({kind})")
    else:
        await conn.execute(text(
            "UPDATE work_type SET kind = :k, follow_up_work_type_id = COALESCE(:f, follow_up_work_type_id) "
            "WHERE work_type_id = :w"), {"k": kind, "f": follow_up, "w": wt})
    return wt


async def main(dry_run: bool) -> None:
    async with engine.connect() as conn:
        tx = await conn.begin()
        divisions = {}
        for name in (ACS_DIVISION, CCTV_DIVISION):
            div = (await conn.execute(text(
                "SELECT division_id FROM division WHERE name = :n AND delete_at IS NULL"), {"n": name})).scalar()
            if div is None:
                raise SystemExit(f"Divisi '{name}' tidak ditemukan — jalankan seed_survei_acs_cctv.py dulu.")
            divisions[name] = div

        task_types = {}
        for name, division in SURVEY_TASKS:
            task_types[division] = await _work_type(conn, name, divisions[division], "SURVEY_TASK", "")

        first_point_type = {}
        for name, division, desc, install, slots, materials in POINT_TYPES:
            div_id = divisions[division]
            install_id = await _work_type(conn, install, div_id, "WORK", f"Pemasangan {name.lower()} hasil survei.")
            wt = await _work_type(conn, name, div_id, "SURVEY_POINT", desc, install_id)
            first_point_type.setdefault(division, wt)
            for order, (slot, mandatory, hint) in enumerate(slots, start=1):
                exists = (await conn.execute(text(
                    "SELECT 1 FROM image_requirement WHERE work_type_id = :w AND name = :n AND delete_at IS NULL"),
                    {"w": wt, "n": slot})).first()
                if not exists:
                    await conn.execute(text(
                        "INSERT INTO image_requirement (work_type_id, name, path_image, is_mandatory, sort_order, "
                        "description) VALUES (:w, :n, 'sop/placeholder.jpg', :m, :o, :h)"),
                        {"w": wt, "n": slot, "m": mandatory, "o": order, "h": hint})
                    print(f"  + slot foto {slot}")
            for order, (mat, qty, unit) in enumerate(materials, start=1):
                exists = (await conn.execute(text(
                    "SELECT 1 FROM work_type_default_materials WHERE work_type_id = :w AND lower(material_name) = "
                    "lower(:n) AND delete_at IS NULL"), {"w": wt, "n": mat})).first()
                if not exists:
                    await conn.execute(text(
                        "INSERT INTO work_type_default_materials (work_type_id, material_name, default_qty, unit, "
                        "category, sort_order) VALUES (:w, :n, :q, :u, 'MATERIAL', :o)"),
                        {"w": wt, "n": mat, "q": qty, "u": unit, "o": order})
            print(f"  katalog {name}: {len(materials)} material dicek")

        # Titik lama: work type tugas survei → jenis titik pertama divisinya.
        for division, task_wt in task_types.items():
            moved = (await conn.execute(text(
                "UPDATE work_plan_item SET work_type_id = :new, point_status = COALESCE(point_status, 'PROPOSED') "
                "WHERE work_type_id = :old AND task_phase = 'SURVEY' AND depends_on_item_id IS NOT NULL "
                "AND delete_at IS NULL"), {"new": first_point_type[division], "old": task_wt})).rowcount
            if moved:
                print(f"~ {moved} titik lama {division} dipindah ke jenis titik pertama")

        if dry_run:
            await tx.rollback()
            print("uji kering: dibatalkan")
        else:
            await tx.commit()
            print("selesai")


if __name__ == "__main__":
    asyncio.run(main("--uji-kering" in sys.argv))
