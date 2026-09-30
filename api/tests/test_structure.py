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

ALLOWED_DIRS = {"api", "core", "models", "schemas", "crud", "services", "templates"}

# folder lama → berkas .py yang masih boleh ada (dikosongkan oleh tahap migrasi di docs/26).
LEGACY_DIRS: dict[str, set[str]] = {
    "controllers": {"__init__.py", "auth_controller.py"},  # M4
    "repositories": {  # M3
        "__init__.py", "asset_reservation_repo.py", "attendance_monitor_repo.py",
        "attendance_session_repo.py", "base_repo.py", "document_repo.py", "employee_repo.py",
        "file_access_repo.py", "monitoring_repo.py", "org_clock_repo.py", "org_ref_repo.py",
        "overtime_repo.py", "plan_access_repo.py", "plan_assignment_repo.py", "plan_attachment_repo.py",
        "plan_change_repo.py", "plan_day_repo.py", "plan_location_repo.py", "plan_member_repo.py",
        "plan_transition_repo.py", "session_repo.py", "signature_repo.py", "sync_repo.py", "unit_repo.py",
        "user_repo.py", "weekly_report_repo.py",
    },
}

# lapisan (folder teratas di app/) → lapisan yang tidak boleh diimpornya.
FORBIDDEN: dict[str, set[str]] = {
    "core": {"api", "services", "crud", "repositories", "controllers"},
    "crud": {"api", "services", "controllers"},
    "repositories": {"api", "services", "controllers"},
    "services": {"api", "controllers"},
    "schemas": {"api", "services", "crud", "repositories", "controllers"},
    "api": {"crud", "repositories"},
}
# `api/deps.py` adalah tempat perakitan dependency; boleh mengimpor apa saja.
EXEMPT_FILES = {"api/deps.py"}

# "berkas -> lapisan terlarang yang diimpor"; hanya boleh menyusut.
# api -> repositories: perakitan service pindah ke api/deps.py (M5).
# services -> api: `guards` pindah (M2), `CurrentUser` ke core/security.py (M5).
KNOWN_VIOLATIONS: set[str] = {
    "api/accounts.py -> repositories",
    "api/attendance.py -> repositories",
    "api/attendance_cron.py -> repositories",
    "api/documents.py -> repositories",
    "api/expiry.py -> repositories",
    "api/guards.py -> repositories",
    "api/hse.py -> repositories",
    "api/plan_members.py -> repositories",
    "api/plan_transitions.py -> repositories",
    "api/plans.py -> repositories",
    "api/units.py -> repositories",
    "services/asset_reservation_service.py -> api",
    "services/monitoring_service.py -> api",
    "services/overtime_service.py -> api",
    "services/plan_assignment_service.py -> api",
    "services/plan_attachment_service.py -> api",
    "services/plan_change_service.py -> api",
    "services/plan_day_service.py -> api",
    "services/plan_location_service.py -> api",
    "services/plan_member_service.py -> api",
    "services/signature_service.py -> api",
    "services/sync_service.py -> api",
    "services/weekly_report_service.py -> api",
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
