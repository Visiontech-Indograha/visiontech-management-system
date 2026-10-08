"""
app/services/app_release_service.py
Rilis aplikasi Android tanpa Play Store (docs/32). Sumber data: berkas `android/latest.json` di folder rilis
(`APP_RELEASE_DIR`, di-mount read-only di server) yang ditulis skrip `scripts/rilis-apk.sh` — tanpa basis data.

Prinsip: pemeriksaan pembaruan **tidak pernah** mengunci HP karena kesalahan server. Manifest hilang atau rusak
dianggap "belum ada rilis", dan status REQUIRED hanya diberikan bila memang ada berkas yang bisa diunduh HP itu.
"""
from __future__ import annotations

import logging
from pathlib import Path

from pydantic import ValidationError as PydanticValidationError

from app.core.errors import NotFoundError
from app.schemas.app_release import AppUpdateOut, ReleaseFile, ReleaseFileOut, ReleaseManifest

logger = logging.getLogger(__name__)

# Jalur publik berkas APK (relatif ke host API). Klien menggabungkannya dengan alamat API-nya sendiri,
# sehingga tidak pernah mengunduh dari host yang disebut server.
FILES_PATH = "/api/v1/app/android/files"
DEFAULT_ABI = "arm64-v8a"

_cache: dict[Path, tuple[float, ReleaseManifest | None]] = {}


class AppReleaseService:
    """Membaca manifest rilis Android dan memutuskan status pembaruan sebuah HP."""

    def __init__(self, release_dir: str) -> None:
        self.base = Path(release_dir) / "android" if release_dir else None

    def manifest(self) -> ReleaseManifest | None:
        """Manifest yang berlaku, dibaca ulang hanya bila berkasnya berubah (mtime)."""
        if self.base is None:
            return None
        path = self.base / "latest.json"
        try:
            mtime = path.stat().st_mtime
        except OSError:
            return None
        cached = _cache.get(path)
        if cached and cached[0] == mtime:
            return cached[1]
        try:
            manifest: ReleaseManifest | None = ReleaseManifest.model_validate_json(path.read_bytes())
        except (OSError, PydanticValidationError) as e:
            logger.warning("Manifest rilis Android tidak valid, dianggap belum ada rilis: %s", e)
            manifest = None
        _cache[path] = (mtime, manifest)
        return manifest

    def check_update(self, build: int, abis: list[str]) -> AppUpdateOut:
        """Status pembaruan untuk HP dengan versionCode `build` dan daftar ABI `abis` (urutan prioritas HP)."""
        manifest = self.manifest()
        if manifest is None:
            return AppUpdateOut(status="UP_TO_DATE", current_build=build)
        file = _pick_file(manifest.files, abis)
        min_build = min(manifest.min_build, manifest.build)   # tidak mungkin mewajibkan build yang belum ada
        out = AppUpdateOut(
            status="UP_TO_DATE", current_build=build, latest_build=manifest.build,
            latest_version=manifest.version_name, min_build=min_build,
            released_at=manifest.released_at, notes=manifest.notes,
        )
        if build >= manifest.build or file is None:
            return out
        out.status = "REQUIRED" if build < min_build else "OPTIONAL"
        out.download = ReleaseFileOut(abi=file.abi, url=f"{FILES_PATH}/{file.name}", sha256=file.sha256,
                                      size=file.size)
        return out

    def latest_file_name(self, abi: str | None) -> str:
        """Nama APK terbaru untuk tautan pemasangan pertama (bawaan arm64-v8a)."""
        manifest = self.manifest()
        file = _pick_file(manifest.files, [abi or DEFAULT_ABI]) if manifest else None
        if file is None:
            raise NotFoundError("Rilis aplikasi Android")
        return file.name

    def resolve_file(self, name: str) -> Path:
        """Jalur APK di disk — hanya nama yang tercantum di manifest dan berada di dalam folder rilis."""
        manifest = self.manifest()
        if self.base is None or manifest is None or name not in {f.name for f in manifest.files}:
            raise NotFoundError("Berkas aplikasi")
        path = (self.base / name).resolve()
        if path.parent != self.base.resolve() or not path.is_file():
            raise NotFoundError("Berkas aplikasi")
        return path


def _pick_file(files: list[ReleaseFile], abis: list[str]) -> ReleaseFile | None:
    """Berkas pertama yang cocok dengan urutan ABI HP; tanpa daftar ABI → arm64-v8a lalu berkas pertama."""
    by_abi = {f.abi: f for f in files}
    for abi in abis or [DEFAULT_ABI]:
        if abi in by_abi:
            return by_abi[abi]
    return None if abis else files[0]
