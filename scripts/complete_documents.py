"""
Melengkapi dan memperbaiki pemetaan dokumen karyawan.

- Menghapus seluruh baris vms.employee_document lama (rebuild dari nol).
- Mengunggah berkas dari folder uploads/ ke MinIO bila belum ada (file_object baru).
- Memasukkan baris employee_document dengan pemetaan nama berkas -> email karyawan yang benar.
- doc_type dipakai spesifik (KTP, BPJS TK, BPJS KES, KK, SIM A, SIM B II, SIM C, MCU,
  KONTRAK, Sertifikat ...) karena ada unique index (employee_id, doc_type) untuk status PENDING.

Jalankan dari folder api/:  .venv/Scripts/python.exe ../../scripts/complete_documents.py
"""
from __future__ import annotations

import hashlib
import os
import re
import sys
import uuid
from pathlib import Path

import psycopg2
from minio import Minio

API_DIR = Path(__file__).resolve().parent.parent / "api"
UPLOADS = Path(r"C:/Users/ageng/visiontect-vms/uploads")
ORG_ID = "01a0dd85-ab65-737b-8938-a1421957055f"
UPLOADED_BY = "01a0e5f5-b2f9-7d30-b862-3de528698747"  # ageng@visiontech.id (ADMIN)
MAX_BYTES = 10 * 1024 * 1024

# --- baca .env ---
env: dict[str, str] = {}
for line in (API_DIR / ".env").read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    k, v = line.split("=", 1)
    env[k.strip()] = v.strip()

dsn = env["DATABASE_URL"].replace("postgresql+asyncpg://", "postgresql://")
minio = Minio(
    env["MINIO_ENDPOINT"],
    access_key=env["MINIO_ACCESS_KEY"],
    secret_key=env["MINIO_SECRET_KEY"],
    secure=env.get("MINIO_SECURE", "false").lower() == "true",
)
BUCKET = env.get("MINIO_BUCKET", "vms-files")

# (nama berkas relatif terhadap uploads/, email karyawan, doc_type)
MAPPING: list[tuple[str, str, str]] = [
    # --- dokumen pribadi ---
    ("dokumen_pribadi/001_KTP_Ramadani.pdf", "ramadani@visiontech.id", "KTP"),
    ("dokumen_pribadi/09.BPJS_Ketenagakerjaan_Ramadani_Depan.jpg", "ramadani@visiontech.id", "BPJS TK"),
    ("dokumen_pribadi/16.KK_Ramadani.pdf", "ramadani@visiontech.id", "KK"),
    ("dokumen_pribadi/01._KTP_E_Syafrudin.pdf", "syafruddin@visiontech.id", "KTP"),
    ("dokumen_pribadi/08.BPJS_Ketenagakerjaan_Syafruddin_Depan.jpg", "syafruddin@visiontech.id", "BPJS TK"),
    ("dokumen_pribadi/09.BPJS_Kesehatan_Syafruddin_Depan.jpg", "syafruddin@visiontech.id", "BPJS KES"),
    ("dokumen_pribadi/02.KTP_Yulfi_Hendri_New.JPG", "yulfi@visiontech.id", "KTP"),
    ("dokumen_pribadi/08.BPJS_Ketenagakerjaan_Yulfi_Depan.JPG", "yulfi@visiontech.id", "BPJS TK"),
    ("dokumen_pribadi/09.BPJS_Kesehatan_Yulfi_Depan.JPG", "yulfi@visiontech.id", "BPJS KES"),
    ("dokumen_pribadi/KTP_REMON_NEW_22.jpeg", "raimon@visiontech.id", "KTP"),
    ("dokumen_pribadi/08.BPJS_Ketenagakerjaan_Remon_Depan.JPG", "raimon@visiontech.id", "BPJS TK"),
    ("dokumen_pribadi/09.BPJS_Kesehatan_Remon_Depan.jpg", "raimon@visiontech.id", "BPJS KES"),
    ("dokumen_pribadi/KTP_Rouzi_Dewantoro_Seumur_Hidup.jpg", "rouzi@visiontech.id", "KTP"),
    ("dokumen_pribadi/08.BPJS_Ketenagakerjaan_Rouzi_Dewantoro_Depan.jpg", "rouzi@visiontech.id", "BPJS TK"),
    ("dokumen_pribadi/09.BPJS_Kesehatan_Rouzi_Dewantoro_Depan.jpg", "rouzi@visiontech.id", "BPJS KES"),
    ("dokumen_pribadi/08.BPJS_Ketenagakerjaan_Rusyidi.JPG", "rusyidin@visiontech.id", "BPJS TK"),
    ("dokumen_pribadi/09.BPJS_Kesehatan_Rusyidi.pdf", "rusyidin@visiontech.id", "BPJS KES"),
    ("dokumen_pribadi/BPJS_KES_Yuli_Candra.pdf", "candra@visiontech.id", "BPJS KES"),
    ("dokumen_pribadi/KTP_YULI_CANDRA.jpg", "candra@visiontech.id", "KTP"),
    ("dokumen_pribadi/BPJS_TK_SHOFAN_RIZKI_SETYAWAN.pdf", "shofan@visiontech.id", "BPJS TK"),
    ("dokumen_pribadi/KTP_SHOFAN.pdf", "shofan@visiontech.id", "KTP"),
    ("dokumen_pribadi/Doni_Efendi_2_Kartu_BPJS_Kesehatan.pdf", "doni@visiontech.id", "BPJS KES"),
    ("dokumen_pribadi/E-KTP_Doni_Efendi_Belakang.jpg", "doni@visiontech.id", "KTP"),
    ("dokumen_pribadi/KIS_BPJS_Kesehatan_Septian_Dwi_Nugroho.pdf", "septyan@visiontech.id", "BPJS KES"),
    ("dokumen_pribadi/KTP_Septian_Dwi_Nugroho.jpg", "septyan@visiontech.id", "KTP"),
    # --- kontrak ---
    ("kontrak/PKWT_Asrul_Mulya_2025.pdf", "asrul@visiontech.id", "KONTRAK"),
    ("kontrak/PKWT_Azman_Aug_2025_1.pdf", "azman@visiontech.id", "KONTRAK"),
    ("kontrak/PKWT_Doni_Efendi_Agus_2026.pdf", "doni@visiontech.id", "KONTRAK"),
    ("kontrak/PKWT_Fajar_23_Okt_2026.pdf", "m.fajar@visiontech.id", "KONTRAK"),
    ("kontrak/PKWT_Handoko_Agus_2025_1.pdf", "handoko@visiontech.id", "KONTRAK"),
    ("kontrak/PKWT_Martaffery_MB__Agus_2025_1.pdf", "martaferi@visiontech.id", "KONTRAK"),
    ("kontrak/PKWT_M_Ananda_Jalil_Isaq.pdf", "ananda@visiontech.id", "KONTRAK"),
    ("kontrak/PKWT_NURFAUZIAH_SAPUTRI_2025.pdf", "putri@visiontech.id", "KONTRAK"),
    ("kontrak/PKWT_PINTO_2025.pdf", "pinto@visiontech.id", "KONTRAK"),
    ("kontrak/PKWT_Rouzi_Dewantoro_2025.pdf", "rouzi@visiontech.id", "KONTRAK"),
    ("kontrak/PKWT_Rusyidi_Halomoan_Siregar_agus_2025._3.pdf", "rusyidin@visiontech.id", "KONTRAK"),
    ("kontrak/PKWT_SHOFAN_2025.pdf", "shofan@visiontech.id", "KONTRAK"),
    ("kontrak/PKWT_TEGUH_JULI_20251.pdf", "teguh@visiontech.id", "KONTRAK"),
    ("kontrak/PKWT_Yuli_candra_2025.pdf", "candra@visiontech.id", "KONTRAK"),
    ("kontrak/rev_PKWT_AHMADI_SCAN_Update_sep_2025_compressed.pdf", "ahmadi@visiontech.id", "KONTRAK"),
    # --- MCU ---
    ("mcu/MCU-2025_ASRUL_MULYA1.pdf", "asrul@visiontech.id", "MCU"),
    ("mcu/MCU_2025_Akmal_Yusuf_Visiontech.pdf", "akmal@visiontech.id", "MCU"),
    ("mcu/MCU_2025_Aris_Setyawan.pdf", "aris@visiontech.id", "MCU"),
    ("mcu/MCU_Agustus_2025_MARTAFFERI_MAJO_BUNGSU.pdf", "martaferi@visiontech.id", "MCU"),
    ("mcu/MCU_Agustus_2025_Syafruddin.pdf", "syafruddin@visiontech.id", "MCU"),
    ("mcu/MCU_AHMADI_Agust_2025.pdf", "ahmadi@visiontech.id", "MCU"),
    ("mcu/MCU_AZMAN_exp_2026_11zon.pdf", "azman@visiontech.id", "MCU"),
    ("mcu/MCU_DONI_EFENDI_Nov_20261_compressed.pdf", "doni@visiontech.id", "MCU"),
    ("mcu/MCU_HANDOKO_2026.pdf", "handoko@visiontech.id", "MCU"),
    ("mcu/MCU_Heru_Prayoga_Mei_2025.pdf", "heru@visiontech.id", "MCU"),
    ("mcu/MCU_M._TEGUH_WICAKSONO_Aug_2025.pdf", "teguh@visiontech.id", "MCU"),
    ("mcu/MCU_NURFAUZIAH_SAPUTRI_2025.pdf", "putri@visiontech.id", "MCU"),
    ("mcu/MCU_RAIMON_ALBERT_SantaMaria_2025_compressed.pdf", "raimon@visiontech.id", "MCU"),
    ("mcu/MCU_ROUZI_DEWANTORO_Sep_2025_compressed.pdf", "rouzi@visiontech.id", "MCU"),
    ("mcu/MCU_RUSYIDI_HALOMOAN_SIREGAR_2025_2_compressed.pdf", "rusyidin@visiontech.id", "MCU"),
    ("mcu/MCU_SHOFAN_RIZKI_SETIAWAN_Des_2025.pdf", "shofan@visiontech.id", "MCU"),
    ("mcu/MCU_YULI_CANDRA_exp_2026_compressed.pdf", "candra@visiontech.id", "MCU"),
    ("mcu/M._FAJAR_DWITHYA.pdf", "m.fajar@visiontech.id", "MCU"),
    # --- sertifikat ---
    ("sertifikat/ASRUL_MULYA_drone_sertifikat_2025.pdf", "asrul@visiontech.id", "Sertifikat Drone"),
    ("sertifikat/DONI_EFENDI_drone_sertifikat_2025.pdf", "doni@visiontech.id", "Sertifikat Drone"),
    ("sertifikat/ROUZI_DEWANTORO_drone_sertifikat_2025.pdf", "rouzi@visiontech.id", "Sertifikat Drone"),
    ("sertifikat/YULI_CANDRA_Drone_Sartifikat_2025.pdf", "candra@visiontech.id", "Sertifikat Drone"),
    ("sertifikat/Certificate_Project_Management_Professional_PMP_2025.pdf", "ageng@visiontech.id", "Sertifikat PMP"),
    ("sertifikat/SKP_Fajar_2025.pdf", "m.fajar@visiontech.id", "SKP"),
    ("sertifikat/TKPK_II_rusyidi_halomoan_siregar5_1_2.pdf", "rusyidin@visiontech.id", "Sertifikat K3"),
    ("sertifikat/Yulfi_Hendri_-_Lenel_Onguard_Certification_Certificate_8_3.pdf", "yulfi@visiontech.id", "Sertifikat Lenel"),
    ("sertifikat/Yulfi_Hendri_-_Milestone_Certified_Design_Engineer_MCDE_Assessment_-_Completion_Certificate.pdf", "yulfi@visiontech.id", "Sertifikat MCDE"),
    # --- SIM ---
    ("sim/SIM_A_ASRUL_MULYAA.jpeg", "asrul@visiontech.id", "SIM A"),
    ("sim/SIM_A_Handoko.pdf", "handoko@visiontech.id", "SIM A"),
    ("sim/SIM_A_M._Fajar_.jpg", "m.fajar@visiontech.id", "SIM A"),
    ("sim/SIM_A_Rusyidi_new_agustus_2023.pdf", "rusyidin@visiontech.id", "SIM A"),
    ("sim/SIM_A_SUTONO.pdf", "sutono@visiontech.id", "SIM A"),
    ("sim/SIM_C_SUTONO.pdf", "sutono@visiontech.id", "SIM C"),
    ("sim/SIM_B_II_MARTAFFERY.jpeg", "martaferi@visiontech.id", "SIM B II"),
    # --- hasil verifikasi visual (berkas bernama generik tanpa identitas di nama berkas) ---
    ("dokumen_pribadi/KTP_Ucok.pdf", "rusyidin@visiontech.id", "KTP"),
    ("kontrak/PKWT_2025.pdf", "raimon@visiontech.id", "KONTRAK"),
    ("mcu/MCU_Juli_2025.pdf", "pinto@visiontech.id", "MCU"),
    ("sim/SIM_A_New.JPG", "syafruddin@visiontech.id", "SIM A"),
    ("dokumen_pribadi/09.BPJS_Kesehatan_Dani_Depan.JPG", "ramadani@visiontech.id", "BPJS KES"),
    ("mcu/MCU_Agus_2025.pdf", "ramadani@visiontech.id", "MCU"),
    ("sim/SIM_A_NEW.pdf", "doni@visiontech.id", "SIM A"),
    # MCU 2024 milik Doni: dia sudah punya MCU 2025, jadi jenis dibedakan agar
    # tidak bentrok dengan unique index (employee_id, doc_type) untuk status PENDING.
    ("mcu/DONI_EFENDI.pdf", "doni@visiontech.id", "MCU 2024"),
]

MIME = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".webp": "image/webp",
}


def sha256_hex(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    conn = psycopg2.connect(dsn)
    conn.autocommit = False
    cur = conn.cursor()

    # 1. Peta email -> employee_id
    cur.execute("SELECT email, id FROM vms.employee WHERE email IS NOT NULL")
    emp = {e.lower(): i for e, i in cur.fetchall()}

    # 2. Bersihkan baris lama (rebuild agar pemetaan yang salah ikut hilang)
    cur.execute("DELETE FROM vms.employee_document")
    print(f"Baris employee_document lama dihapus: {cur.rowcount}")

    stats = {"upload": 0, "reuse": 0, "insert": 0, "skip_size": 0, "skip_missing": 0, "skip_email": 0}

    for rel, email, doc_type in MAPPING:
        src = UPLOADS / rel
        eid = emp.get(email.lower())
        if eid is None:
            print(f"  SKIP (email tak ada) {email} <- {rel}")
            stats["skip_email"] += 1
            continue
        if not src.exists():
            print(f"  SKIP (berkas tak ada) {rel}")
            stats["skip_missing"] += 1
            continue
        size = src.stat().st_size
        if size > MAX_BYTES:
            print(f"  SKIP (>10MB {size/1048576:.1f}MB) {rel}")
            stats["skip_size"] += 1
            continue

        ext = src.suffix.lower()
        mime = MIME.get(ext, "application/octet-stream")
        digest = sha256_hex(src)

        # Pakai file_object yang sudah ada bila sha256-nya sama (dedup tingkat organisasi)
        cur.execute(
            "SELECT id FROM vms.file_object WHERE organization_id = %s AND sha256 = decode(%s,'hex') LIMIT 1",
            (ORG_ID, digest),
        )
        row = cur.fetchone()
        if row:
            file_id = row[0]
            stats["reuse"] += 1
        else:
            file_id = str(uuid.uuid4())
            folder = rel.split("/")[0]
            storage_key = f"{ORG_ID}/documents/{folder}/{uuid.uuid4().hex}{ext}"
            minio.fput_object(BUCKET, storage_key, str(src), content_type=mime)
            cur.execute(
                """INSERT INTO vms.file_object
                   (id, organization_id, storage_key, file_name, mime_type, byte_size, sha256, uploaded_by)
                   VALUES (%s,%s,%s,%s,%s,%s,decode(%s,'hex'),%s)""",
                (file_id, ORG_ID, storage_key, src.name, mime, size, digest, UPLOADED_BY),
            )
            stats["upload"] += 1

        cur.execute(
            """INSERT INTO vms.employee_document
               (employee_id, doc_type, number_masked, status, lifecycle, file_id, uploaded_by)
               VALUES (%s,%s,'', 'PENDING','PENDING',%s,%s)""",
            (eid, doc_type, file_id, UPLOADED_BY),
        )
        stats["insert"] += 1

    conn.commit()

    # 3. Verifikasi
    cur.execute("SELECT COUNT(*), COUNT(DISTINCT employee_id) FROM vms.employee_document")
    total, karyawan = cur.fetchone()
    print(f"\nSelesai: upload={stats['upload']} reuse={stats['reuse']} insert={stats['insert']} "
          f"skip_size={stats['skip_size']} skip_missing={stats['skip_missing']} skip_email={stats['skip_email']}")
    print(f"Total employee_document: {total} baris untuk {karyawan} karyawan")

    cur.execute("""
        SELECT e.full_name, COUNT(*) FROM vms.employee_document d
        JOIN vms.employee e ON e.id = d.employee_id
        GROUP BY e.full_name ORDER BY 2 DESC, 1
    """)
    print("\nJumlah dokumen per karyawan:")
    for name, n in cur.fetchall():
        print(f"  {name}: {n}")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
