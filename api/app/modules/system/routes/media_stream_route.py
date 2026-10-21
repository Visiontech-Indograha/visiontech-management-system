"""
app/modules/system/routes/media_stream_route.py

Media rujukan statis (/media/preview, /media/download) dari `api/uploads/` — contoh foto SOP, foto alat & kendaraan
hasil seed. Dipakai tag <img> web yang tidak bisa mengirim header Bearer, jadi rute ini publik dan sengaja sempit:

- hanya berkas di dalam `api/uploads/<folder rujukan>/` (tanpa naik folder, tanpa pencarian nama berkas);
- hanya jenis gambar/PDF;
- berkas pribadi (foto karyawan, dokumen, swafoto, inspeksi) TIDAK disajikan di sini — semua unggahan pengguna lewat
  `/files/upload` (MinIO) dan dibuka lewat `/files/{id}/url` dengan pemeriksaan akses.
Unggah lewat `/media/upload` dihapus (dulu menulis ke disk tanpa login).
"""

from __future__ import annotations

import mimetypes
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response

from app.shared.content_disposition import content_disposition

router = APIRouter(prefix="/media", tags=["Media Streaming"])

UPLOADS_DIR = (Path(__file__).resolve().parents[4] / "uploads").resolve()  # api/uploads
PUBLIC_FOLDERS = frozenset({"sop", "tools", "vehicles"})
PUBLIC_SUFFIXES = frozenset({".jpg", ".jpeg", ".png", ".webp", ".svg", ".pdf"})


def _resolve_file_path(requested_path: str) -> Path | None:
    """Path relatif ("/uploads/sop/x.png", "sop/x.png") → berkas di folder rujukan publik, atau None."""
    clean = requested_path.strip().replace("\\", "/").lstrip("/")
    if clean.startswith("uploads/"):
        clean = clean[len("uploads/"):]
    parts = [p for p in clean.split("/") if p]
    if len(parts) < 2 or parts[0] not in PUBLIC_FOLDERS or any(p in (".", "..") for p in parts):
        return None
    candidate = (UPLOADS_DIR / Path(*parts)).resolve()
    if not candidate.is_relative_to(UPLOADS_DIR / parts[0]) or candidate.suffix.lower() not in PUBLIC_SUFFIXES:
        return None
    return candidate if candidate.is_file() else None


def _placeholder_svg(name: str = "Dokumen") -> Response:
    """Gambar placeholder bila berkas rujukan belum ada di storage dev (tampilan tidak rusak)."""
    label_text = "".join(ch for ch in name[:30] if ch.isalnum() or ch in " ._-")
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" viewBox="0 0 400 300">'
        '<rect width="100%" height="100%" fill="#f1f5f9"/>'
        '<rect x="20" y="20" width="360" height="260" rx="12" fill="#ffffff" stroke="#cbd5e1" stroke-width="2"/>'
        '<path d="M175 110 h50 v80 h-50 z" fill="#e2e8f0"/>'
        '<path d="M190 95 h20 v15 h-20 z" fill="#94a3b8"/>'
        '<text x="200" y="165" font-family="sans-serif" font-size="14" font-weight="600" fill="#475569" '
        'text-anchor="middle">Pratinjau Berkas</text>'
        f'<text x="200" y="190" font-family="sans-serif" font-size="12" fill="#64748b" '
        f'text-anchor="middle">{label_text}</text>'
        "</svg>"
    )
    return Response(content=svg, media_type="image/svg+xml")


def _serve(path: str, disposition: str) -> Response:
    resolved = _resolve_file_path(path)
    if resolved is None:
        if disposition == "inline" and Path(path).suffix.lower() in PUBLIC_SUFFIXES - {".pdf"}:
            return _placeholder_svg(Path(path).name)
        raise HTTPException(status_code=404, detail="Berkas tidak ditemukan.")
    mime_type = mimetypes.guess_type(str(resolved))[0] or "application/octet-stream"
    return FileResponse(
        path=str(resolved),
        media_type=mime_type,
        headers={"Content-Disposition": content_disposition(disposition, resolved.name),
                 "Cache-Control": "public, max-age=3600", "X-Content-Type-Options": "nosniff"},
    )


@router.get("/preview")
async def preview_media(path: str = Query(..., max_length=300, description="Path rujukan, mis. /uploads/sop/x.png")
                        ) -> Response:
    """Pratinjau inline media rujukan (contoh SOP, foto alat/kendaraan)."""
    return _serve(path, "inline")


@router.get("/download")
async def download_media(path: str = Query(..., max_length=300, description="Path rujukan, mis. /uploads/sop/x.pdf")
                         ) -> Response:
    """Unduh media rujukan (Content-Disposition: attachment)."""
    return _serve(path, "attachment")


__all__ = ["router"]
