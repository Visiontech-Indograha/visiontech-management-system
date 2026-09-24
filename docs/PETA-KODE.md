# Peta kode (satu halaman — baca ini sebelum menjelajah)

Untuk agen AI & developer: letak hal-hal penting, supaya tidak perlu memindai seluruh repo.

## API (`api/`) — router tipis → services → repositories
| Kebutuhan | Letak |
|---|---|
| Otorisasi SK (ketua/anggota/PM unit, 404 vs 403) | `app/api/guards.py` — `plan_access(need)`, `plan_day_access`, `allocation_plan_access`, `incident_plan_access`, `check_plan_access`, `require_plan_status`, `ensure_same_org`, `check_file_access`, `check_unit_manager` |
| Siapa melihat SK apa (satu kueri) | `app/repositories/plan_access_repo.py` (`_STANDING`) |
| Transisi SK: terbit, terima, mulai, banding, revisi, batal, arsip, pulihkan | `services/plan_transition_service.py` + `repositories/plan_transition_repo.py`, rute `api/plan_transitions.py` |
| Adendum perpanjangan/personel | `services/plan_change_service.py` + `repositories/plan_change_repo.py`, rute `api/plan_changes.py` |
| Susunan tim draf | `services/plan_member_service.py` + `repositories/plan_member_repo.py` |
| Absensi | `services/attendance_session_service.py` + `repositories/attendance_session_repo.py` |
| Jam/tanggal organisasi | `repositories/org_clock_repo.py` (jangan `datetime.now()` — hanya `core/time.py`) |
| Galat & pesan trigger DB | `core/errors.py` (`AppError`, `trigger_rule_error`) |
| Izin per peran | `core/permissions.py` · enum DB: `core/enums.py` |
| Rute lama (masih SQL di router, direfaktor bertahap) | `api/hse.py`, `api/assets.py`, `api/plans.py`, `api/employees.py`, `api/documents.py` |

Jalur: `/api/v1/work-plans/...`, `/api/v1/changes/{id}/...` (dok 05). Migrasi: `api/alembic/versions/000N_*.py` + `db/0*.sql` disamakan.

## Uji (`api/tests/`) — PostgreSQL sungguhan
| Pembantu | Letak |
|---|---|
| Organisasi uji lengkap (8 peran) | fixture `world` / `other_world` (`conftest.py`); `world.add_person`, `world.add_unit`, `world.headers(client, "pm")` |
| SK siap pakai | `test_flow_plans.py`: `create_draft_plan`, `run_plan_to_accepted`, `run_plan_to_in_progress` |
| Kueri langsung | `sync_query(sql, params)`; berkas palsu: fixture `fake_storage` |
| Penjaga otomatis | `test_route_guards.py` (setiap rute berizin), `test_sql_matches_schema.py` (SQL vs skema), `test_no_dead_modules.py` |

Perintah: `cd api && PYTHONPATH=. .venv\Scripts\python -m pytest -q tests/<berkas>.py` · `ruff check app tests` · `mypy`.

## Web (`web/`)
Kontrak API: `web/openapi.json` (jangan dibaca utuh — grep nama jalur). Komponen dasar `src/components/ui/`,
bersama `src/components/molecules/` (mis. `FilePreview`). Fitur per folder `src/features/<modul>/`.
Perintah: `npm run lint` · `npm run typecheck` · `npm test`.

## Aturan bisnis
`prototype/js/domain.js` — sumber kebenaran. Cari dengan `grep -n "case 'NAMA_TRANSAKSI'"`; jangan baca utuh.
Rencana kerja aktif: `docs/PLAN-VERIFIKASI-MODUL-RINCI.md` (W6 = transaksi yang belum ada).

## Verifikasi branch (Claude)
`bash scripts/verify-branch.sh <branch> web|api [uji...]` → satu baris LULUS/GAGAL dari salinan bersih.
