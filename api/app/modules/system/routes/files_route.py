"""
app/modules/system/routes/files_route.py

Rute endpoint HTTP untuk unggah berkas dan pembuatan URL MinIO (/files).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""
import uuid

from fastapi import APIRouter, Depends, File, UploadFile
from fastapi.responses import Response

from app.api.deps import get_current_user
from app.core.security import CurrentUser
from app.modules.system.controllers.files_controller import FilesController

router = APIRouter(prefix="/files", tags=["Files"])


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    controller: FilesController = Depends(),
) -> dict[str, str]:
    """
    Unggah file (maks 10MB).
    Gambar (jpeg/png) akan dikompresi ke WebP 3 ukuran (thumb, view, full) secara asinkron.
    Deduplikasi otomatis berbasis SHA-256 (mencegah double upload untuk org yang sama).

    Return: ID file yang baru saja diunggah dan pesan sukses
    """
    return await controller.handle_upload(current_user, file)


@router.get("/{file_id}")
async def get_file_content(
    file_id: uuid.UUID,
    variant: str = "view",
    current_user: CurrentUser = Depends(get_current_user),
    controller: FilesController = Depends(),
) -> Response:
    """
    Menyajikan isi berkas langsung sebagai byte (bukan JSON) sehingga bisa dipakai
    sebagai `src` pada tag <img>. Otorisasi tetap diperiksa (404 bila tidak berhak).

    Query params:
    - variant: "thumb" | "view" | "full" (default "view")
    """
    return await controller.handle_get_file_content(current_user, file_id, variant=variant)


@router.get("/{file_id}/url")
async def get_file_url(
    file_id: uuid.UUID,
    variant: str = "full",
    current_user: CurrentUser = Depends(get_current_user),
    controller: FilesController = Depends(),
) -> dict[str, str]:
    """
    Mendapatkan URL Presigned MinIO untuk mengakses file (valid 5 menit).
    Varian: full, view, thumb. URL dibuat hanya setelah otorisasi per berkas (V-17, dok 13 §7).

    Path params:
    - file_id: UUID dari file yang diminta

    Query params:
    - variant: variasi kompresi ("full", "view", "thumb")

    Return: Presigned URL dari MinIO beserta mime_type asli
    """
    return await controller.handle_get_file_url(current_user, file_id, variant=variant)


__all__ = ["router"]

