# Aturan tetap untuk Gemini (dibaca otomatis setiap sesi)

Proyek: VMS — FastAPI (`api/`), React/Vite/shadcn (`web/`), Flutter (`mobile/`). Aturan lengkap:
`CLAUDE.md`. Peta kode singkat: `docs/PETA-KODE.md` — baca itu, jangan menjelajah seluruh repo.

## Peran
- **Gemini A = WEB**: hanya `web/` (+ `docs/14` bila menambah pustaka).
- **Gemini B = API**: hanya `api/app/` untuk membuat **uji-spesifikasi** di `api/tests/` lulus.
  Isi berkas uji TIDAK boleh diubah. Aturan bisnis: `prototype/js/domain.js` (cari dengan grep nama transaksinya).
- Jangan menyentuh `prototype/`, `docs/10`, `docs/PLAN-*`, atau bagian yang bukan peran Anda.
  **ATURAN SINKRONISASI SKEMA (DUAL-SCHEMA RULE):** Jika membuat migrasi DDL baru di `api/alembic/versions/`, tabel/kolom/indeks/RLS yang bersangkutan **WAJIB** disinkronkan ke `db/01_schema.sql` dan `db/03_policies.sql` / `db/05_face.sql`. CI GitHub Actions tidak menjalankan `alembic upgrade head`, melainkan memasang dari `db/*.sql` lalu menjalankan `alembic stamp head`.

## Git — WAJIB
- **ATURAN GLOBAL AGEN AI (DILARANG MERGE KE PROD):**
  - **DILARANG KERAS merge, commit, atau push langsung ke `prod` / `main`.**
  - Penggabungan ke `prod` sepenuhnya hak pemilik produk (manusia) melalui PR `development` → `prod`.
  - Agen AI diizinkan merge atau push ke `development` jika tugas telah terverifikasi dan lulus uji.
- **ATURAN IDENTITAS COMMIT & DOKUMENTASI AGENT (WAJIB):**
  - **DILARANG KERAS** menyertakan Gemini, Claude, AI, bot, atau asisten apa pun sebagai co-author (`Co-authored-by`), collaborator, atau kontributor dalam pesan commit maupun metadata git.
  - Semua commit harus bersih dari jejak/trailer atribusi AI (hanya author manusia sesuai konfigurasi git).
  - **DILARANG KERAS** meng-commit atau push berkas/folder internal agen AI (seperti `.agents/`, `.hermes/`, `.claude/`, `.gemini/`, `.cursor/`, `.windsurf/`, file scratch agent, dsb.) ke repositori GitHub. Pastikan folder tersebut masuk `.gitignore`.
- Kerja di **worktree terpisah**: `git worktree add ../vms-<nama> -b feature/gemini-<tugas> origin/development`.
- **DILARANG `git stash`** (tumpukan stash dipakai bersama semua worktree).
- Stage per path, jangan `git add -A`. Jangan commit `migrate_baca.py`, `test_db.py`, `.env`.
- **CHANGELOG.md**: sisipkan entri dengan editor. **JANGAN** `Get-Content`/`Set-Content`/`>` PowerShell —
  itu merusak penyandian (pernah 125 baris rusak). Cek: `git diff --stat CHANGELOG.md` = beberapa baris saja.
- Berkas JSON/teks yang dibuat skrip: tulis dari Python dengan `encoding="utf-8"` (PowerShell 5.1 `>` = UTF-16).

## Kode
- Web: TypeScript strict; **dilarang** `any`, `@ts-ignore`, `eslint-disable`, `alert/confirm/prompt`; shadcn/ui;
  TanStack Query; 4 keadaan (memuat/kosong/galat/berhasil); sentuh ≥ 44px; input 16px. Kontrak = `web/openapi.json`.
- API: router tipis → `services/` (nama fungsi = transaksi domain.js) → `repositories/` (SQL statis, bukan
  f-string, `CAST(:x AS tipe)` bukan `:x::tipe`); galat `AppError` berbahasa Indonesia.

## Bukti selesai (jalankan dari SALINAN BERSIH, bukan disk kerja)
- Web: `git archive <branch> web | tar -x -C <folder-kosong>` → `npm ci`, `npm run lint`, `npm run typecheck`, `npm test`.
- API: `cd api && PYTHONPATH=. .venv\Scripts\python -m pytest -q tests/<berkas-uji>.py` + `ruff check app tests` + `mypy`.

## Laporan — HANYA format ini (3 baris, tanpa penjelasan panjang)
```
BRANCH: <nama>   COMMIT: <hash>
BUKTI: <npm ci/lint/typecheck = exit code; test = n lulus/n total>  ATAU  <pytest n lulus; ruff exit; mypy exit>
CATATAN: <maks. 1 kalimat, hanya bila ada yang perlu diputuskan>
```
Laporan yang tidak cocok dengan isi branch akan ditolak.
