"""
V-14 · Tidak ada kode mati di lapisan servis & repositori. Setiap berkas di
`app/modules/*/services/`, `app/modules/*/repositories/`, dan `app/shared/` harus terjangkau dari aplikasi
(`app.main`). Kode yang tidak pernah dijalankan tidak pernah diuji — di proyek ini kode seperti itu
terbukti tidak cocok dengan skema (E9).

Diperiksa di proses Python terpisah: di dalam suite, uji lain bisa sudah mengimpor modul secara
langsung sehingga modul mati tampak "terpakai".
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

_PROBE = "import json, sys; import app.main; print(json.dumps(sorted(m for m in sys.modules if m.startswith('app.'))))"


def test_every_service_and_crud_is_used_by_the_app():
    loaded = set(json.loads(subprocess.run(
        [sys.executable, "-c", _PROBE], capture_output=True, text=True, check=True, cwd=Path.cwd(),
    ).stdout.strip().splitlines()[-1]))
    paths = [
        *Path("app", "modules").glob("*/services/*.py"),
        *Path("app", "modules").glob("*/repositories/*.py"),
        *Path("app", "shared").rglob("*.py"),
    ]
    modules = [".".join(p.with_suffix("").parts) for p in sorted(paths) if p.stem != "__init__"]
    assert modules, "inventaris kosong"
    assert [m for m in modules if m not in loaded] == []
