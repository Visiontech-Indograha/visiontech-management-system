"""
Penjaga struktur modular `app/` (docs/12 §1, docs/26).

Pemeriksaan statis (AST, tanpa DB):
- folder di bawah `app/` hanya `ALLOWED_DIRS`; folder lama (services/, crud/, schemas/, db/, templates/,
  api/v1/endpoints/) tidak boleh muncul lagi;
- setiap modul `app/modules/<m>/` hanya berisi lapisan `MODULE_LAYERS` (+ `dependencies.py`);
- arah impor:
  * `core`, `database`, `shared` tidak mengimpor `app.modules` maupun `app.api`;
  * `routes` tidak menyentuh `sqlalchemy` atau `repositories`;
  * `controllers` tidak menyentuh `repositories` atau `sqlalchemy` (kecuali tipe sesi);
  * `services` & `repositories` tidak mengimpor `app.api`, `controllers`, `routes`, dan tidak `raise HTTPException`
    (pakai `app.core.errors`);
  * antarmodul hanya lewat `services`/`schemas`/`dependencies` modul lain — tidak ke `repositories`,
    `controllers`, atau `routes` modul lain (`dependencies.py` = titik perakitan, boleh).

`KNOWN_VIOLATIONS` hanya boleh MENYUSUT: pelanggaran baru langsung merah, dan entri yang sudah bersih
juga merah (hapus barisnya).
"""
from __future__ import annotations

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[2] / "app"

ALLOWED_DIRS = {"api", "core", "database", "shared", "modules"}
ALLOWED_ROOT_FILES = {"main.py", "cli.py"}
ALLOWED_API_ITEMS = {"__init__.py", "deps.py", "v1"}
ALLOWED_API_V1_ITEMS = {"__init__.py", "router.py"}
MODULE_LAYERS = {"routes", "controllers", "services", "repositories", "schemas"}
MODULE_FILES = {"__init__.py", "dependencies.py"}

# "berkas -> pelanggaran"; hanya boleh menyusut. Butuh API service di modul pemilik (lihat docs/26).
KNOWN_VIOLATIONS: set[str] = {
    "modules/accounts/services/account_service.py -> app.modules.auth.repositories.auth_session_repository",
    "modules/accounts/services/account_service.py -> app.modules.auth.repositories.auth_user_repository",
    "modules/accounts/services/account_service.py -> app.modules.employees.repositories.employee_repository",
    "modules/work_plans/services/plan_amendment_service.py -> app.modules.assets.repositories.asset_repository",
    "modules/work_plans/services/plan_draft_service.py -> app.modules.assets.repositories.asset_repository",
    "modules/work_plans/services/plan_transition_service.py"
    " -> app.modules.reports.repositories.weekly_report_repository",
}


def _py_files() -> list[Path]:
    return [p for p in APP_DIR.rglob("*.py") if "__pycache__" not in p.parts]


def _imports(path: Path) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            found.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            found.add(node.module)
    return found


def _raises_http_exception(path: Path) -> bool:
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Raise) and node.exc is not None:
            target = node.exc.func if isinstance(node.exc, ast.Call) else node.exc
            if isinstance(target, ast.Name) and target.id == "HTTPException":
                return True
    return False


def _violations() -> set[str]:
    out: set[str] = set()
    for path in _py_files():
        rel = path.relative_to(APP_DIR).as_posix()
        parts = rel.split("/")
        imports = _imports(path)

        if parts[0] in ("core", "database", "shared"):
            out |= {f"{rel} -> {m}" for m in imports if m.startswith(("app.modules", "app.api"))}
            continue
        if parts[0] != "modules" or len(parts) < 3:
            continue

        module, layer = parts[1], parts[2]
        for m in imports:
            seg = m.split(".")
            if (
                seg[:2] == ["app", "modules"]
                and len(seg) > 3
                and seg[2] != module
                and seg[3] in ("repositories", "controllers", "routes")
                and layer != "dependencies.py"
            ):
                out.add(f"{rel} -> {m}")
        if layer == "routes":
            out |= {f"{rel} -> {m}" for m in imports if m.startswith("sqlalchemy") or ".repositories" in m}
        elif layer == "controllers":
            out |= {f"{rel} -> {m}" for m in imports if ".repositories" in m or m == "sqlalchemy"}
        elif layer in ("services", "repositories"):
            out |= {
                f"{rel} -> {m}"
                for m in imports
                if m.startswith("app.api") or ".controllers" in m or ".routes" in m
            }
            if _raises_http_exception(path):
                out.add(f"{rel} raise HTTPException")
    return out


def _children(folder: Path) -> set[str]:
    return {p.name for p in folder.iterdir() if p.name != "__pycache__"}


def test_only_allowed_folders_under_app() -> None:
    dirs = {p.name for p in APP_DIR.iterdir() if p.is_dir() and p.name != "__pycache__"}
    assert dirs <= ALLOWED_DIRS, f"Folder di luar struktur modular (docs/12 §1): {sorted(dirs - ALLOWED_DIRS)}"


def test_only_allowed_files_at_app_root() -> None:
    extra = {p.name for p in APP_DIR.glob("*.py")} - ALLOWED_ROOT_FILES
    assert not extra, f"Berkas di akar app/ di luar struktur wajib (docs/12 §1): {sorted(extra)}"


def test_api_package_holds_only_router_and_cross_cutting_deps() -> None:
    assert _children(APP_DIR / "api") <= ALLOWED_API_ITEMS, sorted(_children(APP_DIR / "api") - ALLOWED_API_ITEMS)
    v1 = _children(APP_DIR / "api" / "v1")
    assert v1 <= ALLOWED_API_V1_ITEMS, f"Endpoint ditulis di modul, bukan api/v1: {sorted(v1 - ALLOWED_API_V1_ITEMS)}"


def test_modules_only_contain_standard_layers() -> None:
    bad = {}
    for module in (APP_DIR / "modules").iterdir():
        if not module.is_dir() or module.name == "__pycache__":
            continue
        extra = _children(module) - MODULE_LAYERS - MODULE_FILES
        if extra:
            bad[module.name] = sorted(extra)
    assert not bad, f"Isi modul di luar lapisan standar {sorted(MODULE_LAYERS)}: {bad}"


def test_no_new_forbidden_imports() -> None:
    new = sorted(_violations() - KNOWN_VIOLATIONS)
    assert not new, "Batas modul/lapisan dilanggar (docs/12 §1):\n  " + "\n  ".join(new)


def test_known_violations_only_shrink() -> None:
    fixed = sorted(KNOWN_VIOLATIONS - _violations())
    assert not fixed, f"Sudah bersih — hapus dari KNOWN_VIOLATIONS: {fixed}"


# ── Struktur tes mengikuti struktur aplikasi ────────────────────────────────────────────────────
TESTS_DIR = APP_DIR.parent / "tests"
TEST_GROUPS = {"architecture", "core", "shared", "integration", "modules"}


def test_tests_live_in_groups_not_at_root() -> None:
    loose = sorted(p.name for p in TESTS_DIR.glob("test_*.py"))
    assert not loose, f"Taruh uji di tests/{{{','.join(sorted(TEST_GROUPS))}}}/ — bukan di akar: {loose}"
    groups = {p.name for p in TESTS_DIR.iterdir() if p.is_dir() and (p / "__init__.py").exists()}
    assert groups <= TEST_GROUPS, f"Kelompok uji tak dikenal: {sorted(groups - TEST_GROUPS)}"


def test_module_tests_mirror_app_modules() -> None:
    app_modules = {p.name for p in (APP_DIR / "modules").iterdir() if p.is_dir() and p.name != "__pycache__"}
    test_modules = {
        p.name for p in (TESTS_DIR / "modules").iterdir() if p.is_dir() and p.name != "__pycache__"
    }
    orphan = sorted(test_modules - app_modules)
    assert not orphan, f"tests/modules/ tanpa pasangan di app/modules/: {orphan}"
