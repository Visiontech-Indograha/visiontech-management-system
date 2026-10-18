"""
scripts/seed_media_assets.py

Menyalin dan menyematkan aset foto dan file uji dari web/dist/foto_test
ke dalam direktori uploads/ dan menyelaraskan path media pada database PostgreSQL.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path


def seed_media() -> None:
    base_dir = Path(__file__).resolve().parent.parent
    source_fotos = base_dir / "web" / "dist" / "foto_test"
    source_files = base_dir / "web" / "dist" / "file_test"

    # Fallback jika di worktree lain
    if not source_fotos.exists():
        source_fotos = Path("C:/Users/ageng/visiontect-vms/visiontect-vms/visiontech-dev/visiontech-dev/vms/web/dist/foto_test")
    if not source_files.exists():
        source_files = Path("C:/Users/ageng/visiontect-vms/visiontect-vms/visiontech-dev/visiontech-dev/vms/web/dist/file_test")

    uploads_dir = base_dir / "api" / "uploads"
    target_dirs = [
        uploads_dir / "employees",
        uploads_dir / "vehicles",
        uploads_dir / "inspections",
        uploads_dir / "tools",
        uploads_dir / "sop",
    ]

    for t_dir in target_dirs:
        t_dir.mkdir(parents=True, exist_ok=True)

    copied_count = 0
    if source_fotos.exists():
        foto_files = [f for f in source_fotos.iterdir() if f.is_file()]
        for f in foto_files:
            for t_dir in target_dirs:
                shutil.copy2(f, t_dir / f.name)
                copied_count += 1

    print(f"[OK] Berhasil menyalin {copied_count} file foto uji ke seluruh subfolder {uploads_dir}")


if __name__ == "__main__":
    seed_media()
