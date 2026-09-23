# Plan Verifikasi Modul Backend (Fase 2–7) — 7 Segmen Pengecekan

**Dibuat:** 2026-09-24 · **Metode:** pemecahan masalah 7 segmen, setiap segmen berbasis bukti
**Lanjutan dari:** `PLAN-PERBAIKAN-TEMUAN.md` (fondasi: sesi, transaksi, izin, galat, CI — selesai)
**Rincian eksekusi:** `PLAN-VERIFIKASI-MODUL-RINCI.md` (diturunkan dari dokumen ini)
**Mendahului:** `PLAN-SISA-MVP.md` blok A-3 dst. — tidak ada fitur baru dibangun di atas modul
yang belum terbukti bekerja.

Alat bukti (lokal, `.local_tests/`, tidak di-commit — akan dijadikan uji resmi di V-01/V-02):
- `probe_modules.py` — alur bahagia 39 langkah di semua modul terhadap PostgreSQL + MinIO nyata,
  memeriksa status HTTP **dan** baris yang tersimpan; membersihkan diri sendiri.
- `check_sql_against_schema.py` — setiap literal SQL di `app/` di-`PREPARE` terhadap skema nyata.

---

## Segmen 1 · Definisi masalah

> Setelah fondasi diperbaiki, **34 dari 39 langkah alur bahagia berhasil dan datanya tersimpan** —
> tetapi modul inti produk, **siklus SK, tidak bisa melewati tahap draft**, tidak satu pun endpoint
> menegakkan aturan inti "kewenangan mengikuti SK", beberapa endpoint menerima data lintas
> organisasi, dan ±24 dari 47 transaksi bisnis prototipe belum punya endpoint.

**Bukti utama**

| # | Bukti | Sumber |
|---|---|---|
| E1 | `POST /plans/{id}/publish` → 500 `column "valid_to" does not exist`; akibatnya accept/start/perpanjangan tidak pernah bisa diuji | probe |
| E2 | 21 kueri gagal `PREPARE` terhadap skema; 7 di antaranya bug nyata di jalur SK (`valid_to` ×3, enum `'SK'`, `'ACCEPTED'`, `'APPLIED'`, tipe `daterange`) | check_sql |
| E3 | Tidak ada endpoint untuk menambah anggota tim, padahal `publish` mensyaratkan anggota aktif | inventaris rute |
| E4 | `is_plan_leader`/`is_plan_member` tidak dipakai di satu pun router (0 dari 13) | grep |
| E5 | `POST /hse/incidents` & laporan harian: tanpa izin, tanpa cek organisasi/keterlibatan pada `work_plan_id` maupun `evidence_file_ids` | kode `hse.py` |
| E6 | Laporan harian untuk **2026-10-01** diterima pada 2026-09-24 (melanggar regresi wajib R6); insiden & laporan diterima untuk SK berstatus DRAFT | probe |
| E7 | `tg_audit_row()` gagal (organization_id NULL) untuk `asset_allocation` di luar konteks permintaan → penghapusan berantai & tugas pemeliharaan gagal | pembersihan probe |
| E8 | Kontrak dok 05 memakai `/work-plans`, kode `/plans`; ±24 transaksi prototipe tanpa endpoint | dok 05, `domain.js` |
| E9 | `repositories/plan_repo.py`, `services/pdf_service.py` merujuk kolom yang tidak ada (`business_unit_id`, `day_date`, `ar.allocation_id`) — kode mati dari sesi lain | check_sql |

**Kriteria selesai (terukur)**
1. Pemeriksa SQL-vs-skema menjadi uji resmi di CI dengan **0** kueri gagal.
2. Alur bahagia setiap modul menjadi uji integrasi resmi dan hijau, termasuk siklus SK
   `DRAFT → PUBLISHED → ACCEPTED → IN_PROGRESS` dan perpanjangan.
3. Setiap endpoint yang menyentuh pekerjaan menegakkan keterlibatan (PM unit / ketua / anggota
   menurut SK) dan organisasi; sumber daya milik organisasi lain → 404 (dok 05, dok 08).
4. Regresi wajib dok 07 §3 yang relevan dengan backend (R2, R3, R4, R6, R7, R9, R10) punya uji.
5. Tidak ada kode servis/repository yang tidak dipakai atau tidak cocok skema.
6. Daftar transaksi prototipe yang belum ada dipetakan ke task berurutan (fase 3 → 7).

---

## Segmen 2 · Pemecahan masalah (pohon isu, MECE)

```
Modul backend belum dapat dipercaya
├── A. Benar terhadap skema
│   ├── A1 Kolom/enum salah di jalur SK ....................... E1, E2
│   ├── A2 Trigger audit tanpa organisasi ..................... E7
│   └── A3 Kode mati tak cocok skema .......................... E9
├── B. Lengkap untuk alur
│   ├── B1 Anggota tim tidak bisa ditambahkan ................. E3
│   └── B2 Transaksi prototipe belum ada (±24) ................ E8
├── C. Aman
│   ├── C1 Kewenangan mengikuti SK tidak ditegakkan ........... E4
│   ├── C2 Rujukan lintas organisasi diterima ................. E5
│   └── C3 Endpoint tanpa izin sama sekali .................... E5
├── D. Patuh aturan bisnis (prototipe = kebenaran)
│   ├── D1 Tanggal belum tiba, status SK tidak dicek .......... E6
│   └── D2 Regresi wajib dok 07 belum punya uji ............... kriteria 4
└── E. Proses
    ├── E1 Tidak ada uji alur per modul ....................... probe hanya lokal
    └── E2 Tidak ada pemeriksaan SQL-vs-skema di CI ........... E2 lolos sampai sekarang
```

---

## Segmen 3 · Prioritas

Skor = dampak × kemungkinan (1–5 masing-masing); urutan juga mengikuti ketergantungan.

| Isu | Dampak | Kemungkinan | Skor | Biaya | Memblokir | Urutan |
|---|---|---|---|---|---|---|
| E2 pemeriksa SQL di CI (E-proses) | 5 | 5 | 25 | S | mencegah E1 terulang | **1** |
| A1 jalur SK rusak | 5 | 5 | 25 | S | seluruh fase 3–7 | **2** |
| B1 anggota tim | 5 | 5 | 25 | M | publish | **3** |
| E1 uji alur per modul | 5 | 4 | 20 | M | pembuktian semua task berikut | **4** |
| C2 lintas organisasi | 5 | 4 | 20 | M | keamanan (RLS mati, T-12) | **5** |
| C1 kewenangan SK | 5 | 4 | 20 | M | aturan inti #1 | **6** |
| C3 endpoint tanpa izin | 4 | 5 | 20 | S | RBAC | **7** |
| D1 aturan tanggal/status | 4 | 5 | 20 | S | regresi R6 | **8** |
| A2 trigger audit | 4 | 3 | 12 | S | pemeliharaan, penghapusan | **9** |
| A3 kode mati | 2 | 5 | 10 | S | kebingungan agen | **10** |
| D2 regresi wajib | 4 | 3 | 12 | M | DoD fase | **11** |
| B2 transaksi yang belum ada | 5 | 5 | 25 | L | MVP | **12** (bergelombang per fase) |

---

## Segmen 4 · Rencana kerja

| Gelombang | Isi | Keluaran yang dapat diperiksa |
|---|---|---|
| **W1 · Alat bukti permanen** | pemeriksa SQL-vs-skema → uji CI; probe → uji alur resmi | CI merah bila kueri tak cocok skema |
| **W2 · Siklus SK hidup** | kolom/enum, anggota tim, tipe daterange | uji alur SK sampai IN_PROGRESS + perpanjangan hijau |
| **W3 · Aman** | penjaga organisasi + keterlibatan + izin | uji lintas organisasi & lintas peran hijau |
| **W4 · Patuh aturan** | tanggal, status SK, regresi wajib | uji R2/R3/R4/R6/R7/R9/R10 hijau |
| **W5 · Bersih** | trigger audit, kode mati, `/work-plans` | 0 kode tak terpakai; kontrak jalur sesuai dok 05 |
| **W6 · Lengkap** | transaksi prototipe yang belum ada, per fase 3 → 7 | cakupan transaksi naik dari ±22/47 |

---

## Segmen 5 · Analisis (bukti & akar masalah)

**Hasil probe per modul** (2026-09-24, org sekali pakai)

| Modul | Langkah lulus | Catatan |
|---|---|---|
| M2 Karyawan & dokumen | 11/11 | berkas → MinIO → dokumen → verifikasi HR tersimpan |
| M3 SK | 5/10 | berhenti di `publish` (E1); accept/start/perpanjangan tidak teruji |
| M4 Lokasi & absensi | 7/7 | tetapi check-in tidak mengecek keterlibatan pada pekerjaan di lokasi itu |
| M5 Laporan harian | 2/2 | tetapi tanggal belum tiba & SK DRAFT diterima (E6) |
| M6 Aset | 5/5 | tetapi alokasi ke SK DRAFT diterima; pengembalian oleh non-ketua diterima |
| M7 Insiden | 2/2 | tetapi tanpa izin & tanpa cek organisasi (E5) |

**5 × mengapa — siklus SK rusak (E1/E2)**
1. Mengapa publish 500? Kueri memakai `work_plan_member.valid_to`, skema memakai `valid_period` (daterange).
2. Mengapa tidak cocok? Router ditulis dari ingatan model data percobaan lama, bukan dari `db/01`.
3. Mengapa lolos? Tidak ada uji yang melewati publish; tidak ada pemeriksaan SQL terhadap skema.
→ **Akar:** tidak ada pemeriksaan otomatis kueri terhadap skema + tidak ada uji alur.

**5 × mengapa — aturan inti tidak ditegakkan (E4/E5)**
1. Mengapa siapa pun bisa melapor insiden pada SK mana pun? Router tidak memeriksa keterlibatan.
2. Mengapa? Fungsi `is_plan_leader/member` ada di DB, tetapi tidak ada penjaga bersama di API.
3. Mengapa tidak terasa? RLS dianggap penjaga terakhir — padahal mati (T-12), dan tidak ada uji peran.
→ **Akar:** tidak ada dependency penjaga "sumber daya milik organisasi & keterlibatan" yang dipakai ulang.

**Pemetaan transaksi prototipe (47)** — ada & perlu verifikasi: CREATE_PLAN, EDIT_DRAFT, PUBLISH,
ACCEPT, START, REQUEST_CHANGE (perpanjangan), APPROVE_CHANGE, CHECK_IN, CHECK_OUT,
EXPLAIN_ATTENDANCE, REVIEW_ATTENDANCE, REPORT_INCIDENT, RESOLVE_INCIDENT, SAVE_REPORT,
SUBMIT_REPORT, RELEASE_ASSET (≈ allocate), RETURN_ASSET, VERIFY_RETURN, OFFBOARD,
UPDATE_EMPLOYEE, UPLOAD_DOCUMENT, VERIFY_DOCUMENT, PROMOTE (≈ assignments). **Belum ada:**
APPEAL, REVISE, CANCEL_PLAN, RESTORE_PLAN, DELETE_PLAN, REQUEST_COMPLETE, APPROVE_COMPLETE,
RETURN_COMPLETE, ACCEPT_CHANGE, REJECT_CHANGE, WITHDRAW_CHANGE, REQUEST_PERSONNEL_CHANGE,
RESERVE_ASSET, CHECK_ASSET, REPORT_OVERTIME, REVIEW_OVERTIME, REVIEW_REPORT, SAVE_WEEKLY,
SUBMIT_WEEKLY, REVIEW_WEEKLY, SAVE_DAY, TOGGLE_TASK, SAVE_ATTACHMENTS, RESTORE_EMPLOYEE.

---

## Segmen 6 · Sintesis

1. **Fondasi sudah benar; kerusakan kini terkonsentrasi.** Modul yang tidak bergantung pada
   SK hampir semuanya bekerja. Yang rusak adalah modul inti — justru yang paling bernilai.
2. **Aman ≠ bekerja.** Endpoint yang lulus alur bahagia belum tentu aman: tanpa penjaga
   organisasi dan keterlibatan, "berhasil" bisa berarti "berhasil menulis data orang lain".
3. **Pola yang sama berulang:** kode ditulis tanpa dicocokkan dengan skema dan tanpa uji alur.
   Karena itu W1 (alat bukti permanen) dikerjakan pertama, sebelum memperbaiki apa pun.
4. **Satu penjaga bersama lebih baik dari 13 perbaikan lokal.** Keterlibatan & organisasi harus
   jadi dependency yang dipakai ulang, bukan `if` yang disalin ke setiap router.

---

## Segmen 7 · Rekomendasi & pencegahan

| # | Pencegahan | Bentuk konkret | Task |
|---|---|---|---|
| Q-1 | Kueri tidak bisa lagi tak cocok skema | uji `test_sql_matches_schema.py` di CI (PREPARE setiap literal SQL) | V-01 |
| Q-2 | Setiap modul punya uji alur | `tests/flows/test_*_flow.py` dari probe | V-02, dan setiap task berikut |
| Q-3 | Penjaga bersama | dependency `plan_access(plan_id, need=…)` + `same_org(...)` → 404 | V-07, V-08 |
| Q-4 | Endpoint tanpa izin terdeteksi | uji asap diperluas: setiap rute non-publik wajib punya dependency izin atau penjaga pekerjaan | V-09 |
| Q-5 | Aturan waktu dari server | semua pemeriksaan tanggal lewat `core/time.py` | V-10 |
| Q-6 | Tidak ada kode mati | uji: setiap modul `services/`/`repositories/` diimpor oleh kode aplikasi | V-14 |

Keputusan yang tetap menunggu pemilik produk (tidak menghalangi W1–W5): T-12 (R3, R4, role
server), format nomor SK (K-14, fase 6).
