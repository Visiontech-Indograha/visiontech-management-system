import io
from minio import Minio
from minio.error import S3Error
from datetime import timedelta
import logging

from app.core.config import settings

logger = logging.getLogger(__name__)

# Initialize MinIO client
minio_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE
)

def ensure_bucket():
    try:
        if not minio_client.bucket_exists(settings.MINIO_BUCKET):
            minio_client.make_bucket(settings.MINIO_BUCKET)
    except Exception as e:
        logger.error(f"Error ensuring MinIO bucket exists: {e}")

# Run on startup
ensure_bucket()

def upload_file(object_name: str, file_data: bytes, content_type: str) -> bool:
    """Uploads file data (bytes) to MinIO."""
    try:
        data_stream = io.BytesIO(file_data)
        minio_client.put_object(
            settings.MINIO_BUCKET,
            object_name,
            data_stream,
            length=len(file_data),
            content_type=content_type
        )
        return True
    except Exception as e:
        logger.error(f"Error uploading to MinIO {object_name}: {e}")
        return False

def get_presigned_url(object_name: str, expires: timedelta = timedelta(minutes=5)) -> str:
    """Generates a presigned URL valid for a maximum of 5 minutes (or as requested)."""
    try:
        url = minio_client.get_presigned_url(
            "GET",
            settings.MINIO_BUCKET,
            object_name,
            expires=expires
        )
        return url
    except Exception as e:
        logger.error(f"Error generating presigned URL for {object_name}: {e}")
        return ""
