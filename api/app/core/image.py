import io
import logging

from PIL import Image, ImageOps
from PIL.Image import Image as PILImage
from pillow_heif import register_heif_opener

logger = logging.getLogger(__name__)

# Dekoder HEIC/HEIF untuk Pillow (foto iPhone/Android): setelah ini `Image.open` menerima HEIC asli.
# HEIC palsu/terpotong tetap gagal didekode dan ditolak (415/422) oleh `is_decodable_image`.
register_heif_opener()

# Constants for image resizing
SIZES = {
    "thumb": 256,
    "view": 1024
}

def is_decodable_image(image_bytes: bytes) -> bool:
    """Gambar benar-benar bisa didekode seluruhnya (PNG/JPEG/WebP). Berkas terpotong atau bertanda tipe palsu
    (mis. HEIC tanpa pustaka dekoder) → False. Hanya magic bytes tidak cukup untuk memeriksa gambar."""
    try:
        with Image.open(io.BytesIO(image_bytes)) as src:
            src.load()
        return True
    except Exception:
        return False


def compress_image(image_bytes: bytes) -> dict[str, bytes] | None:
    """
    Mengkompresi gambar ke WebP dalam 3 ukuran: thumb, view, dan full.
    Menghapus metadata EXIF secara otomatis.
    Jika gagal, mengembalikan None agar file asal tetap digunakan utuh.
    """
    try:
        results = {}
        with Image.open(io.BytesIO(image_bytes)) as src:
            # Hapus EXIF dan putar gambar ke arah yang benar berdasarkan EXIF orientation
            img: PILImage = ImageOps.exif_transpose(src)

            # Konversi ke RGB jika format asli memiliki alpha/pallet yang tidak didukung JPEG/WebP
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")

            # 1. Full (asli tapi webp dan tanpa EXIF)
            full_io = io.BytesIO()
            img.save(full_io, format="WEBP", quality=85)
            results["full"] = full_io.getvalue()

            # 2. View (maks 1024px)
            view_img = img.copy()
            view_img.thumbnail((SIZES["view"], SIZES["view"]), Image.Resampling.LANCZOS)
            view_io = io.BytesIO()
            view_img.save(view_io, format="WEBP", quality=80)
            results["view"] = view_io.getvalue()

            # 3. Thumb (maks 256px)
            thumb_img = img.copy()
            thumb_img.thumbnail((SIZES["thumb"], SIZES["thumb"]), Image.Resampling.LANCZOS)
            thumb_io = io.BytesIO()
            thumb_img.save(thumb_io, format="WEBP", quality=75)
            results["thumb"] = thumb_io.getvalue()

        return results
    except Exception as e:
        logger.error(f"Gagal memproses gambar: {e}")
        return None
