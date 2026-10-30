"""
app/shared/documents/branding.py
Logo kop laporan survei yang bisa diganti per organisasi: logo perusahaan (Visiontech Indograha) dan logo klien
(Pertamina Hulu Rokan). Ukuran baku = ukuran logo di template sekarang; logo pengganti dipasang "contain"
(rasio dijaga, sisa ruang transparan/putih) ke kotak tiap template sehingga tata letak kop tidak bergeser.
"""
from __future__ import annotations

import io
import logging
from pathlib import Path
from typing import Any, Literal

import filetype
from PIL import Image, ImageOps, UnidentifiedImageError

from app.core import storage
from app.core.errors import AppError, ValidationError

LogoRole = Literal["company", "client"]
# (logo Visiontech — selalu ada, logo tim — None bila tim belum punya logo)
KopLogos = tuple[bytes, bytes | None]
VISIONTECH_LOGO = Path(__file__).resolve().parent / "templates" / "assets" / "logo-visiontech.png"
DPI = 300
# Ukuran baku (cm) diambil dari kop template ACS/CCTV; dipakai sebagai format resmi logo pengganti.
STANDARD: dict[str, dict[str, Any]] = {
    "company": {"label": "Logo perusahaan (Visiontech Indograha)", "width_cm": 4.59, "height_cm": 1.34},
    "client": {"label": "Logo klien (Pertamina Hulu Rokan)", "width_cm": 5.23, "height_cm": 1.67},
}
# Gambar kop di setiap template → peran logonya.
TEMPLATE_MEDIA: dict[str, dict[str, LogoRole]] = {
    "ACS": {"image1.png": "company", "image2.png": "client", "image16.png": "client"},
    "CCTV": {"image3.jpeg": "company", "image2.png": "client"},
}
MAX_UPLOAD = 5 * 1024 * 1024


def standard_px(role: str) -> tuple[int, int]:
    s = STANDARD[role]
    return round(s["width_cm"] / 2.54 * DPI), round(s["height_cm"] / 2.54 * DPI)


def logo_key(organization_id: str, role: str) -> str:
    return f"branding/{organization_id}/logo_{role}.png"


def normalize_upload(raw: bytes) -> bytes:
    """Validasi & simpan sebagai PNG (transparansi dijaga), dipangkas tepi kosongnya, maks 2× ukuran baku."""
    if len(raw) > MAX_UPLOAD:
        raise ValidationError("Logo maksimal 5 MB.")
    try:
        src = Image.open(io.BytesIO(raw))
        src.load()
    except (UnidentifiedImageError, OSError):
        raise ValidationError("Berkas logo harus gambar PNG/JPG/WebP.") from None
    img: Image.Image = ImageOps.exif_transpose(src).convert("RGBA")
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)
    img.thumbnail((standard_px("client")[0] * 2, standard_px("client")[1] * 2))
    out = io.BytesIO()
    img.save(out, "PNG", optimize=True)
    return out.getvalue()


def fit_logo(logo: bytes, size: tuple[int, int], fmt: str) -> bytes:
    """Logo di tengah kanvas berukuran `size` (rasio kotak template), tanpa distorsi."""
    img = Image.open(io.BytesIO(logo)).convert("RGBA")
    w, h = size
    scale = min(w / img.width, h / img.height)
    img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.Resampling.LANCZOS)
    jpeg = fmt.lower() in ("jpeg", "jpg")
    canvas = Image.new("RGBA", size, (255, 255, 255, 255 if jpeg else 0))
    canvas.alpha_composite(img, ((w - img.width) // 2, (h - img.height) // 2))
    out = io.BytesIO()
    if jpeg:
        canvas.convert("RGB").save(out, "JPEG", quality=92)
    else:
        canvas.save(out, "PNG", optimize=True)
    return out.getvalue()


def custom_logos(organization_id: str | None) -> dict[str, bytes]:
    if not organization_id:
        return {}
    found = {}
    for role in STANDARD:
        data = storage.get_object_bytes(logo_key(organization_id, role))
        if data:
            found[role] = data
    return found


def apply_logos(doc: Any, template_format: str, logos: dict[str, bytes]) -> None:
    """Ganti isi gambar kop template (python-docx Document) dengan logo pengganti, ukuran kotak tetap."""
    if not logos:
        return
    media = TEMPLATE_MEDIA.get(template_format, {})
    for part in doc.part.package.iter_parts():
        name = str(part.partname).rsplit("/", 1)[-1]
        role = media.get(name)
        if role not in logos:
            continue
        try:
            orig = Image.open(io.BytesIO(part.blob))
            target = (max(orig.width, standard_px(role)[0]),
                      max(1, round(max(orig.width, standard_px(role)[0]) * orig.height / orig.width)))
        except (UnidentifiedImageError, OSError):
            target = standard_px(role)
        part._blob = fit_logo(logos[role], target, name.rsplit(".", 1)[-1])


# ── Logo tim (ketua tim mengganti; dipakai di semua dokumen tim) ──────────────────────────────
# Format mengikuti logo Visiontech: PNG (logo_company.png). Berkas disimpan apa adanya, tanpa dipangkas.
TEAM_LOGO_MAX_BYTES = 2 * 1024 * 1024
TEAM_LOGO_MIN_PX = 64
TEAM_LOGO_MAX_PX = 4000
TEAM_LOGO_MIMES = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
COMPANY_BOX_PX = standard_px("company")  # kotak logo standar kop dokumen (≈4,59 × 1,34 cm @300 dpi)

logger = logging.getLogger(__name__)


def validate_team_logo(raw: bytes) -> tuple[str, str]:
    """Berkas logo tim yang lolos uji → (mime, ekstensi). Galat: 413 ukuran, 415 tipe, 422 rusak/ukuran piksel."""
    if len(raw) > TEAM_LOGO_MAX_BYTES:
        raise AppError("FILE_TOO_LARGE", "Ukuran logo melebihi batas 2 MB.", status=413)
    kind = filetype.guess(raw)
    mime = kind.mime if kind else None
    if mime not in TEAM_LOGO_MIMES:
        raise AppError("INVALID_FILE_TYPE", "Logo tim harus berformat PNG, JPEG, atau WebP.", status=415)
    try:
        img = Image.open(io.BytesIO(raw))
        img.load()  # dekode penuh: berkas terpotong ikut tertolak
    except (UnidentifiedImageError, OSError, ValueError):
        raise AppError("IMAGE_CORRUPT", "Berkas logo rusak atau terpotong.", status=422) from None
    w, h = img.size
    if not (TEAM_LOGO_MIN_PX <= w <= TEAM_LOGO_MAX_PX and TEAM_LOGO_MIN_PX <= h <= TEAM_LOGO_MAX_PX):
        raise AppError("LOGO_SIZE_INVALID",
                       f"Sisi logo harus {TEAM_LOGO_MIN_PX}-{TEAM_LOGO_MAX_PX} piksel.", status=422)
    return mime, TEAM_LOGO_MIMES[mime]


def team_logo_storage_key(organization_id: str, team_id: str, file_id: str, ext: str) -> str:
    return f"{organization_id}/team-logo/{team_id}/{file_id}.{ext}"


_logo_warned = False  # peringatan kegagalan ambil logo tim hanya sekali per proses (bukan per dokumen)


def team_logo_bytes(team_id: str | None, storage_key: str | None) -> bytes | None:
    """Isi logo tim dari storage, atau None bila tim tak punya logo / berkas tak terbaca.
    MinIO mati/berkas hilang = None (dokumen tetap terbit, hanya logo tim yang tidak tampil).

    Kunci logo tercatat di DB tetapi tidak terbaca → WARNING sekali (agar tidak senyap)."""
    global _logo_warned
    if not storage_key:
        return None
    try:
        data = storage.get_object_bytes(storage_key)
    except Exception:  # noqa: BLE001 - dokumen tetap terbit dengan logo Visiontech
        data = None
    if data:
        return data
    if not _logo_warned:
        _logo_warned = True
        logger.warning("Logo tim %s tidak dapat diambil dari storage (%s); dokumen memakai logo Visiontech saja.",
                       team_id, storage_key)
    return None


def visiontech_logo() -> bytes:
    """Logo Visiontech bawaan repo. Selalu tampil di kop dokumen; tidak dapat diubah lewat aplikasi."""
    return VISIONTECH_LOGO.read_bytes()


def kop_logos(team_id: str | None, storage_key: str | None) -> KopLogos:
    """Logo kop dokumen: (logo Visiontech, logo tim atau None). Logo Visiontech selalu ada."""
    return visiontech_logo(), team_logo_bytes(team_id, storage_key)


def default_kop_logos() -> KopLogos:
    """Kop tanpa logo tim (dipakai bila pemanggil tidak memberi logo tim)."""
    return visiontech_logo(), None


def fit_contain_png(logo: bytes, box: tuple[int, int] = COMPANY_BOX_PX) -> bytes:
    """Logo di tengah kotak `box` (skala proporsional, kanvas transparan). Persegi tampil lebih kecil, tak dipangkas."""
    return fit_logo(logo, box, "png")
