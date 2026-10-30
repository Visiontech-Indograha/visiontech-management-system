"""
app/core/storage.py

File storage utility for MinIO.
No connection is made during module import: bucket existence is checked on
first usage and cached on success. Short timeouts are used to fail fast
if MinIO is down, allowing other features to keep running.
"""
import io
import logging
from datetime import timedelta
from functools import lru_cache
from urllib.parse import urlparse

import urllib3
from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = logging.getLogger(__name__)

# Konfigurasi koneksi MinIO dengan urllib3 PoolManager
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
    """Check if the bucket is ready."""
    # Mengembalikan status kesiapan bucket
    return _bucket_ready


def ensure_bucket() -> bool:
    """
    Ensure the MinIO bucket exists.
    Returns True if ready. Failures are not cached so retries can happen later.
    """
    global _bucket_ready
    if _bucket_ready:
        # Bucket sudah dipastikan ada sebelumnya
        return True
    try:
        # Membuat bucket bila belum ada di server MinIO
        if not minio_client.bucket_exists(settings.MINIO_BUCKET):
            minio_client.make_bucket(settings.MINIO_BUCKET)
    except Exception as e:  # noqa: BLE001
        # MinIO mati tidak boleh menjatuhkan permintaan, biarkan error tercatat
        logger.error(f"MinIO tidak siap (bucket {settings.MINIO_BUCKET}): {e}")
        return False
    _bucket_ready = True
    return True


def upload_file(object_name: str, file_data: bytes, content_type: str) -> bool:
    """
    Upload file bytes to MinIO.
    Returns False if MinIO is not ready or the upload fails.
    """
    if not ensure_bucket():
        # Batalkan unggahan jika bucket tidak siap
        return False
    try:
        # Mengunggah objek ke MinIO menggunakan io.BytesIO
        minio_client.put_object(
            settings.MINIO_BUCKET,
            object_name,
            io.BytesIO(file_data),
            length=len(file_data),
            content_type=content_type,
        )
        return True
    except Exception as e:  # noqa: BLE001
        # Tangani error unggahan dengan aman
        logger.error(f"Gagal mengunggah ke MinIO {object_name}: {e}")
        return False


def get_image_bytes(storage_key: str) -> bytes | None:
    """Isi gambar unggahan untuk diproses server (laporan, wajah, tanda tangan).

    Unggahan gambar lewat `/files/upload` hanya menyimpan varian WebP `{org}/{id}_{full|view|thumb}.webp` —
    kunci asli `{org}/{id}.{ext}` yang tercatat di `file_object.storage_key` tidak ikut tersimpan. Coba kunci asli
    dulu (berkas non-kompresi / data lama), lalu varian terbesar."""
    if not storage_key:
        return None
    base = storage_key.rsplit(".", 1)[0]
    for key in (storage_key, f"{base}_full.webp", f"{base}_view.webp", f"{base}_thumb.webp"):
        if object_exists(key):
            data = get_object_bytes(key)
            if data:
                return data
    return None


def get_object_bytes(object_name: str) -> bytes | None:
    """Unduh isi objek dari MinIO. None bila objek tidak ada atau MinIO tidak tersedia."""
    if not ensure_bucket():
        return None
    response = None
    try:
        response = minio_client.get_object(settings.MINIO_BUCKET, object_name)
        return response.read()
    except S3Error as e:
        if e.code == "NoSuchKey":  # objek memang belum ada (mis. logo pengganti belum diunggah): bukan galat
            logger.debug(f"Objek MinIO belum ada: {object_name}")
        else:
            logger.error(f"Gagal membaca dari MinIO {object_name}: {e}")
        return None
    except Exception as e:  # noqa: BLE001
        logger.error(f"Gagal membaca dari MinIO {object_name}: {e}")
        return None
    finally:
        if response is not None:
            response.close()
            response.release_conn()


def delete_object(object_name: str) -> bool:
    """Hapus objek dari MinIO (idempoten: objek yang sudah tidak ada dianggap berhasil)."""
    if not ensure_bucket():
        return False
    try:
        minio_client.remove_object(settings.MINIO_BUCKET, object_name)
        return True
    except Exception as e:  # noqa: BLE001
        logger.error(f"Gagal menghapus dari MinIO {object_name}: {e}")
        return False


def object_exists(object_name: str) -> bool:
    """Cek keberadaan objek di MinIO tanpa mengunduh isinya."""
    if not ensure_bucket():
        return False
    try:
        minio_client.stat_object(settings.MINIO_BUCKET, object_name)
        return True
    except Exception:  # noqa: BLE001
        return False


@lru_cache(maxsize=1)
def presign_client() -> Minio:
    """
    Create a specific MinIO client used for URL presigning with a public origin.
    S3 signatures are bound to the host, so URLs must be created for the host
    used by the browser. Region is set to ensure local presigning without network calls.
    """
    if not settings.MINIO_PUBLIC_URL:
        # Kembalikan client standar jika URL publik tidak dikonfigurasi
        return minio_client

    public = urlparse(settings.MINIO_PUBLIC_URL)
    # Buat client MinIO khusus penandatanganan URL
    return Minio(
        public.netloc,
        access_key=settings.MINIO_ACCESS_KEY,
        secret_key=settings.MINIO_SECRET_KEY,
        secure=public.scheme == "https",
        region=settings.MINIO_REGION,
    )


def get_presigned_url(object_name: str, expires: timedelta = timedelta(minutes=5)) -> str:
    """
    Generate a presigned URL valid for a maximum of the specified duration.
    """
    try:
        # Membuat URL bertanda tangan untuk diakses sementara
        return presign_client().get_presigned_url("GET", settings.MINIO_BUCKET, object_name, expires=expires)
    except Exception as e:  # noqa: BLE001
        # Gagal membuat presigned URL
        logger.error(f"Gagal membuat URL bertanda tangan untuk {object_name}: {e}")
        return ""
