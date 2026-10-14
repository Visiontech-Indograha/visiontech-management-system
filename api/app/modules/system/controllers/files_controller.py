"""
app/modules/system/controllers/files_controller.py

Controller orkestrasi use case unggah berkas, kompresi gambar, dan pembuatan presigned URL MinIO.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""
from __future__ import annotations

import asyncio
import hashlib
import uuid

import filetype
from fastapi import Depends, HTTPException, UploadFile
from fastapi.responses import Response

import app.api.v1.endpoints.files as files_api
from app.api.deps import get_file_service
from app.core.config import settings
from app.core.errors import AppError, NotFoundError
from app.core.image import compress_image
from app.core.security import CurrentUser, create_file_access_ticket
from app.core.storage import get_object_bytes, upload_file
from app.modules.system.services.system_service import FileService

MAX_FILE_SIZE = getattr(files_api, "MAX_FILE_SIZE", 10 * 1024 * 1024)
ALLOWED_MIMES = [
    "image/jpeg",
    "image/png",
    "image/webp",
    "image/heic",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]


class FilesController:
    """Controller pengelolaan unggahan berkas dan penyediaan URL presigned MinIO."""

    def __init__(
        self,
        file_service: FileService = Depends(get_file_service),
    ) -> None:
        self.service = file_service

    async def handle_upload(
        self,
        current_user: CurrentUser,
        file: UploadFile,
    ) -> dict[str, str]:
        """Validasi tipe, ukuran, deduplikasi SHA-256, kompresi citra, dan penyimpanan MinIO."""
        max_size = getattr(files_api, "MAX_FILE_SIZE", MAX_FILE_SIZE)
        file_bytes = await file.read(max_size + 1)
        byte_size = len(file_bytes)

        if byte_size > max_size:
            raise HTTPException(
                status_code=413,
                detail={"code": "FILE_TOO_LARGE", "message": "Ukuran berkas melebihi batas 10MB."},
            )
        if byte_size == 0:
            raise HTTPException(
                status_code=400,
                detail={"code": "FILE_EMPTY", "message": "Berkas kosong."},
            )

        kind = filetype.guess(file_bytes)
        mime_type = kind.mime if kind else file.content_type
        if mime_type not in ALLOWED_MIMES:
            raise HTTPException(
                status_code=415,
                detail={"code": "INVALID_FILE_TYPE", "message": f"Tipe berkas tidak diizinkan: {mime_type}"},
            )

        file_hash = hashlib.sha256(file_bytes).digest()

        existing_file = await self.service.duplicate_of(current_user.organization_id, file_hash)
        if existing_file:
            return {"file_id": str(existing_file.id), "message": "File sudah ada (deduplikasi)."}

        file_id = str(uuid.uuid4())
        ext = kind.extension if kind else (file.filename or "bin").rsplit(".", 1)[-1]
        storage_key = f"{current_user.organization_id}/{file_id}.{ext}"

        stored_id = await self.service.register(
            current_user,
            file_id=file_id,
            storage_key=storage_key,
            file_name=file.filename,
            mime_type=mime_type,
            byte_size=byte_size,
            sha256=file_hash,
        )
        if stored_id != file_id:
            return {"file_id": stored_id, "message": "File sudah ada (deduplikasi)."}

        is_image = mime_type.startswith("image/")
        uploader = getattr(files_api, "upload_file", upload_file)

        def process_and_upload() -> bool:
            if is_image:
                results = compress_image(file_bytes)
                if results:
                    return all(
                        uploader(f"{current_user.organization_id}/{file_id}_{variant}.webp", v_bytes, "image/webp")
                        for variant, v_bytes in results.items()
                    )
            return uploader(storage_key, file_bytes, mime_type)

        loop = asyncio.get_running_loop()
        if not await loop.run_in_executor(None, process_and_upload):
            raise AppError(
                "STORAGE_UNAVAILABLE",
                "Penyimpanan berkas sedang tidak tersedia. Coba lagi beberapa saat.",
                status=503,
            )

        return {"file_id": file_id, "message": "Berkas berhasil diunggah."}

    async def handle_get_file_content(
        self,
        current_user: CurrentUser,
        file_id: uuid.UUID,
        variant: str = "view",
        download: bool = False,
    ) -> Response:
        """
        Menyajikan isi berkas langsung sebagai byte agar bisa dipakai sebagai `src` <img> atau unduhan aman.

        Urutan pencarian objek di MinIO:
        1. `{org}/{file_id}_{variant}.webp` (hasil kompresi aplikasi)
        2. `file_object.storage_key` (berkas asli / hasil impor massal)
        3. Semua varian webp lain sebagai cadangan
        """
        file_obj = await self.service.authorize(file_id, current_user)
        is_image = file_obj.mime_type.startswith("image/")

        candidates: list[str] = []
        if is_image and variant in ("thumb", "view", "full"):
            candidates.append(f"{current_user.organization_id}/{file_id}_{variant}.webp")
        candidates.append(file_obj.storage_key)
        if is_image:
            for v in ("view", "full", "thumb"):
                candidates.append(f"{current_user.organization_id}/{file_id}_{v}.webp")

        seen: set[str] = set()
        for key in candidates:
            if not key or key in seen:
                continue
            seen.add(key)
            data = get_object_bytes(key)
            if data:
                file_name = getattr(file_obj, "file_name", None) or f"{file_id}.{file_obj.mime_type.split('/')[-1]}"
                safe_name = str(file_name).replace('"', '\\"')
                disp_type = "attachment" if download else "inline"
                return Response(
                    content=data,
                    media_type="image/webp" if key.endswith(".webp") else file_obj.mime_type,
                    headers={
                        "Content-Disposition": f'{disp_type}; filename="{safe_name}"',
                        "Cache-Control": "private, no-cache, no-store, must-revalidate",
                    },
                )

        raise NotFoundError("Berkas")

    async def handle_get_file_url(
        self,
        current_user: CurrentUser,
        file_id: uuid.UUID,
        variant: str = "full",
    ) -> dict[str, str]:
        """Memeriksa otorisasi akses pengguna atas berkas dan membuat URL aplikasi bertiket aman."""
        file_obj = await self.service.authorize(file_id, current_user)

        # Buat tiket akses berumur singkat terikat ke user_id dan file_id
        ticket = create_file_access_ticket(
            current_user.user_id,
            str(file_id),
            current_user.organization_id,
            variant=variant,
        )

        base_url = (settings.MINIO_PUBLIC_URL or "").rstrip("/")
        url = f"{base_url}/api/v1/files/{file_id}?variant={variant}&token={ticket}"
        return {"url": url, "mime_type": file_obj.mime_type}


__all__ = ["ALLOWED_MIMES", "MAX_FILE_SIZE", "FilesController"]

