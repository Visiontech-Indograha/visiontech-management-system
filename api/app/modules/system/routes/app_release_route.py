"""
app/modules/system/routes/app_release_route.py

Rute endpoint HTTP untuk pembaruan aplikasi Android tanpa Play Store (/app/android).
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.1.
"""

from fastapi import APIRouter, Depends, Query, Response
from fastapi.responses import FileResponse, RedirectResponse

from app.modules.system.controllers.app_release_controller import (
    AppReleaseController,
)
from app.modules.system.schemas.system_schema import AppUpdateOut

router = APIRouter(prefix="/app/android", tags=["App"])


@router.get("/update", response_model=AppUpdateOut)
async def check_android_update(
    response: Response,
    build: int = Query(ge=0, description="versionCode aplikasi yang terpasang"),
    abi: list[str] = Query(default=[], description="ABI HP berurutan prioritas (Build.SUPPORTED_ABIS)"),
    controller: AppReleaseController = Depends(),
) -> AppUpdateOut:
    """Apakah HP ini perlu memperbarui aplikasi: UP_TO_DATE, OPTIONAL, atau REQUIRED + berkas unduhannya."""
    return controller.handle_check_update(response, build, abi)


@router.get("/files/{name}", response_class=FileResponse)
@router.head("/files/{name}", response_class=FileResponse, include_in_schema=False)
async def download_android_release(
    name: str,
    controller: AppReleaseController = Depends(),
) -> FileResponse:
    """Berkas APK berversi. Nama tidak pernah dipakai ulang, jadi aman di-cache selamanya (Cloudflare)."""
    return controller.handle_download_release(name)


@router.get("/latest.apk", response_class=RedirectResponse, status_code=302)
async def latest_android_release(
    abi: str | None = Query(default=None, description="mis. armeabi-v7a untuk HP 32-bit; bawaan arm64-v8a"),
    controller: AppReleaseController = Depends(),
) -> RedirectResponse:
    """Tautan tetap untuk pemasangan pertama (QR di halaman login): diarahkan ke APK terbaru."""
    return controller.handle_latest_release(abi)


__all__ = ["router"]
