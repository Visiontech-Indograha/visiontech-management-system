# Laporan Bukti — Foto Profil & Dokumen Karyawan

Tanggal: 12 Oktober 2026 · Worktree: `C:/Users/ageng/visiontect-vms/vms-update`
Commit: `77e710dc` — *feat(files): foto profil & dokumen tampil di web dan HP*

---

## 1. Masalah yang dilaporkan

> "apinya juga saya cek tidak ada yang mengembalikan url image sama sekali dan documen juga belum lengkap"

Tiga akar masalah yang ditemukan:

1. **`<img src="/api/v1/files/{id}">` tidak pernah bisa bekerja.**
   Berkas hanya dilayani API setelah otorisasi (V-17), dan browser **tidak**
   menyertakan header `Authorization` pada permintaan gambar. Jadi walau URL-nya
   benar, server selalu menjawab 404.
2. **Route `GET /files/{file_id}` tidak ada.** Yang tersedia hanya
   `/files/{file_id}/url` yang mengembalikan JSON, bukan gambar.
3. **`/url` selalu menunjuk varian webp** (`{org}/{file_id}_view.webp`), padahal
   berkas hasil impor massal disimpan di `file_object.storage_key`
   (`.../documents/.../xxx.pdf`). Akibatnya URL dibuat untuk objek yang tidak ada
   → 404 dari MinIO.

Ditambah: **`check_file_access` tidak mengenali foto profil** — foto hanya
tertaut lewat `employee.photo_file_id`, tidak di tabel mana pun yang diperiksa
(`employee_document`, `attendance`, `report_evidence`), sehingga selalu 404.

---

## 2. Perbaikan

### API
| Berkas | Perubahan |
|---|---|
| `app/modules/system/routes/files_route.py` | Tambah `GET /files/{file_id}` |
| `app/modules/system/controllers/files_controller.py` | `handle_get_file_content()` (byte langsung) + `handle_get_file_url()` memilih objek yang benar-benar ada |
| `app/api/v1/endpoints/files.py` | Sama (jalur endpoint alternatif) |
| `app/crud/crud_file_access.py` | Kenali `profile_photo` & `own_profile_photo` |
| `app/services/access_service.py` | Izin foto profil: pemilik & pemegang `view:users` |
| `app/core/storage.py` | `object_exists()` — cek objek tanpa unduh |
| `app/modules/auth/schemas/auth_profile_schema.py` | `photo_file_id` di `/auth/me` |
| `app/modules/auth/controllers/auth_profile_controller.py` | Query `photo_file_id` |

### Web
| Berkas | Perubahan |
|---|---|
| `src/hooks/useFileUrl.ts` (baru) | Presigned URL via axios (Authorization ikut terkirim) |
| `src/components/organisms/account/AccountSummaryCard.tsx` | Foto profil di **Akun & keamanan** |
| `src/components/organisms/directory/EmployeeProfileCard.tsx` | Foto profil di detail karyawan |
| `src/lib/apiTypes.ts` | `photo_file_id` di `UserMeResponse` |

### Mobile
| Berkas | Perubahan |
|---|---|
| `lib/features/auth/auth_state.dart` | `AuthUser.photoFileId` |
| `lib/features/profile/profile_screen.dart` | Avatar bulat pakai foto profil (fallback inisial) |

---

## 3. Bukti pengujian

### 3.1 Foto profil — 31/31 dapat diakses

```
GET /api/v1/auth/me          → photo_file_id: 01a12e49-5089-7c74-9378-e868168e5321
GET /api/v1/files/{id}/url   → HTTP 200, presigned URL ke storage_key yang BENAR
GET /api/v1/files/{id}       → HTTP 200, 82.955 byte, image/jpeg
Unduh presigned URL          → 82.955 byte, JPEG magic ffd8 ✔
Unduh via API                → 82.955 byte, JPEG magic ffd8 ✔
```

Verifikasi seluruh karyawan (via API, akun HR):
```
FOTO profil OK : 31/31 karyawan berfoto
```

### 3.2 Objek di MinIO — 0 hilang

```
Objek dokumen di DB: 83 | hilang di MinIO: 0
Objek profil di DB: 31 | hilang di MinIO: 0
```

### 3.3 Dokumen — 82/83 berkas terpetakan

```
baris_dokumen | file_unik | karyawan_punya_dok | karyawan_punya_foto
            82 |        82 |                 25 |                 31
```

Verifikasi akses tiap berkas (akun HR, `dara@visiontech.id`):
```
TOTAL dokumen terlihat oleh HR: 74  → seluruhnya dapat diakses (74/74)
```
(74 saat itu; setelah 8 berkas generik diidentifikasi menjadi **82**)

Dokumen Ramadani (sebagai pemilik):
```
KTP      PENDING  → 120.129 byte  ✔
BPJS TK  PENDING  →  71.254 byte  ✔
KK       PENDING  →  98.078 byte  ✔
```

### 3.4 Rincian 83 berkas di folder `uploads/`

| Folder | Jumlah |
|---|---|
| dokumen_pribadi | 28 |
| kontrak | 16 |
| mcu | 21 |
| sertifikat | 9 |
| sim | 9 |
| **TOTAL** | **83** |

**82 dipakai, 1 dibuang** (`Screenshot_1.png` — sampah, dikonfirmasi pemilik).

8 berkas bernama generik diidentifikasi dengan **membuka isinya**:

| Berkas | Pemilik sebenarnya | Jenis |
|---|---|---|
| `KTP_Ucok.pdf` | RUSYIDI HALOMOAN SIREGAR | KTP |
| `PKWT_2025.pdf` | RAIMON ALBERT (Remon) | KONTRAK |
| `MCU_Juli_2025.pdf` | MHD PINTO NURHADI | MCU |
| `MCU_Agus_2025.pdf` | **RAMADANI** (bukan Agus) | MCU |
| `09.BPJS_Kesehatan_Dani_Depan.JPG` | **RAMADANI** (bukan Dani) | BPJS KES |
| `SIM_A_New.JPG` | SYAFRUDDINI | SIM A |
| `SIM_A_NEW.pdf` | DONI EFENDI | SIM A |
| `DONI_EFENDI.pdf` | DONI EFENDI (MCU lama 2024) | MCU 2024 |

### 3.5 Hasil test otomatis

| Platform | Perintah | Hasil |
|---|---|---|
| Web | `npx vitest run` | **175/175 PASS** (29 berkas) |
| Mobile | `flutter test` | **116/116 PASS** |
| Mobile | `flutter analyze` | **No issues found** |
| API | `pytest tests/ -q` | **949 passed, 1 skipped, 3 failed** |

3 kegagalan API — **pre-existing, bukan dari perubahan ini**:
1. `test_runtime_role_can_use_every_table_but_no_partition_directly` — partisi
   `attendance_*`/`audit_event_*` hasil `pg_dump` tidak membawa GRANT.
2. `test_database_functions_run_as_owner_except_pure_context_readers` — fungsi
   `personnel_conflict` & `employee_busy_dates` belum `SECURITY DEFINER`
   **di produksi juga** (sudah dicek langsung ke `visiontech_db`).
3. `test_matching_works_under_rls_as_the_app_role` — mengandaikan DB uji bersih
   (mengharap 3 baris `face_enrollment`), sedangkan DB lokal memuat 42 karyawan
   dari produksi.

### 3.6 Aplikasi lokal berjalan

```
API   http://localhost:8000/health  → {"status":"ok"}
Vite  http://localhost:5173/        → HTTP 200
Proxy http://localhost:5173/api/v1/auth/me → HTTP 401 (benar, butuh auth)
```

---

## 4. Akun uji

6 akun baru, kata sandi `Vms-o0YxZtMWfO9a`:

| Email | Tipe | Login terverifikasi |
|---|---|---|
| rafael@visiontech.id | Kantor (OFFICE) | Web ✔ |
| nendra@visiontech.id | Lapangan (FIELD) | HP ✔ |
| riky@visiontech.id | Lapangan (FIELD) | HP ✔ |
| sirajuddin@visiontech.id | Lapangan (FIELD) | HP ✔ |
| noberly@visiontech.id | Lapangan (FIELD) | HP ✔ |
| heru@visiontech.id | Lapangan (FIELD) | HP ✔ (akun lama, sandi disetel ulang) |

Catatan: akun FIELD **sengaja ditolak** saat login web dengan pesan
"Silakan gunakan aplikasi HP Visiontech" — itu aturan R-33, bukan kegagalan.

Akun uji lain (DB lokal): `ramadani@visiontech.id`, `dara@visiontech.id` (HR),
`ageng@visiontech.id` (ADMIN) — sandi `password123`.

---

## 5. Catatan penting

- **`photo_file_id` sudah ada di DB** sejak migration `0037_employee_photo.py`:
  kolom `uuid` di `vms.employee` dengan FK ke `vms.file_object.id`. Path berkas
  disimpan di `file_object.storage_key`, sesuai arsitektur storage aplikasi.
- **`/auth/me` sekarang mengembalikan `photo_file_id`.** Sebelumnya tidak —
  inilah sebabnya web/HP tidak punya cara menemukan foto.
- **`Screenshot_1.png` dibuang** dari pemetaan sesuai konfirmasi pemilik.
