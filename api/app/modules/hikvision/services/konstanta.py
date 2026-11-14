"""Semua nilai dan nama field Hikvision di SATU tempat.

PERLU VERIFIKASI dari tangkapan perangkat asli (DS-K1T343MX, firmware V3.3.4): seluruh nilai major/minor dan nama
field di bawah berasal dari dokumentasi/ingatan, BELUM dari perangkat. Jangan dianggap pasti; ubah di sini saja.
"""
from __future__ import annotations

from datetime import timedelta, timezone

# --- Jenis event (PERLU VERIFIKASI dari tangkapan perangkat asli) ---
MAJOR_AKSES = 5                 # major "Access Control Event"
MINOR_WAJAH = 75                # verifikasi wajah lolos
MINOR_KARTU = 1                 # kartu lolos
MINOR_SIDIK_JARI = 38           # sidik jari lolos
MINOR_VERIFIKASI_LOLOS = frozenset({MINOR_WAJAH, MINOR_KARTU, MINOR_SIDIK_JARI})

TOLERANSI_BANDING_MENIT = 5     # selisih mesin vs aplikasi yang masih dianggap cocok (sama dengan web)

# --- Nama field (PERLU VERIFIKASI dari tangkapan perangkat asli). Tuple = urutan alternatif yang dicoba. ---
BLOK_EVENT = "AccessControllerEvent"
F_JENIS_EVENT = ("eventType",)
JENIS_HEARTBEAT = frozenset({"heartbeat"})          # dibandingkan huruf kecil
F_MAJOR = ("majorEventType", "major")
F_MINOR = ("subEventType", "minor")
F_WAKTU = ("dateTime", "time")
F_SERIAL_EVENT = ("serialNo",)
F_KARYAWAN = ("employeeNoString",)
F_KARTU = ("cardNo",)
F_MODE = ("currentVerifyMode",)
F_SERIAL_PERANGKAT = ("deviceSerial", "serialNumber", "deviceID")

# --- Batas validasi ---
MAKS_BYTE_KIRIMAN = 2 * 1024 * 1024
MAKS_BYTE_JSON = 64 * 1024
MAKS_BAGIAN_MULTIPART = 4
MAKS_PANJANG_SERIAL_PERANGKAT = 64
MAKS_PANJANG_PENGENAL = 50      # employeeNo/cardNo (selaras employee_no VARCHAR(50))
MAKS_PANJANG_MODE = 50
WAKTU_TERAWAL = (2015, 1, 1)
TOLERANSI_MASA_DEPAN = timedelta(minutes=5)
MAGIC_JPEG = b"\xff\xd8\xff"

# --- Zona waktu perangkat bila waktu tanpa offset (bawaan Asia/Jakarta) ---
ZONA_PERANGKAT_BAWAAN = timezone(timedelta(hours=7), "WIB")

# --- Tarik riwayat ISAPI (PERLU VERIFIKASI: path, nama field, nilai status, batas maxResults) ---
PATH_ACS_EVENT = "/ISAPI/AccessControl/AcsEvent?format=json"
STATUS_LAGI = "MORE"
STATUS_SELESAI = "OK"
STATUS_KOSONG = "NO MATCH"
MAKS_HASIL_PER_HALAMAN = 30
