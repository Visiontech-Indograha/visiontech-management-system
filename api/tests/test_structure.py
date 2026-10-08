"""
R-28 M0 · Penjaga struktur folder `app/` (docs/12 §1, rencana docs/26).

Pemeriksaan statis (AST, tanpa DB):
- folder di bawah `app/` hanya yang ada di `ALLOWED_DIRS`; folder lama di `LEGACY_DIRS` masih boleh ada
  selama migrasi, tetapi TIDAK boleh bertambah berkas;
- arah impor antarlapisan (`FORBIDDEN`): pelanggaran yang sudah ada tercatat di `KNOWN_VIOLATIONS`.

`LEGACY_DIRS` dan `KNOWN_VIOLATIONS` hanya boleh MENYUSUT: pelanggaran baru langsung merah, dan entri
yang sudah bersih juga merah (hapus barisnya).
"""
from __future__ import annotations

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"

# Persis contoh pemilik (docs/12 §1, R-28/R-30) + `templates/` (Jinja2 PDF).
ALLOWED_DIRS = {"api", "core", "crud", "models", "schemas", "services", "db", "templates"}
# Berkas di akar app/: main.py (contoh pemilik) + cli.py (seed/create-admin). Tidak ada dependencies.py.
ALLOWED_ROOT_FILES = {"main.py", "cli.py"}

# folder lama → berkas .py yang masih boleh ada (dikosongkan oleh tahap migrasi di docs/26).
LEGACY_DIRS: dict[str, set[str]] = {}  # kosong sejak M4: db/, repositories/, controllers/ sudah dipindah

# lapisan (folder teratas di app/) → lapisan yang tidak boleh diimpornya.
FORBIDDEN: dict[str, set[str]] = {
    "core": {"api", "services", "crud"},
    "db": {"api", "services", "crud"},
    "crud": {"api", "services"},
    "services": {"api"},
    "schemas": {"api", "services", "crud"},
    "api": {"crud"},
}
# `api/deps.py` adalah tempat perakitan dependency; boleh mengimpor apa saja.
EXEMPT_FILES = {"api/deps.py"}

# "berkas -> lapisan terlarang yang diimpor"; hanya boleh menyusut.
# endpoint -> crud: SQL/crud keluar dari endpoint per modul (docs/26 M6).
KNOWN_VIOLATIONS: set[str] = {
    "api/v1/endpoints/work_plans.py -> crud",
}


def _layer_of_module(module: str) -> str | None:
    parts = module.split(".")
    return parts[1] if len(parts) > 1 and parts[0] == "app" else None


def _imports(path: Path) -> set[str]:
    rel_pkg = path.relative_to(APP_DIR.parent).with_suffix("").parts[:-1]
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                base = list(rel_pkg[: len(rel_pkg) - node.level + 1])
                found.add(".".join(base + ([node.module] if node.module else [])))
            elif node.module:
                found.add(node.module)
    return found


def _violations() -> set[str]:
    out: set[str] = set()
    for path in APP_DIR.rglob("*.py"):
        rel = path.relative_to(APP_DIR).as_posix()
        layer = rel.split("/")[0]
        if rel in EXEMPT_FILES or layer not in FORBIDDEN:
            continue
        for module in _imports(path):
            target = _layer_of_module(module)
            if target in FORBIDDEN[layer]:
                out.add(f"{rel} -> {target}")
    return out


def _dirs() -> set[str]:
    return {p.name for p in APP_DIR.iterdir() if p.is_dir() and p.name != "__pycache__"}


def test_only_allowed_folders_under_app():
    unknown = _dirs() - ALLOWED_DIRS - set(LEGACY_DIRS)
    assert not unknown, f"Folder di luar struktur wajib (docs/12 §1): {sorted(unknown)}"


def test_only_allowed_files_at_app_root():
    extra = {p.name for p in APP_DIR.glob("*.py")} - ALLOWED_ROOT_FILES
    assert not extra, f"Berkas di akar app/ di luar struktur wajib (docs/12 §1): {sorted(extra)}"


def test_legacy_folders_do_not_grow():
    grown = {}
    for name, allowed in LEGACY_DIRS.items():
        folder = APP_DIR / name
        if folder.is_dir():
            extra = {p.name for p in folder.glob("*.py")} - allowed
            if extra:
                grown[name] = sorted(extra)
    assert not grown, f"Berkas baru di folder LEGACY — taruh di struktur baru (docs/12 §1): {grown}"


def test_legacy_list_only_shrinks():
    stale = {}
    for name, allowed in LEGACY_DIRS.items():
        present = {p.name for p in (APP_DIR / name).glob("*.py")} if (APP_DIR / name).is_dir() else set()
        if allowed - present:
            stale[name] = sorted(allowed - present)
    assert not stale, f"Sudah dipindah — hapus dari LEGACY_DIRS: {stale}"


def test_no_new_forbidden_imports():
    new = sorted(_violations() - KNOWN_VIOLATIONS)
    assert not new, "Arah impor antarlapisan dilanggar (docs/12 §1):\n  " + "\n  ".join(new)


def test_known_violations_only_shrink():
    fixed = sorted(KNOWN_VIOLATIONS - _violations())
    assert not fixed, f"Sudah bersih — hapus dari KNOWN_VIOLATIONS: {fixed}"
