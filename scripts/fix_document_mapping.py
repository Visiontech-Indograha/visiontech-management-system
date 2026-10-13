"""
Perbaiki mapping employee_document berdasarkan data lama (nama file → employee yang benar).
Hapus semua employee_document lama, insert ulang dengan mapping yang benar.
"""
import hashlib
import uuid
from pathlib import Path

import psycopg2
from minio import Minio

DB_HOST = "127.0.0.1"
DB_PORT = 55434
DB_USER = "vms_app"
DB_PASSWORD = "password123"
DB_NAME = "vms_test"

# Mapping file_name → employee email (dari data lama)
FILE_TO_EMAIL = {
    # dokumen_pribadi
    "001_KTP_Ramadani.pdf": "ramadani@visiontech.id",
    "01._KTP_E_Syafrudin.pdf": "syafruddin@visiontech.id",
    "02.KTP_Yulfi_Hendri_New.JPG": "yulfi@visiontech.id",
    "08.BPJS_Ketenagakerjaan_Remon_Depan.JPG": "raimon@visiontech.id",
    "08.BPJS_Ketenagakerjaan_Rouzi_Dewantoro_Depan.jpg": "rouzi@visiontech.id",
    "08.BPJS_Ketenagakerjaan_Rusyidi.JPG": "rusyidin@visiontech.id",
    "08.BPJS_Ketenagakerjaan_Syafruddin_Depan.jpg": "syafruddin@visiontech.id",
    "08.BPJS_Ketenagakerjaan_Yulfi_Depan.JPG": "yulfi@visiontech.id",
    "09.BPJS_Kesehatan_Dani_Depan.JPG": "dani@visiontech.id",  # Dani tidak ada di data baru, skip
    "09.BPJS_Kesehatan_Remon_Depan.jpg": "raimon@visiontech.id",
    "09.BPJS_Kesehatan_Rouzi_Dewantoro_Depan.jpg": "rouzi@visiontech.id",
    "09.BPJS_Kesehatan_Rusyidi.pdf": "rusyidin@visiontech.id",
    "09.BPJS_Kesehatan_Syafruddin_Depan.jpg": "syafruddin@visiontech.id",
    "09.BPJS_Kesehatan_Yulfi_Depan.JPG": "yulfi@visiontech.id",
    "09.BPJS_Ketenagakerjaan_Ramadani_Depan.jpg": "ramadani@visiontech.id",
    "16.KK_Ramadani.pdf": "ramadani@visiontech.id",
    "BPJS_KES_Yuli_Candra.pdf": "candra@visiontech.id",
    "BPJS_TK_SHOFAN_RIZKI_SETYAWAN.pdf": "shofan@visiontech.id",
    "Doni_Efendi_2_Kartu_BPJS_Kesehatan.pdf": "doni@visiontech.id",
    "E-KTP_Doni_Efendi_Belakang.jpg": "doni@visiontech.id",
    "KIS_BPJS_Kesehatan_Septian_Dwi_Nugroho.pdf": "septyan@visiontech.id",
    "KTP_REMON_NEW_22.jpeg": "raimon@visiontech.id",
    "KTP_Rouzi_Dewantoro_Seumur_Hidup.jpg": "rouzi@visiontech.id",
    "KTP_Septian_Dwi_Nugroho.jpg": "septyan@visiontech.id",
    "KTP_SHOFAN.pdf": "shofan@visiontech.id",
    "KTP_Ucok.pdf": None,  # tidak jelas pemiliknya
    "KTP_YULI_CANDRA.jpg": "candra@visiontech.id",
    "Screenshot_1.png": None,  # bukan dokumen yang jelas
    # kontrak
    "PKWT_2025.pdf": None,  # tidak jelas
    "PKWT_Asrul_Mulya_2025.pdf": "asrul@visiontech.id",
    "PKWT_Azman_Aug_2025_1.pdf": "azman@visiontech.id",
    "PKWT_Doni_Efendi_Agus_2026.pdf": "doni@visiontech.id",
    "PKWT_Fajar_23_Okt_2026.pdf": "m.fajar@visiontech.id",
    "PKWT_Handoko_Agus_2025_1.pdf": "handoko@visiontech.id",
    "PKWT_Martaffery_MB__Agus_2025_1.pdf": "martaferi@visiontech.id",
    "PKWT_M_Ananda_Jalil_Isaq.pdf": "ananda@visiontech.id",
    "PKWT_NURFAUZIAH_SAPUTRI_2025.pdf": "putri@visiontech.id",
    "PKWT_PINTO_2025.pdf": "pinto@visiontech.id",
    "PKWT_Rouzi_Dewantoro_2025.pdf": "rouzi@visiontech.id",
    "PKWT_Rusyidi_Halomoan_Siregar_agus_2025_3.pdf": "rusyidin@visiontech.id",
    "PKWT_SHOFAN_2025.pdf": "shofan@visiontech.id",
    "PKWT_TEGUH_JULI_20251.pdf": "teguh@visiontech.id",
    "PKWT_Yuli_candra_2025.pdf": "candra@visiontech.id",
    "rev_PKWT_AHMADI_SCAN_Update_sep_2025.pdf": "ahmadi@visiontech.id",
    # mcu
    "DONI_EFENDI.pdf": "doni@visiontech.id",
    "M._FAJAR_DWITHYA.pdf": "m.fajar@visiontech.id",
    "MCU-2025_ASRUL_MULYA1.pdf": "asrul@visiontech.id",
    "MCU_2025_Akmal_Yusuf_Visiontech.pdf": "akmal@visiontech.id",
    "MCU_2025_Aris_Setyawan.pdf": "aris@visiontech.id",
    "MCU_Agustus_2025_MARTAFFERI_MAJO_BUNGSU.pdf": "martaferi@visiontech.id",
    "MCU_Agustus_2025_Syafruddin.pdf": "syafruddin@visiontech.id",
    "MCU_Agus_2025.pdf": "ageng@visiontech.id",
    "MCU_AHMADI_Agust_2025.pdf": "ahmadi@visiontech.id",
    "MCU_AZMAN_exp_2026_11zon.pdf": "azman@visiontech.id",
    "MCU_DONI_EFENDI_Nov_20261.pdf": "doni@visiontech.id",
    "MCU_DONI_EFENDI_Nov_20261_compressed.pdf": "doni@visiontech.id",
    "MCU_HANDOKO_2026.pdf": "handoko@visiontech.id",
    "MCU_Heru_Prayoga_Mei_2025.pdf": "heru@visiontech.id",
    "MCU_Juli_2025.pdf": "candra@visiontech.id",  # Yuli Candra
    "MCU_M._TEGUH_WICAKSONO_Aug_2025.pdf": "teguh@visiontech.id",
    "MCU_NURFAUZIAH_SAPUTRI_2025.pdf": "putri@visiontech.id",
    "MCU_RAIMON_ALBERT_SantaMaria_2025.pdf": "raimon@visiontech.id",
    "MCU_ROUZI_DEWANTORO_Sep_2025.pdf": "rouzi@visiontech.id",
    "MCU_RUSYIDI_HALOMOAN_SIREGAR_2025_2.pdf": "rusyidin@visiontech.id",
    "MCU_SHOFAN_RIZKI_SETYAWAN_Des_2025.pdf": "shofan@visiontech.id",
    "MCU_YULI_CANDRA_exp_2026.pdf": "candra@visiontech.id",
    "MCU_YULI_CANDRA_exp_2026_compressed.pdf": "candra@visiontech.id",
    # sertifikat
    "ASRUL_MULYA_drone_sertifikat_2025.pdf": "asrul@visiontech.id",
    "Certificate_Project_Management_Professional_PMP_2025.pdf": "ageng@visiontech.id",
    "DONI_EFENDI_drone_sertifikat_2025.pdf": "doni@visiontech.id",
    "ROUZI_DEWANTORO_drone_sertifikat_2025.pdf": "rouzi@visiontech.id",
    "SKP_Fajar_2025.pdf": "m.fajar@visiontech.id",
    "TKPK_II_rusyidi_halomoan_siregar5_1_2.pdf": "rusyidin@visiontech.id",
    "Yulfi_Hendri_-_Lenel_Onguard_Certification_Certificate_8_3.pdf": "yulfi@visiontech.id",
    "Yulfi_Hendri_-_Milestone_Certified_Design_Engineer_MCDE_Assessment_-_Completion_Certificate.pdf": "yulfi@visiontech.id",
    "YULI_CANDRA_Drone_Sartifikat_2025.pdf": "candra@visiontech.id",
    # sim
    "SIM_A_ASRUL_MULYAA.jpeg": "asrul@visiontech.id",
    "SIM_A_Handoko.pdf": "handoko@visiontech.id",
    "SIM_A_M._Fajar_.jpg": "m.fajar@visiontech.id",
    "SIM_A_New.JPG": None,  # tidak jelas
    "SIM_A_NEW.pdf": None,  # tidak jelas
    "SIM_A_Rusyidi_new_agustus_2023.pdf": "rusyidin@visiontech.id",
    "SIM_A_SUTONO.pdf": "sutono@visiontech.id",
    "SIM_B_II_MARTAFFERY.jpeg": "martaferi@visiontech.id",
    "SIM_C_SUTONO.pdf": "sutono@visiontech.id",
    # kendaraan
    "KIR_BM_8214_QP1.pdf": None,  # kendaraan, bukan dokumen karyawan
    "KIR_BM_8215_QP.pdf": None,
    "KIR_BM_8216_QP.pdf": None,
    "KIR_BM_8362_QN.pdf": None,
    "KIR_HILUX_2025.pdf": None,
    "KIR_TRITON.pdf": None,
    "BM1880AAC_2024.pdf": None,
    "BM_1239_AAP.pdf": None,
    "BM_1240_AAP.pdf": None,
    "BM_1673AAC_2024.pdf": None,
    "BM_8214_QP_NEW.pdf": None,
    "BM_8215_QP.pdf": None,
    "BM_8216_QP.pdf": None,
    "Scan_BM_1400_OQ_NEW_2025.pdf": None,
    "SCAN_BM_1650_TL_NEW_2025.pdf": None,
    "SCAN_BM_8362_QN_NEW_2025.pdf": None,
    "SCAN_STNK_BM_8674_TQ_NEW_2025_2.pdf": None,
    "STNK_1893QQ_NEW_2025.pdf": None,
    "STNK_BM1945QQ_NEW_2025.pdf": None,
    "STNK_BM_1427_LLN_NEW_2025.pdf": None,
}

# doc_type berdasarkan prefix folder
FOLDER_DOCTYPE = {
    "dokumen_pribadi": "DOKUMEN_PRIBADI",
    "kontrak": "KONTRAK",
    "mcu": "MCU",
    "sertifikat": "SERTIFIKAT",
    "sim": "SIM",
    "kendaraan": None,  # kendaraan bukan employee_document
    "dokumen_internal": None,  # internal bukan employee_document
}


def main():
    conn = psycopg2.connect(host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, dbname=DB_NAME)
    conn.autocommit = False
    cur = conn.cursor()

    # 1. Hapus semua employee_document lama
    cur.execute("DELETE FROM vms.employee_document")
    print(f"Deleted {cur.rowcount} old employee_document rows")

    # 2. Buat mapping email → employee_id
    cur.execute("SELECT id, email FROM vms.employee")
    email_to_id = {email: emp_id for emp_id, email in cur.fetchall()}
    print(f"Employees: {len(email_to_id)}")

    # 2b. Ambil satu app_user.id yang valid untuk uploaded_by
    cur.execute("SELECT id FROM vms.app_user WHERE is_active = true LIMIT 1")
    row = cur.fetchone()
    uploaded_by_id = row[0] if row else None
    print(f"Using uploaded_by: {uploaded_by_id}")

    # 3. Buat mapping file_name → file_id dari file_object
    cur.execute("SELECT id, file_name FROM vms.file_object")
    file_to_id = {fname: fid for fid, fname in cur.fetchall()}
    print(f"Files: {len(file_to_id)}")

    # 4. Insert ulang dengan mapping yang benar
    inserted = 0
    skipped = 0

    for file_name, email in FILE_TO_EMAIL.items():
        if email is None:
            skipped += 1
            continue
        if file_name not in file_to_id:
            print(f"  [WARN] File tidak ditemukan: {file_name}")
            skipped += 1
            continue
        if email not in email_to_id:
            print(f"  [WARN] Email tidak ditemukan: {email}")
            skipped += 1
            continue

        # Tentukan doc_type dari file_name
        doc_type = None
        for prefix, dt in FOLDER_DOCTYPE.items():
            if file_name.startswith(prefix):
                doc_type = dt
                break
        if doc_type is None:
            # Coba tentukan dari pola file
            if "PKWT" in file_name:
                doc_type = "KONTRAK"
            elif "MCU" in file_name:
                doc_type = "MCU"
            elif "BPJS" in file_name or "KTP" in file_name or "KK" in file_name or "KIS" in file_name:
                doc_type = "DOKUMEN_PRIBADI"
            elif "SIM" in file_name:
                doc_type = "SIM"
            elif "sertifikat" in file_name.lower() or "Certificate" in file_name or "SKP" in file_name or "TKPK" in file_name:
                doc_type = "SERTIFIKAT"
            elif "drone" in file_name.lower():
                doc_type = "SERTIFIKAT"

        if doc_type is None:
            print(f"  [SKIP] Tidak bisa tentukan doc_type: {file_name}")
            skipped += 1
            continue

        cur.execute("""
            INSERT INTO vms.employee_document (employee_id, doc_type, number_masked, file_id, uploaded_by, status, lifecycle)
            VALUES (%s, %s, %s, %s, %s, 'PENDING', 'CURRENT')
            ON CONFLICT (employee_id, doc_type) WHERE lifecycle = 'CURRENT'
            DO UPDATE SET file_id = EXCLUDED.file_id, status = 'PENDING'
        """, (email_to_id[email], doc_type, "", file_to_id[file_name], uploaded_by_id))
        inserted += 1

    conn.commit()
    print(f"\nInserted: {inserted}")
    print(f"Skipped: {skipped}")

    # 5. Verifikasi
    cur.execute("""
        SELECT e.full_name, e.email, ed.doc_type, f.file_name 
        FROM vms.employee_document ed
        JOIN vms.employee e ON e.id = ed.employee_id
        JOIN vms.file_object f ON f.id = ed.file_id
        ORDER BY e.full_name, ed.doc_type
    """)
    rows = cur.fetchall()
    print(f"\n=== Verifikasi: {len(rows)} dokumen ===")
    for r in rows[:10]:
        print(f"  {r[0]} ({r[1]}) → {r[2]}: {r[3]}")

    conn.close()


if __name__ == "__main__":
    main()
