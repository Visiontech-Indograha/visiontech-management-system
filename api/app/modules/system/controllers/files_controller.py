"""
app/modules/system/controllers/files_controller.py

Controller orkestrasi unggah berkas, kompresi gambar, dan akses berkas bertiket.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

import asyncio
import hashlib
import uuid

import filetype
from fastapi import Depends, HTTPException, UploadFile
from fastapi.responses import Response

from app.core.errors import AppError, NotFoundError
from app.core.image import compress_image, is_decodable_image
from app.core.security import CurrentUser, create_file_access_ticket
from app.core.storage import get_object_bytes, upload_file
from app.modules.system.dependencies import get_file_service
from app.modules.system.services.system_service import FileService
from app.shared.content_disposition import content_disposition

MAX_FILE_SIZE = 10 * 1024 * 1024
# Selaras jendela tiket (security.FILE_TICKET_WINDOW_SECONDS = 1800 s); sedikit di bawahnya.
IMAGE_CACHE_CONTROL = "private, max-age=1500"
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
    """Controller pengelolaan unggahan berkas dan URL akses aplikasi bertiket."""

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
        file_bytes = await file.read(MAX_FILE_SIZE + 1)
        byte_size = len(file_bytes)

        if byte_size > MAX_FILE_SIZE:
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
        # Tipe ditentukan dari isi berkas (magic bytes), bukan klaim klien: header palsu tidak lolos.
        mime_type = kind.mime if kind else None
        if mime_type not in ALLOWED_MIMES:
            message = (f"Tipe berkas tidak diizinkan: {mime_type}" if mime_type
                       else "Tipe berkas tidak dikenali. Unggah berkas asli (foto, PDF, atau dokumen), bukan teks.")
            raise HTTPException(status_code=415, detail={"code": "INVALID_FILE_TYPE", "message": message})

        if mime_type.startswith("image/") and not is_decodable_image(file_bytes):
            if mime_type == "image/heic":
                raise HTTPException(
                    status_code=415,
                    detail={"code": "INVALID_FILE_TYPE",
                            "message": "Format HEIC belum didukung. Unggah sebagai JPG atau PNG."},
                )
            raise HTTPException(
                status_code=422,
                detail={"code": "IMAGE_CORRUPT", "message": "Berkas gambar rusak atau terpotong."},
            )

        file_hash = hashlib.sha256(file_bytes).digest()
        # Kunci dedup per pemilik: isi berkas yang sama dari pengguna lain tidak dikenali (tak ada kebocoran
        # keberadaan berkas). Kunci unik organisasi (office_id, sha256) dijaga dengan kunci turunan pemilik.
        owner_key = hashlib.sha256(current_user.user_id.encode() + b":" + file_bytes).digest()

        existing_file = await self.service.duplicate_of(
            current_user.organization_id, current_user.user_id, [file_hash, owner_key])
        if existing_file:
            return {"file_id": str(existing_file.id), "message": "File sudah ada (deduplikasi)."}
        if await self.service.key_held_by_other(current_user.organization_id, current_user.user_id, file_hash):
            file_hash = owner_key

        file_id = str(uuid.uuid4())
        assert kind is not None
        ext = kind.extension
        storage_key = f"{current_user.organization_id}/{file_id}.{ext}"

        stored_id = await self.service.register(
            current_user,
            file_id=file_id,
            storage_key=storage_key,
            file_name=(file.filename or "berkas")[:200],
            mime_type=mime_type,
            byte_size=byte_size,
            sha256=file_hash,
        )
        if stored_id != file_id:
            return {"file_id": stored_id, "message": "File sudah ada (deduplikasi)."}

        is_image = mime_type.startswith("image/")

        def process_and_upload() -> bool:
            if is_image:
                results = compress_image(file_bytes)
                if results:
                    return all(
                        upload_file(f"{current_user.organization_id}/{file_id}_{variant}.webp", v_bytes, "image/webp")
                        for variant, v_bytes in results.items()
                    )
            return upload_file(storage_key, file_bytes, mime_type)

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
        1. `{kantor pengunggah}/{file_id}_{variant}.webp` (hasil kompresi aplikasi)
        2. `file_object.storage_key` (berkas asli / hasil impor massal)
        3. Semua varian webp lain sebagai cadangan
        """
        file_obj = await self.service.authorize(file_id, current_user)
        is_image = file_obj.mime_type.startswith("image/")

        # Varian WebP disimpan di prefiks kantor PENGUNGGAH (`storage_key` = `{kantor}/{id}.{ext}`), bukan kantor
        # yang membuka — PM kantor lain harus tetap bisa melihat foto ketua tim.
        base = (file_obj.storage_key or "").rsplit(".", 1)[0] or f"{current_user.organization_id}/{file_id}"
        candidates: list[str] = []
        if is_image and variant in ("thumb", "view", "full"):
            candidates.append(f"{base}_{variant}.webp")
        candidates.append(file_obj.storage_key)
        if is_image:
            for v in ("view", "full", "thumb"):
                candidates.append(f"{base}_{v}.webp")

        seen: set[str] = set()
        for key in candidates:
            if not key or key in seen:
                continue
            seen.add(key)
            data = get_object_bytes(key)
            if data:
                file_name = getattr(file_obj, "file_name", None) or f"{file_id}.{file_obj.mime_type.split('/')[-1]}"
                # Non-gambar (PDF, dokumen) selalu diunduh, tak dirender inline dari origin API.
                disp_type = "attachment" if (download or not is_image) else "inline"
                # Gambar biasa (foto profil, aset, bukti kerja) boleh di-cache peramban; unduhan, dokumen pribadi, dan
                # swafoto absensi (sensitif) tetap tanpa cache. Isi berkas per id tidak berubah, URL stabil per jendela.
                sensitive = bool(getattr(file_obj, "personal_document", False) or getattr(file_obj, "selfie", False))
                cacheable = is_image and not download and not sensitive
                cache_control = IMAGE_CACHE_CONTROL if cacheable else "private, no-cache, no-store, must-revalidate"
                return Response(
                    content=data,
                    media_type="image/webp" if key.endswith(".webp") else file_obj.mime_type,
                    headers={
                        "Content-Disposition": content_disposition(disp_type, str(file_name)),
                        "Cache-Control": cache_control,
                        "X-Content-Type-Options": "nosniff",
                    },
                )

        raise NotFoundError("Berkas")

    async def handle_get_file_url(
        self,
        current_user: CurrentUser,
        file_id: uuid.UUID,
        variant: str = "full",
    ) -> dict[str, str]:
        """Memeriksa otorisasi dan membuat URL aplikasi bertiket yang bisa dipakai browser."""
        file_obj = await self.service.authorize(file_id, current_user)

        # URL file harus menuju FastAPI, bukan MINIO_PUBLIC_URL yang merupakan origin S3/MinIO.
        ticket = create_file_access_ticket(
            current_user.user_id,
            str(file_id),
            current_user.organization_id,
            variant=variant,
        )

        query = f"variant={variant}&token={ticket}"
        if variant == "full":
            query += "&download=true"
        url = f"/api/v1/files/{file_id}?{query}"
        return {"url": url, "mime_type": file_obj.mime_type}


__all__ = ["ALLOWED_MIMES", "IMAGE_CACHE_CONTROL", "MAX_FILE_SIZE", "FilesController"]
