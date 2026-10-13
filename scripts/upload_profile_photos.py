"""
Upload foto profil karyawan dari folder vms-photos ke MinIO dan simpan referensi
di database. Nama file diacak agar tidak mudah ditebak.

Langkah:
1. Baca daftar file foto di folder vms-photos
2. Cocokkan dengan nama karyawan (fuzzy matching)
3. Generate storage_key teracak (UUID + extension)
4. Upload ke MinIO
5. Insert record ke vms.file_object
6. Print summary
"""

import hashlib
import os
import sys
import uuid
import mimetypes
from pathlib import Path
from difflib import SequenceMatcher

import psycopg2
from minio import Minio

import _config as _cfg
from minio.error import S3Error

# Konfigurasi
PHOTOS_DIR = Path(r"C:\Users\ageng\visiontect-vms\vms-photos")
# Kredensial dibaca dari api/.env (gitignored) atau variabel lingkungan —
# TIDAK ditulis di kode, agar tidak masuk riwayat git (aturan git-flow §8).
MINIO_ENDPOINT = _cfg.get("MINIO_ENDPOINT", "127.0.0.1:9100")
MINIO_ACCESS_KEY = _cfg.get("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = _cfg.get("MINIO_SECRET_KEY")
MINIO_BUCKET = _cfg.get("MINIO_BUCKET", "vms-files")
MINIO_SECURE = _cfg.get("MINIO_SECURE", "false").lower() == "true"

ORG_ID = "01a0dd85-ab65-737b-8938-a1421957055f"
UPLOADED_BY = "01a0e5f5-b2f9-7d30-b862-3de528698747"  # ageng (ADMIN)


def normalize_name(name: str) -> str:
    """Normalisasi nama untuk matching."""
    return "".join(c for c in name.lower() if c.isalnum())


def similarity(a: str, b: str) -> float:
    """Hitung kemiripan dua string."""
    return SequenceMatcher(None, a, b).ratio()


def match_employee(filename: str, employees: list[tuple[str, str]]) -> tuple[str, float] | None:
    """Cocokkan filename dengan nama karyawan. Return (employee_id, score)."""
    # Ekstrak nama dari filename (hapus prefix seperti PAS_FOTO, Foto, dll)
    name_part = Path(filename).stem
    # Hapus prefix umum
    for prefix in ["PAS_FOTO_", "PAS_FOTO", "FOTO_", "Foto_", "foto_", "PASS_FOTO_", "Pass_Foto_", "pass_foto_"]:
        if name_part.upper().startswith(prefix.upper()):
            name_part = name_part[len(prefix):]
    # Hapus suffix seperti _3x4, _merah, _red, _biru, _baru, _new, _fix, _ok
    for suffix in ["_3x4", "_merah", "_red", "_biru", "_blue", "_new", "_fix", "_ok", "_baru", "_latarmerah", "_latar_merah", "_background_merah", "_removebg", "_preview", "_marah", "_pass"]:
        name_part = name_part.lower().replace(suffix, "")

    norm_name = normalize_name(name_part)

    best_match = None
    best_score = 0.0

    for emp_id, emp_name in employees:
        norm_emp = normalize_name(emp_name)
        score = similarity(norm_name, norm_emp)
        if score > best_score:
            best_score = score
            best_match = emp_id

    if best_score > 0.4:
        return best_match, best_score
    return None


MANUAL_OVERRIDES = {
    "Foto_Rusyidi_Biru.jpeg": "01a0dd85-ab83-7c22-8815-6264145700fc",  # RUSYIDI HALOMOAN SEREGAR
    "Pass_Foto_3x4_PHR.jpg": "01a0dd85-ab83-785b-8a1b-4c83681f63d6",  # HANDOKO
    "mega-removebg-preview.png": "01a0dd85-ab8f-7a78-aca4-2ef4a0e3b203",  # MEGAWATI THIO
    "NIta-removebg-preview.png": "01a0dd85-ab7d-7ff7-8b44-c7a92ca20efd",  # Nurfauziah Putri
    "swa_foto_teguh.jpg": "01a0dd85-ab91-7317-ab03-07225b47f56b",  # M. TEGUH WICAKSONO
    "Screenshot_1.png": "01a0dd85-ab91-7317-ab03-07225b47f56b",  # M. TEGUH WICAKSONO
}

SKIP_FILES = {"PAS_FOTO.jpg", "Pass_Foto-Biru.jpg"}

# Untuk karyawan dengan banyak foto, pilih yang skornya tertinggi
PREFERRED_DUPLICATES = {
    "DONI EFENDI": "Foto_Doni_Efendi_New_Merah_Fix_3x4.jpg",
    "SRI WILDANI": "13.Foto_Sri_Wildani.jpg",
    "ROUZI DEWANTORO": "13.Foto_Rouzi_Dewantoro.jpg",
}


def main():
    # 1. Baca daftar file foto
    photo_files = [f for f in PHOTOS_DIR.iterdir() if f.is_file()]
    print(f"[INFO] Ditemukan {len(photo_files)} file foto di {PHOTOS_DIR}")

    # 2. Baca daftar karyawan dari database
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASSWORD, dbname=DB_NAME
    )
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("SELECT id, full_name FROM vms.employee ORDER BY full_name")
    employees = cur.fetchall()
    emp_names = {eid: name for eid, name in employees}
    print(f"[INFO] Ditemukan {len(employees)} karyawan di database")

    # 3. Cocokkan foto ke karyawan
    mappings = []
    unmatched = []
    skipped = []

    for photo_file in photo_files:
        if photo_file.name in SKIP_FILES:
            skipped.append(photo_file)
            continue

        if photo_file.name in MANUAL_OVERRIDES:
            emp_id = MANUAL_OVERRIDES[photo_file.name]
            mappings.append((photo_file, emp_id, 1.0))
            continue

        match = match_employee(photo_file.name, employees)
        if match:
            emp_id, score = match
            mappings.append((photo_file, emp_id, score))
        else:
            unmatched.append(photo_file)

    # 4. Deduplikasi: untuk karyawan dengan banyak foto, pilih yang preferred
    by_emp = {}
    for photo_file, emp_id, score in mappings:
        by_emp.setdefault(emp_id, []).append((photo_file, score))

    final_mappings = []
    for emp_id, photos in by_emp.items():
        if len(photos) == 1:
            final_mappings.append((photos[0][0], emp_id, photos[0][1]))
        else:
            emp_name = emp_names.get(emp_id, emp_id)
            preferred = PREFERRED_DUPLICATES.get(emp_name)
            if preferred:
                for photo_file, score in photos:
                    if photo_file.name == preferred:
                        final_mappings.append((photo_file, emp_id, score))
                        break
                else:
                    # Preferred tidak ada, ambil skor tertinggi
                    best = max(photos, key=lambda x: x[1])
                    final_mappings.append((best[0], emp_id, best[1]))
            else:
                # Ambil skor tertinggi
                best = max(photos, key=lambda x: x[1])
                final_mappings.append((best[0], emp_id, best[1]))

    print(f"\n[OK] Berhasil cocokkan: {len(final_mappings)} foto")
    print(f"[WARN] Tidak cocok: {len(unmatched)} foto")
    print(f"[SKIP] Dilewati: {len(skipped)} foto")

    if unmatched:
        print("\nFoto yang tidak cocok:")
        for f in unmatched:
            print(f"  - {f.name}")

    if skipped:
        print("\nFoto yang dilewati:")
        for f in skipped:
            print(f"  - {f.name}")

    # 4. Upload ke MinIO dan simpan ke database
    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )

    # Pastikan bucket ada
    try:
        if not minio_client.bucket_exists(MINIO_BUCKET):
            minio_client.make_bucket(MINIO_BUCKET)
            print(f"🪣 Bucket '{MINIO_BUCKET}' dibuat")
    except S3Error as e:
        print(f"❌ Gagal membuat bucket: {e}")
        sys.exit(1)

    print(f"\n[UPLOAD] Uploading {len(mappings)} foto ke MinIO...")

    success = 0
    failed = 0

    for photo_file, emp_id, score in final_mappings:
        # Generate storage_key teracak
        ext = photo_file.suffix.lower()
        if not ext:
            ext = mimetypes.guess_extension(photo_file.name) or ".jpg"
        storage_key = f"{ORG_ID}/profile/{uuid.uuid4().hex}{ext}"

        mime_type = mimetypes.guess_type(photo_file.name)[0] or "image/jpeg"

        try:
            # Upload ke MinIO
            minio_client.fput_object(
                MINIO_BUCKET,
                storage_key,
                str(photo_file),
                content_type=mime_type,
            )

            # Insert ke database (SHA256 dihitung untuk integritas)
            file_size = photo_file.stat().st_size
            sha256_hash = hashlib.sha256(photo_file.read_bytes()).digest()
            cur.execute("""
                INSERT INTO vms.file_object (organization_id, storage_key, file_name, mime_type, byte_size, sha256, uploaded_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (ORG_ID, storage_key, photo_file.name, mime_type, file_size, sha256_hash, UPLOADED_BY))
            conn.commit()

            success += 1
            emp_name = next((name for eid, name in employees if eid == emp_id), emp_id)
            print(f"  [OK] {photo_file.name} -> {emp_name} (score={score:.2f})")
        except Exception as e:
            conn.rollback()
            failed += 1
            print(f"  [FAIL] {photo_file.name}: {e}")

    conn.commit()
    conn.close()

    print(f"\n📊 SUMMARY")
    print(f"  ✅ Berhasil: {success}")
    print(f"  ❌ Gagal: {failed}")
    print(f"  📁 Total foto: {len(photo_files)}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
