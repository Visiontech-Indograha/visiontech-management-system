"""Pembaruan aplikasi Android tanpa Play Store (docs/32). Rute PUBLIK — keputusan pemilik 2026-10-07:
pembaruan wajib harus bisa diunduh dari layar login, dan karyawan baru memasang dari tautan di halaman login.
APK tidak memuat rahasia. Tanpa pembatas laju per-IP: di belakang Caddy semua klien tampak ber-IP sama."""

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import FileResponse, RedirectResponse

from app.api.deps import get_app_release_service
from app.schemas.app_release import AppUpdateOut
from app.services.app_release_service import FILES_PATH, AppReleaseService

router = APIRouter(prefix="/app/android", tags=["App"])

APK_MEDIA_TYPE = "application/vnd.android.package-archive"


@router.get("/update", response_model=AppUpdateOut)
async def check_android_update(
    response: Response,
    build: int = Query(ge=0, description="versionCode aplikasi yang terpasang"),
    abi: list[str] = Query(default=[], description="ABI HP berurutan prioritas (Build.SUPPORTED_ABIS)"),
    release_service: AppReleaseService = Depends(get_app_release_service),
) -> AppUpdateOut:
    """Apakah HP ini perlu memperbarui aplikasi: UP_TO_DATE, OPTIONAL, atau REQUIRED + berkas unduhannya."""
    response.headers["Cache-Control"] = "no-store"
    return release_service.check_update(build, abi)


@router.get("/files/{name}", response_class=FileResponse)
async def download_android_release(
    name: str, release_service: AppReleaseService = Depends(get_app_release_service),
) -> FileResponse:
    """Berkas APK berversi. Nama tidak pernah dipakai ulang, jadi aman di-cache selamanya (Cloudflare)."""
    return FileResponse(
        release_service.resolve_file(name), media_type=APK_MEDIA_TYPE, filename=name,
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.get("/latest.apk", response_class=RedirectResponse, status_code=302)
async def latest_android_release(
    abi: str | None = Query(default=None, description="mis. armeabi-v7a untuk HP 32-bit; bawaan arm64-v8a"),
    release_service: AppReleaseService = Depends(get_app_release_service),
) -> RedirectResponse:
    """Tautan tetap untuk pemasangan pertama (QR di halaman login): diarahkan ke APK terbaru."""
    return RedirectResponse(f"{FILES_PATH}/{release_service.latest_file_name(abi)}", status_code=302,
                            headers={"Cache-Control": "no-store"})
