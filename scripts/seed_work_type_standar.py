"""Work type standar semua divisi: Instalasi / Maintenance / Replacement (+ persiapan lapangan CCTV & ACS).

Tiap work type: slot foto sebelum–proses–sesudah (wajib), katalog material dasar per divisi (jumlah bawaan).
Persiapan (scaffolding, galian parit, penarikan kabel) dipakai sebagai item lanjutan hasil survei dan sebagai
prasyarat lintas divisi (kabel ACS menunggu galian CCTV).

Aman diulang (idempoten): nama yang sudah ada di divisi dipakai ulang (slot/material ditambah bila belum ada).
Tidak menghapus apa pun.

    cd api
    .venv/Scripts/python.exe ../scripts/seed_work_type_standar.py            # terapkan
    .venv/Scripts/python.exe ../scripts/seed_work_type_standar.py --uji-kering   # jalankan lalu batalkan
"""
from __future__ import annotations

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "api"))

from sqlalchemy import text  # noqa: E402

from app.database.session import engine  # noqa: E402

PHOTOS = {
    "Instalasi": [("Foto Sebelum", "Kondisi titik sebelum dipasang."),
                  ("Foto Proses", "Proses pemasangan/penarikan kabel."),
                  ("Foto Sesudah", "Perangkat terpasang & berfungsi.")],
    "Maintenance": [("Foto Sebelum", "Kondisi perangkat sebelum dirawat."),
                    ("Foto Proses", "Pembersihan/pengecekan/pengukuran."),
                    ("Foto Sesudah", "Perangkat normal setelah dirawat.")],
    "Replacement": [("Foto Perangkat Lama", "Perangkat yang diganti (label/serial terlihat)."),
                    ("Foto Proses Penggantian", "Proses bongkar & pasang."),
                    ("Foto Perangkat Baru", "Perangkat baru terpasang & berfungsi.")],
}

# divisi → nama singkat, material per jenis [(nama, qty bawaan, satuan)]
DIVISIONS = {
    "Divisi CCTV & Keamanan Elektronik": ("CCTV", {
        "Instalasi": [("Kamera CCTV", 1, "Unit"), ("Bracket Kamera", 1, "Unit"), ("Kabel STP", 30, "Meter"),
                      ("Konektor RJ45", 2, "Buah"), ("Pipa Conduit + Socket", 5, "Batang")],
        "Maintenance": [("Cairan Pembersih Lensa", 1, "Set"), ("Konektor RJ45", 2, "Buah")],
        "Replacement": [("Kamera CCTV", 1, "Unit"), ("Adaptor/PoE Injector", 1, "Unit")],
    }),
    "Divisi Access Control System (ACS)": ("ACS", {
        "Instalasi": [("Reader Multiclass", 1, "Unit"), ("Magnetic Lock", 1, "Pasang"), ("Exit Button", 1, "Unit"),
                      ("Kabel ACS", 30, "Meter"), ("Pipa Conduit", 5, "Batang")],
        "Maintenance": [("Battrey backup", 1, "Unit"), ("Door Contact", 1, "Pasang")],
        "Replacement": [("Reader Multiclass", 1, "Unit"), ("Magnetic Lock", 1, "Pasang"), ("Power Supply", 1, "Unit")],
    }),
    "Divisi Electrical & Arus Kuat": ("Electrical", {
        "Instalasi": [("Panel Distribusi", 1, "Unit"), ("MCB", 2, "Unit"), ("Kabel NYY 4x10mm", 30, "Meter"),
                      ("Kabel Grounding", 10, "Meter")],
        "Maintenance": [("Contact Cleaner", 1, "Buah"), ("Terminal Lug", 4, "Buah")],
        "Replacement": [("MCB", 1, "Unit"), ("Kontaktor", 1, "Unit")],
    }),
    "Divisi Wall Display & LED Screen": ("Wall Display", {
        "Instalasi": [("Panel LED / Monitor", 1, "Unit"), ("Bracket Dinding", 1, "Set"), ("Kabel HDMI", 5, "Meter"),
                      ("Video Controller", 1, "Unit")],
        "Maintenance": [("Cairan Pembersih Layar", 1, "Set")],
        "Replacement": [("Modul LED", 1, "Unit"), ("Power Supply LED", 1, "Unit")],
    }),
}

# Persiapan lapangan (hasil survei) per divisi: (nama, deskripsi, slot foto, material)
PREPARATION = {
    "Divisi CCTV & Keamanan Elektronik": [
        ("Pemasangan Scaffolding", "Scaffolding untuk titik tinggi (dipakai bergantian lintas tim di lokasi yang sama).",
         [("Scaffolding Terpasang", "Scaffolding berdiri, terkunci, ada tag aman.")], [("Sewa Scaffolding", 1, "Set")]),
        ("Galian Parit", "Galian parit jalur kabel (target dalam meter, bisa beberapa hari).",
         [("Foto Galian", "Kedalaman & lebar galian terlihat (pakai meteran)."),
          ("Foto Urug", "Parit ditutup kembali / jalur kabel aman.")], [("Pasir Urug", 1, "Lot")]),
    ],
    "Divisi Access Control System (ACS)": [
        ("Penarikan Kabel ACS", "Penarikan kabel ACS di jalur parit/tray (menunggu galian selesai).",
         [("Foto Jalur Kabel", "Kabel di dalam pipa/parit."), ("Foto Ujung Kabel", "Ujung kabel berlabel di panel.")],
         [("Kabel ACS", 30, "Meter"), ("Pipa Conduit", 5, "Batang")]),
    ],
}


async def _type(conn, div_id, name: str, desc: str) -> tuple[object, bool]:
    wt = (await conn.execute(text(
        "SELECT work_type_id FROM work_type WHERE lower(name) = lower(:n) AND division_id = :d AND delete_at IS NULL"),
        {"n": name, "d": div_id})).scalar()
    if wt is not None:
        return wt, False
    wt = (await conn.execute(text(
        "INSERT INTO work_type (name, description, division_id, kind) VALUES (:n, :desc, :d, 'WORK') "
        "RETURNING work_type_id"), {"n": name, "desc": desc, "d": div_id})).scalar()
    return wt, True


async def _fill(conn, wt, photos, materials) -> None:
    for order, (slot, hint) in enumerate(photos, start=1):
        if not (await conn.execute(text(
                "SELECT 1 FROM image_requirement WHERE work_type_id = :w AND lower(name) = lower(:n) "
                "AND delete_at IS NULL"), {"w": wt, "n": slot})).first():
            await conn.execute(text(
                "INSERT INTO image_requirement (work_type_id, name, path_image, is_mandatory, sort_order, description) "
                "VALUES (:w, :n, 'sop/placeholder.jpg', TRUE, :o, :h)"), {"w": wt, "n": slot, "o": order, "h": hint})
    for order, (mat, qty, unit) in enumerate(materials, start=1):
        if not (await conn.execute(text(
                "SELECT 1 FROM work_type_default_materials WHERE work_type_id = :w AND lower(material_name) = lower(:n) "
                "AND delete_at IS NULL"), {"w": wt, "n": mat})).first():
            await conn.execute(text(
                "INSERT INTO work_type_default_materials (work_type_id, material_name, default_qty, unit, category, "
                "sort_order) VALUES (:w, :n, :q, :u, 'MATERIAL', :o)"),
                {"w": wt, "n": mat, "q": qty, "u": unit, "o": order})


async def main(dry_run: bool) -> None:
    async with engine.connect() as conn:
        tx = await conn.begin()
        for division, (short, kinds) in DIVISIONS.items():
            div_id = (await conn.execute(text(
                "SELECT division_id FROM division WHERE name = :n AND delete_at IS NULL"), {"n": division})).scalar()
            if div_id is None:
                print(f"- lewati: divisi '{division}' tidak ada")
                continue
            for kind, photos in PHOTOS.items():
                name = f"{kind} {short}"
                wt, created = await _type(conn, div_id, name, f"{kind} perangkat {short}.")
                await _fill(conn, wt, photos, kinds[kind])
                print(f"{'+' if created else '='} {name}")
            for name, desc, photos, materials in PREPARATION.get(division, []):
                wt, created = await _type(conn, div_id, name, desc)
                await _fill(conn, wt, [(s, h) for s, h in photos], materials)
                print(f"{'+' if created else '='} {name}")
        if dry_run:
            await tx.rollback()
            print("uji kering: dibatalkan")
        else:
            await tx.commit()
            print("selesai")


if __name__ == "__main__":
    asyncio.run(main("--uji-kering" in sys.argv))
