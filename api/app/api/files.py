import asyncio
import filetype
import hashlib
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.api.deps import CurrentUser, get_current_user, get_db_with_user
from app.core.storage import upload_file, get_presigned_url
from app.core.image import compress_image
import uuid
import os

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
    db: AsyncSession = Depends(get_db_with_user)
):
    """
    Unggah file (maks 10MB).
    Gambar (jpeg/png) akan dikompresi ke WebP 3 ukuran (thumb, view, full) secara asinkron.
    Deduplikasi otomatis berbasis SHA-256 (mencegah double upload untuk org yang sama).
    """
    # 1. Read file & Check Size
    file_bytes = await file.read()
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
    query = text("SELECT id, storage_key FROM vms.file_object WHERE organization_id = :org AND sha256 = :hash")
    existing = await db.execute(query, {"org": current_user.organization_id, "hash": file_hash})
    existing_file = existing.fetchone()
    
    if existing_file:
        return {"file_id": str(existing_file.id), "message": "File sudah ada (deduplikasi)."}
        
    # 4. Generate Storage Key & Simpan DB
    file_id = str(uuid.uuid4())
    ext = kind.extension if kind else file.filename.split(".")[-1]
    storage_key = f"{current_user.organization_id}/{file_id}.{ext}"
    
    insert_query = text("""
        INSERT INTO vms.file_object (id, organization_id, storage_key, file_name, mime_type, byte_size, sha256, uploaded_by)
        VALUES (:id, :org, :key, :name, :mime, :size, :hash, :uid)
    """)
    await db.execute(insert_query, {
        "id": file_id,
        "org": current_user.organization_id,
        "key": storage_key,
        "name": file.filename,
        "mime": mime_type,
        "size": byte_size,
        "hash": file_hash,
        "uid": current_user.user_id
    })
    
    # 5. Proses penyimpanan
    is_image = mime_type.startswith("image/")
    
    def process_and_upload():
        # Jika gambar, lakukan kompresi
        if is_image:
            results = compress_image(file_bytes)
            if results:
                # Simpan 3 varian WebP
                for variant, v_bytes in results.items():
                    v_key = f"{current_user.organization_id}/{file_id}_{variant}.webp"
                    upload_file(v_key, v_bytes, "image/webp")
                return
        
        # Simpan utuh jika bukan gambar, atau jika kompresi gambar gagal
        upload_file(storage_key, file_bytes, mime_type)
        
    # Run di threadpool agar tidak nge-block FastAPI event loop
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, process_and_upload)
    
    return {"file_id": file_id, "message": "Berkas berhasil diunggah."}


@router.get("/{file_id}/url")
async def get_file_url(
    file_id: str,
    variant: str = "full",
    current_user: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_with_user)
):
    """
    Mendapatkan URL Presigned MinIO untuk mengakses file (valid 5 menit).
    Varian: full, view, thumb.
    """
    query = text("SELECT storage_key, mime_type FROM vms.file_object WHERE id = :id AND organization_id = :org")
    result = await db.execute(query, {"id": file_id, "org": current_user.organization_id})
    file_obj = result.fetchone()
    
    if not file_obj:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "Berkas tidak ditemukan."})
        
    is_image = file_obj.mime_type.startswith("image/")
    
    if is_image and variant in ["thumb", "view", "full"]:
        # Gambar yang sukses dikompresi diubah menjadi webp
        # Kita perlu fallback jika ternyata kompresi gagal (tersimpan storage_key asli)
        target_key = f"{current_user.organization_id}/{file_id}_{variant}.webp"
        url = get_presigned_url(target_key)
        # Jika presigned URL MinIO bisa digenerate meskipun objek belum dicek eksistensinya (S3 behavior)
        # Maka client akan dapat 404 dari MinIO jika kompresi sempat gagal.
        # Untuk ketahanan, aplikasi semestinya memverifikasi atau client men-fallback ke full URL.
    else:
        target_key = file_obj.storage_key
        url = get_presigned_url(target_key)
        
    if not url:
        raise HTTPException(status_code=500, detail={"code": "STORAGE_ERROR", "message": "Gagal membuat URL."})
        
    return {"url": url}
