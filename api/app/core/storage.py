"""
Penyimpanan berkas di MinIO (dok 13).

Tidak ada koneksi saat modul diimpor: bucket diperiksa pada pemakaian pertama dan hasil
suksesnya diingat. Batas waktu pendek & tanpa percobaan ulang berlapis — bila MinIO mati,
unggahan gagal cepat dengan jelas dan fitur lain tetap berjalan (prinsip 3).
"""
import io
import logging
from datetime import timedelta
from functools import lru_cache
from urllib.parse import urlparse

import urllib3
from minio import Minio

from app.core.config import settings

logger = logging.getLogger(__name__)

minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE,
    http_client=urllib3.PoolManager(
        timeout=urllib3.Timeout(connect=3, read=30),
        retries=urllib3.Retry(total=1, backoff_factor=0.2),
    ),
)

_bucket_ready = False


def bucket_ready() -> bool:
    return _bucket_ready


def ensure_bucket() -> bool:
    """Pastikan bucket ada. True bila siap; kegagalan tidak diingat agar dicoba lagi nanti."""
    global _bucket_ready
    if _bucket_ready:
        return True
    try:
        if not minio_client.bucket_exists(settings.MINIO_BUCKET):
            minio_client.make_bucket(settings.MINIO_BUCKET)
    except Exception as e:  # noqa: BLE001 — MinIO mati tidak boleh menjatuhkan permintaan
        logger.error(f"MinIO tidak siap (bucket {settings.MINIO_BUCKET}): {e}")
        return False
    _bucket_ready = True
    return True


def upload_file(object_name: str, file_data: bytes, content_type: str) -> bool:
    """Unggah bytes ke MinIO. False bila MinIO tidak siap atau unggahan gagal."""
    if not ensure_bucket():
        return False
    try:
        minio_client.put_object(
            settings.MINIO_BUCKET,
            object_name,
            io.BytesIO(file_data),
            length=len(file_data),
            content_type=content_type,
        )
        return True
    except Exception as e:  # noqa: BLE001
        logger.error(f"Gagal mengunggah ke MinIO {object_name}: {e}")
        return False


@lru_cache(maxsize=1)
def presign_client() -> Minio:
    """Klien khusus penandatanganan URL untuk asal publik (`MINIO_PUBLIC_URL`). Tanda tangan S3
    mengikat host, jadi URL harus dibuat untuk host yang dipakai peramban. Region ditetapkan agar
    penandatanganan murni lokal (tanpa panggilan jaringan ke MinIO)."""
    if not settings.MINIO_PUBLIC_URL:
        return minio_client
    public = urlparse(settings.MINIO_PUBLIC_URL)
    return Minio(
        public.netloc,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=public.scheme == "https",
        region=settings.MINIO_REGION,
    )


def get_presigned_url(object_name: str, expires: timedelta = timedelta(minutes=5)) -> str:
    """URL bertanda tangan, paling lama 5 menit (dok 08, dok 13)."""
    try:
        return presign_client().get_presigned_url("GET", settings.MINIO_BUCKET, object_name, expires=expires)
    except Exception as e:  # noqa: BLE001
        logger.error(f"Gagal membuat URL bertanda tangan untuk {object_name}: {e}")
        return ""
