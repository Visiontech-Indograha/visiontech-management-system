# Plan Rinci — Verifikasi Modul Backend (turunan 7 segmen)

**Sumber:** `PLAN-VERIFIKASI-MODUL.md` (segmen 1–7 dan bukti E1–E9).
**Aturan kerja:** `.agy/rules/*` + `CLAUDE.md` — uji dulu; satu task = satu commit; CHANGELOG;
pemindaian rahasia; push; "selesai" = uji dijalankan & hijau (ai-testing butir 4).
**Acuan aturan bisnis:** `prototype/js/domain.js` (baris disebut per task). Bila berbeda dengan
dok 02/10, dok 02/10 yang berlaku.

Format tiap task: **Tujuan · Uji dulu · Perubahan · DoD · Acuan · Bergantung pada**.
Centang hanya setelah commit di-push.

---

## W1 · Alat bukti permanen

- [x] **V-01 · Pemeriksa SQL-vs-skema menjadi uji resmi**
  - Tujuan: kueri yang tak cocok skema (E1/E2) langsung membuat CI merah.
  - Uji dulu: `tests/test_sql_matches_schema.py` — setiap literal SQL di `app/` di-`PREPARE`
    terhadap DB uji; potongan f-string dilewati **dan dihitung**; uji gagal bila inventaris kosong
    (ai-testing j). Pada kode sekarang uji ini harus merah dengan daftar E2.
  - Perubahan: helper pengambil literal (AST) yang tidak memeriksa potongan di dalam f-string;
    daftar pengecualian eksplisit untuk kode mati yang akan dihapus di V-14 (hanya boleh menyusut).
  - DoD: uji merah menampilkan tepat bug E2; setelah W2 & V-14 → hijau tanpa pengecualian.
  - Bergantung pada: —

- [x] **V-02 · Uji alur per modul (dari probe)**
  - Tujuan: bukti permanen bahwa alur bahagia setiap modul menyimpan data.
  - Uji: `tests/flows/test_employee_flow.py`, `…_document_flow.py`, `…_attendance_flow.py`,
    `…_asset_flow.py`, `…_incident_flow.py`, `…_plan_flow.py` (SK: ditandai `xfail(strict=True)`
    sampai W2 — begitu lulus, xfail ketat membuatnya merah sehingga penanda wajib dicabut).
  - Perubahan: fixture `org_world` (organisasi, unit, lokasi, karyawan admin/HR/PM/ketua/anggota,
    pengguna tertaut) + pembersihan yang menyetel konteks organisasi (E7) — dipindah dari probe.
  - DoD: semua alur non-SK hijau; alur SK `xfail` dengan alasan yang merujuk V-03..V-05.
  - Bergantung pada: —

## W2 · Siklus SK hidup (E1–E3)

- [x] **V-03 · Keanggotaan memakai `valid_period`**
  - Uji dulu: alur SK sampai publish (V-02) + uji unit kueri anggota aktif.
  - Perubahan: `plan_transitions.py:39`, `plan_changes.py:101,110` — `valid_to IS NULL` →
    `upper(valid_period) IS NULL` (sama dengan `is_plan_member`); penutupan baris →
    `valid_period = daterange(lower(valid_period), :tanggal, '[)')`.
  - DoD: `check_sql` bersih untuk tiga baris itu; publish tidak lagi 500.
  - Acuan: `db/01` `work_plan_member`, `db/02` `is_plan_member`.

- [x] **V-04 · Nilai enum sesuai skema**
  - Perubahan: `document_kind` `'SK'` → `'INITIAL_ORDER'` (revisi → `'REVISION'`, `domain.js:321`);
    `document_status` `'ACCEPTED'` → `'EFFECTIVE'` (dokumen lama → `'SUPERSEDED'`);
    `change_status` `'APPLIED'` → `'EFFECTIVE'`; `daterange` pada `plan_changes.py:45` diberi cast
    `CAST(:x AS date)`.
  - Uji: uji kesetaraan — setiap literal enum di kode ada di `enum_range(...)` (ditangkap V-01);
    alur SK sampai ACCEPTED hijau.
  - Acuan: `db/01` baris 36–39, `domain.js:319–327`.

- [x] **V-05 · Anggota tim SK draft**
  - Tujuan: SK dapat diberi ketua & anggota sebelum terbit (E3).
  - Endpoint: `PUT /plans/{id}/members` (PM unit, hanya DRAFT, `row_version`) — daftar lengkap
    `{leader_employee_id, member_employee_ids[]}`; menulis `work_plan_member` dengan
    `valid_period = [period_start, )`; bentrok jadwal ditolak dengan pesan dari `personnel_conflict`.
  - Uji dulu: ketua & anggota tersimpan; ketua ganda / karyawan organisasi lain → 422/404;
    bentrok jadwal → 409 berbahasa Indonesia; bukan DRAFT → 409; `row_version` usang → 409.
  - Acuan: `domain.js` `checkMembers`, `checkSchedule`; `db/02` `tg_member_no_conflict`.

- [x] **V-06 · Aturan publish & start lengkap**
  - Uji dulu: publish ditolak bila ada tanggal periode tanpa hari, hari tanpa judul/tugas
    (`domain.js:319`); start ditolak sebelum `period_start` menurut jam server (`domain.js:330`);
    accept hanya oleh **ketua menurut SK** (`is_plan_leader`) — pengguna lain 403.
  - DoD: alur SK DRAFT → PUBLISHED → ACCEPTED → IN_PROGRESS → perpanjangan disetujui hijau;
    penanda `xfail` di V-02 dicabut.

## W3 · Aman (E4, E5)

- [x] **V-07 · Penjaga keterlibatan pekerjaan (dependency bersama)**
  - Perubahan: `app/api/guards.py::plan_access(need)` — `need ∈ {PM_UNIT, LEADER, MEMBER,
    LEADER_OR_MEMBER, VIEW}`; memakai `is_plan_leader`/`is_plan_member`/`has_role('PM', unit)`;
    SK organisasi lain atau tak terlihat → **404**; terlihat tapi tak berwenang → 403.
  - Uji dulu (parametrik peran × kebutuhan): PM unit lain, OPS, ketua lama setelah diganti,
    anggota, pengguna tanpa peran. Termasuk regresi **R3** (ketua diganti kehilangan hak ketua,
    tetap anggota bila masih terdaftar).
  - **Temuan V-06 (wajib diputuskan di sini):** di prototipe (`domain.js` baris 174) OPS memegang
    kewenangan PM lintas unit (CREATE_PLAN, PUBLISH, APPROVE_CHANGE, CANCEL_PLAN, …), sedangkan peta
    izin T-03 mengikuti dok 03 §1 ("OPS = baca"). Urutan kewenangan menempatkan prototipe di atas
    dok 03 → peta izin OPS disesuaikan dengan prototipe dan dicatat di dok 10 Bagian C.

- [x] **V-08 · Penjaga organisasi untuk rujukan di badan permintaan**
  - Perubahan: `same_org(table, id)` untuk `work_plan_id`, `site_id`, `asset_id`,
    `evidence_file_ids`, `file_id`, `pm_employee_id`, `leader_employee_id`, `driver_employee_id`.
  - Uji dulu: untuk setiap endpoint tulis, id milik organisasi lain → 404 dan **tidak ada baris
    tersimpan** (tulis → baca ulang).

- [x] **V-09 · Setiap rute punya izin atau penjaga**
  - Uji dulu: perluasan `test_route_smoke.py` — rute non-publik tanpa `require_permission` dan
    tanpa `plan_access` → gagal (inventaris dependency dari FastAPI).
  - Perubahan: pasang pada insiden (`LEADER_OR_MEMBER`, `domain.js:582`), laporan harian
    (`LEADER`), pengembalian aset (`LEADER` + bukan peran ASSET, `domain.js:506`), GET `/sites`.
  - Tambahan: regresi **R2** — PM unit CCTV tidak melihat insiden/lembur unit Wall Display.

## W4 · Patuh aturan (E6, regresi wajib)

- [x] **V-10 · Tanggal dari server**: laporan hanya pada/setelah tanggal pelaksanaan
  (`domain.js:360,372`, regresi **R6**); insiden bertanggal hari ini menurut server;
  semua lewat `core/time.py`. Uji: tanggal belum tiba → 422 berbahasa Indonesia.
- [x] **V-11 · Status SK sebagai syarat**: laporan & insiden hanya untuk `IN_PROGRESS`;
  alokasi aset hanya bila SK bukan `COMPLETED/CANCELLED` (`domain.js:489`); pengemudi kendaraan
  harus anggota tim. Uji per aturan.
- [x] **V-12 · Absensi**: sesi terbuka dicegah, satu absensi aktif per hari kecuali ditolak
  (`domain.js:533`); kode `is_late` mati di router dihapus (trigger yang menentukan, K-11);
  regresi **R10** (jam perangkat tidak dipakai) diuji.
- [x] **V-13 · Regresi wajib tersisa**: **R4** (kolom `plan_document` terkunci — UPDATE ditolak),
  **R7** (penanda bentrok personel), **R9** (siklus aset tanpa jalan buntu).

## W5 · Bersih (E7–E9)

- [x] **V-14 · Hapus kode mati tak cocok skema**: `repositories/plan_repo.py`,
  `repositories/attendance_repo.py`, `services/plan_service.py`, `services/attendance_service.py`,
  `services/document_service.py`, `services/pdf_service.py` (tak diimpor; E9). Uji penjaga:
  setiap modul di `services/` & `repositories/` diimpor kode aplikasi. Pengecualian V-01 dikosongkan.
- [ ] **V-15 · Trigger audit menemukan organisasi** (migrasi 0006; 0004 dipakai V-07, 0005 dipakai V-13): untuk baris tanpa
  `organization_id`, ambil dari `work_plan`/`asset` terkait sebelum `current_org_id()`. Uji:
  hapus `asset_allocation` tanpa konteks → berhasil & tercatat di audit dengan organisasi benar.
- [x] **V-17 · Kebijakan akses berkas** (temuan V-09): `GET /files/{file_id}/url` hanya memeriksa
  organisasi — siapa pun di organisasi dapat mengambil URL KTP/SIM karyawan lain (dok 08: dokumen
  pribadi hanya pemilik & HR; CLAUDE.md "berkas tak berwenang → 404"). Aturan: pengunggah; HR untuk
  dokumen karyawan; bukti insiden/laporan → penjaga SK (VIEW); swafoto absensi → pemilik & FINANCE/HR.
  Uji: matriks peran × jenis berkas → 200/404. Dikerjakan tepat setelah V-09 (sebelum W4).
- [ ] **V-16 · Jalur sesuai kontrak**: `/plans` → `/work-plans` (dok 05); `/hse/daily-reports` →
  `/work-plans/{id}/days/{day_id}`. Web belum memakai rute ini (tidak ada dampak).

## W6 · Lengkap — transaksi prototipe yang belum ada

Dikerjakan berurutan per fase (dok 06). Setiap transaksi = satu task dengan pola sama:
uji aturan dari baris `domain.js` → servis → penjaga W3 → uji alur.

| Task | Transaksi | Fase | Acuan `domain.js` |
|---|---|---|---|
| V-20 | APPEAL, REVISE | 3 | 328–329 |
| V-21 | CANCEL_PLAN, RESTORE_PLAN, DELETE_PLAN | 3 | case masing-masing |
| V-22 | REQUEST_PERSONNEL_CHANGE, ACCEPT_CHANGE, REJECT_CHANGE, WITHDRAW_CHANGE | 3 | 413 dst. |
| V-23 | SAVE_DAY, TOGGLE_TASK | 5 | case masing-masing |
| V-24 | REVIEW_REPORT | 5 | case REVIEW_REPORT |
| V-25 | SAVE_WEEKLY, SUBMIT_WEEKLY, REVIEW_WEEKLY | 5 | case masing-masing |
| V-26 | REQUEST_COMPLETE, APPROVE_COMPLETE, RETURN_COMPLETE | 5 | 454, 472 |
| V-27 | RESERVE_ASSET, RELEASE_ASSET (ganti `allocate`), CHECK_ASSET | 7 | 489, 273 |
| V-28 | REPORT_OVERTIME, REVIEW_OVERTIME + rekap | 7 | case masing-masing |
| V-29 | RESTORE_EMPLOYEE, SAVE_ATTACHMENTS | 2/5 | 177 (izin), case masing-masing |
| V-30 | Lini masa OPS dikelompokkan per pekerjaan, rekap absensi | 7 | dok 03 M11 |

Setiap task W6 dirinci (uji & DoD per aturan) tepat sebelum dikerjakan, di bagian bawah dokumen ini.

---

## Urutan & titik aman

`V-01 → V-02 → V-03 → V-04 → V-05 → V-06` (SK hidup) `→ V-07 → V-08 → V-09 → V-17` (aman)
`→ V-10 … V-13` (patuh) `→ V-14 … V-16` (bersih) `→ W6`.
Setiap task adalah titik aman: di-commit, di-push, suite hijau.
