import io
import logging
from PIL import Image, ImageOps
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# Constants for image resizing
SIZES = {
    "thumb": 256,
    "view": 1024
}

def compress_image(image_bytes: bytes) -> Optional[Dict[str, bytes]]:
    """
    Mengkompresi gambar ke WebP dalam 3 ukuran: thumb, view, dan full.
    Menghapus metadata EXIF secara otomatis.
    Jika gagal, mengembalikan None agar file asal tetap digunakan utuh.
    """
    try:
        results = {}
        with Image.open(io.BytesIO(image_bytes)) as img:
            # Hapus EXIF dan putar gambar ke arah yang benar berdasarkan EXIF orientation
            img = ImageOps.exif_transpose(img)
            
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
