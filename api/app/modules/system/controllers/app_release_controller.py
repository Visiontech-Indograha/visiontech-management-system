"""
app/modules/system/controllers/app_release_controller.py

Controller orkestrasi use case pembaruan aplikasi Android tanpa Play Store.
Mengikuti Panduan Standar Arsitektur API FastAPI Modular §4 & §5.2.
"""

from __future__ import annotations

from fastapi import Depends, Response
from fastapi.responses import FileResponse, RedirectResponse

from app.modules.system.dependencies import get_app_release_service
from app.modules.system.schemas.system_schema import AppUpdateOut
from app.modules.system.services.system_service import (
    FILES_PATH,
    AppReleaseService,
)

APK_MEDIA_TYPE = "application/vnd.android.package-archive"


class AppReleaseController:
    """Controller pengecekan versi dan unduhan berkas APK aplikasi Android."""

    def __init__(
        self,
        release_service: AppReleaseService = Depends(get_app_release_service),
    ) -> None:
        self.service = release_service

    def handle_check_update(
        self,
        response: Response,
        build: int,
        abi: list[str],
    ) -> AppUpdateOut:
        """Mengecek apakah perangkat memerlukan pembaruan aplikasi."""
        response.headers["Cache-Control"] = "no-store"
        return self.service.check_update(build, abi)

    def handle_download_release(
        self,
        name: str,
    ) -> FileResponse:
        """Mengunduh berkas APK berversi (immutable cache)."""
        path = self.service.resolve_file(name)
        return FileResponse(
            path,
            media_type=APK_MEDIA_TYPE,
            filename=path.name,
            headers={"Cache-Control": "public, max-age=31536000, immutable"},
        )

    def handle_latest_release(
        self,
        abi: str | None,
    ) -> RedirectResponse:
        """Mengarahkan ke berkas rilis APK terbaru untuk instalasi pertama."""
        return RedirectResponse(
            f"{FILES_PATH}/{self.service.latest_file_name(abi)}",
            status_code=302,
            headers={"Cache-Control": "no-store"},
        )


__all__ = ["APK_MEDIA_TYPE", "AppReleaseController"]
