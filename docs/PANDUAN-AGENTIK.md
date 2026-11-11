# Panduan agentik VMS

Versi: 0.1 - 2026-11-04 - cabang `docs/skills-agentik`
Lingkup: repo VMS lama (`vms-master-local`, produksi v1.5.0) dan kerja agen Claude di dalamnya.

Sumber fakta dalam panduan ini ditulis di dalam kurung siku, misalnya [sumber: `.github/workflows/ci.yml`]. Angka yang belum diukur ditulis BELUM DIUKUR. Tautan resmi di bagian 14 belum dibuka pada saat panduan ini ditulis.

---

## 0. Ringkasan satu halaman

**Apa ini.** VMS dibangun oleh satu tim kecil dengan agen Claude. Pemilik (klien) memutuskan prioritas dan menyetujui. Arsitek (sesi utama Claude) merancang, memecah tugas, dan meninjau. Engineer per lapisan (web, mobile, api, db, devops) mengerjakan brief di worktree terpisah. QA menguji sebagai orang awam. Tidak ada yang merge ke `beta` atau `prod` selain pemilik.

**Tiga aturan yang tidak boleh dilanggar.**
1. Merge ke `prod` = deploy produksi dalam ±1 menit. Server menarik `origin/prod` tiap menit [sumber: `deploy/autodeploy.sh`, `deploy/README.md`].
2. Tes database hanya atas perintah pemilik, dan hanya di `vms_test` (127.0.0.1:55432). DB dev (55433) tidak disentuh [sumber: `CLAUDE.md`, brief pengguna].
3. Commit tanpa trailer AI; stage per path; tanpa `git add -A` dan tanpa `git stash` bersama [sumber: memori pengguna "Commit VMS", aturan worktree].

**Alur satu fitur.**
```
brief (arsitek) -> desain/ADR (bila perlu) -> engineer di worktree -> tinjau (arsitek)
   -> QA di beta -> PR beta->prod (CI) -> persetujuan pemilik -> deploy otomatis -> pantau Discord
```

**Yang sudah ada di repo ini.** CI (5 workflow), skrip deploy dan cadangan, pre-commit, skrip versi, dan kebijakan aturan proyek di `CLAUDE.md` (lokal). Skill proses dan sub-agen ditambahkan oleh cabang ini.

**Yang belum ada (perlu keputusan atau pekerjaan).** `web/CLAUDE.md`, `mobile/CLAUDE.md`, `api/CLAUDE.md`, `db/CLAUDE.md` belum ada. Enam skill lapisan (`vms-web`, `vms-mobile`, `vms-ux-design-system`, `vms-api`, `vms-db`, `vms-storage-minio`) sudah ada di worktree, ditulis agen lain dan belum ditinjau di panduan ini. `CLAUDE.md` tetap diabaikan Git. Worktree ini juga sudah mengubah `.gitignore` agar `.claude/skills/` dan `.claude/agents/` dibagikan lewat Git; perubahan itu dibuat agen lain, bukan oleh panduan ini, dan perlu keputusan pemilik (lihat bagian 3.2).

**Tiga risiko teratas (dari audit yang sudah tercatat).**
1. Rahasia ikut masuk image Docker: `api/.env` ikut ter-copy, dan tidak ada `api/.dockerignore` [sumber: riset `01` F-01; dicek ulang: berkas `.dockerignore` tidak ada di `api/`].
2. Kebocoran data lintas divisi pada beberapa endpoint GET [sumber: `vms-next/docs/08`, bagian Usulan tenggat].
3. Endpoint mutasi tanpa `Idempotency-Key` (189 mutasi) dan transisi status tanpa compare-and-set [sumber: riset `01` F-03, F-12].

**Keputusan yang menunggu pemilik.** Lihat bagian 13 (daftar keputusan) dan `vms-architect` bagian 6.

---

## 1. Peran dan tanggung jawab

| Peran | Siapa | Boleh | Tidak boleh |
|---|---|---|---|
| Klien / pemilik | pengguna (pemilik software house) | memutuskan prioritas, menyetujui merge ke `beta` dan `prod`, memberi perintah tes DB, menyetujui perubahan aturan bisnis | - |
| Arsitek | sesi utama Claude (`vms-architect`, sub-agen `architect`) | merancang, memecah tugas, menulis brief dan ADR, meninjau PR, mengatur urutan rilis, menentukan standar teknis | mengubah aturan bisnis; merge ke `beta`/`prod`; menjalankan tes DB tanpa perintah |
| QA | sub-agen `qa` (`vms-qa`) | uji nyata per peran, audit kebocoran GET-only, uji HP dan web, laporan | mengubah kode aplikasi; menyatakan lulus tanpa bukti; POST saat audit |
| Engineer web | `web-engineer` (`vms-web`, `vms-ux-design-system`) | mengerjakan brief di `web/` | merge; mengedit tipe generator tangan |
| Engineer mobile | `mobile-engineer` (`vms-mobile`) | mengerjakan brief di `mobile/`; uji APK di emulator/HP uji | menyentuh keystore; memasang ke aplikasi produksi HP pengguna |
| Engineer API | `api-engineer` (`vms-api`, `vms-db`, `vms-storage-minio`) | route, service, repository, skema, OpenAPI | `LIKE '%...'`; pengecualian baru di `test_sql_rules.py` |
| Engineer DB | `db-engineer` (`vms-db`) | skema, indeks, migrasi | menjalankan skrip seed di produksi |
| Engineer DevOps | `devops-engineer` (`vms-cicd-versioning`) | workflow, skrip deploy, cadangan, APK | mematikan workflow demi lolos; menjalankan `docker compose`/`ssh` ke produksi tanpa perintah |

Peran pengguna di aplikasi (bukan peran agen): SUPER_ADMIN, OM, PM, TEAM_LEADER (ketua), HR (ADMIN_HR_GA), FINANCE, EMPLOYEE, dan "field" (akun tanpa baris peran) [sumber: `vms-next/docs/sumber-lama/diagram_00-peran-dan-izin.md`]. Peran legacy (ADMIN, OPS, LEADER, MEMBER, ASSET) hanya ada di VMS lama.

---

## 2. Siklus kerja

```
[1 Brief] -> [2 Desain/ADR] -> [3 Implementasi] -> [4 Tinjau] -> [5 QA] -> [6 Rilis]
    ^                                                  |
    +-------------- perbaikan lewat brief baru ---------+
```

### 2.1 Brief (arsitek -> engineer)

Brief adalah satu-satunya cara memberi tugas. Brief yang tidak lengkap dikembalikan.

```
# Brief: <judul singkat>
Lapisan: web | mobile | api | db | devops
Cabang: feature/<nama> (dari development), worktree terisolasi
Tujuan (1-2 kalimat, bahasa awam): ...
Konteks: ADR <n> / docs <n> / CHANGELOG <versi>
Boleh disentuh: <daftar berkas/folder>
Tidak boleh disentuh: <daftar>
Perilaku yang diharapkan (contoh nyata): ...
Tes yang harus lulus:
  - bash scripts/verify-branch.sh <cabang> web|api  -> LULUS
  - tes baru: <nama> (tulis dulu, lalu implementasi)
Tes DB: hanya bila pemilik memerintahkan (vms_test 127.0.0.1:55432)
Larangan: commit tanpa trailer AI; stage per path; tanpa merge ke beta/prod; tanpa rahasia
Laporan balik: format di .claude/agents/<peran>.md
```

### 2.2 Desain dan ADR

Buat ADR bila keputusan lintas lapisan, mengubah standar kerja, memilih teknologi baru, atau sulit dibalik. Format di bawah. ADR berstatus `Usulan` sampai pemilik menyetujui.

```
# ADR <nomor>: <judul keputusan>
Status: Usulan | Diterima | Ditolak | Diganti oleh ADR <n>
Tanggal: YYYY-MM-DD
Konteks: masalah dan batasan (server 4 GB, tenggat, data).
Pilihan yang dipertimbangkan:
  A. ... (kelebihan / kekurangan)
  B. ...
Keputusan: pilihan dan alasan.
Konsekuensi: perubahan, biaya, risiko, uji yang diperlukan.
Keputusan pemilik: (tanggal + ringkasan, bila ada)
Sumber: berkas atau tautan.
```

Contoh ADR yang sudah ada (VMS Next, repo lain): `vms-next/docs/adr/0001-keputusan-awal.md`, `0002-jawaban-pemilik-dan-mekanisme-rilis.md`, `0003-referensi-best-practice.md`.

### 2.3 Implementasi (engineer)

Engineer bekerja di worktree sendiri. Urutan yang diminta [sumber: `vms-next/docs/07`, cara kerja per fase]:
1. baca dokumen terkait; tulis rencana singkat (berkas, tes, risiko);
2. tulis tes (kontrak/perilaku) lebih dulu, lalu implementasi;
3. jalankan gerbang lapisan (lihat bagian 6.3);
4. perbarui OpenAPI dan tipe klien, CHANGELOG, dan dokumen bila keputusan berubah;
5. satu PR per fase kecil; jangan menggabung fase.

### 2.4 Tinjau (arsitek)

Gunakan daftar tinjau di `.claude/skills/vms-architect/SKILL.md` bagian 3. Hasil: SETUJU, PERBAIKI (brief baru), atau TOLAK (alasan tertulis).

### 2.5 Format PR

Isi PR mengikuti `.github/pull_request_template.md` [sumber: berkas itu]:

```
## Ringkasan
<apa yang berubah dan kenapa, 1-3 kalimat>

## Keputusan pemilik / pertanyaan terbuka
<keputusan yang dipakai, atau pertanyaan yang belum dijawab>

## Bukti
<perintah yang dijalankan + hasil (n lulus); tangkapan layar uji nyata web/HP>

## Checklist
- [ ] Lint & tipe bersih (ruff/mypy · eslint/tsc · flutter analyze)
- [ ] Uji hijau (pytest dengan DB nyata bila diperintahkan · npm test · flutter test)
- [ ] OpenAPI / migrasi / db/*.sql disamakan (bila berubah)
- [ ] Rute publik/izin baru beralasan
- [ ] Tidak ada rahasia
- [ ] Langkah server/APK untuk pemilik ditulis (bila ada)
```

Judul PR: pola `tipe(lapisan): ringkasan`, mengikuti riwayat repo (`fix(db): ...`, `feat(web): ...`). Commit tanpa trailer.

### 2.6 Rencana uji (QA)

```
Fitur: <nama> (PR #<n>, cabang beta, versi <X.Y.Z>)
Tujuan uji: <peran> dapat <tujuan> tanpa bantuan; <peran lain> tidak melihat data divisi lain.
Lingkungan: web localhost:5173 | API 127.0.0.1:8000 | APK beta di emulator/HP uji
Akun: <peran> = akun dari daftar akun uji lokal (sandi tidak ditulis di laporan)
Skenario (prioritas):
  S1 (P1) alur bahagia peran utama
  S2 (P1) peran yang tidak berhak -> 403 atau tidak terlihat (404)
  S3 (P2) galat input -> pesan Bahasa Indonesia, penanda di kolom yang salah (422)
  S4 (P2) lima kondisi layar: kosong, galat jaringan, sebagian
  S5 (P3) mode gelap, fokus keyboard
  S6 (P1, HP) offline lalu sinkron, tanpa duplikat
Kriteria lulus: S1-S3 dan S6 lulus; tidak ada P1 terbuka.
Kriteria tahan rilis: ada P1 terbuka, atau kebocoran lintas divisi.
```

Contoh lengkap ada di `.claude/skills/vms-qa/references/rencana-uji.md`.

Uji kegunaan (usability testing, pengguna awam per peran) diatur di `.claude/skills/vms-qa/references/uji-kegunaan.md`; wajib sebelum rilis MINOR/MAJOR yang menyentuh layar.

### 2.7 Laporan QA

```
Laporan QA - beta <X.Y.Z>, <tanggal>, penguji: QA
Ringkasan: lulus X, gagal Y, dilewati Z
Rekomendasi: LANJUT | TAHAN (alasan)

P1 (wajib sebelum rilis)
  QA-<area>-<nomor> | <peran> | <langkah ringkas> | harapan: ... | hasil nyata: ... | bukti: <path> | BARU
P2 ...
P3 ...
Belum diuji dan alasannya: ...
```

Laporan tanpa data pribadi nyata. Format lengkap di `vms-qa` bagian 8.

### 2.8 Catatan rilis

```
Versi: X.Y.Z (MAJOR | MINOR | PATCH, alasan)
Tanggal:
Untuk pengguna (Bahasa Indonesia sederhana): ...
Perubahan teknis: PR #...
Langkah untuk pemilik: (mis. pasang APK beta, cek Discord, cadangan)
Risiko dan rollback: image sebelumnya dipulihkan otomatis bila cek siap gagal; migrasi tidak di-downgrade otomatis.
Versi minimum APK (min_build): tidak wajib | WAJIB ke build N
```

Isi bagian `## [X.Y.Z] - tanggal` di `CHANGELOG.md` adalah catatan rilis yang dibaca `rilis.yml` [sumber: `.github/workflows/rilis.yml`].

---

## 3. Struktur repo dan lokasi

### 3.1 Tabel lokasi

| Apa | Lokasi | Status | Catatan |
|---|---|---|---|
| Aturan proyek (perintah, aturan, alur) | `CLAUDE.md` (root) | ADA, lokal | diabaikan Git (`.gitignore` baris 120) |
| Aturan web | `web/CLAUDE.md` | TIDAK ADA | isi yang dimaksud ada di skill `vms-web` |
| Aturan mobile | `mobile/CLAUDE.md` | TIDAK ADA | isi yang dimaksud ada di skill `vms-mobile` |
| Aturan API | `api/CLAUDE.md` | TIDAK ADA | isi yang dimaksud ada di skill `vms-api` |
| Aturan DB | `db/CLAUDE.md` | TIDAK ADA | `db/README.md` ada (urutan pasang) |
| Konteks agen | `KONTEKS-AGEN.md` (root) | ADA | merujuk repo VMS Next |
| Skill proses | `.claude/skills/vms-architect`, `vms-qa`, `vms-cicd-versioning`, `vms-system-design` | ADA (cabang ini) | ditulis panduan ini |
| Skill lapisan | `.claude/skills/vms-web`, `vms-mobile`, `vms-ux-design-system`, `vms-api`, `vms-db`, `vms-storage-minio` | ADA di worktree | ditulis agen lain; belum ditinjau di panduan ini |
| Indeks skill | `.claude/skills/README.md` | ADA (cabang ini) | |
| Sub-agen | `.claude/agents/*.md` (7 berkas) | ADA (cabang ini) | |
| Pengaturan Claude Code | `.claude/settings.local.json` | ADA, lokal | jangan di-commit |
| Dokumen panduan ini | `docs/PANDUAN-AGENTIK.md` | ADA (cabang ini) | repo `KONTEKS-AGEN.md` menyebut `docs/` dihapus; keputusan pemilik |
| ADR repo ini | `docs/adr/` | TIDAK ADA | ADR VMS Next ada di repo `vms-next` |
| Panduan rilis | `docs/RILIS.md` | DIRUJUK tapi TIDAK ADA | dirujuk `CLAUDE.md`, `rilis.yml`, `versi.sh`, `apk.yml` |
| Runbook CI / produksi | `docs/RUNBOOK-CI.md`, `docs/RUNBOOK-PRODUKSI.md` | DIRUJUK; `RUNBOOK-PRODUKSI` disebut di `deploy/README.md`; tidak ada | |
| Riwayat perubahan | `CHANGELOG.md` | ADA | bagian `[Unreleased]` dan `[X.Y.Z]` |
| Versi | `VERSION`, `api/VERSION`, `web/package.json`, `mobile/pubspec.yaml` | ADA | disinkronkan `scripts/versi.sh --tulis` |
| Workflow CI/rilis | `.github/workflows/*.yml` (5) | ADA | |
| Template PR | `.github/pull_request_template.md` | ADA | |
| Hook sebelum commit | `.githooks/pre-commit` | ADA | pasang: `bash scripts/pasang-hook.sh` |
| Skrip verifikasi | `scripts/verify.sh`, `scripts/verify-branch.sh` | ADA | |
| Skrip versi dan APK | `scripts/versi.sh`, `scripts/rilis-apk.sh`, `scripts/rilis-apk.bat` | ADA | |
| Skrip deploy server | `deploy/autodeploy.sh` dan lainnya | ADA | salinan di server |
| Dokumentasi deploy | `deploy/README.md`, `scripts/README.md`, `db/README.md` | ADA | |
| Skill infrastruktur (server, deploy, Docker, cadangan, insiden) | `.claude/skills/vms-devops-infra` (SKILL.md + `references/01`-`04`) | ADA (v0.1, 2026-11-04) | dipakai `devops-engineer` WAJIB; tanpa akses SSH; rujuk `vms-cicd-versioning` dan `vms-system-design`, jangan salin |
| Koleksi Postman | `postman/collections`, `postman/environments`, `postman/fixtures` | ADA | |
| Tes API | `api/tests/` (termasuk `architecture/test_sql_rules.py`) | ADA | |
| Akun uji lokal | `scripts/akun-uji-lokal.txt` (menurut `CLAUDE.md`) | TIDAK DITEMUKAN di `scripts/` | konfirmasi lokasi ke pemilik |
| Standar dan status VMS Next | `vms-next/docs/00`..`10` (repo lain) | ADA di folder lokal | sumber keputusan bisnis dan rencana |
| Riset praktik terbaik | `riset-best-practice/01..03` (folder lokal) | ADA | bahan, bukan aturan |
| Memori pengguna | folder memori Claude Code (lokal) | ADA | berisi aturan pemilik; tidak di repo |

### 3.2 Masalah Git yang harus diputuskan

Di repo sumber (`integrasi/uji-ulang`), `.gitignore` mengabaikan `.agents/` (baris 109), `.claude/` (baris 110), dan `CLAUDE.md` (baris 120). Akibatnya sub-agen dan skill baru di `.claude/` tidak ikut `git add` biasa, dan `CLAUDE.md` tidak ikut Git.

Di worktree cabang ini, `.gitignore` sudah diubah oleh agen lain (bukan oleh panduan ini): `.claude/*` diabaikan, lalu `!.claude/skills/` dan `!.claude/agents/` dibebaskan. `.agents/` dan `CLAUDE.md` tetap diabaikan. Perubahan itu belum ditinjau di sini; panduan ini tidak mengubah `.gitignore` dan tidak membatalkannya.

Pilihan untuk pemilik: (a) menerima perubahan `.gitignore` itu, (b) `git add -f` per berkas, atau (c) memindahkan aturan proyek ke dokumen yang di-commit (`CLAUDE.md` tetap lokal).

### 3.3 Peta dokumen VMS Next (repo `vms-next`, privat)

| Berkas | Isi | Dipakai oleh |
|---|---|---|
| `00-KONTEKS-DOMAIN.md` | pemakai, modul, aturan bisnis yang tidak boleh hilang | semua peran |
| `01-STANDAR-ENGINEERING.md` | ringkasan standar dari panduan PDF | engineer, arsitek |
| `02-ARSITEKTUR-DAN-STRUKTUR-FOLDER.md` | struktur API, web, mobile, face, infra | engineer |
| `03-SKEMA-DATA.md` | kelompok tabel, alamat, perangkat, kolom sensitif | db-engineer |
| `04-DESAIN-UI.md` | token 3 tingkat, atomic design, lima kondisi | web, mobile, QA |
| `05-ALUR-BISNIS.md` | rantai utama, state machine, absensi, offline | QA, arsitek |
| `06-KEAMANAN-DAN-OPERASI.md` | autentikasi, OWASP, observability, CI/CD, rilis | arsitek, devops |
| `07-RENCANA-FASE-DAN-PLAYBOOK-AGEN.md` | fase 0-10, kriteria A-E, larangan | arsitek |
| `08-KEADAAN-VMS-SAAT-INI.md` | stack, server, utang teknis | arsitek, devops |
| `09-STATUS-VMS-NEXT.md` | status dan langkah berikut | arsitek |
| `10-PETA-PANDUAN-PDF.md` | peta panduan PDF | semua |
| `adr/0001..0003` | keputusan awal, jawaban pemilik, referensi | arsitek |
| `sumber-lama/` | diagram peran, state machine, matriks uji, desain | QA, arsitek |

---

## 4. Desain sistem

### 4.1 Arsitektur komponen (VMS lama, produksi)

```
Browser (web React/Vite)                 HP (APK Flutter)
        | HTTPS                                | HTTPS
        v                                      |
 vms_web :8080 (proxy, Caddy/nginx)            |
        | /api/v1/*                            |
        v                                      v
 +-------------- vms_api :8000 (FastAPI, monolit berlapis) ---------------+
 | routes -> services -> repositories (SQLAlchemy async)                  |
 +-----+------------------------+------------------------+----------------+
       v                        v                        v
 vms_db_prod :5433         MinIO vms_minio_prod     vms_face (internal,
 PostgreSQL 18 + PostGIS   berkas; URL presigned     token internal, tanpa
 + pgvector                /vms-files/* lewat Caddy  port publik)
```
[sumber: `docker-compose.yml`, `deploy/compose.limits.yml`, `deploy/README.md`, `vms-next/docs/08`]

Beta berjalan di folder terpisah dengan port berbeda: web 8081, api 8001, db 5435, MinIO 9002/9003 [sumber: `vms-next/docs/08`, `deploy/autodeploy.sh` baris 13].

### 4.2 Alur data

1. Permintaan dari web atau HP masuk ke `vms_api`.
2. Dependensi auth: JWT dan sesi di `user_sessions`; lalu izin global (`require_permission`); lalu cek relasi (divisi, tim, SK).
3. Service memegang batas transaksi; repository hanya SQL.
4. Berkas: API membuat URL presigned; klien mengunduh atau mengunggah langsung dengan URL berumur pendek.
5. Wajah: dipanggil hanya saat absen masuk atau pulang [sumber: `vms-next/docs/06`].
6. Offline HP: perubahan disimpan lokal (outbox), lalu sinkron dengan `client_op_id`.

### 4.3 Kapasitas server 4 GB

- Spesifikasi: 4 GB RAM, 2 CPU [sumber: `deploy/compose.limits.yml`, `vms-next/docs/08`].
- Pengukuran 2026-10-28: face prod 482 MB, beta 259 MB, swap 561 MB [sumber: `deploy/compose.limits.yml`].
- Batas memori: `api` 768m, `web` 128m, `face` 768m; log `json-file` 10m x 3 [sumber: `deploy/compose.limits.yml`].
- Memori DB dan MinIO: BELUM DIUKUR. Ukur dengan `docker stats --no-stream`.
- Aturan: komponen baru hanya bila ada anggaran memori tertulis, batas `mem_limit`, dan alasan. Server staging atau preview bersama ditunda [sumber: `vms-next/docs/06`, butir 6].

### 4.4 Big O di tingkat sistem

Biaya per permintaan = jumlah kueri x biaya per kueri; n = baris yang tersentuh.

| Pola yang ada | Kompleksitas | Tindakan |
|---|---|---|
| `apply_list` memuat seluruh tabel lalu memotong di Python | O(N) per halaman | pindahkan `LIMIT` ke SQL dengan keyset (bukan `OFFSET` baru); indeks |
| Daftar tanpa `LIMIT` (projects, clients, divisions, job_positions) | O(N) respons | tambahkan `ListParams` |
| Bulk jadwal memakai kueri per sel | O(sel) kueri | batch dengan `IN` atau JOIN |
| `COUNT(*)` per halaman log aktivitas | O(N) per halaman | hitung terpisah atau estimasi; indeks `created_at` |

[sumber: riset `01` F-05, F-06, F-07, F-10]

### 4.5 Keputusan keamanan

| Keputusan | Status | Sumber |
|---|---|---|
| Argon2id untuk sandi | sudah sesuai | riset `01` ringkasan 8 |
| Access token 15 menit; refresh berotasi dengan deteksi reuse | sudah sesuai | riset `01` ringkasan 8 |
| Refresh di cookie HttpOnly (web) | sudah sesuai | riset `01` ringkasan 8 |
| Lockout login (5 gagal = 15 menit di VMS Next) | ada di VMS lama; VMS Next: `LOGIN_MAX_FAILURES`, `LOGIN_LOCK_MINUTES` | `api/app/modules/auth/`, `vms-next/docs/06` |
| Rate limit umum | BELUM ADA (F-19); target 6/menit login, 120/menit per pengguna | ADR 0002 keputusan 9 |
| Rahasia di image | MASALAH (F-01): tambahkan `.dockerignore` | riset `01` F-01 |
| RLS | belum ada policy; `set_config` ada | riset `02` |
| Enkripsi NIK dan rekening | rencana VMS Next (AES-256-GCM, blind index) | `vms-next/docs/06`, ADR 0001 keputusan 10 |
| Pemberitahuan push tanpa data pribadi | rencana VMS Next | `vms-next/docs/06` |

### 4.6 Observability

- Sudah ada: log JSON dengan `request_id` (`X-Request-ID`); `/health` (tanpa DB) dan `/ready` (DB); alarm Discord dari `deploy/healthcheck.sh` [sumber: riset `01` T13, T24; `deploy/README.md`].
- Belum ada: `duration_ms`, metrik RED/USE, tracing [sumber: riset `01` F-20].
- Target bertahap: log akses lengkap (tanpa data pribadi) -> metrik RED bila anggaran memungkinkan -> tracing (ditunda, perlu ADR).

---

## 5. Desain UI/UX (proses)

- Sumber visual: Figma; sumber kebenaran kode: `design/tokens/*.json` (rencana VMS Next, ADR 0002 keputusan 3; fase 3) [sumber: `vms-next/docs/04`, `vms-next/docs/07`]. Pipeline token di repo VMS lama belum diperiksa pada sesi ini.
- Atomic design di web: Atoms -> Molecules -> Organisms -> Templates -> Pages. Template tidak mengimpor molekul; halaman tidak mengimpor halaman [sumber: `CLAUDE.md`; `vms-next/docs/04`].
- Lima kondisi layar wajib: loading (kerangka), kosong (ilustrasi + aksi), sebagian, ideal, galat (bahasa manusiawi + coba lagi) [sumber: `vms-next/docs/04`].
- Aksesibilitas: kontras 4,5:1; target sentuh 48 dp; label untuk pembaca layar; fokus keyboard terlihat; tidak hanya warna [sumber: `vms-next/docs/04`].
- Bahasa: Indonesia sederhana. Daftar jargon terlarang di UI: BAST, BoM, BoQ, rollover, prasyarat [sumber: memori "Bahasa sederhana di UI"].
- Galat 422 di web dipetakan ke kolom lewat `applyFieldErrors` (`web/src/lib/errors.ts`) [sumber: `CLAUDE.md`].
- Batas input web dan mobile sama dengan skema API [sumber: `CLAUDE.md`].
- Offline HP: setiap fitur HP harus offline-first dan sinkron otomatis [sumber: memori "Mode offline HP"; pola di `vms-next/docs/38`].
- Detail untuk engineer: skill `vms-ux-design-system` (ditulis agen lain; belum ada di repo ini).

---

## 6. CI/CD dan pipeline

### 6.1 Alur cabang

```
feature/<nama> --PR--> development --merge--> beta --PR (CI)--> prod
                                                  |                |
                          server beta menarik beta (deploy)  server prod menarik prod (deploy, tiap menit)
hotfix/<nama> (dari prod) --PR langsung--> prod --back-merge--> beta, development
```
[sumber: `KONTEKS-AGEN.md`, `deploy/README.md` "Alur pengembangan beta -> produksi", `deploy/beta/pasang-beta.sh`]

Catatan: PR ke `beta` tidak memicu CI (`ci.yml` hanya untuk PR ke `prod` dan `development`). Karena itu gerbang untuk `development` -> `beta` dijalankan manual dengan `scripts/verify-branch.sh`, lalu uji nyata QA di beta. Hal ini dicatat sebagai pelajaran sesi ini.

### 6.2 Workflow: apa memicu apa

| Workflow | Pemicu | Langkah utama |
|---|---|---|
| `ci.yml` (CI) | PR ke `prod` atau `development`; manual | gitleaks; api (ruff, mypy, pytest dengan PostgreSQL, face-service); web (lint, typecheck, test, build); mobile (analyze, test); Discord `#vms-ci` |
| `cd.yml` (CD guard) | push `prod` | pastikan HEAD = `origin/prod`; cek sintaks skrip deploy |
| `rilis.yml` (Rilis) | push `prod` | validasi `VERSION`; gagal bila tag sudah ada; buat tag dan GitHub Release |
| `images.yml` (Images) | push `prod` | build dan dorong image api dan web ke GHCR |
| `apk.yml` (APK) | push `beta` atau `prod` bila `mobile/**` berubah; manual | build APK tertandatangani; cek sertifikat; `latest.json`; push ke `rilis-apk-<env>` |
| Autodeploy (cron server) | tiap menit | cek `origin/$BRANCH`; pasang APK; build; backup; migrasi; `up -d`; cek siap; rollback bila gagal |
| Healthcheck (cron server) | tiap 5 menit | kontainer, `/health`, `/ready`, disk, RAM, cadangan; alarm bila berubah |
| Cadangan (cron server) | 01:30 prod, 01:45 beta | `pg_dump` ke MinIO dan folder lokal |

[sumber: `.github/workflows/*.yml`, `deploy/autodeploy.sh`, `deploy/healthcheck.sh`, `vms-next/docs/08`]

Semua workflow berjalan di runner self-hosted `[self-hosted, linux, vms]`, kecuali APK (`ubuntu-24.04`) [sumber: `apk.yml` komentar].

### 6.3 Gerbang kualitas per tahap

```
Sebelum commit   pre-commit: rahasia ditolak; ruff (api); dart analyze (mobile); eslint (web/src)
PR -> development  CI: gitleaks + api/web/mobile sesuai bagian yang berubah
development -> beta  TIDAK ada CI otomatis: verify-branch.sh + uji nyata QA + APK beta
PR beta -> prod    CI penuh; persetujuan pemilik
merge ke prod      rilis (tag) + images + APK prod + cd guard
server             build -> backup -> alembic -> up -d -> cek siap (3x berturut) -> rollback bila gagal
```

Gerbang lokal yang harus dijalankan engineer sebelum lapor:
- web: `npm run lint`, `npx tsc -b`, `npm test`, `npm run build` [sumber: memori "Cek seperti CI"];
- API: `ruff check app tests`, `python -m mypy` (tes DB hanya atas perintah);
- mobile: `flutter analyze`, `flutter test` [sumber: `ci.yml`, `CLAUDE.md`].

Cek siap pakai sebelum "Siap dipakai" dilaporkan [sumber: `deploy/README.md`]: `/health` 200; `/ready` 200; web 200; `/api/v1/auth/me` tanpa login 401; kontainer `vms_api` dan `vms_web` berjalan; image yang berjalan = image build ini.

### 6.4 Deploy dan rollback

- Urutan: checkout -> simpan image lama sebagai `:rollback` -> build -> backup DB -> migrasi (`alembic upgrade head`) -> `up -d --force-recreate` -> cek siap [sumber: `deploy/autodeploy.sh`].
- Rollback otomatis bila kode keluar 14, 16, 17, atau 18 (kontainer baru gagal sehat): image `:rollback` dikembalikan sebagai `:latest` tanpa build [sumber: `deploy/autodeploy.sh` `rollback_images`].
- Migrasi maju-saja: harus kompatibel mundur (tambah dulu, pakai, baru hapus) [sumber: `deploy/README.md`; `vms-next/docs/06` butir 4-5].
- Anti-loop: commit yang sama yang gagal dicoba lagi setelah `VMS_DEPLOY_RETRY_AFTER` (bawaan 900 detik) [sumber: `deploy/README.md`].
- Skrip server adalah salinan; perubahan `autodeploy.sh` disalin manual dengan cadangan [sumber: `deploy/README.md`].

### 6.5 Build APK per lingkungan

| Lingkungan | Cara | Paket | Catatan |
|---|---|---|---|
| dev (uji lokal) | `VMS_DEVELOPMENT=1 flutter build apk --release --dart-define=API_BASE_URL=http://<ip-lan>:8000` | sesuai `applicationId` dev | jangan ke HP produksi [sumber: `CLAUDE.md`] |
| uji ke emulator | `bash scripts/rilis-apk.sh bangun --uji-lokal --build N` | - | hasil di `mobile/build/rilis-uji/N`; tidak dikirim ke server [sumber: `scripts/rilis-apk.sh`] |
| beta | `apk.yml` env beta: `VMS_BETA=1`, dart-define `VMS_BETA=true`, `UPDATE_CHANNEL=beta`, URL tailnet | `com.visiontech.vms_mobile.beta` | kanal beta [sumber: `apk.yml`] |
| prod | `apk.yml` env prod: URL portal publik | `com.visiontech.vms_mobile` | kanal stable [sumber: `apk.yml`] |
| kirim manual | `scripts/rilis-apk.sh kirim` dari laptop | - | keystore tidak pernah ke server [sumber: `deploy/README.md`] |

Sertifikat APK harus cocok dengan `deploy/android-release-cert.sha256`. Bila tidak, build dibatalkan [sumber: `apk.yml`].

### 6.6 Rahasia

| Tempat | Isi | Catatan |
|---|---|---|
| GitHub secrets | `ANDROID_KEYSTORE_B64`, `ANDROID_STORE_PASSWORD`, `ANDROID_KEY_ALIAS`, `ANDROID_KEY_PASSWORD`, `DISCORD_WEBHOOK_CI` | [sumber: workflows] |
| Server (tidak di Git, chmod 600) | `api.env`, `notify.env` (`DISCORD_WEBHOOK_DEPLOY`, `DISCORD_WEBHOOK_BUILD`), deploy key `~/.ssh/vms_deploy` (baca saja) | [sumber: `deploy/README.md`] |
| Laptop pemilik | keystore `.jks`, `key.properties` | diblokir pre-commit [sumber: `.githooks/pre-commit`] |

Agen tidak pernah membaca atau mencetak isi berkas rahasia. Agen tidak menaruh rahasia di brief, PR, log, atau skill.

---

## 7. Versi

- SemVer `MAJOR.MINOR.PATCH` untuk produk; sekarang `1.5.0` dengan tag `v1.5.0` [sumber: `VERSION`, `git tag`].
- Aturan (sumber: `CLAUDE.md`): perubahan API yang tidak kompatibel = MAJOR; fitur = MINOR; perbaikan = PATCH. Aturan ini sejalan dengan SemVer 2.0.0 (lihat bagian 14).
- Versi API: path `/api/v1`. Perubahan tidak kompatibel = `/api/v2` dengan masa deprecation minimal 6 bulan (rencana VMS Next) [sumber: `vms-next/docs/06`, ADR 0002 keputusan 8].
- Versi mobile: `version: x.y.z+N` di `mobile/pubspec.yaml`. `N` = `git rev-list --count HEAD` (dari `versi.sh --tulis`) dan dipakai sebagai versionCode [sumber: `scripts/versi.sh`].
- Versi minimum APK: `latest.json` memuat `min_build`. Bawaan 1. Dengan opsi wajib, `min_build` = build ini [sumber: `apk.yml`]. Untuk VMS Next: server menolak versi di bawah `min_app_version` dengan masa tenggang 60 hari [sumber: ADR 0002 keputusan 7].
- Versi skema DB: revisi Alembic head, bukan SemVer [sumber: `vms-next/docs/06`].

### 7.1 Langkah rilis

1. PR ke `development`: naikkan `VERSION`; jalankan `bash scripts/versi.sh --tulis`; tulis `## [X.Y.Z] - tanggal` di `CHANGELOG.md` (pindahkan isi `[Unreleased]`).
2. `bash scripts/versi.sh` harus menulis `LULUS`.
3. Uji beta (QA); APK beta diuji nyata.
4. PR `beta` -> `prod`; CI hijau; pemilik menyetujui.
5. Merge: `rilis.yml` membuat tag `vX.Y.Z` dan GitHub Release. Server memasang versi baru.
6. Pantau Discord `#vms-deploy`.

Catatan: `rilis.yml` dan `versi.sh` merujuk `docs/RILIS.md` yang tidak ada di repo ini. Bagian 7 panduan ini menggantikannya sampai pemilik memutuskan lain.

---

## 8. Aturan keras agen

| Aturan | Sumber |
|---|---|
| Jangan merge atau push ke `beta` atau `prod`. Merge ke `prod` = deploy. | `KONTEKS-AGEN.md`, `vms-next/docs/07` |
| Tes DB (`pytest` yang memakai DB) hanya atas perintah pemilik. | memori "Tes hanya atas perintah" |
| Tes DB hanya di `vms_test` (127.0.0.1:55432). Jangan DB dev (55433). | brief pengguna; `CLAUDE.md` Perintah |
| `api/.env.test` menunjuk server lama (menurut brief pengguna). Jangan dipakai sebagai acuan DB uji. | brief pengguna (belum diverifikasi di sesi ini) |
| Jangan menyuntik data langsung ke DB. Kecuali wajah palsu dengan izin tertulis pemilik. | brief pengguna |
| Jangan menebak sandi berulang. Akun uji dari daftar akun uji lokal. Lockout 5 kali gagal. | `CLAUDE.md`, `vms-next/docs/06` |
| Jangan restart adb atau memutus pairing wireless-debug. Jangan menyentuh aplikasi produksi di HP pengguna. | `CLAUDE.md` |
| Jangan memotret orang sungguhan dalam uji kamera. | brief pengguna |
| Uji UI: tab Chrome sendiri, tutup setelah selesai. | `CLAUDE.md` |
| Commit tanpa trailer AI atau `Co-authored-by`. Stage per path. Tanpa `git add -A`, tanpa `git stash` bersama. | memori "Commit VMS"; aturan worktree |
| Hook `.githooks/pre-commit` aktif. Jangan `--no-verify` kecuali darurat yang diperintahkan. | `.githooks/pre-commit` |
| Jangan mengubah aturan bisnis di `00-KONTEKS-DOMAIN`. | `vms-next/docs/07` Larangan |
| Teks UI: Bahasa Indonesia sederhana. | `CLAUDE.md`; memori "Bahasa sederhana" |
| Dilarang menyalin kode lama mentah; kode lama hanya referensi alur. | `vms-next/docs/07` |
| Jangan melewati tes keamanan atau mematikan workflow demi lolos. | `vms-next/docs/07` Larangan; pelajaran sesi ini |
| Daftar API: `ListParams`/`apply_list`; tanpa parameter = perilaku lama. | `CLAUDE.md` |
| SQL: tanpa `LIKE '%...'`; tanpa pengecualian baru di `test_sql_rules.py`. | `CLAUDE.md` |
| Pengaman izin menolak merge ke prod dan penghapusan massal tanpa verifikasi. Agen tidak mengakali pengaman. Minta pemilik. | pelajaran sesi ini |
| Agen yang terjebak tidak mengirim ulang laporan yang sama. Satu laporan akhir. | pelajaran sesi ini |
| Batas perangkat bawaan 4 per akun. Uji perangkat harus memperhatikan batas ini (bukan menambah perangkat tanpa batas). | ADR 0002 keputusan 1-2 (rencana VMS Next) |

---

## 9. Cara memanggil sub-agen dengan skill

Sub-agen dipanggil lewat alat Agent dengan `subagent_type` sama dengan nama berkas di `.claude/agents/` (tanpa `.md`). Prompt cukup berisi brief; sub-agen membaca skill wajibnya sendiri.

### 9.1 Prompt siap pakai

Arsitek ke engineer web:
```
subagent_type: web-engineer
description: Ubah halaman daftar pekerjaan
prompt: Baca skill vms-web, vms-ux-design-system, vms-cicd-versioning sebelum bekerja.
  Brief: <isi brief dari bagian 2.1>. Kerja di worktree terisolasi, cabang feature/<nama> dari development.
  Gerbang: npm run lint, npx tsc -b, npm test, npm run build. Laporkan sesuai format agen.
```

Arsitek ke engineer API:
```
subagent_type: api-engineer
prompt: Baca skill vms-api, vms-db, vms-system-design. Brief: <...>. Tes DB TIDAK dijalankan
  (tidak diperintahkan). Gerbang: ruff check app tests; python -m mypy.
```

Arsitek ke QA:
```
subagent_type: qa
prompt: Baca skill vms-qa. Uji fitur <nama> di beta untuk peran <daftar>. Hanya GET untuk audit.
  Tidak ada tes DB. Akun uji dari daftar akun uji lokal. Tutup tab browser setelah selesai.
  Keluarkan laporan standar dengan P1-P3.
```

Arsitek ke DevOps:
```
subagent_type: devops-engineer
prompt: Baca skill vms-cicd-versioning dan vms-system-design. Brief: perbaiki gerbang api di ci.yml
  yang gagal karena urutan skema. Jangan mematikan job. Jalankan bash -n pada skrip yang diubah.
```

Pemilik / arsitek meninjau: lihat `.claude/skills/vms-architect/SKILL.md` bagian 3.

### 9.2 Aturan pemanggilan

- Satu brief = satu sub-agen = satu cabang. Jangan dua sub-agen menyentuh berkas yang sama.
- Sub-agen tidak memanggil sub-agen lain.
- Hasil sub-agen diperiksa arsitek sebelum diteruskan ke pemilik.

---

## 10. Skill global: kapan dipakai

| Skill global | Kapan dipakai di VMS |
|---|---|
| `modern-web-guidance:modern-web-guidance` | WAJIB untuk tugas HTML/CSS/JS sisi klien (web) sebelum mengubah kode |
| `postman:api-engineer`, `postman:api-testing` | uji kontrak endpoint; memakai Postman CLI yang terpasang |
| `postman:api-documentation`, `postman:ai-readiness` | dokumentasi dan kesiapan API |
| `postman:ci-integration` | menambah uji API ke CI (atas persetujuan arsitek) |
| `postman:variables` | memisahkan rahasia dan variabel lingkungan Postman |
| `security-review` (`/security-review`) | tinjauan keamanan cabang sebelum PR ke `prod` |
| `code-review` (`/code-review`) | tinjauan diff/PR oleh arsitek; mode `max`/`ultra` hanya bila pemilik minta |
| `simplify` (`/simplify`) | merapikan kode yang berubah sebelum lapor |
| `run` | menjalankan aplikasi nyata (web 5173, API 8000) untuk uji |
| `claude-in-chrome` atau `anthropic-skills:chrome-browser` | uji UI di Chrome pengguna |
| `anthropic-skills:built-in-browser` | uji UI di browser panel aplikasi Claude |
| `dataviz` | grafik dan dasbor web |
| `update-config`, `fewer-permission-prompts` | pengaturan Claude Code; dipakai arsitek atau pemilik |
| `loop`, `schedule` | pemantauan berulang; tidak untuk mengubah server |
| `anthropic-skills:skill-creator` | membuat atau memperbaiki skill |

Skill yang tidak dipakai untuk produk VMS: `claude-api`, `plugin-authoring`, `init` (CLAUDE.md sudah ada), `keybindings-help`, `anthropic-skills:docx`/`pdf`/`xlsx`/`pptx`/`docs` (ekspor dokumen VMS dibuat di API).

Daftar lengkap ada di `.claude/skills/README.md` bagian 4.

---

## 11. Pemeliharaan skill

- Pemilik skill proses: arsitek. Skill lapisan: agen penulis, atas persetujuan arsitek.
- Perbarui saat: aturan `CLAUDE.md` berubah; workflow CI berubah; ADR disetujui; atau sebuah kejadian menunjukkan aturan kurang.
- Tinjau semua skill proses saat menutup satu fase.
- Naikkan versi skill (format di `.claude/skills/README.md` bagian 5).
- Klaim faktual di skill wajib punya sumber. Klaim tanpa sumber ditandai.
- Tidak ada rahasia, sandi, atau data pribadi di skill atau panduan.

---

## 12. Pelajaran dari sesi ini

Bagian ini dicatat agar kesalahan tidak berulang. Setiap butir merujuk bukti.

1. Merge ke `prod` adalah deploy. Alur `beta` -> `prod` harus diuji di beta dahulu [sumber: `cd.yml`, `autodeploy.sh`].
2. PR ke `beta` tidak memicu CI. Gerbang untuk `development` -> `beta` harus manual [sumber: `ci.yml`].
3. Workflow bisa dimatikan manual, dan CI lama bisa rusak diam-diam. Periksa daftar workflow aktif setelah perubahan CI [brief pengguna].
4. Urutan skema di CI penting: tabel yang direferensikan dibuat lebih dulu. Contoh: commit `d8a12df5` [sumber: git log `integrasi/uji-ulang`].
5. Tes DB hanya di `vms_test` (127.0.0.1:55432). Jangan DB dev (55433) [brief pengguna].
6. Jangan menyuntik data langsung ke DB [brief pengguna].
7. Pengaman izin menolak merge ke `prod` dan penghapusan massal tanpa verifikasi. Ini sinyal untuk meminta pemilik, bukan untuk mencari jalan lain [brief pengguna].
8. Akun uji dan batas 4 perangkat per akun [sumber: ADR 0002 keputusan 1].
9. Jangan memotret orang sungguhan dalam uji kamera [brief pengguna].
10. Versi SemVer harus lewat `VERSION` dan `scripts/versi.sh` [sumber: `CLAUDE.md`].
11. APK dev, beta, dan prod berbeda paket dan kanal [sumber: `apk.yml`].
12. Agen yang terjebak mengirim ulang laporan yang sama. Satu laporan akhir per tugas [brief pengguna].

---

## 13. Keputusan yang harus dibawa ke pemilik

Arsitek membawa ini dalam bahasa awam, dengan pilihan dan dampaknya.

| No | Keputusan | Pilihan | Sumber |
|---|---|---|---|
| 1 | Cara skill dan sub-agen ikut Git (`.gitignore` di repo sumber mengabaikan `.claude/`; worktree sudah punya pengecualian buatan agen lain) | (a) terima pengecualian di worktree, (b) `git add -f`, (c) pindahkan aturan ke dokumen | bagian 3.2 |
| 2 | Lokasi `docs/` (KONTEKS-AGEN menyebut `docs/` dihapus) | (a) simpan panduan di repo, (b) pindahkan ke `vms-next` | `KONTEKS-AGEN.md` |
| 3 | `docs/RILIS.md` dan runbook yang dirujuk tetapi tidak ada | buat ulang atau ubah rujukan | bagian 3.1 |
| 4 | Akun uji: file `scripts/akun-uji-lokal.txt` tidak ditemukan | konfirmasi lokasi | bagian 3.1 |
| 5 | Rahasia di image Docker (F-01, P0) | tambahkan `.dockerignore` (perbaikan kecil) | riset `01` |
| 6 | Kebocoran lintas divisi pada endpoint GET | urutan perbaikan dan tenggat | `vms-next/docs/08` |
| 7 | Batas perangkat per akun (bawaan 4) | tetap 4 atau ubah | ADR 0002 |
| 8 | Staging/preview | ditunda sampai anggaran server | `vms-next/docs/06` |
| 9 | Feature flag | belum dijawab | ADR 0002 keputusan 12 |
| 10 | Lisensi model wajah (InsightFace non-komersial) | putuskan lisensi komersial sebelum penuh | `deploy/README.md` |
| 11 | Cadangan berkas MinIO dan cadangan luar-server | aktifkan dan jadwalkan | `deploy/README.md` |
| 12 | Waktu cutover dan nasib VMS lama | jadwal | ADR 0002 keputusan 7 |
| 13 | Anggaran server (RAM 4 GB padat) | upgrade atau tetap | `vms-next/docs/07` |
| 14 | Tenggat utang teknis (usulan) | setujui atau ubah | `vms-next/docs/08` |
| 15 | Batas laju login dan endpoint umum | setujui | ADR 0002 keputusan 9 |

---

## 14. Sumber dan tautan

Sumber internal (berkas dalam repo atau folder lokal) sudah dikutip di setiap bagian.

Tautan resmi untuk belajar lebih lanjut. Tautan ini BELUM dibuka pada sesi ini; verifikasi sebelum dipakai untuk keputusan.
- GitHub Actions, sintaks workflow: https://docs.github.com/actions/using-workflows/workflow-syntax-for-github-actions
- GitHub Actions, pengerasan keamanan (pin action ke SHA): https://docs.github.com/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions
- Semantic Versioning 2.0.0: https://semver.org/
- Conventional Commits 1.0.0: https://www.conventionalcommits.org/
- Keep a Changelog: https://keepachangelog.com/
- Claude Code, skills dan sub-agen: dokumentasi resmi Claude Code (buka lewat asisten claude-code-guide atau situs dokumentasi Claude Code)
- Playwright: https://playwright.dev/
- PostgreSQL 18: https://www.postgresql.org/docs/18/
- Alembic: https://alembic.sqlalchemy.org/
- RFC 8594 (header Sunset) dan RFC 9745 (header Deprecation), sebagaimana dirujuk ADR 0002

Sumber internal utama:
- `CLAUDE.md`, `KONTEKS-AGEN.md`, `SECURITY.md` (root repo)
- `.github/workflows/*.yml`, `.github/pull_request_template.md`
- `deploy/autodeploy.sh`, `deploy/README.md`, `deploy/compose.limits.yml`, `deploy/healthcheck.sh`
- `scripts/versi.sh`, `scripts/verify.sh`, `scripts/verify-branch.sh`, `scripts/rilis-apk.sh`
- `.githooks/pre-commit`
- `riset-best-practice/01-PDF-DAN-AUDIT-VMS.md`, `02-API-DB-MINIO.md`, `03-WEB-MOBILE.md`
- `vms-next/docs/00`..`10`, `vms-next/docs/adr/0001..0003`, `vms-next/docs/sumber-lama/`
- `vms-next/docs/panduan/panduan-fullstack.txt` (bagian sistem design baris 844-1050, DevOps baris 1686-akhir, testing 1482-1609, observability 1610-1685, keamanan 1362-1481). Ringkasan dipakai dari riset `01` yang sudah memetakannya.

---

## 15. Glosarium

| Istilah | Arti |
|---|---|
| ADR | Architecture Decision Record; catatan keputusan teknis yang sulit dibalik |
| APK | paket aplikasi Android |
| Arsitek | sesi utama Claude yang merancang, memecah tugas, dan meninjau |
| Atomic design | cara menyusun UI dari atoms, molecules, organisms, templates, pages |
| Brief | surat tugas dari arsitek ke engineer atau QA |
| Cek siap pakai | pemeriksaan setelah deploy (health, ready, web, auth) sebelum "berhasil" |
| Compare-and-set | update hanya bila status masih sama (`WHERE status = ...`) |
| Expand-contract | migrasi tiga tahap: tambah, pakai, lalu hapus |
| Gerbang | pemeriksaan yang harus hijau sebelum tahap berikutnya |
| Idempotency-Key | header agar permintaan ganda tidak membuat data ganda |
| Lima kondisi layar | loading, kosong, sebagian, ideal, galat |
| Lockout | kunci sementara setelah beberapa kali gagal login |
| min_build | versi minimum APK; di bawahnya aplikasi wajib diperbarui |
| Outbox offline | antrean perubahan lokal di HP yang dikirim saat ada sinyal |
| Presigned URL | tautan berumur pendek untuk unduh atau unggah berkas di MinIO |
| QA | penguji independen yang melapor dengan bukti |
| RLS | Row-Level Security; kebijakan akses per baris di PostgreSQL |
| RPO | jumlah data maksimal yang boleh hilang (waktu sejak cadangan terakhir) |
| RTO | waktu maksimal untuk pulih |
| Rollback | kembali ke image sebelumnya bila deploy gagal |
| SemVer | penomoran MAJOR.MINOR.PATCH |
| Worktree | salinan terisolasi repo git untuk satu tugas |
| `vms_test` | DB uji di 127.0.0.1:55432 |
| Cabang `beta` | lingkungan uji nyata sebelum produksi |
| Cabang `prod` | sumber produksi; merge = deploy |
