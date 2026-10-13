"""
Kompres 6 dokumen PDF yang melebihi 10MB lalu upload ke MinIO.
Menggunakan pikepdf untuk kompresi lossless (dedup, objek bersih).
"""

import hashlib
import sys
import uuid
from pathlib import Path

import psycopg2
from minio import Minio

import _config as _cfg
from minio.error import S3Error
import fitz

UPLOADS_DIR = Path(r"C:\Users\ageng\visiontect-vms\uploads")
# Kredensial dibaca dari api/.env (gitignored) atau variabel lingkungan —
# TIDAK ditulis di kode, agar tidak masuk riwayat git (aturan git-flow §8).
MINIO_ENDPOINT = _cfg.get("MINIO_ENDPOINT", "127.0.0.1:9100")
MINIO_ACCESS_KEY = _cfg.get("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = _cfg.get("MINIO_SECRET_KEY")
MINIO_BUCKET = _cfg.get("MINIO_BUCKET", "vms-files")
MINIO_SECURE = _cfg.get("MINIO_SECURE", "false").lower() == "true"

ORG_ID = "01a0dd85-ab65-737b-8938-a1421957055f"
UPLOADED_BY = "01a0e5f5-b2f9-7d30-b862-3de528698747"

# File yang perlu dikompres (dari folder, nama file)
FILES_TO_COMPRESS = [
    ("kontrak", "rev_PKWT_AHMADI_SCAN_Update_sep_2025.pdf", "KONTRAK"),
    ("mcu", "MCU_DONI_EFENDI_Nov_20261.pdf", "MCU"),
    ("mcu", "MCU_RAIMON_ALBERT_SantaMaria_2025.pdf", "MCU"),
    ("mcu", "MCU_ROUZI_DEWANTORO_Sep_2025.pdf", "MCU"),
    ("mcu", "MCU_RUSYIDI_HALOMOAN_SIREGAR_2025_2.pdf", "MCU"),
    ("mcu", "MCU_YULI_CANDRA_exp_2026.pdf", "MCU"),
]

TMP_DIR = Path(r"C:\Users\ageng\AppData\Local\hermes\cache\scratch")


def compress_pdf(input_path: Path, output_path: Path) -> int:
    """Kompres PDF dengan PyMuPDF. Return ukuran output."""
    doc = fitz.open(str(input_path))
    # save dengan garbage=4, deflate=True, clean=True untuk kompresi agresif
    doc.save(
        str(output_path),
        garbage=4,
        deflate=True,
        clean=True,
        deflate_images=True,
        deflate_fonts=True,
    )
    doc.close()
    return output_path.stat().st_size


def main():
    minio_client = Minio(
        MINIO_ENDPOINT, access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY, secure=MINIO_SECURE,
    )

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER,
        password=DB_PASSWORD, dbname=DB_NAME
    )
    conn.autocommit = False
    cur = conn.cursor()

    cur.execute("SELECT id, full_name FROM vms.employee ORDER BY full_name")
    employees = cur.fetchall()

    success = 0
    failed = 0

    for folder_name, file_name, doc_type in FILES_TO_COMPRESS:
        input_path = UPLOADS_DIR / folder_name / file_name
        if not input_path.exists():
            print(f"  [SKIP] {file_name}: file tidak ditemukan")
            continue

        original_size = input_path.stat().st_size
        print(f"\n[COMPRESS] {folder_name}/{file_name}: {original_size:,} bytes")

        try:
            # Kompres
            output_path = TMP_DIR / f"compressed_{file_name}"
            compressed_size = compress_pdf(input_path, output_path)
            print(f"  -> {compressed_size:,} bytes ({compressed_size/original_size*100:.1f}%)")

            if compressed_size > 10485760:
                print(f"  [SKIP] Masih >10MB setelah kompresi")
                failed += 1
                continue

            # Upload ke MinIO
            storage_key = f"{ORG_ID}/documents/{doc_type.lower()}/{uuid.uuid4().hex}.pdf"
            minio_client.fput_object(
                MINIO_BUCKET, storage_key, str(output_path),
                content_type="application/pdf",
            )

            # Insert file_object
            sha256_hash = hashlib.sha256(output_path.read_bytes()).digest()
            cur.execute("""
                INSERT INTO vms.file_object (organization_id, storage_key, file_name, mime_type, byte_size, sha256, uploaded_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                RETURNING id
            """, (ORG_ID, storage_key, file_name, "application/pdf", compressed_size, sha256_hash, UPLOADED_BY))
            row = cur.fetchone()
            if row is None:
                raise RuntimeError("INSERT file_object tidak mengembalikan id")
            file_id = row[0]

            # Cocokkan employee (nama dari file)
            name_from_file = file_name.replace(".pdf", "").replace("_", " ")
            best_emp = None
            best_score = 0.0
            for emp_id, emp_name in employees:
                norm_name = emp_name.lower()
                if norm_name in name_from_file.lower() or any(part in name_from_file.lower() for part in norm_name.split()):
                    # Rough match
                    score = len(set(norm_name.split()) & set(name_from_file.lower().split())) / max(len(norm_name.split()), 1)
                    if score > best_score:
                        best_score = score
                        best_emp = emp_id

            if best_emp:
                emp_name = next((n for i, n in employees if i == best_emp), "?")
                cur.execute("""
                    INSERT INTO vms.employee_document (employee_id, doc_type, number_masked, file_id, uploaded_by, status, lifecycle)
                    VALUES (%s, %s, %s, %s, %s, 'PENDING', 'CURRENT')
                """, (best_emp, doc_type, '', file_id, UPLOADED_BY))
                conn.commit()
                success += 1
                print(f"  [OK] -> {emp_name} ({doc_type})")
            else:
                conn.commit()
                success += 1
                print(f"  [OK] -> ({doc_type}, no employee match)")

            # Cleanup
            output_path.unlink(missing_ok=True)

        except Exception as e:
            conn.rollback()
            failed += 1
            print(f"  [FAIL] {e}")

    conn.close()
    print(f"\n[SUMMARY] OK: {success}, FAIL: {failed}")


if __name__ == "__main__":
    main()
