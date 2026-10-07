# Aturan tetap untuk Gemini (dibaca otomatis setiap sesi)

Proyek: VMS — FastAPI (`api/`), React/Vite/shadcn (`web/`), Flutter (`mobile/`). Aturan lengkap:
`CLAUDE.md`. Peta kode singkat: `docs/PETA-KODE.md` — baca itu, jangan menjelajah seluruh repo.

## Peran
- **Gemini A = WEB**: hanya `web/` (+ `docs/14` bila menambah pustaka).
- **Gemini B = API**: hanya `api/app/` untuk membuat **uji-spesifikasi** di `api/tests/` lulus.
  Isi berkas uji TIDAK boleh diubah. Aturan bisnis: `prototype/js/domain.js` (cari dengan grep nama transaksinya).
- Jangan menyentuh `db/`, `prototype/`, `docs/10`, `docs/PLAN-*`, atau bagian yang bukan peran Anda.

## Git — WAJIB
- Kerja di **worktree terpisah**: `git worktree add ../vms-<nama> -b feature/gemini-<tugas> origin/development`.
- **DILARANG merge atau push ke `development`.** Push branch fitur saja; Claude yang memverifikasi & merge.
- **DILARANG `git stash`** (tumpukan stash dipakai bersama semua worktree).
- Stage per path, jangan `git add -A`. Jangan commit `migrate_baca.py`, `test_db.py`, `.env`.
- **CHANGELOG.md**: sisipkan entri dengan editor. **JANGAN** `Get-Content`/`Set-Content`/`>` PowerShell —
  itu merusak penyandian (pernah 125 baris rusak). Cek: `git diff --stat CHANGELOG.md` = beberapa baris saja.
- Berkas JSON/teks yang dibuat skrip: tulis dari Python dengan `encoding="utf-8"` (PowerShell 5.1 `>` = UTF-16).

## Kode
- Web: TypeScript strict; **dilarang** `any`, `@ts-ignore`, `eslint-disable`, `alert/confirm/prompt`; shadcn/ui;
  TanStack Query; 4 keadaan (memuat/kosong/galat/berhasil); sentuh ≥ 44px; input 16px. Kontrak = `web/openapi.json`.
- API: router tipis → `services/` (nama fungsi = transaksi domain.js) → `crud/crud_<entitas>.py` (SQL statis, bukan
  f-string, `CAST(:x AS tipe)` bukan `:x::tipe`); galat `AppError` berbahasa Indonesia. Skema baru `<Entitas>In/Out`
  (`docs/12` §10); `ruff check app tests` wajib bersih (set aturan di `api/ruff.toml`, baris ≤ 120).

## Bila ragu
- **Tanyakan, jangan menebak.** Spesifikasi ambigu atau ada dua pilihan masuk akal → berhenti dan tulis pertanyaannya
  di baris CATATAN laporan. Jangan mengisi celah dengan asumsi (`docs/12` §12).

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
