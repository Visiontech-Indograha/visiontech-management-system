import asyncio
import hashlib
import uuid

import filetype
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import Response

from app.api.deps import get_current_user, get_file_service, get_file_viewer, get_file_viewer_service
from app.core.errors import AppError, NotFoundError
from app.core.image import compress_image
from app.core.security import CurrentUser, create_file_access_ticket
from app.core.storage import get_object_bytes, upload_file
from app.services.file_service import FileService

router = APIRouter(prefix="/files", tags=["Files"])

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_MIMES = [
    "image/jpeg", "image/png", "image/webp", "image/heic",
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
]

@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    current_user: CurrentUser = Depends(get_current_user),
    files: FileService = Depends(get_file_service),
) -> dict[str, str]:
    """
    Unggah file (maks 10MB).
    Gambar (jpeg/png) akan dikompresi ke WebP 3 ukuran (thumb, view, full) secara asinkron.
    Deduplikasi otomatis berbasis SHA-256 (mencegah double upload untuk org yang sama).

    Return: ID file yang baru saja diunggah dan pesan sukses
    """
    # Mengambil objek pengguna saat ini dan koneksi ke database dari injeksi dependensi (Depends)
    # Melakukan pengecekan hash sebelum mengunggah objek
    # 1. Baca paling banyak batas + 1 bita: berkas raksasa tidak pernah dimuat utuh ke memori (O-12).
    file_bytes = await file.read(MAX_FILE_SIZE + 1)
    byte_size = len(file_bytes)

    if byte_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail={"code": "FILE_TOO_LARGE", "message": "Ukuran berkas melebihi batas 10MB."})
    if byte_size == 0:
        raise HTTPException(status_code=400, detail={"code": "FILE_EMPTY", "message": "Berkas kosong."})

    # 2. Validasi Magic Bytes
    kind = filetype.guess(file_bytes)
    mime_type = kind.mime if kind else file.content_type
    if mime_type not in ALLOWED_MIMES:
        raise HTTPException(status_code=415, detail={"code": "INVALID_FILE_TYPE", "message": f"Tipe berkas tidak diizinkan: {mime_type}"})

    # 3. Hash SHA-256 untuk deduplikasi & integritas
    file_hash = hashlib.sha256(file_bytes).digest()

    # Cek deduplikasi di DB (Tingkat Organisasi)
    existing_file = await files.duplicate_of(current_user.organization_id, file_hash)

    if existing_file:
        return {"file_id": str(existing_file.id), "message": "File sudah ada (deduplikasi)."}

    # 4. Generate Storage Key & Simpan DB
    file_id = str(uuid.uuid4())
    ext = kind.extension if kind else (file.filename or "bin").rsplit(".", 1)[-1]
    storage_key = f"{current_user.organization_id}/{file_id}.{ext}"

    stored_id = await files.register(current_user, file_id=file_id, storage_key=storage_key, file_name=file.filename,
                                     mime_type=mime_type, byte_size=byte_size, sha256=file_hash)
    if stored_id != file_id:
        # Unggahan bersamaan berisi berkas yang sama tercatat lebih dulu (uji beban P9-1): pakai berkas itu.
        return {"file_id": stored_id, "message": "File sudah ada (deduplikasi)."}

    # 5. Proses penyimpanan
    is_image = mime_type.startswith("image/")

    def process_and_upload() -> bool:
        # Jika gambar, lakukan kompresi
        if is_image:
            results = compress_image(file_bytes)
            if results:
                # Simpan 3 varian WebP
                return all(
                    upload_file(f"{current_user.organization_id}/{file_id}_{variant}.webp", v_bytes, "image/webp")
                    for variant, v_bytes in results.items()
                )

        # Simpan utuh jika bukan gambar, atau jika kompresi gambar gagal
        return upload_file(storage_key, file_bytes, mime_type)

    # Run di threadpool agar tidak nge-block FastAPI event loop
    loop = asyncio.get_running_loop()
    if not await loop.run_in_executor(None, process_and_upload):
        # Penyimpanan gagal → galat; transaksi permintaan di-rollback sehingga baris file_object
        # tidak tertinggal tanpa objek (sebelumnya klien menerima file_id berkas yang tidak ada).
        raise AppError("STORAGE_UNAVAILABLE",
                       "Penyimpanan berkas sedang tidak tersedia. Coba lagi beberapa saat.", status=503)

    return {"file_id": file_id, "message": "Berkas berhasil diunggah."}


@router.get("/{file_id}")
async def get_file_content(
    file_id: uuid.UUID,
    variant: str = "view",
    download: bool = False,
    current_user: CurrentUser = Depends(get_file_viewer),
    files: FileService = Depends(get_file_viewer_service),
) -> Response:
    """
    Menyajikan isi berkas langsung (bukan JSON) agar bisa dipakai sebagai `src` <img> atau unduhan aman.
    Mendukung Header Authorization: Bearer ATAU query parameter ?token=<ticket>.

    Urutan pencarian objek di MinIO:
    1. `{org}/{file_id}_{variant}.webp` (hasil kompresi aplikasi)
    2. `{org}/{file_id}.{ext}` (berkas asli)
    3. `file_object.storage_key` (jalur penyimpanan apa pun, termasuk impor massal)

    Otorisasi tetap dilakukan lewat `files.authorize` (404 bila tidak berhak).
    """
    file_obj = await files.authorize(file_id, current_user)
    is_image = file_obj.mime_type.startswith("image/")

    candidates: list[str] = []
    if is_image and variant in ("thumb", "view", "full"):
        candidates.append(f"{current_user.organization_id}/{file_id}_{variant}.webp")
    candidates.append(file_obj.storage_key)
    # Ekstra: coba semua varian webp bila jalur utama tidak ketemu
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


@router.get("/{file_id}/url")
async def get_file_url(
    file_id: uuid.UUID,
    variant: str = "full",
    current_user: CurrentUser = Depends(get_current_user),
    files: FileService = Depends(get_file_service),
) -> dict[str, str]:
    """
    Mendapatkan URL API bertiket aman untuk mengakses file (valid 5 menit).
    Varian: full, view, thumb. URL dibuat hanya setelah otorisasi per berkas (V-17, dok 13 §7).

    Path params:
    - file_id: UUID dari file yang diminta

    Query params:
    - variant: variasi kompresi ("full", "view", "thumb")

    Return: URL API same-origin bertiket beserta mime_type asli
    """
    file_obj = await files.authorize(file_id, current_user)

    # Buat tiket akses berumur singkat terikat ke user_id dan file_id
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
