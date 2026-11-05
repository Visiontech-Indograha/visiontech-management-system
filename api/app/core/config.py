"""
Modul konfigurasi aplikasi VMS.

Memuat pengaturan sistem dan rahasia (secrets) dari variabel lingkungan (environment variables)
atau berkas `.env` menggunakan pydantic-settings.
"""
from __future__ import annotations

import logging
from urllib.parse import quote

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import make_url

logger = logging.getLogger(__name__)


def encode_url_credentials(url: str) -> tuple[str, bool]:
    """Kembalikan ``(url, diubah)``. Sandi di userinfo yang belum di-URL-encode diperbaiki.

    Insiden 2026-10-13: ``api.env`` produksi memuat sandi berkarkter ``@`` mentah —
    ``postgresql+asyncpg://vms_api:P@ss@vms_db_prod:5432/visiontech_db``. SQLAlchemy membaca
    ``@`` **pertama** sebagai pemisah userinfo/host, sehingga host menjadi
    ``ss@vms_db_prod`` dan API gagal dengan ``socket.gaierror`` (``/ready`` 503, migrasi
    alembic putus). Sandi wajib di-encode (``P%40ss``).

    **Cakupan deteksi.** Hanya ``@`` di dalam sandi yang bisa dikenali tanpa mengetahui host yang
    diharapkan, dan deteksi memakai hasil parse SQLAlchemy sendiri: ``@`` yang masih tersisa di
    host berarti URL salah bentuk. ``: / ? # %`` dan spasi di sandi terbukti ter-parse dengan
    benar oleh SQLAlchemy (host tetap bersih), jadi tidak perlu diubah.

    **Batas yang diketahui.** Sandi yang memuat ``@`` **dan** ``?`` (``p@ss?x``) menghasilkan URL
    yang tampak sehat (host ``ss``) sehingga tidak terdeteksi di sini — memperlebarnya berisiko
    merusak query string yang sah (``/db?sslmode=require``). Kasus itu ditangkap oleh pemeriksaan
    koneksi sungguhan (``wait_api_reaches_db`` di ``deploy/autodeploy.sh``) yang mencetak
    petunjuk ``db_hint``. Nama basis data yang memuat ``@`` juga sengaja tidak disentuh: host-nya
    bersih, dan menulis ulang URL seperti itu justru merusaknya.
    """
    try:
        if "@" not in (make_url(url).host or ""):
            return url, False
    except Exception:  # noqa: BLE001 — penjaga ini TIDAK BOLEH menjatuhkan pemuatan konfigurasi;
        return url, False  # URL yang tak terurai dibiarkan apa adanya (perilaku lama), bukan bikin API gagal start.

    sep = url.find("://")
    if sep == -1:
        return url, False
    head, rest = url[: sep + 3], url[sep + 3 :]
    at = rest.rfind("@")                   # '@' terakhir = pemisah userinfo/host yang sebenarnya
    if at == -1:
        return url, False
    user, colon, secret = rest[:at].partition(":")
    if not colon or not secret:
        return url, False

    fixed = f"{head}{quote(user, safe='')}:{quote(secret, safe='')}@{rest[at + 1:]}"
    try:
        if "@" in (make_url(fixed).host or ""):   # masih salah bentuk → jangan tebak-tebakan
            return url, False
    except Exception:  # noqa: BLE001 — sama: hasil perbaikan yang tak terurai diperlakukan sebagai "gagal perbaiki".
        return url, False
    return fixed, True


def normalize_database_url_port(url: str) -> tuple[str, bool]:
    """Perbaiki port kontainer ``vms_db_prod:5433`` menjadi ``vms_db_prod:5432``.

    Insiden 2026-10-13: Port PostgreSQL dipetakan ke host sebagai 5433 (0.0.0.0:5433->5432/tcp).
    Pengguna sering keliru mengisi port 5433 pada DATABASE_URL di api.env padahal di dalam jaringan
    Docker, kontainer vms_api berkomunikasi langsung dengan kontainer vms_db_prod pada port internal 5432.
    Jika diisi 5433, koneksi ditolak (ConnectionRefusedError: [Errno 111]).
    """
    try:
        parsed = make_url(url)
        if parsed.host in ("vms_db_prod", "vms_db") and parsed.port == 5433:
            fixed_url = parsed.set(port=5432).render_as_string(hide_password=False)
            return fixed_url, True
    except Exception:  # noqa: BLE001
        return url, False
    return url, False


class Settings(BaseSettings):
    """
    Model konfigurasi global untuk VMS.
    Nilai bawaan (default) disediakan untuk pengembangan lokal, tetapi akan ditolak
    saat berjalan di lingkungan produksi (APP_ENV=production).
    """
    PROJECT_NAME: str = "Visiontech VMS"
    # Nilai asli hanya di api/.env (tidak masuk Git). Bawaan ini sengaja tidak bisa login.
    DATABASE_URL: str = "postgresql+asyncpg://vms_app:CHANGE_ME@localhost:5433/visiontech_db"
    # Migrasi (alembic) memakai peran pemilik skema; API memakai peran runtime `vms_api` yang tunduk RLS (0024).
    # Kosong → migrasi memakai DATABASE_URL (perilaku lama, sebelum pemisahan peran).
    MIGRATION_DATABASE_URL: str = ""

    # Access token EdDSA (dok 08 §7): seed Ed25519 32 byte (hex). Nilai asli hanya di api/.env / KMS.
    JWT_PRIVATE_KEY_HEX: str = ""
    JWT_KID: str = "jwt-dev-1"

    # Tanda tangan dokumen (fase 6). Sementara: seed Ed25519 hex dari lingkungan; sebelum produksi diganti
    # adaptor KMS (keputusan pemilik 2026-09-26, dok 10). Kosong → kunci sementara per proses (dev/uji saja).
    DOC_SIGNING_KEY_HEX: str = ""
    DOC_SIGNING_KMS_REF: str = "env:DOC_SIGNING_KEY_HEX"
    PUBLIC_VERIFY_URL: str = "http://localhost:5173/verify"   # isi QR: <PUBLIC_VERIFY_URL>/<token>

    # Pencarian lokasi penugasan (revisi PM 2026-09-26): Nominatim/OpenStreetMap lewat backend.
    GEOCODER_URL: str = "https://nominatim.openstreetmap.org/search"
    GEOCODER_USER_AGENT: str = "VisiontechVMS/1.0 (lokasi-penugasan)"

    # Discord #vms-alerts (dok 17). Kosong = peringatan hanya dicatat di log.
    DISCORD_WEBHOOK_ALERTS: str = ""

    # Konfigurasi penyimpanan objek (S3/MinIO)
    MINIO_ENDPOINT: str = "127.0.0.1:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "vms-files"
    MINIO_SECURE: bool = False

    # Asal (origin) publik untuk URL presigned, mis. "https://vms.visiontech.id": Caddy meneruskan
    # /<bucket>/* ke MinIO sehingga peramban & HP memuat berkas dari domain aplikasi (CSP img-src 'self',
    # MinIO tanpa port publik). Kosong = pakai MINIO_ENDPOINT (lokal).
    MINIO_PUBLIC_URL: str = ""
    MINIO_REGION: str = "us-east-1"

    # Layanan inferensi wajah (face-service, jaringan internal). Kosong = fitur wajah dilewati (absen tetap jalan).
    FACE_SERVICE_URL: str = "http://127.0.0.1:8001"
    FACE_SERVICE_TOKEN: str = ""
    FACE_SERVICE_TIMEOUT_S: float = 8.0
    # Konversi .docx → PDF untuk pratinjau laporan (LibreOffice headless). Kosong = cari "soffice" di PATH.
    SOFFICE_PATH: str = ""
    DOCX_TO_PDF_TIMEOUT_S: float = 90.0
    # Gambar wajah sementara hanya berlaku untuk absen online dalam beberapa menit (offline: terikat payload bertanda tangan).
    FACE_PROBE_MAX_AGE_MIN: int = 15
    # Masa berlaku template di HP; sama dengan batas absen offline (7 hari) agar penarikan persetujuan tetap berlaku.
    FACE_TEMPLATE_TTL_DAYS: int = 7
    # True = akun yang terhubung ke karyawan WAJIB mendaftarkan wajah sebelum membuka menu lain (web dan HP).
    # Bawaan True (keputusan pemilik 2026-10-08): absen HP ditolak tanpa wajah terdaftar. Lingkungan yang belum punya
    # face-service harus mematikannya LEWAT SKRIP `scripts/saklar-wajah.sh off`, kalau tidak semua pekerja terkunci.
    FACE_ENROLLMENT_REQUIRED: bool = True
    # Mode wajah palsu KHUSUS DEV (uji): enroll menyimpan embedding sintetis deterministik per karyawan dan verifikasi
    # mencocokkan swafoto apa pun dengan skor tinggi (tanpa face-service). Hanya berlaku bila APP_ENV=development;
    # nilai true di lingkungan lain membuat API menolak start (lihat `_fake_face_only_in_development`).
    FACE_FAKE_MODE: bool = False

    # Folder rilis aplikasi HP (docs/32): berisi `android/latest.json` + APK berversi, di-mount read-only.
    # Kosong = belum ada rilis; pemeriksaan pembaruan selalu menjawab UP_TO_DATE.
    APP_RELEASE_DIR: str = ""

    # Pengaturan jam operasional absensi (06:45 s.d. 19:00, 8 jam kerja efektif + 1 jam istirahat)
    ATTENDANCE_OPEN_TIME: str = "06:45"  # tombol absen masuk aktif mulai jam ini
    ATTENDANCE_LATE_AFTER: str = "08:00"  # absen masuk setelah jam ini tetap boleh tetapi bertanda terlambat
    ATTENDANCE_CLOSE_TIME: str = "19:00"
    ATTENDANCE_REQUIRED_WORK_HOURS: int = 8
    ATTENDANCE_BREAK_HOURS: int = 1
    SKIP_ATTENDANCE_HOURS_CHECK: bool = False

    # "production" menyalakan penjaga di bawah; nilai lain (development/test) memakai bawaan lokal.
    APP_ENV: str = "development"
    # Origin web yang boleh memanggil API dengan cookie (dipisah koma). Kosong = semua origin TANPA credentials.
    CORS_ORIGINS: str = ""
    # Seed media & order contoh saat startup (demo/uji). Bawaan MATI: bila aktif, foto kosong/bukan /uploads/
    # ditimpa gambar contoh — jangan pernah diaktifkan di data sungguhan.
    SEED_DEMO_MEDIA: bool = False
    # Rate limit in-memory (token bucket, satu instance API). Bawaan hanya MENCATAT (log WARNING);
    # set RATE_LIMIT_ENFORCE=true untuk menolak 429 + Retry-After. Limit = permintaan per menit per IP
    # dan per pengguna (pengguna = `sub` token sah; login/refresh hanya per IP).
    RATE_LIMIT_ENFORCE: bool = False
    # Peran ganda (ADR 0002): bila true, izin dan cakupan kantor memakai union peran utama + penugasan aktif
    # (tabel user_role_assignment). Bawaan MATI = perilaku lama persis (peran utama saja).
    ROLE_ASSIGNMENT_ENABLED: bool = False
    RATE_LIMIT_AUTH_PER_MIN: int = 30
    RATE_LIMIT_FILE_URL_PER_MIN: int = 120
    RATE_LIMIT_UPLOAD_PER_MIN: int = 60
    RATE_LIMIT_FACE_PER_MIN: int = 60
    # Proxy tepercaya (IP atau CIDR, dipisah koma). X-Forwarded-For hanya dibaca bila koneksi datang dari sini.
    # Kosong = abaikan X-Forwarded-For (sama seperti login: pakai IP koneksi langsung).
    TRUSTED_PROXY_IPS: str = ""

    # Mengabaikan variabel lingkungan berlebih yang tidak dipetakan ke atribut di sini
    model_config = SettingsConfigDict(env_file=(".env", "api/.env"), extra="ignore")

    @model_validator(mode="after")
    def _encode_database_url_credentials(self) -> Settings:
        """Sandi DB yang memuat ``@`` wajib di-URL-encode dan port kontainer dinormalisasi.

        Tanpa ini API start lalu mati di ``/ready`` dengan ``socket.gaierror`` atau ``ConnectionRefusedError``
        yang menyesatkan (salah parse URL atau salah port host alih-alih port kontainer).
        Nilai diperbaiki otomatis dan dicatat agar tetap terlihat, bukan didiamkan.
        """
        for field in ("DATABASE_URL", "MIGRATION_DATABASE_URL"):
            current = getattr(self, field)
            if not current:
                continue
            fixed, changed = encode_url_credentials(current)
            if changed:
                logger.warning(
                    "%s memuat sandi yang belum di-URL-encode — diperbaiki otomatis. "
                    "Perbarui api.env agar tidak bergantung pada perbaikan ini.",
                    field,
                )
                current = fixed
                object.__setattr__(self, field, fixed)

            fixed_port, port_changed = normalize_database_url_port(current)
            if port_changed:
                logger.warning(
                    "%s memakai port host 5433 untuk host kontainer %s — diperbaiki otomatis ke 5432. "
                    "Perbarui api.env agar memakai port internal 5432.",
                    field,
                    make_url(fixed_port).host,
                )
                object.__setattr__(self, field, fixed_port)
        return self

    @model_validator(mode="after")
    def _fake_face_only_in_development(self) -> Settings:
        """Penjaga mode wajah palsu: tidak boleh aktif di luar APP_ENV=development (API gagal start)."""
        if self.FACE_FAKE_MODE and self.APP_ENV.strip().lower() != "development":
            raise ValueError(
                "FACE_FAKE_MODE=true hanya boleh di APP_ENV=development "
                f"(APP_ENV saat ini: {self.APP_ENV!r}). Matikan FACE_FAKE_MODE."
            )
        return self

    @model_validator(mode="after")
    def _production_requires_secrets(self) -> Settings:
        """
        Validasi paska inisialisasi: Produksi tidak boleh diam-diam memakai kunci JWT sementara,
        tanpa kunci tanda tangan, atau kredensial MinIO bawaan — API menolak start (dok 08).
        """
        if self.APP_ENV.strip().lower() != "production":
            return self
        missing = [name for name, bad in (
            ("JWT_PRIVATE_KEY_HEX", not self.JWT_PRIVATE_KEY_HEX),
            ("DOC_SIGNING_KEY_HEX", self.DOC_SIGNING_KMS_REF.startswith("env:") and not self.DOC_SIGNING_KEY_HEX),
            ("MINIO_ACCESS_KEY", self.MINIO_ACCESS_KEY in ("", "minioadmin")),
            ("MINIO_SECRET_KEY", self.MINIO_SECRET_KEY in ("", "minioadmin")),
        ) if bad]
        if missing:
            raise ValueError("APP_ENV=production tetapi rahasia belum diisi / masih bawaan: " + ", ".join(missing))
        return self

settings = Settings()
