# 24 · Audit QA & Rencana Perbaikan (2026-09-29)

**Diminta pemilik (R-26):** "pull development, audit seperti QA — sudah sesuai belum, ada konflik
atau error — lalu susun plan perbaikan, kemudian plan yang lebih rinci."
**Titik audit:** `development` = `5dfb8a81` (sama dengan GitHub) · server `prod` = `e1cf1933`.
**Berlaku untuk:** manusia & agen. Setiap task tetap tunduk pada `CLAUDE.md` (uji dulu, satu task =
satu commit, CHANGELOG, pindai rahasia, push ke `development`; `prod` hanya atas permintaan pemilik).

> **Aturan pemilik 2026-09-29:** tidak ada commit sebelum **uji otomatis lulus dan uji nyata lulus**,
> sesuai prosedur. Uji nyata berarti **web** dijalankan di peramban sungguhan terhadap API + PostgreSQL nyata
> (bukan hanya vitest dengan mock), dan **mobile** di HP nyata. Karena itu, pada rencana di bawah, commit T1 baru dilakukan **setelah**
> T2 (ujung-ke-ujung) dan T3 (HP nyata) untuk fitur yang sama selesai.

---

## Bagian 1 · Hasil audit

### 1.1 Pemeriksaan otomatis pada `development`

| Lapisan | Perintah | Hasil |
|---|---|---|
| API lint / tipe | `ruff check app tests` · `mypy app` | ✅ bersih · ✅ 105 berkas tanpa galat |
| API uji penuh | `pytest` (PostgreSQL nyata) | ✅ 689/689 lulus, 28 mnt 45 dtk |
| Web | `lint` · `typecheck` · `vitest` | ✅ bersih · ✅ · ✅ 137/137 (24 berkas) — **mock**, uji peramban nyata belum |
| Mobile | `flutter analyze` · `flutter test` | ✅ tanpa isu · ✅ 77/77 — uji HP nyata belum |
| Uji penjaga router (R-25a, baru) | `pytest tests/test_router_layering.py` | ✅ 3 lulus |
| Server | `/ready`, versi berjalan, skrip deploy | ✅ `e1cf1933` sehat, db ok, `autodeploy.sh` server = repo |
| CI GitHub Actions | — | ⚠️ tidak dapat dicek lokal (`gh` tidak terpasang) |

### 1.2 Temuan

Prioritas: **P1** = salah aturan bisnis / data, **P2** = pekerjaan tertunda atau risiko, **P3** = kebersihan.

| ID | Pri | Temuan | Bukti | Dampak |
|---|---|---|---|---|
| **A-00** | **P0** | **Uji API di laptop menulis ke DB PRODUKSI.** `api/.env` `DATABASE_URL` → `100.117.92.14:5433/visiontech_db` = `vms_db_prod`/`visiontech_db` yang dipakai aplikasi produksi; `tests/conftest.py:24` memakai `settings.DATABASE_URL`. Setiap suite (±690 uji) membuat organisasi "Dunia uji …", akun `@contoh.test`, SK, absensi, dll. di produksi | `api.env` server vs `api/.env` laptop (host, port 5433→5432, nama DB sama); skrip pembersih lama `purge_test_orgs.py` | Data uji bercampur dengan data asli; beban DB produksi; risiko uji yang menghapus/mengunci data. **Uji API dihentikan sampai ada DB uji terpisah** |
| **A-01** | P1 | **Celah ganti ketua lewat `PATCH /work-plans/{id}`**: tidak memanggil `validate_team_scope`, jadi aturan R-23 "PM hanya memilih personel unitnya" bisa dilewati. **Sudah ada di produksi.** | `api/app/api/plans.py:181-205` langsung `UPDATE … leader_employee_id` + `INSERT work_plan_member` | PM dapat menjadikan orang di luar unitnya (dan nanti: pegawai kantor) ketua SK draf |
| **A-02** | P1 | Pekerjaan Codex "ketua/anggota hanya staf lapangan" **belum masuk repo**; tersimpan di `stash@{0}` ("Teleport auto-stash", 2026-09-28 22:22) | `git stash show --include-untracked stash@{0}` | Permintaan pemilik belum terpenuhi di aplikasi |
| **A-03** | P1 | Nomor revisi **bentrok**: stash memakai **R-25**, padahal R-25 sudah dipakai sesi lain untuk O-02/Figma (`5dfb8a81`) | `docs/19` baris R-25 vs isi stash | Catatan revisi rancu; harus jadi **R-26** |
| **A-04** | P1 | Dengan stash diterapkan, **4 uji API gagal** | `test_monitoring::test_timeline_groups_days_per_plan`, `test_plan_access::test_day_of_another_plan_is_404_under_this_plan_path`, `test_regressions_r4_r7_r9::test_r4_published_document_content_cannot_be_updated`, `test_trigger_messages::test_changing_to_a_busy_leader_is_409_not_500` | Penyebab: data uji memakai `leader="hr"`/`"ops"` (peran kantor) sebagai ketua, jadi yang salah data ujinya, bukan kode |
| **A-05** | P2 | Stash juga membawa berkas yang **tidak boleh di-commit** | `docker-compose.yml`, `db/Dockerfile`, `migrate_baca.py`, `test_db.py`, `.claude/launch.json` | Harus dipulihkan tanpa ikut ter-stage |
| **A-06** | P2 | **Belum ada uji perangkat nyata** untuk fitur yang sudah di produksi | docs/19: R-06, R-11, R-12 (mobile), R-21, R-23; skenario UAT docs/22 belum satu pun ✅; `adb devices` kosong | Bug HP (kamera, GPS, luring, sinkron) bisa lolos ke pengguna |
| **A-07** | P2 | R-25b (O-02 per modul) dan R-25c (FigJam/Figma) **belum dimulai** | tidak ada branch `feature/r25-o02-*` di GitHub | 9 router masih menulis SQL langsung (termasuk `plans.py`, sumber A-01) |
| **A-08** | — | ~~Suite API melambat~~ **Ditutup:** 1 j 53 mnt (2026-09-28) terjadi karena dua suite berjalan bersamaan di DB yang sama; sendirian 28 mnt 45 dtk | keluaran pytest 2026-09-29 | Jangan jalankan dua suite paralel pada satu DB |
| **A-09** | P3 | Branch `wip/web-overtime-2026-09-25` **basi & konflik** dengan `development`; fiturnya sudah ada di `development` | `Overtime.tsx`, `OvertimeRecapPage.tsx`, `overtime.test.tsx` sudah ada | Membingungkan; aman diarsipkan setelah pemilik setuju |
| **A-10** | P3 | 4 branch `feature/*` di GitHub sudah **tergabung penuh** (+0 commit) dan 4 worktree lokal lama (`temp-l3`, `temp-v28`, `vms-api-agent-2`, `vms-gemini`); `stash@{1}` lama (sesi Gemini) | `git rev-list development..origin/<b>` = 0 | Kebersihan; hapus setelah pemilik setuju |
| **A-11** | P3 | Status basi di docs/19: R-22 "skrip di server perlu disalin ulang", padahal skrip server sudah sama dengan repo | `diff` skrip server vs `src/` = sama | Agen berikutnya bisa mengulang pekerjaan |
| **A-12** | P3 | `PATCH /work-plans` memakai `HTTPException` (bukan `AppError`) dan SQL di router | `plans.py:149-156` | Melanggar `docs/12`; bentuk galat tidak baku. Diselesaikan bersama R-25b modul `plans` |
| **A-13** | P1 | **Jam server melompat saat menyala ulang.** 2026-09-30: semua kontainer (termasuk `vms_db_prod`) tercatat mulai 07:59 UTC, padahal saat diperiksa pukul 01:37 UTC. Jadi jam ±6,5 jam lebih cepat saat boot, lalu dibetulkan NTP. Pernah terlihat juga 2026-09-28 (±2 jam) | `docker inspect … StartedAt` vs `date -u`; `timedatectl` = tersinkron sesudahnya | Aturan 3 ("jangan percaya perangkat") bergantung pada jam server. Absensi/tanda tangan di jeda itu bisa salah waktu. Usul: cek jam RTC/BIOS server, `chrony` dengan `makestep` saat boot, dan API menolak absensi bila jam belum tersinkron. **Butuh izin pemilik** (pengaturan server) |

**Tidak ditemukan konflik** antara `development` lokal dan GitHub (pull fast-forward). Konflik hanya
pada branch basi A-09.

### 1.3 Kesesuaian dengan dokumentasi

| Aturan | Status |
|---|---|
| Kewenangan mengikuti SK (aturan 1) | ⚠️ A-01: pemilihan ketua lewat PATCH tidak dijaga |
| Router → service → repository (docs/12) | ⚠️ 9 router masih ber-SQL (dipantau R-25a, dikerjakan R-25b) |
| Galat `AppError` berbahasa Indonesia | ⚠️ A-12 |
| Setiap permintaan tercatat di docs/19 | ⚠️ A-03 bentrok nomor, A-11 status basi |
| "Selesai" = uji hijau & dilaporkan | ⚠️ A-06: uji perangkat nyata belum |
| CHANGELOG UTF-8, rahasia tidak di-commit | ✅ |

### 1.4 Hasil uji lengkap

Semua otomatis **hijau** pada `development` `5dfb8a81`: API 689/689 · web 137/137 · mobile 77/77 ·
ruff/mypy/eslint/tsc/flutter analyze bersih. Belum ada uji nyata (peramban terhadap API nyata, HP).

---

## Bagian 2 · Rencana perbaikan (urutan)

Satu fitur diselesaikan sampai tuntas (kode → uji otomatis → uji ujung-ke-ujung → uji HP nyata →
catat) sebelum pindah ke fitur berikutnya.

| Tahap | Isi | Menutup | Butuh pemilik? |
|---|---|---|---|
| **T0** | **Pisahkan DB uji dari produksi** (DB uji lokal/staging + penjaga di `conftest.py` yang menolak berjalan pada DB produksi), lalu bersihkan data uji di produksi setelah backup | A-00 | **Ya**: pilih lokasi DB uji + izin pembersihan produksi |
| **T1** | R-26: pulihkan stash staf lapangan, ganti nomor ke R-26, perbaiki 4 uji, **tutup celah PATCH** (A-01) | A-01…A-05 | Tidak |
| **T2** | Uji ujung-ke-ujung alur SK (API nyata + web) untuk R-23 & R-26 | A-06 sebagian | Tidak |
| **T3** | Uji HP nyata: APK baru → skenario docs/22 A, B, C, E | A-06 | **Ya**: sambungkan HP (USB debug) + Tailscale |
| **T4** | Gabung ke `prod` → verifikasi server → uji ulang singkat di HP | — | **Ya**: izin merge `prod` |
| **T6** | R-25b O-02 per modul (mulai `plans`, lalu 8 modul lain) | A-07, A-12 | Tidak |
| **T7** | Kebersihan repo (branch basi, worktree, stash lama) + status docs/19 | A-09…A-11 | **Ya**: izin hapus |
| **T8** | R-25c FigJam/Figma (my-edu) | A-07 | Tidak |
| **T10** | R-28 migrasi struktur folder API (`docs/26`, M0–M8; menggantikan T6/R-25b yang digabung ke M6) | A-07, A-12 | K-1 |
| **T9** | R-27 audit kesesuaian dengan `prototype/`: tambahan pemilik dipertahankan, selisih lain dicatat & ditanyakan | — | Ya, untuk selisih yang ragu |

---

## Bagian 3 · Rencana rinci

### T0 · Pisahkan DB uji (wajib sebelum uji apa pun) — ✅ SELESAI 2026-09-29

Hasil: kontainer `vms_db_test` (:5434, `vms_test`) & `vms_minio_test` (:9100) di server, jaringan sendiri, hanya IP Tailscale; rahasia di `~/deploy/vms-test-db/test.env` (600) dan `api/.env.test` (git-ignored). `tests/db_guard.py` menolak DB/MinIO produksi (uji `test_db_guard.py`). Data uji produksi yang tersisa (2 organisasi) **belum** dihapus karena pengaman otomatis memblokir; perintah untuk pemilik ada di laporan. Catatan: pgvector dipasang via apt di kontainer uji, jadi hilang bila kontainer dibuat ulang (pasang lagi, lalu restart).


1. Pilih DB uji:
   - (a) PostgreSQL + PostGIS lokal di Docker laptop, dengan skema dari `db/*.sql` + Alembic; atau
   - (b) DB terpisah `visiontech_test` di server (bukan `visiontech_db`).
2. `api/.env.test` (git-ignored) dengan `DATABASE_URL` ke DB uji. `conftest.py` membaca
   `TEST_DATABASE_URL` dan **menolak berjalan** bila nama DB bukan `*_test`/lokal, atau bila host = server
   produksi dengan DB `visiontech_db`. Ujinya ditulis lebih dulu.
3. Uji web nyata (T2) memakai API lokal yang menembak DB uji yang sama, bukan produksi.
4. Produksi: backup → hapus organisasi "Dunia uji %"/"Organisasi uji" dan `login_attempt @contoh.test`
   (skrip pembersih lama, setelah ditinjau). Hanya dengan izin pemilik.

### T1 · R-26 staf lapangan + celah PATCH — ✅ kode & uji; laporan uji nyata `docs/25`

1. **Pulihkan tanpa merusak.** `git stash show -p stash@{0} -- api docs CHANGELOG.md | git apply`
   (hanya jalur ini). Berkas terlarang (A-05) **tidak** dipulihkan ke area stage; `stash@{0}` dibiarkan
   sampai T1 di-push.
2. **Ganti nomor**: R-25 → **R-26** di `CHANGELOG.md`, `docs/10` (Bagian C), `docs/19`, `docs/23`
   (nomor berikutnya jadi **R-27**).
3. **Uji dulu untuk celah PATCH** (`api/tests/test_plan_assignment_scope.py`):
   - PM mem-PATCH ketua dengan karyawan unit lain → 422 `PERSONNEL_OUTSIDE_PM_UNIT` (kode galat R-23 yang ada).
   - Siapa pun mem-PATCH ketua dengan pegawai kantor → 422 `PERSONNEL_NOT_FIELD_STAFF`.
   - OPS mem-PATCH ketua lintas unit dengan staf lapangan → 200.
4. **Perbaikan**: di `update_plan` panggil
   `PlanAssignmentService(PlanAssignmentRepo(db)).validate_team_scope(current_user, row.unit_id, [leader])`
   sebelum `UPDATE`, hanya bila ketua berubah.
5. **Perbaiki 4 uji A-04**: ganti `leader="hr"`/`"ops"` dengan staf lapangan dari
   `world.add_person(...)` (yang memiliki akun aktif tanpa peran kantor). Pastikan maksud tiap uji tetap
   sama (misalnya "ketua lain pada periode sama").
6. **Tinjau jalur lain yang menetapkan tim**: `plan_member_repo` (PUT tim), `plan_change_repo` (adendum),
   `plans.py` create/patch, CLI/impor. Masing-masing harus melewati `validate_team_scope`.
7. **Kasus tepi yang diputuskan & dicatat di docs/10 Bagian C**: adendum yang **mempertahankan**
   anggota lama. Anggota lama yang kini berperan kantor atau berasal dari unit lain (dibuat OPS) akan
   menolak adendum PM. Usul: aturan unit/peran hanya diterapkan pada orang **yang baru ditambahkan**.
8. **Verifikasi**:
   - `ruff`, `mypy`;
   - uji terarah (`test_plan_assignment_scope`, `test_plan_members`, `test_plan_changes`, keempat uji A-04);
   - lalu suite penuh;
   - web tetap hijau. Karena skema tidak berubah, `gen:api` tidak perlu, tapi dicek.
9. **Commit, hanya setelah T2 dan T3 lulus untuk R-26**: `feat(R-26): ketua/anggota SK hanya staf lapangan + tutup celah PATCH ketua`, pindai
   rahasia, lalu push ke `development`. Setelah itu hapus `stash@{0}`, hanya dengan izin pemilik.

**Selesai bila:** semua uji hijau, 3 uji PATCH baru ada, docs/19 R-26 = "Selesai (kode)", tidak ada
berkas terlarang di commit.

### T2 · Uji ujung-ke-ujung alur SK (lokal, data nyata sementara)

1. API lokal + PostgreSQL nyata (data uji `UJI-`), web `npm run dev` yang menembak API itu (bukan mock),
   dibuka di peramban sungguhan (peramban bawaan aplikasi), dan diklik seperti pengguna. Ini termasuk
   jalur galat: pesan 422 tampil jelas dalam Bahasa Indonesia.
2. Skenario per peran:
   - **OPS**: buat SK lintas unit, dialog tim hanya menampilkan staf lapangan.
   - **PM**: hanya unitnya; mencoba ketua pegawai kantor lewat API ditolak.
   - Terbit → ketua menerima (web petunjuk + API) → adendum ganti ketua → kewenangan pindah (aturan 1).
3. Bukti: tangkapan layar + daftar permintaan jaringan, disimpan di `.local_tests/e2e-<tanggal>/`
   (tidak di Git), ringkasan hasil di docs/22 tabel Temuan.

**Selesai bila:** tiap langkah ✅ atau temuan tercatat.

### T3 · Uji HP nyata (butuh HP tersambung)

1. Prasyarat pemilik: HP USB debugging aktif (`adb devices` menampilkan perangkat) + Tailscale menyala.
2. Build APK rilis ke server **setelah T4**, atau APK ke API lokal untuk pra-uji.
3. Jalankan docs/22:
   - **A** (login, kunci, kartu kantor)
   - **B1–B8** (SK sampai laporan harian)
   - **C1–C4** (absensi)
   - **E1–E7** (luring/sinkron)
4. Catat ✅/❌ + tanggal di docs/22; temuan → docs/19.

### T4 · Rilis ke `prod`

1. Setelah T1–T2 hijau dan pemilik setuju: `git push origin development:prod` (fast-forward).
2. Pantau Discord ✅ "Siap dipakai", lalu `curl /ready` dan cocokkan versi di server.
3. Uji ulang singkat di HP: login, buat/terima SK, absen.

### T5 · (ditutup, lihat A-08)

Tidak ada pekerjaan. Aturan: satu suite API per DB pada satu waktu.

### T6 · R-25b O-02 per modul

Satu modul = satu branch `feature/r25-o02-<modul>` = satu commit. Urutan:
`plans` (menutup A-12) → `attendance` → `employees` → `assets` → `hse` → `files` → `sites` → `audit` → `expiry`.

Untuk tiap modul:
1. SQL dari router dipindah ke repository.
2. Service memanggil repository; router hanya memanggil service.
3. `HTTPException` diganti `AppError`.
4. Nama modul dikeluarkan dari daftar `LEGACY` di `test_router_layering.py`.
5. Uji modul yang ada + suite penuh hijau (perilaku API tidak berubah).

### T7 · Kebersihan (setelah izin)

1. Arsipkan lalu hapus `wip/web-overtime-2026-09-25` (fitur sudah di `development`).
2. Hapus 4 branch `feature/*` yang sudah tergabung, 4 worktree lokal lama, dan `stash@{1}`.
3. Perbarui status docs/19 R-22 → "Selesai (server sudah sama)".

### T8 · R-25c Figma/FigJam

Alur SK, absensi, laporan, aset/insiden/lembur di FigJam; desain menu PM HP (R-09) di tim my-edu.
