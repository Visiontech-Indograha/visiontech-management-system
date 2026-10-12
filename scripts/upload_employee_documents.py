"""
Upload dokumen karyawan dari folder uploads ke MinIO dan simpan ke employee_document.
Mapping dokumen ke employee berdasarkan nama file (fuzzy matching).
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
UPLOADS_DIR = Path(r"C:\Users\ageng\visiontect-vms\uploads")
# Kredensial dibaca dari api/.env (gitignored) atau variabel lingkungan —
# TIDAK ditulis di kode, agar tidak masuk riwayat git (aturan git-flow §8).
MINIO_ENDPOINT = _cfg.get("MINIO_ENDPOINT", "127.0.0.1:9100")
MINIO_ACCESS_KEY = _cfg.get("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = _cfg.get("MINIO_SECRET_KEY")
MINIO_BUCKET = _cfg.get("MINIO_BUCKET", "vms-files")
MINIO_SECURE = _cfg.get("MINIO_SECURE", "false").lower() == "true"

ORG_ID = "01a0dd85-ab65-737b-8938-a1421957055f"
UPLOADED_BY = "01a0e5f5-b2f9-7d30-b862-3de528698747"  # ageng (ADMIN)

# Mapping folder ke doc_type
FOLDER_TO_DOCTYPE = {
    "dokumen_pribadi": "DOKUMEN_PRIBADI",
    "dokumen_internal": "DOKUMEN_INTERNAL",
    "kendaraan": "KENDARAAN",
    "kontrak": "KONTRAK",
    "mcu": "MCU",
    "sertifikat": "SERTIFIKAT",
    "sim": "SIM",
}


def normalize_name(name: str) -> str:
    return "".join(c for c in name.lower() if c.isalnum())


def similarity(a: str, b: str) -> float:
    return SequenceMatcher(None, a, b).ratio()


def extract_names_from_filename(filename: str) -> list[str]:
    """Ekstrak kemungkinan nama dari filename dokumen."""
    name_part = Path(filename).stem
    # Hapus prefix angka dan titik
    parts = name_part.replace(".", " ").replace("_", " ").split()
    # Filter kata-kata umum
    stopwords = {"KTP", "BPJS", "Kesehatan", "Ketenagakerjaan", "Depan", "Belakang", "PDF", "JPG", "JPEG", "PNG", "New", "NEW", "rev", "Rev", "e", "E", "KIS", "KK", "Kartu", "Keluarga", "Tanda", "Penduduk", "Seumur", "Hidup", "Berlaku", "UU", "No", "Tahun", "2013", "2024", "2025", "2026", "Scan", "SCAN", "STNK", "KIR", "BM", "HILUX", "TRITON", "Line", "Flight", "Drone", "Time", "Timeline", "eKTP", "Berlaku", "seumur", "hidup", "UU", "No", "24", "Tahun", "2013"}
    names = [p for p in parts if p not in stopwords and len(p) > 2]
    return names


def match_employee_from_doc(filename: str, employees: list[tuple[str, str]]) -> tuple[str, float] | None:
    """Cocokkan dokumen ke employee berdasarkan nama di filename."""
    names_in_file = extract_names_from_filename(filename)
    if not names_in_file:
        return None

    best_match: str | None = None
    best_score = 0.0

    for emp_id, emp_name in employees:
        norm_emp = normalize_name(emp_name)
        for name in names_in_file:
            norm_name = normalize_name(name)
            score = similarity(norm_name, norm_emp)
            if score > best_score:
                best_score = score
                best_match = emp_id

    if best_score > 0.3 and best_match is not None:
        return best_match, best_score
    return None


def main():
    # 1. Baca daftar file
    doc_files = []
    for folder in UPLOADS_DIR.iterdir():
        if folder.is_dir():
            for f in folder.iterdir():
                if f.is_file():
                    doc_files.append((f, folder.name))
    print(f"[INFO] Ditemukan {len(doc_files)} file dokumen di {UPLOADS_DIR}")

    # 2. Baca daftar karyawan
    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASSWORD, dbname=DB_NAME
    )
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("SELECT id, full_name FROM vms.employee ORDER BY full_name")
    employees = cur.fetchall()
    print(f"[INFO] Ditemukan {len(employees)} karyawan di database")

    # 3. Upload ke MinIO dan simpan ke database
    minio_client = Minio(
        MINIO_ENDPOINT,
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        secure=MINIO_SECURE,
    )

    try:
        if not minio_client.bucket_exists(MINIO_BUCKET):
            minio_client.make_bucket(MINIO_BUCKET)
            print(f"[INFO] Bucket '{MINIO_BUCKET}' dibuat")
    except S3Error as e:
        print(f"[ERROR] Gagal membuat bucket: {e}")
        sys.exit(1)

    print(f"\n[UPLOAD] Uploading {len(doc_files)} dokumen ke MinIO...")

    success = 0
    failed = 0
    skipped = 0

    for doc_file, folder_name in doc_files:
        doc_type = FOLDER_TO_DOCTYPE.get(folder_name, "LAINNYA")

        # Generate storage_key teracak
        ext = doc_file.suffix.lower()
        if not ext:
            ext = mimetypes.guess_extension(doc_file.name) or ".bin"
        storage_key = f"{ORG_ID}/documents/{doc_type.lower()}/{uuid.uuid4().hex}{ext}"

        mime_type = mimetypes.guess_type(doc_file.name)[0] or "application/octet-stream"

        try:
            # Cek ukuran file (maks 10MB)
            file_size = doc_file.stat().st_size
            if file_size > 10485760:
                conn.rollback()
                skipped += 1
                print(f"  [SKIP] {doc_file.name}: {file_size} bytes exceeds 10MB limit")
                continue

            # Upload ke MinIO
            minio_client.fput_object(
                MINIO_BUCKET,
                storage_key,
                str(doc_file),
                content_type=mime_type,
            )

            # Insert ke file_object
            sha256_hash = hashlib.sha256(doc_file.read_bytes()).digest()
            cur.execute("""
                INSERT INTO vms.file_object (organization_id, storage_key, file_name, mime_type, byte_size, sha256, uploaded_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (ORG_ID, storage_key, doc_file.name, mime_type, file_size, sha256_hash, UPLOADED_BY))
            file_id = cur.fetchone()[0]

            # Coba cocokkan ke employee
            match = match_employee_from_doc(doc_file.name, employees)
            if match:
                emp_id, score = match
                emp_name = next((name for eid, name in employees if eid == emp_id), emp_id)

                # Insert ke employee_document (number_masked diisi default)
                cur.execute("""
                    INSERT INTO vms.employee_document (employee_id, doc_type, number_masked, file_id, uploaded_by, status, lifecycle)
                    VALUES (%s, %s, %s, %s, %s, 'PENDING', 'CURRENT')
                """, (emp_id, doc_type, '', file_id, UPLOADED_BY))

                conn.commit()
                success += 1
                print(f"  [OK] {doc_file.name} -> {emp_name} ({doc_type}, score={score:.2f})")
            else:
                # Dokumen tidak cocok ke employee (mis. kendaraan, kontrak)
                conn.commit()
                success += 1
                print(f"  [OK] {doc_file.name} -> ({doc_type}, no employee match)")

        except Exception as e:
            conn.rollback()
            failed += 1
            print(f"  [FAIL] {doc_file.name}: {e}")

    conn.close()

    print(f"\n[SUMMARY]")
    print(f"  [OK] Berhasil: {success}")
    print(f"  [FAIL] Gagal: {failed}")
    print(f"  [SKIP] Dilewati (>10MB): {skipped}")
    print(f"  [INFO] Total dokumen: {len(doc_files)}")

    if failed > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
