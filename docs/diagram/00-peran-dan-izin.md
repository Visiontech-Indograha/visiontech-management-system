# 00. Peran dan izin

Dibuat dari kode per 2026-10-29. Sumber utama: `api/app/core/permissions.py`, `api/app/api/deps.py`,
`api/app/shared/access/access_service.py`, dan pengecekan peran di service tiap modul.

## 1. Dua lapis otorisasi

Setiap permintaan diperiksa dua kali, dan keduanya harus lolos.

| Lapis | Di mana | Isi |
|---|---|---|
| Global (izin) | `require_permission(...)` di `api/app/api/deps.py:172-184` | Gabungan izin dari daftar peran pengguna (`permissions_for_roles`, `api/app/core/permissions.py:151-161`). Akun dengan peran `ADMIN` (legacy) lolos tanpa cek izin (`deps.py:180`). |
| Relasi (SK/tim/divisi) | `check_daily_access` (`access_service.py:71-91`), `check_division_manager` (`access_service.py:94-100`), `_access` di work_completion (`work_completion_service.py:133-146`) | MANAGE = PM/OM divisi jadwal atau SUPER_ADMIN. LEADER = `team.leader_employee_id`. TEAM = ketua atau anggota aktif tim. VIEW = salah satu di atas, atau ADMIN_HR_GA. |

Catatan pemetaan peran:

- `CurrentUser.role` = `roles[0]` (`api/app/api/deps.py:97` dan `:163`). Service membandingkan satu nilai `role` ini, bukan seluruh daftar peran.
- Peran legacy (`RoleCode`, `permissions.py:12-21`): ADMIN, OPS, PM, LEADER, HR, MEMBER, FINANCE, ASSET.
- Peran Master V2 (`SystemRole`, `permissions.py:24-31`): SUPER_ADMIN, OPERATIONAL_MANAGER (OM), PROJECT_MANAGER (PM), TEAM_LEADER (ketua), ADMIN_HR_GA (HR), EMPLOYEE (anggota).
- LEADER dan MEMBER legacy tidak memberi izin global (`permissions.py:124-125`). Kewenangan ketua dan anggota berasal dari relasi tim pada jadwal.
- Akun tanpa baris `user_role` mendapat label `field` dan hanya izin dasar (`permissions.py:35`, `:155-156`).

## 2. Izin global per peran

Izin dasar untuk semua akun login: `VIEW_USERS`, `VIEW_DOCUMENTS`, `UPLOAD_DOCUMENTS` (`permissions.py:104`).

| Peran | Setara | Izin tambahan utama | Sumber |
|---|---|---|---|
| SUPER_ADMIN | (Master V2) | Semua izin termasuk `DELETE_ANY` | `permissions.py:130` |
| ADMIN | legacy | Semua kecuali `DELETE_ANY`. Route `require_permission` tetap meloloskan (lihat temuan T1) | `permissions.py:108`, `deps.py:180` |
| OPERATIONAL_MANAGER (OM) | Master V2 | CREATE_PLAN, PUBLISH_PLAN, REVIEW_OVERTIME, VIEW_ALL_ATTENDANCE, REVIEW_ATTENDANCE, VIEW_TIMELINE, VIEW_AUDIT, VIEW_TEAMS, VIEW_MESS, REVIEW_MESS, VIEW_OFFBOARDING, MANAGE_SITES, MANAGE_DIVISIONS | `permissions.py:132-136` |
| PROJECT_MANAGER (PM) | Master V2 | CREATE_PLAN, PUBLISH_PLAN, VIEW_TIMELINE, REVIEW_ATTENDANCE, MANAGE_TEAMS, VIEW_TEAMS, VIEW_MESS, REVIEW_MESS, VIEW_OFFBOARDING, MANAGE_IMAGE_REQUIREMENTS. Tidak punya VIEW_ALL_ATTENDANCE. | `permissions.py:138-141` |
| PM (legacy) | legacy | CREATE_PLAN, PUBLISH_PLAN, VIEW_TIMELINE, REVIEW_ATTENDANCE, MANAGE_SITES | `permissions.py:113-115` |
| ADMIN_HR_GA (HR) | Master V2 | MANAGE_USERS, VERIFY_DOCUMENTS, MANAGE_EMPLOYEE_DOCUMENTS, MANAGE_ASSETS, MANAGE_MESS, VIEW_MESS, REVIEW_MESS, MANAGE_OFFBOARDING, VIEW_OFFBOARDING, VIEW_TEAMS | `permissions.py:142-145` |
| HR | legacy | MANAGE_USERS, VERIFY_DOCUMENTS, MANAGE_EMPLOYEE_DOCUMENTS | `permissions.py:116-118` |
| FINANCE | legacy | VIEW_ALL_ATTENDANCE, REVIEW_ATTENDANCE, EXPORT_ATTENDANCE, REVIEW_OVERTIME, MANAGE_SITES. Tidak punya CREATE_PLAN. | `permissions.py:119-122` |
| OPS | legacy | CREATE_PLAN, PUBLISH_PLAN, REVIEW_OVERTIME, VIEW_TIMELINE, VIEW_AUDIT, VIEW_ALL_ATTENDANCE, REVIEW_ATTENDANCE | `permissions.py:109-112` |
| ASSET | legacy | MANAGE_ASSETS | `permissions.py:123` |
| TEAM_LEADER (ketua) | Master V2 | Tidak ada (hanya izin dasar). Kewenangan ketua dari relasi tim jadwal. | `permissions.py:146` |
| EMPLOYEE (anggota) | Master V2 | Tidak ada (hanya izin dasar). | `permissions.py:147` |
| LEADER, MEMBER | legacy | Tidak ada. | `permissions.py:124-125` |

## 3. Matriks aksi work x peran

Keterangan sel:

- **Ya**: diizinkan bila syarat status dan relasi terpenuhi.
- **Relasi**: diizinkan hanya bila pengguna punya relasi (ketua tim jadwal, anggota tim, PM/OM divisi, PM order).
- **Tidak**: ditolak (403 atau 404 sesuai kasus).
- Nama peran di kolom mengikuti Master V2. Kolom ADMIN dan OPS mewakili legacy.

Kode kesalahan: 401 tanpa token. 403 izin atau relasi kurang. 404 jadwal atau order tidak terlihat (tidak dibocorkan). 409 status tidak sesuai. 422 validasi atau foto wajib kurang.

| # | Aksi | Route (berkas:baris) | SUPER_ADMIN | ADMIN | OM | PM | HR | FINANCE | OPS | ASSET | Ketua | Anggota | Syarat service (sumber) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 1 | Kelola klien | `client_route.py:16` (CREATE_PLAN) | Ya | Ya | Ya | Ya | Tidak | Tidak | Ya | Tidak | Tidak | Tidak | Tidak ada cek divisi (T16) |
| 2 | Kelola proyek | `project_route.py:16` (CREATE_PLAN) | Ya | Ya | Ya | Ya | Tidak | Tidak | Ya | Tidak | Tidak | Tidak | Proyek tertutup hanya boleh ubah status (`project_service.py:64-66`) |
| 3 | Kelola jenis pekerjaan, foto, material | `work_type_route.py:28,61,133-170` (CREATE_PLAN) | Ya | Ya | Ya (divisinya) | Ya (divisinya) | Tidak | Tidak | Ya | Tidak | Tidak | Tidak | PM hanya divisi sendiri (`work_type_route.py:68-70`, `work_type_service.py:62-69`) |
| 4 | Buat jadwal harian (DRAFT) | `daily_plan_route.py:82` | Ya | Tidak | Relasi | Relasi | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | `check_division_manager` (`daily_plan_service.py:140-141`, `access_service.py:94-100`) |
| 5 | Ubah, hapus, salin jadwal | `daily_plan_route.py:103-122` | Ya | Tidak | Relasi | Relasi | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | MANAGE + status DRAFT/SUBMITTED (`daily_plan_service.py:152-154`, `:200-204`) |
| 6 | Submit jadwal | `daily_plan_route.py:131` | Ya | Tidak | Relasi | Relasi | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | MANAGE + DRAFT (`daily_plan_service.py:215-218`) |
| 7 | Setujui jadwal (tunggal atau matriks) | `daily_plan_route.py:89,138` | Ya | Tidak | Relasi | Relasi | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | MANAGE + DRAFT/SUBMITTED + tanggal tidak lampau (`daily_plan_service.py:222-229`). Matriks melewati yang gagal (`:231-240`). |
| 8 | Tolak jadwal (kembali DRAFT, dengan alasan) | `daily_plan_route.py:145` | Ya | Tidak | Relasi | Relasi | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | MANAGE + SUBMITTED/APPROVED (`daily_plan_service.py:242-246`) |
| 9 | Mulai hari kerja (APPROVED to ONGOING) | `daily_plan_route.py:152` | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Relasi | Tidak | LEADER + APPROVED + tanggal tidak melewati hari ini (`daily_plan_service.py:249-255`) |
| 10 | Selesaikan hari kerja (ONGOING to COMPLETED) | `daily_plan_route.py:159` | Ya | Tidak | Relasi | Relasi | Tidak | Tidak | Tidak | Tidak | Relasi | Tidak | Ketua atau MANAGE + ONGOING + laporan harian ada, bila tidak 422 (`daily_plan_service.py:257-269`) |
| 11 | Isi laporan harian | `daily_plan_route.py:166` | Ya | Tidak | Relasi | Relasi | Tidak | Tidak | Tidak | Tidak | Relasi | Tidak | Ketua atau MANAGE + APPROVED/ONGOING/COMPLETED (`daily_plan_service.py:271-280`) |
| 12 | Lihat jadwal (daftar dan detail) | `daily_plan_route.py:67,96` | Ya | Ya | Relasi | Relasi | Ya (logistik) | Tidak | Tidak | Tidak | Relasi (dirilis) | Relasi (dirilis) | VIEW (`access_service.py:82`). Status dirilis: APPROVED, ONGOING, COMPLETED (`access_service.py:31`). |
| 13 | Kelola item pekerjaan (buat, ubah, hapus) | `plan_item_route.py:47,61,68` (CREATE_PLAN) | Ya | Tidak | Relasi | Relasi | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | MANAGE. Buat hanya DRAFT/SUBMITTED. Ubah dan hapus juga APPROVED/ONGOING (`plan_item_service.py:40-41`, `:115-117`, `:124-126`, `:149-151`) |
| 14 | Update progres item dan foto | `plan_item_route.py:75` (LOGIN) | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Relasi | Relasi | TEAM (anggota atau ketua) + ONGOING (`plan_item_service.py:164-166`) |
| 15 | Minta pindah hari | `plan_item_route.py:82` (LOGIN) | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Relasi | Tidak | LEADER + APPROVED/ONGOING (`plan_item_service.py:194-196`) |
| 16 | Putuskan pindah hari (setujui atau tolak, atau proaktif) | `plan_item_route.py:89` (CREATE_PLAN) | Ya | Tidak | Relasi | Relasi | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | MANAGE (`plan_item_service.py:204-205`). Tolak hanya saat WAITING_PM (`:213-214`). |
| 17 | Isi survei (titik, material, laporan) | `survey_route.py:51-107` (LOGIN) | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Relasi | Tidak | LEADER + jadwal APPROVED/ONGOING + survei DRAFT (`survey_service.py:76-83`). BoM saat PM meninjau juga boleh (`:275`). |
| 18 | Kirim survei | `survey_route.py:114` (LOGIN) | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Relasi | Tidak | `_editable_task` + min 1 titik + foto slot lengkap (`survey_service.py:251-266`) |
| 19 | Tinjau survei (setujui atau kembalikan) | `survey_route.py:121` (CREATE_PLAN) | Ya | Tidak | Relasi | Relasi | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | MANAGE + SUBMITTED (`survey_service.py:325-328`) |
| 20 | Buat rencana dari survei | `survey_route.py:128` (CREATE_PLAN) | Ya | Tidak | Relasi | Relasi | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | MANAGE + survei APPROVED (`survey_service.py:335-340`) |
| 21 | Ajukan koreksi laporan | `daily_correction_route.py:41` (LOGIN) | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Relasi | Tidak | LEADER + jadwal COMPLETED, tak ada koreksi terbuka (`daily_correction_service.py:37-43`) |
| 22 | Putuskan koreksi (setujui, tolak, terima, kembalikan) | `daily_correction_route.py:50` (LOGIN) | Ya | Tidak | Relasi | Relasi | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | MANAGE (`daily_correction_service.py:69`) |
| 23 | Kirim revisi koreksi | `daily_correction_route.py:59` (LOGIN) | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Relasi | Tidak | LEADER + REVISING + laporan ada (`daily_correction_service.py:101-107`) |
| 24 | Ajukan lembur | `overtime_route.py:26` (LOGIN) | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Relasi | Relasi | TEAM + ONGOING, 0 < jam <= 12, alasan wajib (`overtime_service.py:50-60`) |
| 25 | Putuskan lembur | `overtime_route.py:59` (LOGIN) | Ya (tanpa jadwal) | Tidak | Relasi | Relasi | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Ber-jadwal: MANAGE. Tanpa jadwal: admin saja. Pengaju tidak boleh memutuskan sendiri (`overtime_service.py:72-84`) |
| 26 | Rekap lembur | `overtime_recap_route.py` | Ya | Ya | Ya | Relasi (PM) | Tidak | Ya | Ya | Tidak | Tidak | Tidak | REVIEW_OVERTIME atau admin, atau peran PM (`overtime_service.py:111-116`). Cakupan PM perlu verifikasi (T20). |
| 27 | Absen masuk dan pulang | `attendance_route.py:92,105` (LOGIN) | Ya | Ya | Ya | Ya | Ya | Ya | Ya | Ya | Ya (HP) | Ya (HP) | Kanal sesuai mode: FIELD ke MOBILE, OFFICE ke WEB (`attendance_session_service.py:79-107`) |
| 28 | Tinjau absensi NEEDS_REVIEW | `attendance_route.py:130` (REVIEW_ATTENDANCE) | Ya | Tidak | Ya | Ya | Tidak | Tidak* | Tidak* | Tidak | Tidak | Tidak | `can_review` (SQL: SUPER_ADMIN, OM, PM, ADMIN_HR_GA; bukan diri sendiri). *Lihat T3. |
| 29 | Lihat semua absensi | `attendance_route.py:37` | Ya | Ya | Ya | Relasi [VERIFIKASI] | Tidak | Ya | Ya | Tidak | Tidak | Tidak | VIEW_ALL_ATTENDANCE (`permissions.py:60`) |
| 30 | Ekspor absensi CSV | `attendance_route.py:169` (EXPORT_ATTENDANCE) | Ya | Ya | Tidak | Tidak | Tidak | Ya | Tidak | Tidak | Tidak | Tidak | EXPORT_ATTENDANCE |
| 31 | Hapus absensi | `attendance_route.py:148,158` (DELETE_ANY) | Ya | Tidak* | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | *Legacy ADMIN lolos lewat bypass (T1). |
| 32 | Buat order klien | `work_completion_route.py:63` (CREATE_PLAN) | Ya | Tidak | Ya | Ya (atas nama sendiri) | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Peran wajib SUPER_ADMIN, OM, atau PM (`work_completion_service.py:183-189`). PM hanya pm_id diri sendiri (`:185-189`). |
| 33 | Ubah order, status, BoM, revisi, hapus order | `work_completion_route.py:110-259` (CREATE_PLAN) | Ya | Tidak | Relasi | Relasi | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | `_access` manage (PM order atau PM/OM divisi, SUPER_ADMIN) (`work_completion_service.py:143-144`). Terkunci setelah PM tanda tangan (`:148-153`). Hapus ditolak bila ketua sudah tanda tangan kecuali SUPER_ADMIN (`:240-241`). |
| 34 | Lihat order (detail, daftar, revisi) | `work_completion_route.py:39,77,259` (LOGIN) | Ya | Tidak | Relasi | Relasi | Ya (HR) | Tidak | Tidak | Tidak | Relasi (tim) | Relasi (tim) | `visible` = manage, ADMIN_HR_GA, atau anggota tim berjadwal (`work_completion_service.py:138-142`). Tak terlihat: 404. |
| 35 | ACC klien (MENUNGGU_ACC, DITERIMA, DITOLAK_REWORK) | `work_completion_route.py:231` (CREATE_PLAN) | Ya | Tidak | Relasi | Relasi | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | manage (`work_completion_service.py:406`) |
| 36 | Tanda tangan BAST ketua | `work_completion_route.py:147` (LOGIN) | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | Relasi (peran TEAM_LEADER + anggota tim order) | Tidak | `work_completion_service.py:288-293`. Peran FIELD_ROLES ditolak (`:298-299`). |
| 37 | Tanda tangan BAST PM/OM (mengunci order) | `work_completion_route.py:147` (LOGIN) | Ya | Tidak | Relasi | Relasi | Tidak | Tidak | Tidak | Tidak | Tidak | Tidak | manage + ketua sudah tanda tangan (409 `LEADER_SIGNATURE_REQUIRED`, `work_completion_service.py:301-304`) |
| 38 | Ekspor dokumen order (BAST docx, survei docx, BAST PDF, BoQ, slide) | `export_route.py:36` (LOGIN) | Ya | Ya | Ya | Ya | Ya (HR) | Tidak | Tidak | Tidak | Relasi (tim) | Relasi (tim) | Lewat `get_order_detail` (visibilitas). BAST PDF hanya setelah PM tanda tangan (`export_service.py:228-229`). |
| 39 | Ekspor periodik (rekap xlsx dan slide pptx) | `export_route.py:105,126` (CREATE_PLAN) | Ya | Ya | Ya | Ya | Tidak | Tidak | Ya | Tidak | Tidak | Tidak | Rentang maks 31 hari (`export_service.py:250`) |
| 40 | Ekspor laporan survei | `export_route.py:85,47` (LOGIN) | Ya | Ya | Relasi | Relasi | Tidak | Tidak | Tidak | Tidak | Relasi (ketua) | Tidak | Survei harus sudah dikirim (`export_service.py:118-121`) |
| 41 | Logo kop survei | `export_route.py:58,64` (CREATE_PLAN) | Ya | Ya | Ya | Ya | Tidak | Tidak | Ya | Tidak | Tidak | Tidak | Izin CREATE_PLAN (`export_route.py:33`) |
| 42 | Verifikasi publik BAST (QR) | `work_completion_route.py:276` (tanpa login) | Publik | Publik | Publik | Publik | Publik | Publik | Publik | Publik | Publik | Publik | Wajib sidik SHA-256 64 hex. Sidik salah atau belum disahkan: 404 (`work_completion_service.py:338-345`) |
| 43 | Kelola peran, pengguna, dokumen karyawan | modul `employees`, `accounts` | Ya | Ya | Tidak | Tidak | Ya | Tidak | Tidak | Tidak | Tidak | Tidak | `MANAGE_USERS` (lihat bagian 2). Di luar cakupan dokumen alur work ini. |

## 4. Catatan temuan izin

Setiap item berikut perlu dikonfirmasi pemilik kode. Nomor T mengacu ke daftar di `README.md`.

- **T1 (DELETE_ANY).** `require_permission` membebaskan akun ber-peran `ADMIN` dari semua pengecekan (`api/app/api/deps.py:180`). `permissions.py:108` sengaja mengecualikan `DELETE_ANY` dari ADMIN, dan komentar di `permissions.py:42` menyatakan hapus permanen hanya untuk SUPER_ADMIN. Akibatnya ADMIN bisa menghapus absensi (`attendance_route.py:148,158`). [VERIFIKASI] apakah bypass ini disengaja.
- **T2 (ADMIN di jadwal).** Akun ADMIN lolos `_PLANNER` karena bypass, tetapi `is_admin` hanya bernilai SUPER_ADMIN (`access_service.py:67-68`). Akibatnya approve, submit, dan lainnya ditolak 403 untuk ADMIN. [VERIFIKASI] apakah ADMIN memang tidak boleh memutuskan jadwal.
- **T3 (tinjau absensi).** Izin `REVIEW_ATTENDANCE` dimiliki FINANCE dan OPS legacy (`permissions.py:111`, `:120`), tetapi SQL `can_review` hanya mengenali `system_role` SUPER_ADMIN, OPERATIONAL_MANAGER, PROJECT_MANAGER, dan ADMIN_HR_GA (`attendance_session_repository.py:599-611`). Komentar R-33 di `review_attendance` menyebut Finance dan OPS. [VERIFIKASI].
- **T13 (multi-peran).** `CurrentUser.role` = `roles[0]`. Jika akun punya lebih dari satu peran, hasil cek `role ==` bergantung urutan peran. [VERIFIKASI] urutan peran di token.
- **Ketua di dua tempat.** Ketua jadwal harian dikenali dari relasi tim (`access_service.py:44-87`). Ketua BAST dikenali dari peran `TEAM_LEADER` plus `on_team` (`work_completion_service.py:288`). Akun berperan `EMPLOYEE` yang menjadi ketua tim tidak bisa menandatangani BAST. [VERIFIKASI].
- **T16 (proyek dan klien).** Tidak ada cek divisi atau kepemilikan pada ubah dan hapus proyek maupun klien. Siapa pun ber-CREATE_PLAN bisa mengubah proyek divisi lain. [VERIFIKASI] apakah disengaja.
- **T20 (rekap lembur PM).** Untuk PM, `recap` memanggil `repo.recap(month, user.employee_id)` (`overtime_service.py:111-115`). Cakupan yang dihasilkan (divisi atau hanya diri sendiri) belum dipastikan dari kode yang dibaca. [VERIFIKASI].
