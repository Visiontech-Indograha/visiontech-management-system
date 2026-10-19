"""
app/modules/system/routes/media_stream_route.py

Rute endpoint Universal Media & Document Streaming (/media).
Menangani streaming berkas inline (pratinjau) dan unduhan (attachment)
untuk foto kendaraan, inspeksi, profil, dokumen, bukti absensi, dan contoh SOP foto.
"""

from __future__ import annotations

import mimetypes
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Form, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, Response

from app.core.time import utcnow

router = APIRouter(prefix="/media", tags=["Media Streaming"])

BASE_API_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent  # api/
UPLOADS_DIR = BASE_API_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)


def _resolve_file_path(requested_path: str) -> Path | None:
    """Mencari lokasi fisik berkas di storage uploads atau static."""
    clean = requested_path.strip().replace("\\", "/")
    # Hapus prefix /api/v1 atau http(s) jika ada
    if clean.startswith(("http://", "https://")):
        return None
    if clean.startswith("/api/v1/media/preview?path="):
        clean = clean.split("path=", 1)[-1]
    if clean.startswith("/"):
        clean = clean.lstrip("/")
    if clean.startswith("uploads/"):
        clean = clean[len("uploads/") :]

    # 1. Coba langsung di dalam uploads_dir
    candidate = (UPLOADS_DIR / clean).resolve()
    if candidate.is_file():
        return candidate

    # 2. Coba di parent folder (root api)
    candidate_root = (BASE_API_DIR / clean).resolve()
    if candidate_root.is_file():
        return candidate_root

    # 3. Cari berdasarkan nama file saja di dalam subfolder uploads (pencarian fleksibel)
    file_name = Path(clean).name
    if file_name:
        for found in UPLOADS_DIR.rglob(file_name):
            if found.is_file():
                return found

    return None


def _placeholder_svg(name: str = "Dokumen") -> Response:
    """Mengembalikan gambar placeholder SVG jika berkas fisik belum ada di storage dev."""
    title_text = "Pratinjau Berkas"
    label_text = name[:30]
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">'
        '<rect width="100%" height="100%" fill="#f1f5f9"/>'
        '<rect x="20" y="20" width="360" height="260" rx="12" fill="#ffffff" stroke="#cbd5e1" stroke-width="2"/>'
        '<path d="M175 110 h50 v80 h-50 z" fill="#e2e8f0"/>'
        '<path d="M190 95 h20 v15 h-20 z" fill="#94a3b8"/>'
        f'<text x="200" y="165" font-family="sans-serif" font-size="14" font-weight="600" fill="#475569" '
        f'text-anchor="middle">{title_text}</text>'
        f'<text x="200" y="190" font-family="sans-serif" font-size="12" fill="#64748b" '
        f'text-anchor="middle">{label_text}</text>'
        "</svg>"
    )
    return Response(content=svg, media_type="image/svg+xml")



@router.get("/preview")
async def preview_media(
    path: str = Query(..., description="Path relatif berkas di storage"),
) -> Response:
    """
    Menyajikan pratinjau berkas secara inline di peramban (PDF, Foto, dsb.).
    Tidak memicu unduhan paksa (Content-Disposition: inline).
    """
    resolved = _resolve_file_path(path)
    if not resolved:
        file_name = Path(path).name
        # Jika gambar, berikan SVG placeholder agar tampilan UI tidak rusak (zero broken image)
        if any(path.lower().endswith(ext) for ext in [".jpg", ".jpeg", ".png", ".webp", ".svg"]):
            return _placeholder_svg(file_name)
        raise HTTPException(status_code=404, detail=f"Berkas '{file_name}' tidak ditemukan di storage server.")

    mime_type, _ = mimetypes.guess_type(str(resolved))
    if not mime_type:
        mime_type = "application/octet-stream"

    return FileResponse(
        path=str(resolved),
        media_type=mime_type,
        headers={
            "Content-Disposition": f'inline; filename="{resolved.name}"',
            "Cache-Control": "private, max-age=3600",
        },
    )


@router.get("/download")
async def download_media(
    path: str = Query(..., description="Path relatif berkas di storage"),
) -> Response:
    """
    Mengunduh berkas fisik ke komputer pengguna (Content-Disposition: attachment).
    """
    resolved = _resolve_file_path(path)
    if not resolved:
        raise HTTPException(status_code=404, detail="Berkas tidak ditemukan untuk diunduh.")

    mime_type, _ = mimetypes.guess_type(str(resolved))
    if not mime_type:
        mime_type = "application/octet-stream"

    return FileResponse(
        path=str(resolved),
        media_type=mime_type,
        headers={
            "Content-Disposition": f'attachment; filename="{resolved.name}"',
        },
    )


@router.post("/upload")
async def upload_media(
    file: UploadFile,
    module_category: str = Form(default="general"),
) -> dict[str, object]:
    """
    Mengunggah berkas multimedia (foto mobil, foto inspeksi, berkas karyawan, SOP, bukti absen).
    Menyimpan ke partisi folder uploads/{module_category}/{year}/{month}/.
    """
    now = utcnow()
    category_dir = UPLOADS_DIR / module_category / str(now.year) / f"{now.month:02d}"
    category_dir.mkdir(parents=True, exist_ok=True)

    safe_original = (file.filename or "upload.bin").replace(" ", "_").replace("/", "_").replace("\\", "_")
    unique_name = f"{uuid4().hex[:12]}_{safe_original}"
    target_path = category_dir / unique_name

    content = await file.read()
    target_path.write_bytes(content)

    rel_path = f"/uploads/{module_category}/{now.year}/{now.month:02d}/{unique_name}"
    mime_type, _ = mimetypes.guess_type(str(target_path))

    return {
        "success": True,
        "message": "Berkas berhasil diunggah",
        "data": {
            "file_path": rel_path,
            "preview_url": f"/api/v1/media/preview?path={rel_path}",
            "download_url": f"/api/v1/media/download?path={rel_path}",
            "mime_type": mime_type or "application/octet-stream",
            "size_kb": round(len(content) / 1024, 2),
        },
    }


__all__ = ["router"]
