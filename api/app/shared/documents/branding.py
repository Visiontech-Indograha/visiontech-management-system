"""
app/shared/documents/branding.py
Logo kop laporan survei yang bisa diganti per organisasi: logo perusahaan (Visiontech Indograha) dan logo klien
(Pertamina Hulu Rokan). Ukuran baku = ukuran logo di template sekarang; logo pengganti dipasang "contain"
(rasio dijaga, sisa ruang transparan/putih) ke kotak tiap template sehingga tata letak kop tidak bergeser.
"""
from __future__ import annotations

import io
from typing import Any, Literal

from PIL import Image, ImageOps, UnidentifiedImageError

from app.core import storage
from app.core.errors import ValidationError

LogoRole = Literal["company", "client"]
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
